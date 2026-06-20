#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from websocket import WebSocketTimeoutException, create_connection
except ImportError:
    print(
        "Missing dependency: websocket-client\n"
        "Install with: pip install -r test/requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


TEST_DIR = Path(__file__).resolve().parent
ROOT_DIR = TEST_DIR.parent
DEFAULT_OUTPUT = TEST_DIR / "output"
CHROMIUM_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
)


@dataclass
class RunConfig:
    mode: str
    cycles: int
    interval_ms: int
    transition_ms: int
    log_every: int
    snapshot_every: int
    snapshots: str
    port: int
    width: int
    height: int
    timeout_s: int
    output_dir: Path
    chromium: str


@dataclass
class MemorySample:
    timestamp: float
    total_rss_kb: int
    renderer_rss_kb: int
    gpu_rss_kb: int
    other_rss_kb: int
    pids: dict[str, int] = field(default_factory=dict)


class CdpSession:
    def __init__(self, ws_url: str) -> None:
        self.ws = create_connection(ws_url, timeout=10)
        self.ws.settimeout(1.0)
        self._id = 0
        self._pending: dict[int, dict[str, Any]] = {}
        self.console_logs: list[dict[str, Any]] = []
        self.memlogs: list[dict[str, Any]] = []
        self.test_done: dict[str, Any] | None = None
        self._snapshot_chunks: list[str] = []
        self._snapshot_done = threading.Event()
        self._last_chunk_at = 0.0
        self._listener = threading.Thread(target=self._listen, daemon=True)
        self._listener.start()

    def evaluate(self, expression: str) -> Any:
        result = self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
            wait=True,
        )
        if result is None:
            return None
        if isinstance(result, dict) and "__error__" in result:
            return None
        if result.get("exceptionDetails"):
            return None
        value = result.get("result", {}).get("value")
        if isinstance(value, str) and value.startswith("{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def send(self, method: str, params: dict[str, Any] | None = None, wait: bool = False) -> Any:
        msg_id = self._next_id()
        payload = {"id": msg_id, "method": method}
        if params:
            payload["params"] = params
        self.ws.send(json.dumps(payload))
        if not wait:
            return None
        deadline = time.time() + 60
        while time.time() < deadline:
            if msg_id in self._pending:
                return self._pending.pop(msg_id)
            time.sleep(0.01)
        raise TimeoutError(f"CDP call timed out: {method}")

    def _listen(self) -> None:
        while True:
            try:
                raw = self.ws.recv()
            except WebSocketTimeoutException:
                continue
            except Exception:
                break

            if not raw:
                break

            message = json.loads(raw)

            if "id" in message:
                if "result" in message:
                    self._pending[message["id"]] = message["result"]
                elif "error" in message:
                    self._pending[message["id"]] = {"__error__": message["error"]}
                continue

            method = message.get("method")
            params = message.get("params", {})

            if method == "Runtime.consoleAPICalled":
                self._handle_console(params)
            elif method == "HeapProfiler.addHeapSnapshotChunk":
                self._snapshot_chunks.append(params.get("chunk", ""))
                self._last_chunk_at = time.time()
            elif method == "HeapProfiler.reportHeapSnapshotProgress":
                if params.get("finished"):
                    self._snapshot_done.set()

    def _handle_console(self, params: dict[str, Any]) -> None:
        args = params.get("args", [])
        text_parts: list[str] = []
        for arg in args:
            if "value" in arg:
                text_parts.append(str(arg["value"]))
            elif "description" in arg:
                text_parts.append(str(arg["description"]))
        text = " ".join(text_parts).strip()
        entry = {
            "timestamp": time.time(),
            "type": params.get("type"),
            "text": text,
        }
        self.console_logs.append(entry)

        if text.startswith("MEMLOG:"):
            try:
                self.memlogs.append(json.loads(text[len("MEMLOG:") :]))
            except json.JSONDecodeError:
                pass
        elif text.startswith("TEST_DONE:"):
            try:
                self.test_done = json.loads(text[len("TEST_DONE:") :])
            except json.JSONDecodeError:
                pass

    def enable_runtime(self) -> None:
        self.send("Runtime.enable")
        self.send("Log.enable")

    def take_heap_snapshot(self, output_path: Path) -> None:
        self._snapshot_chunks = []
        self._snapshot_done.clear()
        self._last_chunk_at = 0.0
        self.send("HeapProfiler.enable")
        self.send("HeapProfiler.takeHeapSnapshot", {"reportProgress": False})

        deadline = time.time() + 300
        while time.time() < deadline:
            if self._snapshot_done.is_set():
                break
            if self._snapshot_chunks and self._last_chunk_at and time.time() - self._last_chunk_at > 5:
                break
            time.sleep(0.1)

        if not self._snapshot_chunks:
            raise TimeoutError("Heap snapshot produced no data")

        output_path.write_text("".join(self._snapshot_chunks), encoding="utf-8")

    def collect_memory_dump(self) -> dict[str, Any]:
        self.send("Memory.enable")
        self.send("Performance.enable")
        dom_counters = self.send("Memory.getDOMCounters", wait=True) or {}
        metrics = self.send("Performance.getMetrics", wait=True) or {}
        page_state = self.evaluate("JSON.stringify(window.__TEST_STATE__ || null)")
        page_memory = self.evaluate(
            "JSON.stringify({"
            "memory: performance.memory || null,"
            "images: ["
            "document.getElementById('firstImage')?.currentSrc,"
            "document.getElementById('secondImage')?.currentSrc"
            "]"
            "})"
        )
        return {
            "dom_counters": dom_counters,
            "performance_metrics": metrics,
            "page_state": page_state,
            "page_memory": page_memory,
        }


def find_chromium(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in CHROMIUM_CANDIDATES:
        path = subprocess.run(["which", candidate], capture_output=True, text=True)
        if path.returncode == 0:
            return path.stdout.strip()
    raise FileNotFoundError("Chromium not found. Install chromium or pass --chromium.")


def child_pids(root_pid: int) -> list[int]:
    result = {root_pid}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        status_file = entry / "status"
        try:
            for line in status_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("PPid:"):
                    ppid = int(line.split()[1])
                    if ppid in result:
                        result.add(int(entry.name))
                    break
        except OSError:
            continue

    changed = True
    while changed:
        changed = False
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            if pid in result:
                continue
            status_file = entry / "status"
            try:
                for line in status_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.startswith("PPid:"):
                        if int(line.split()[1]) in result:
                            result.add(pid)
                            changed = True
                        break
            except OSError:
                continue
    return sorted(result)


def read_rss_kb(pid: int) -> int:
    try:
        with open(f"/proc/{pid}/status", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        return 0
    return 0


def read_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\0", b" ").decode("utf-8", errors="ignore").strip()
    except OSError:
        return ""


def classify_pid(cmdline: str) -> str:
    lowered = cmdline.lower()
    if "--type=renderer" in lowered:
        return "renderer"
    if "--type=gpu-process" in lowered:
        return "gpu"
    return "other"


def sample_memory(root_pid: int) -> MemorySample:
    totals = {"renderer": 0, "gpu": 0, "other": 0}
    pid_map: dict[str, int] = {}

    for pid in child_pids(root_pid):
        rss = read_rss_kb(pid)
        if rss == 0:
            continue
        role = classify_pid(read_cmdline(pid))
        totals[role] += rss
        pid_map[f"{role}:{pid}"] = rss

    total = sum(totals.values())
    return MemorySample(
        timestamp=time.time(),
        total_rss_kb=total,
        renderer_rss_kb=totals["renderer"],
        gpu_rss_kb=totals["gpu"],
        other_rss_kb=totals["other"],
        pids=pid_map,
    )


def wait_for_cdp(port: int, timeout_s: float = 20.0) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_s
    url = f"http://127.0.0.1:{port}/json/list"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(0.2)
    raise TimeoutError(f"CDP endpoint not ready on port {port}")


def pick_page_target(targets: list[dict[str, Any]]) -> dict[str, Any]:
    for target in targets:
        if target.get("type") == "page" and "memory-test.html" in target.get("url", ""):
            return target
    for target in targets:
        if target.get("type") == "page":
            return target
    raise RuntimeError("No CDP page target found")


def build_test_url(config: RunConfig) -> str:
    html = (TEST_DIR / "memory-test.html").resolve()
    query = (
        f"mode={config.mode}"
        f"&cycles={config.cycles}"
        f"&interval={config.interval_ms}"
        f"&transition={config.transition_ms}"
        f"&logEvery={config.log_every}"
    )
    return f"{html.as_uri()}?{query}"


def build_chromium_command(config: RunConfig, user_data_dir: Path, test_url: str) -> list[str]:
    qtwebengine_flags = os.environ.get(
        "QTWEBENGINE_CHROMIUM_FLAGS",
        "--aggressive-cache-discard --disk-cache-size=52428800",
    ).split()

    command = [
        config.chromium,
        f"--user-data-dir={user_data_dir}",
        f"--remote-debugging-port={config.port}",
        "--remote-allow-origins=*",
        f"--window-size={config.width},{config.height}",
        "--force-device-scale-factor=1",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-sync",
        "--disable-translate",
        "--disable-background-networking",
        "--disable-component-update",
        "--enable-precise-memory-info",
        "--autoplay-policy=no-user-gesture-required",
        f"--app={test_url}",
    ]
    command.extend(qtwebengine_flags)
    return command


def write_csv(path: Path, samples: list[MemorySample]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "timestamp_iso",
                "total_rss_mb",
                "renderer_rss_mb",
                "gpu_rss_mb",
                "other_rss_mb",
            ]
        )
        for sample in samples:
            writer.writerow(
                [
                    datetime.fromtimestamp(sample.timestamp).isoformat(timespec="seconds"),
                    round(sample.total_rss_kb / 1024, 2),
                    round(sample.renderer_rss_kb / 1024, 2),
                    round(sample.gpu_rss_kb / 1024, 2),
                    round(sample.other_rss_kb / 1024, 2),
                ]
            )


def parse_args() -> RunConfig:
    parser = argparse.ArgumentParser(description="Smart Desktop KDE HTML Wallpaper memory test")
    parser.add_argument("--mode", choices=("fixed", "legacy"), default="fixed")
    parser.add_argument("--cycles", type=int, default=94, help="Number of image switches")
    parser.add_argument("--interval", type=int, default=300, help="Switch interval in ms")
    parser.add_argument("--transition", type=int, default=100, help="Crossfade duration in ms")
    parser.add_argument("--log-every", type=int, default=5, help="In-page MEMLOG frequency")
    parser.add_argument(
        "--snapshots",
        choices=("none", "start", "end", "all"),
        default="none",
        help="When to capture heap snapshots (slow on large wallpapers)",
    )
    parser.add_argument(
        "--snapshot-every",
        type=int,
        default=20,
        help="Extra heap snapshot every N cycles (only with --snapshots all)",
    )
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--timeout", type=int, default=600, help="Max test duration in seconds")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chromium", default=None)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = args.output_dir / f"{timestamp}-{args.mode}"
    output_dir.mkdir(parents=True, exist_ok=True)

    return RunConfig(
        mode=args.mode,
        cycles=args.cycles,
        interval_ms=args.interval,
        transition_ms=args.transition,
        log_every=args.log_every,
        snapshot_every=args.snapshot_every,
        snapshots=args.snapshots,
        port=args.port,
        width=args.width,
        height=args.height,
        timeout_s=args.timeout,
        output_dir=output_dir,
        chromium=find_chromium(args.chromium),
    )


def main() -> int:
    config = parse_args()
    test_url = build_test_url(config)
    user_data_dir = config.output_dir / "chromium-profile"
    user_data_dir.mkdir(exist_ok=True)

    command = build_chromium_command(config, user_data_dir, test_url)
    env = os.environ.copy()

    print(f"Output: {config.output_dir}")
    print(f"Mode: {config.mode}")
    print(f"URL: {test_url}")
    print(f"Launching: {' '.join(command)}")

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )

    samples: list[MemorySample] = []
    cdp: CdpSession | None = None
    stop_event = threading.Event()
    browser_logs: list[str] = []
    page_state: dict[str, Any] | None = None
    snapshot_errors: list[str] = []
    memory_dump: dict[str, Any] = {}

    def stop_browser() -> None:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    def log_reader() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            browser_logs.append(line.rstrip())
            if "ERROR" in line or "FATAL" in line:
                print(line.rstrip())

    log_thread = threading.Thread(target=log_reader, daemon=True)
    log_thread.start()

    def on_signal(_signum: int, _frame: Any) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    try:
        targets = wait_for_cdp(config.port)
        page = pick_page_target(targets)
        ws_url = page["webSocketDebuggerUrl"]
        cdp = CdpSession(ws_url)
        cdp.enable_runtime()

        snapshots_dir = config.output_dir / "heap-snapshots"
        snapshots_dir.mkdir(exist_ok=True)

        def snapshot(label: str) -> None:
            assert cdp is not None
            path = snapshots_dir / f"{label}.heapsnapshot"
            print(f"Taking heap snapshot: {path.name}")
            try:
                cdp.take_heap_snapshot(path)
            except Exception as exc:
                msg = f"{label}: {exc}"
                snapshot_errors.append(msg)
                print(f"Heap snapshot failed: {msg}")

        if config.snapshots in ("start", "all"):
            snapshot("000-start")
        last_snapshot_cycle = 0
        start = time.time()
        per_cycle_s = (config.interval_ms + config.transition_ms) / 1000
        run_timeout_s = max(config.timeout_s, int(config.cycles * per_cycle_s) + 120)

        while not stop_event.is_set():
            if process.poll() is not None:
                print("Chromium exited early.")
                break

            sample = sample_memory(process.pid)
            samples.append(sample)
            print(
                f"RSS total={sample.total_rss_kb / 1024:.1f} MB "
                f"(renderer={sample.renderer_rss_kb / 1024:.1f}, "
                f"gpu={sample.gpu_rss_kb / 1024:.1f})"
            )

            page_state = cdp.evaluate("JSON.stringify(window.__TEST_STATE__ || null)")
            if isinstance(page_state, dict) and page_state.get("finished"):
                print(f"Test finished at cycle {page_state.get('cycle')}")
                break

            if cdp.test_done:
                break

            latest_cycle = 0
            if isinstance(page_state, dict):
                latest_cycle = int(page_state.get("cycle") or 0)
            elif cdp.memlogs:
                latest_cycle = int(cdp.memlogs[-1].get("cycle") or 0)

            if (
                config.snapshots == "all"
                and config.snapshot_every > 0
                and latest_cycle > 0
                and latest_cycle % config.snapshot_every == 0
                and latest_cycle != last_snapshot_cycle
            ):
                snapshot(f"cycle-{latest_cycle:03d}")
                last_snapshot_cycle = latest_cycle

            if time.time() - start > run_timeout_s:
                print("Timeout reached.")
                break

            time.sleep(1)

        if config.snapshots in ("end", "all"):
            snapshot("999-end")

        if cdp:
            memory_dump = cdp.collect_memory_dump()
            if samples:
                memory_dump["process_rss"] = {
                    "peak_total_mb": round(max(s.total_rss_kb for s in samples) / 1024, 2),
                    "final_total_mb": round(samples[-1].total_rss_kb / 1024, 2),
                    "peak_renderer_mb": round(max(s.renderer_rss_kb for s in samples) / 1024, 2),
                    "final_renderer_mb": round(samples[-1].renderer_rss_kb / 1024, 2),
                }

        if cdp and page_state is None:
            page_state = cdp.evaluate("JSON.stringify(window.__TEST_STATE__ || null)")

    finally:
        stop_browser()
        if cdp:
            cdp.close()

    memlogs = []
    if isinstance(page_state, dict) and page_state.get("memlogs"):
        memlogs = page_state["memlogs"]
    elif cdp:
        memlogs = cdp.memlogs

    write_csv(config.output_dir / "memory-rss.csv", samples)

    (config.output_dir / "memlogs.json").write_text(
        json.dumps(memlogs, indent=2),
        encoding="utf-8",
    )
    (config.output_dir / "console.json").write_text(
        json.dumps(cdp.console_logs if cdp else [], indent=2),
        encoding="utf-8",
    )
    (config.output_dir / "browser.log").write_text("\n".join(browser_logs), encoding="utf-8")
    (config.output_dir / "memory-dump.json").write_text(
        json.dumps(memory_dump, indent=2),
        encoding="utf-8",
    )

    peak = max(samples, key=lambda s: s.total_rss_kb) if samples else None
    completed = bool(
        (isinstance(page_state, dict) and page_state.get("finished"))
        or (cdp and cdp.test_done)
    )
    summary = {
        "config": {
            "mode": config.mode,
            "cycles": config.cycles,
            "interval_ms": config.interval_ms,
            "transition_ms": config.transition_ms,
            "snapshots": config.snapshots,
            "viewport": [config.width, config.height],
            "test_url": test_url,
            "chromium": config.chromium,
            "qtwebengine_flags": os.environ.get(
                "QTWEBENGINE_CHROMIUM_FLAGS",
                "--aggressive-cache-discard --disk-cache-size=52428800",
            ),
        },
        "result": {
            "completed": completed,
            "test_done": cdp.test_done if cdp else None,
            "page_state": page_state,
            "samples": len(samples),
            "peak_rss_mb": round(peak.total_rss_kb / 1024, 2) if peak else None,
            "final_rss_mb": round(samples[-1].total_rss_kb / 1024, 2) if samples else None,
            "peak_renderer_rss_mb": round(peak.renderer_rss_kb / 1024, 2) if peak else None,
            "snapshot_errors": snapshot_errors,
        },
        "output_files": {
            "rss_csv": "memory-rss.csv",
            "memlogs": "memlogs.json",
            "console": "console.json",
            "browser_log": "browser.log",
            "memory_dump": "memory-dump.json",
            "heap_snapshots": "heap-snapshots/",
        },
    }
    (config.output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n=== Summary ===")
    print(json.dumps(summary["result"], indent=2))
    print(f"Artifacts: {config.output_dir}")
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
