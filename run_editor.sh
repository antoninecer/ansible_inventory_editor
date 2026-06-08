#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$ROOT_DIR/inventory-editor"
VENV_DIR="$PKG_DIR/venv"
REQ_FILE="$PKG_DIR/requirements.txt"

if command -v python3.12 >/dev/null 2>&1; then
  PYTHON_CMD="python3.12"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
else
  echo "ERROR: python3 is not available."
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment: $VENV_DIR"
  "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

echo "Using Python: $("$PYTHON_BIN" --version)"
echo "Using venv:   $VENV_DIR"

if [[ -f "$REQ_FILE" ]]; then
  echo "Installing runtime requirements..."
  "$PIP_BIN" install -r "$REQ_FILE"
fi

echo "Installing AIS package from local checkout..."
"$PIP_BIN" install -e "$PKG_DIR"

cd "$PKG_DIR"

if [[ "$#" -gt 0 ]]; then
  echo "Starting AIS with workspace argument: $1"
  exec "$PYTHON_BIN" -m inventory_editor.gui "$@"
else
  echo "Starting AIS using saved application settings..."
  exec "$PYTHON_BIN" -m inventory_editor.gui
fi
