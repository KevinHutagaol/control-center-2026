import sys, requests, json
from requests.auth import HTTPBasicAuth
from packaging import version
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

# Konfigurasi
LOCAL_VERSION_FILE = "app-config.json"
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
    print("Getting local version...")
    try:
        with open(resource_path(LOCAL_VERSION_FILE)) as f:
            data = json.load(f)
            print(f"Local version: {data['version']}")
            return data["version"]
    except:
        return None

def get_remote_version() -> str:
    print("Getting remote version...")
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    auth = HTTPBasicAuth(GITHUB_USER, GITHUB_TOKEN) if GITHUB_TOKEN else None

    try:
        # timeout=(connect_timeout, read_timeout)
        response = requests.get(url, auth=auth, timeout=(3, 10))
        response.raise_for_status()  # raise if status != 200
        data = response.json()
        return data.get("tag_name")
    except requests.exceptions.Timeout:
        print("Connection timed out. please check your internet connection.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch remote version: {e}")
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