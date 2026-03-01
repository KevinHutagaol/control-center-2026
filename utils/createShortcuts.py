import os
import sys
import platform
from pathlib import Path

def create_windows_shortcut(target_script, icon_path=None):
    try:
        import winshell
        from win32com.client import Dispatch
    except ImportError:
        print("Installing pywin32 for shortcut creation...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32", "winshell"])
        import winshell
        from win32com.client import Dispatch

    desktop = winshell.desktop()
    path = os.path.join(desktop, f"Control Center - Control Lab UI.lnk")

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = str(target_script)
    shortcut.WorkingDirectory = str(target_script.parent)
    if icon_path and icon_path.exists():
        shortcut.IconLocation = str(icon_path)
    shortcut.save()
    print(f"Shortcut created at: {path}")


def create_linux_shortcut(target_script, icon_path=None):
    desktop_file = f"""[Desktop Entry]
Type=Application
Name=Control Center - Control Lab UI
Exec="{target_script}"
Path={target_script.parent}
Terminal=true
"""
    if icon_path and icon_path.exists():
        desktop_file += f"Icon={icon_path}\n"

    app_path = Path.home() / f".local/share/applications/ControlCenter-ControlLabUI.desktop"
    app_path.parent.mkdir(parents=True, exist_ok=True)

    with open(app_path, "w") as f:
        f.write(desktop_file)

    os.chmod(app_path, 0o755)
    print(f"Shortcut created at: {app_path}")
    print("You may need to log out and back in for it to appear in your menu.")


def main():
    root_dir = Path(__file__).parent.parent.absolute()

    system = platform.system()

    if system == "Windows":
        icon_path = root_dir / "public" / "logo_controllab.ico"
        target = root_dir / "run.bat"
        create_windows_shortcut(target, icon_path)
    elif system == "Linux":
        icon_path = root_dir / "public" / "logo_controllab.png"
        target = root_dir / "run.sh"
        create_linux_shortcut(target, icon_path)
    else:
        print(f"Shortcut creation not yet supported for {system}")


if __name__ == "__main__":
    main()