import os
import sys
import zipfile
import shutil
import requests
import json
from packaging import version
from PyQt5.QtWidgets import QMessageBox

# Konfigurasi
REMOTE_JSON_URL = "https://raw.githubusercontent.com/<user>/<repo>/main/latest.json"
LOCAL_VERSION_FILE = "version.json"
UPDATE_ZIP_NAME = "update.zip"
EXTRACT_DIR = "update_temp"
APP_DIR = "."


def get_local_version():
    with open(LOCAL_VERSION_FILE, "r") as f:
        return version.parse(json.load(f)["version"])


def get_remote_version():
    try:
        r = requests.get(REMOTE_JSON_URL)
        if r.status_code == 200:
            data = r.json()
            return version.parse(data["latest_version"]), data["download_url"]
    except Exception as e:
        print("Gagal cek versi:", e)
    return None, None


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

    if remote and remote > local:
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
