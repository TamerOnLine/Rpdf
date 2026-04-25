#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Virtual environment not found at: $PYTHON_BIN"
  echo "Run the following first:"
  echo "  cd \"$PROJECT_DIR\""
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

cd "$PROJECT_DIR"

if [[ $# -eq 0 ]]; then
  exec "$PYTHON_BIN" -m src.main gui
else
  exec "$PYTHON_BIN" -m src.main "$@"
fi
