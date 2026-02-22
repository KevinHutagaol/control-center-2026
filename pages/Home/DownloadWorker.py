import os
import subprocess
import sys
import time

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from pages.Home.installerUtils import bundle_dir, bundle_path


class DownloadWorker(QThread):
    progress = pyqtSignal(int)        # 0..100
    status   = pyqtSignal(str)        # log lines
    done     = pyqtSignal(str)        # filename
    failed   = pyqtSignal(str)        # error text

    def __init__(self, asset):
        super().__init__()
        self.asset = asset
        self._cancel = False

    def cancel(self):
        self._cancel = True
        self.status.emit("Cancel requested by user.")

    @staticmethod
    def launch_updater_and_exit():
        app_dir = bundle_dir()
        updater_exe = app_dir / "updater-NT.exe"
        new_package = app_dir / "temp-updatepackage.exe"

        if not updater_exe.exists():
            raise RuntimeError(f"{updater_exe} not found")

        print("bundle_path=", bundle_path())
        print("bundle_dir =", bundle_dir())
        print("updater    =", updater_exe)
        print("new pkg    =", new_package)

        args = [
            str(updater_exe),
            "--target", str(bundle_path()),
            "--new",    str(new_package),
            "--waitpid", str(os.getpid()),
            "--relaunch",
        ]

        CREATE_NO_WINDOW = 0x08000000
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(args, creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS)
        sys.exit(0)

    def run(self):
        GITHUB_TOKEN = "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"

        try:
            api_url = self.asset["url"]

            filename = "temp-updatepackage.exe"
            dest = bundle_dir() / filename

            headers = {
                "Accept": "application/octet-stream",
                "Authorization": f"token {GITHUB_TOKEN}",
            }

            self.status.emit(f"Connecting to GitHub...")
            with requests.get(api_url, headers=headers, stream=True, timeout=30) as r:
                self.status.emit(f"Connected to GitHub...")

                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                got = 0
                chunk_size = 1024 * 128

                self.status.emit(f"Downloading {self.asset['name']} as {filename} ({total/1_048_576:.2f} MB)...")
                self.status.emit(f"Location: {dest}")
                time.sleep(2)

                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if self._cancel:
                            self.status.emit("Canceled by user.")
                            try:
                                f.close()
                                if dest.exists():
                                    dest.unlink()
                            except Exception:
                                pass
                            return
                        if not chunk:
                            continue

                        f.write(chunk)
                        got += len(chunk)

                        if total > 0:
                            pct = got * 100 / total
                            self.progress.emit(int(pct))

                            self.status.emit(f"Downloading... {pct:.2f}%")

                if total > 0 and got != total:
                    self.status.emit(f"Warning: size mismatch (got {got} / expected {total}).")

                self.status.emit(f"Download Complete: {str(dest)}")
                self.status.emit("Ready for replacing old files...")
                self.status.emit("Replacing old files")
                self.status.emit("The app will close now and the replacement will continue...")

                time.sleep(2)

                DownloadWorker.launch_updater_and_exit()

        except Exception as e:
            self.failed.emit(str(e))
