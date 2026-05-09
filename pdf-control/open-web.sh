#!/usr/bin/env bash
set -euo pipefail

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

pick_port() {
  "$PYTHON_BIN" - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

PORT="${PORT:-$(pick_port)}"
URL="http://localhost:${PORT}"
LOG_FILE="${TMPDIR:-/tmp}/pdf-control-streamlit-${PORT}.log"

cd "$PROJECT_DIR"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS="${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}"
export STREAMLIT_SERVER_MAX_UPLOAD_SIZE="${STREAMLIT_MAX_UPLOAD_SIZE_MB:-1024}"

echo "Starting PDF Control on ${URL}"
echo "Max upload size: ${STREAMLIT_SERVER_MAX_UPLOAD_SIZE} MB per file"
echo "Streamlit log: ${LOG_FILE}"
echo "Press Ctrl+C here to stop the app."

setsid "$PYTHON_BIN" -m streamlit run "$PROJECT_DIR/src/streamlit_app.py" \
  --server.address 127.0.0.1 \
  --server.port "$PORT" \
  --server.headless true >"$LOG_FILE" 2>&1 &

SERVER_PID=$!
STOPPED=0

cleanup() {
  trap - EXIT INT TERM
  STOPPED=1
  if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill -TERM "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
  echo
  echo "Stopped PDF Control."
}
trap cleanup EXIT INT TERM

sleep 2

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v gio >/dev/null 2>&1; then
  gio open "$URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID" || {
  status=$?
  if [[ "$STOPPED" -eq 0 && "$status" -ne 143 && "$status" -ne 130 ]]; then
    echo "PDF Control stopped unexpectedly. Last log lines:"
    tail -n 40 "$LOG_FILE" || true
    exit "$status"
  fi
}
