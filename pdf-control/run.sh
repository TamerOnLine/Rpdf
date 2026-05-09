#!/usr/bin/env bash
set -euo pipefail

# Resolve through symlinks so launching via /home/Rpdf/run.sh still points here.
SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
PROJECT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
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
elif [[ "${1:-}" == "web" || "${1:-}" == "streamlit" ]]; then
  shift
  export STREAMLIT_BROWSER_GATHER_USAGE_STATS="${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}"
  export STREAMLIT_SERVER_MAX_UPLOAD_SIZE="${STREAMLIT_MAX_UPLOAD_SIZE_MB:-1024}"
  exec "$PYTHON_BIN" -m streamlit run "$PROJECT_DIR/src/streamlit_app.py" "$@"
else
  exec "$PYTHON_BIN" -m src.main "$@"
fi
