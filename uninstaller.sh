#!/bin/bash

PROJECT_DIR=$(pwd)
DESKTOP_FILE="$HOME/.local/share/applications/control-center.desktop"

echo "Memulai proses uninstall Control Center 2026..."

if [ -d "$PROJECT_DIR/dist" ]; then
    rm -rf "$PROJECT_DIR/dist"
    echo "🗑️  Folder 'dist' berhasil dihapus."
fi

if [ -d "$PROJECT_DIR/build" ]; then
    rm -rf "$PROJECT_DIR/build"
    echo "🗑️  Folder 'build' berhasil dihapus."
fi

if [ -f "$PROJECT_DIR/ControlCenter.spec" ]; then
    rm -f "$PROJECT_DIR/ControlCenter.spec"
    echo "🗑️  File 'ControlCenter.spec' berhasil dihapus."
fi

if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo "🗑️  Shortcut aplikasi berhasil dihapus dari menu."
fi

echo "✅ Proses uninstall selesai! Semua file build dan shortcut sudah bersih."