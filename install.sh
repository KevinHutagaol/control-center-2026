#!/bin/bash

PROJECT_DIR=$(pwd)
DESKTOP_FILE="$HOME/.local/share/applications/control-center.desktop"
cd "$PROJECT_DIR" || exit
sudo dnf install python3.11
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
sudo dnf install python3.11 python3.11-devel
pyinstaller --noconsole --onedir --name ControlCenter pages/Home/main.py


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

chmod +x "$PROJECT_DIR/dist/ControlCenter/ControlCenter"

echo "✅ Instalasi selesai! Shortcut 'Control Center' sudah ditambahkan ke menu untuk user: $USER"
