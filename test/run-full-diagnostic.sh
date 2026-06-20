#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRAMES=95
PORT="${1:-9240}"

cd "$ROOT"

echo "=== Full memory diagnostic: ${FRAMES} frames ==="

python3 test/run-memory-test.py \
  --mode fixed \
  --cycles "$FRAMES" \
  --interval 500 \
  --transition 150 \
  --log-every 1 \
  --snapshots all \
  --snapshot-every 19 \
  --timeout 7200 \
  --port "$PORT"

OUT="$(ls -td test/output/*-fixed | head -1)"
echo ""
echo "Done. Artifacts: $OUT"
python3 - <<PY
import json
from pathlib import Path

out = Path("$OUT")
summary = json.loads((out / "summary.json").read_text())
memlogs = json.loads((out / "memlogs.json").read_text())
result = summary["result"]

print(f"completed: {result['completed']}")
print(f"frames logged: {len(memlogs)}")
print(f"peak_rss_mb: {result['peak_rss_mb']}")
print(f"final_rss_mb: {result['final_rss_mb']}")
print(f"peak_renderer_rss_mb: {result['peak_renderer_rss_mb']}")
if result.get("snapshot_errors"):
    print(f"snapshot_errors: {len(result['snapshot_errors'])}")
PY
