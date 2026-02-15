#!/usr/bin/env bash
set -euo pipefail

echo "Initializing Python virtual environment for Ubuntu deployment"

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Error: $PY not found. Please install Python 3 before running this script." >&2
  exit 1
fi

# Ensure the venv module is available; if not, try to install system package (requires sudo)
if ! "$PY" -m venv --help >/dev/null 2>&1; then
  echo "python3 venv module not available. Installing system packages (requires sudo)..."
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-pip
fi

VENV_DIR=venv
if [ -d "$VENV_DIR" ]; then
  echo "Virtual environment '$VENV_DIR' already exists — skipping creation."
else
  echo "Creating virtual environment in ./$VENV_DIR"
  "$PY" -m venv "$VENV_DIR"
fi

echo "Upgrading pip and installing project requirements (if present)"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
if [ -f requirements.txt ]; then
  "$VENV_DIR/bin/python" -m pip install -r requirements.txt
else
  echo "No requirements.txt found in project root — skipping pip install." >&2
fi

echo
echo "Done. To use the virtual environment on Ubuntu run:"
echo "  source $VENV_DIR/bin/activate"
echo "Then run your Python scripts, for example:"
echo "  python src/bulbapedia_scraper.py"
