#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "error: backend directory not found at $BACKEND_DIR" >&2
  exit 1
fi

if [[ -x "$BACKEND_DIR/venv/bin/python" ]]; then
  PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
else
  PYTHON_BIN="python3"
fi

cd "$BACKEND_DIR"
exec "$PYTHON_BIN" -m app.cli "$@"
