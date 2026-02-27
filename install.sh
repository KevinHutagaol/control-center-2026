#!/bin/bash

# Ambil direktori tempat script ini dijalankan (biar otomatis)
PROJECT_DIR=$(pwd)
DESKTOP_FILE="$HOME/.local/share/applications/control-center.desktop"
cd "$PROJECT_DIR"
pip install pyinstaller
# sudo dnf install python3.11 python3.11-devel
pyinstaller --noconsole --onedir --name ControlCenter pages/Home/main.py


# Bikin file .desktop dengan path yang menyesuaikan laptop masing-masing
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Version=1.0
Name=Control Center 2026
Comment=Application for Control Lab 2026
Exec=$PROJECT_DIR/dist/ControlCenter/ControlCenter
Icon=$PROJECT_DIR/public/LogoControlLab2026.png
Terminal=false
Categories=Utility;Development;
EOF

# Kasih izin eksekusi ke aplikasi utamanya (jaga-jaga kalau permission-nya hilang saat di-copy)
chmod +x "$PROJECT_DIR/dist/ControlCenter/ControlCenter"

echo "✅ Instalasi selesai! Shortcut 'Control Center' sudah ditambahkan ke menu untuk user: $USER"
