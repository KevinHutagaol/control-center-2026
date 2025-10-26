import os, sys, zipfile, shutil, requests, json
from PyQt5.QtWidgets import QMessageBox
from requests.auth import HTTPBasicAuth
from packaging import version
from pathlib import Path
from tqdm import tqdm
from PyQt5.QtCore import QThread, pyqtSignal

# Konfigurasi
REMOTE_JSON_URL = "https://raw.githubusercontent.com/AtlasCJr/ControlCenter/main/latest.json"
LOCAL_VERSION_FILE = "app-config.json"
UPDATE_ZIP_NAME = "update.zip"
EXTRACT_DIR = "update_temp"
APP_DIR = "."
REPO = "AtlasCJr/ControlCenter"
GITHUB_USER = "AtlasCJr"
GITHUB_TOKEN = "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"

def resource_path(rel: str | Path) -> str:
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
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    auth = HTTPBasicAuth(GITHUB_USER, GITHUB_TOKEN) if GITHUB_TOKEN else None

    response = requests.get(url, auth=auth)
    if response.status_code == 200:
        data = response.json()
        return data.get("tag_name")
    else:
        print(response.text)
        return None
    
def isOutdated():
    local = get_local_version()
    remote = get_remote_version()

    if not local or not remote:
        return False
    
    return version.parse(local) < version.parse(remote)
    
class VersionChecker(QThread):
    result = pyqtSignal(bool, str, str)  # (is_outdated, local, remote)
    error = pyqtSignal(str)

    def run(self):
        try:
            local = get_local_version()
            remote = get_remote_version()

            if not local or not remote:
                self.result.emit(False, local, remote)
                return

            outdated = isOutdated()
            self.result.emit(outdated, local, remote)
        except Exception as e:
            self.error.emit(str(e))

def list_assets():
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    auth = HTTPBasicAuth(GITHUB_USER, GITHUB_TOKEN) if GITHUB_TOKEN else None
    r = requests.get(url, auth=auth)
    r.raise_for_status()
    rel = r.json()
    assets = rel.get("assets", [])
    return rel.get("tag_name"), assets

def download_zip(asset):
    api_url = asset["url"]
    headers = {
        "Accept": "application/octet-stream",
        "Authorization": f"token {GITHUB_TOKEN}",
    }

    with requests.get(api_url, headers=headers, stream=True) as r:
        r.raise_for_status()
        filename = asset["name"]

        # Dapatkan total ukuran file dari header (dalam byte)
        total_size = int(r.headers.get("Content-Length", 0))
        block_size = 8192

        print(f"📦 Downloading update: {filename}")

        # tqdm untuk progress bar
        with open(filename, "wb") as f, tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc="🔽 Progress",
            ncols=80,
        ) as progress:
            for chunk in r.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    progress.update(len(chunk))

        print(f"✅ Download finished: {filename}")


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


def restart_app():
    print("🔁 Restarting...")
    python = sys.executable
    os.execl(python, python, *sys.argv)
