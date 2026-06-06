#!/bin/bash
# Script to run the inventory editor against the lab
SOURCE_DIR=$(cd "$(dirname "$0")" && pwd)
VENV_DIR="$SOURCE_DIR/inventory-editor/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run the setup steps first or ensure the venv directory exists."
    exit 1
fi

cd "$SOURCE_DIR/inventory-editor"
source venv/bin/activate
python -m inventory_editor.gui ../ansible-lab
