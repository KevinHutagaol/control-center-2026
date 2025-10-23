import os
import sys
import zipfile
import shutil
import requests
import json
from PyQt5.QtWidgets import QMessageBox
from requests.auth import HTTPBasicAuth
from packaging import version
from pathlib import Path

# Konfigurasi
REMOTE_JSON_URL = "https://raw.githubusercontent.com/AtlasCJr/ControlCenter/main/latest.json"
LOCAL_VERSION_FILE = "app-config.json"
UPDATE_ZIP_NAME = "update.zip"
EXTRACT_DIR = "update_temp"
APP_DIR = "."

def resource_path(rel: str | Path) -> str:
    """
    Resolve a data file path that works in:
      - dev (walk up parents so files in project root are found),
      - PyInstaller --onedir,
      - PyInstaller --onefile (temp _MEIPASS),
      - PyInstaller v6 layout (data under _internal).
    Returns a string path. It does NOT create files.
    """
    rel_path = Path(rel)

    # 0) Absolute path: just return it (don’t prepend bases)
    if rel_path.is_absolute():
        return str(rel_path)

    candidates: list[Path] = []

    # 1) PyInstaller onefile: temp unpack dir
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        candidates += [base / rel_path, base / "_internal" / rel_path]

    # 2) PyInstaller onedir: beside the executable
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates += [exe_dir / rel_path, exe_dir / "_internal" / rel_path]

    # 3) Dev: walk upwards so root-level assets can be found from subpackages
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        candidates.append(parent / rel_path)
        candidates.append(parent / "_internal" / rel_path)

    # Pick the first existing candidate
    for c in candidates:
        if c.exists():
            return str(c)

    # Fallback: return the first candidate even if missing (caller can handle)
    return str(candidates[0])

def get_local_version() -> str:
    try:
        with open(resource_path(LOCAL_VERSION_FILE)) as f:
            data = json.load(f)
            return data["version"]
    except:
        return None

def get_remote_version() -> str:
    GITHUB_USER = "AtlasCJr"
    GITHUB_TOKEN = "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"

    url = "https://raw.githubusercontent.com/AtlasCJr/ControlCenter/main/app-latest.json"

    response = requests.get(url, auth=HTTPBasicAuth(GITHUB_USER, GITHUB_TOKEN))

    if response.status_code == 200:
        data = response.json()
        return data["latest_version"]
    else:
        return None
    
def isOutdated():
    local = get_local_version()
    remote = get_remote_version()

    print(local, "---",  remote)

    if not local or not remote:
        return False
    
    return version.parse(local) > version.parse(remote)

def download_zip(url):
    print("🔽 Download update...")
    r = requests.get(url, stream=True)
    with open(UPDATE_ZIP_NAME, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print("✅ Selesai download")


def extract_and_replace():
    print("📦 Mengekstrak...")
    with zipfile.ZipFile(UPDATE_ZIP_NAME, "r") as zip_ref:
        zip_ref.extractall(EXTRACT_DIR)

    print("🧹 Menimpa file lama...")
    for name in os.listdir(EXTRACT_DIR):
        src = os.path.join(EXTRACT_DIR, name)
        dst = os.path.join(APP_DIR, name)

        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)

        shutil.move(src, dst)

    os.remove(UPDATE_ZIP_NAME)
    shutil.rmtree(EXTRACT_DIR)


def ask_for_update(parent=None):
    local = get_local_version()
    remote, url = get_remote_version()

    if isOutdated():
        msg = QMessageBox(parent)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Update Tersedia")
        msg.setText(f"Versi baru tersedia: v{remote}, kamu pakai v{local}")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.setInformativeText("Klik OK untuk update dan restart aplikasi.")

        if msg.exec_() == QMessageBox.Ok:
            try:
                download_zip(url)
                extract_and_replace()
                restart_app()
            except Exception as e:
                QMessageBox.critical(parent, "Gagal Update", f"Terjadi error saat update:\n{e}")
    else:
        print("✅ Aplikasi versi terbaru")


def restart_app():
    print("🔁 Restarting...")
    python = sys.executable
    os.execl(python, python, *sys.argv)
