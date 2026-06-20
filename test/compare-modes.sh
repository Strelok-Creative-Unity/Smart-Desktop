#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="$ROOT/test/run-memory-test.py"

CYCLES="${1:-94}"
INTERVAL="${2:-300}"
TRANSITION="${3:-100}"

echo "=== Smart Desktop memory comparison ==="
echo "cycles=$CYCLES interval=${INTERVAL}ms transition=${TRANSITION}ms"

python3 "$RUNNER" \
  --mode fixed \
  --cycles "$CYCLES" \
  --interval "$INTERVAL" \
  --transition "$TRANSITION" \
  --snapshots none \
  --port 9224

python3 "$RUNNER" \
  --mode legacy \
  --cycles "$CYCLES" \
  --interval "$INTERVAL" \
  --transition "$TRANSITION" \
  --snapshots none \
  --port 9225

python3 - <<'PY'
import json
from pathlib import Path

root = Path("test/output")
fixed_paths = sorted(root.glob("*-fixed"))
legacy_paths = sorted(root.glob("*-legacy"))
runs = (fixed_paths[-1:], legacy_paths[-1:])
for label, paths in zip(("fixed", "legacy"), runs):
    summary = json.loads((paths[0] / "summary.json").read_text())
    result = summary["result"]
    print(f"\n{label}:")
    print(f"  completed: {result['completed']}")
    print(f"  peak_rss_mb: {result['peak_rss_mb']}")
    print(f"  final_rss_mb: {result['final_rss_mb']}")
    print(f"  artifacts: {paths[0]}")
PY
