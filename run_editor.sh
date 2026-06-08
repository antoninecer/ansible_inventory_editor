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

echo "Upgrading pip tooling..."
"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel

echo "Installing runtime requirements..."
"$PIP_BIN" install -r "$REQ_FILE"

echo "Installing AIS package from local checkout..."
"$PIP_BIN" install -e "$PKG_DIR"

if [[ "$#" -eq 0 && -d "$ROOT_DIR/ansible-lab" ]]; then
  echo "Starting AIS with default workspace: $ROOT_DIR/ansible-lab"
  exec "$PYTHON_BIN" -m inventory_editor.gui "$ROOT_DIR/ansible-lab"
else
  echo "Starting AIS..."
  exec "$PYTHON_BIN" -m inventory_editor.gui "$@"
fi
