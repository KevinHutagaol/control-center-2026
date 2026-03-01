#!/bin/bash

VENV_DIR=".venv"
MAIN_SCRIPT="-m pages.Home.main"
UI_COMPILER="utils/compileUIFiles.py"
REQUIREMENTS="requirements.txt"
TARGET_VER="3.11"

PYTHON_CMD=""

if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    VER=$(python3 --version 2>&1)
    if [[ "$VER" == *"3.11"* ]]; then
        PYTHON_CMD="python3"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "========================================================"
    echo "[ERROR] Python $TARGET_VER is missing!"
    echo "========================================================"
    echo "This application requires specifically Python 3.11."
    echo ""
    echo "Install instructions:"
    echo "  Ubuntu/Debian: sudo apt install python3.11 python3.11-venv"
    echo "  MacOS:         brew install python@3.11"
    echo "  Fedora:        sudo dnf install python3.11"
    echo "========================================================"
    exit 1
fi

echo "[INFO] Using Python: $PYTHON_CMD"

# --- CHECKS ---
if ! command -v git &> /dev/null; then
    echo "[ERROR] Git is not installed."
    exit 1
fi

# --- VENV ---
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating Python Virtual Environment ($TARGET_VER)..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# --- UPDATE ---
UPDATED=0

if [ -f ".dev_mode" ]; then
    echo "[WARN] '.dev_mode' file detected."
    echo "[WARN] Skipping Git Update/Reset to protect local changes."
else
    echo "[INFO] Checking for updates..."
    PREV_HEAD=$(git rev-parse HEAD)

    git fetch origin
    git reset --hard origin/main
    git pull

    NEW_HEAD=$(git rev-parse HEAD)

    if [ "$PREV_HEAD" != "$NEW_HEAD" ]; then
        echo "[INFO] Update detected!"
        UPDATED=1
    else
        echo "[INFO] Already up to date."
    fi
fi

# --- BUILD ---
FIRST_RUN=0
if [ ! -f ".setup_complete" ]; then
    FIRST_RUN=1
fi

DO_BUILD=0
if [ "$UPDATED" -eq 1 ] || [ "$FIRST_RUN" -eq 1 ]; then
    DO_BUILD=1
fi

if [ "$DO_BUILD" -eq 1 ]; then
    echo "[INFO] Installing/Updating dependencies..."
    pip install -r "$REQUIREMENTS"

    echo "[INFO] Compiling UI files..."
    python3 "$UI_COMPILER"
fi

if [ "$FIRST_RUN" -eq 1 ]; then
    echo "[INFO] First run detected. Creating shortcuts..."
    python3 "utils/createShortcuts.py"

    touch ".setup_complete"
fi

# --- LAUNCH ---
echo "[INFO] Starting Application..."
python3 $MAIN_SCRIPT

echo "Press Enter to continue . . ."
# shellcheck disable=SC2162
read