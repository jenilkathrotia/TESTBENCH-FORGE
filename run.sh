#!/usr/bin/env bash
# TestBench-Forge — interactive demo UI.
# One command from the repo root:   ./run.sh
# Installs deps on first run, then serves the Vite/React demo on localhost and opens it.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB="$HERE/web"
PORT="${PORT:-5173}"

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm/Node.js not found. Install Node 18+ from https://nodejs.org and re-run." >&2
  exit 1
fi

cd "$WEB"

if [ ! -d node_modules ]; then
  echo "── First run: installing dependencies (npm install) ──"
  npm install
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  TestBench-Forge demo  →  http://localhost:${PORT}"
echo "  (Ctrl-C to stop)"
echo "════════════════════════════════════════════════════════════"
echo ""

# Serve on localhost and open the browser. --strictPort keeps the URL predictable.
exec npm run dev -- --port "$PORT" --strictPort --host localhost --open
