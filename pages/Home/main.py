import sys, os, requests, subprocess, time, shutil
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QWidget, QProgressBar, QPushButton, QVBoxLayout, QDialog, QHBoxLayout, QTextEdit, QLabel
from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal, QThread, QTimer
from PyQt5.QtGui import QIcon, QValidator
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import matplotlib.pyplot as plt
from pathlib import Path

import pages.Home.resources_rc as resources_rc

import func.updaterFunc as updaterFunc 

from pages.Modul4.mainCDRL import exec_CDRL
from pages.Modul5.mainCDFR import exec_CDFR
from pages.Modul7.mainCOD import exec_COD
from pages.Modul910.mainDMMCD import exec_DMMCD

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

def bundle_path() -> Path:
    # The actual file the user started (outer EXE when frozen, .py in dev)
    return Path(sys.argv[0]).resolve()

def bundle_dir() -> Path:
    return bundle_path().parent

try:
    cred = credentials.Certificate(resource_path("firebaseAuth.json"))
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
        
    db = firestore.client() 

    print("Home: Firebase initialized successfully")
except Exception as e:
    print("Firebase error:", e)  # tampilkan di console
    QMessageBox.critical(QWidget(), "Firebase Error", f"Failed to Connect to Firebase. Error: {e}")
    sys.exit(1)

class MainWindow(QMainWindow):
    def __init__(self, npm, nama, role, kelompok):
        super().__init__()
        uic.loadUi(resource_path("pages/Home/UI_home/Main.ui"), self)
        self.setWindowTitle(f"Control Practicum Center {updaterFunc.get_local_version()}")
        self.setWindowIcon(QIcon(resource_path("public/Logo Merah.png")))

        self.RootLocus.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.RootLocusPage))
        self.Frequency.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.FreqPage))
        self.CDRootLocus.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CDRootLocusPage))
        self.CDFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CDFreqPage))
        self.StateSpace.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.StateSpacePage))
        self.COD.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CODPage))
        self.DCOD.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.DCODPage))
        self.DCMotor.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.MotorPage))

        self.RunRL.clicked.connect(lambda checked, n=nama, p=npm: self.run_root_locus(n, p))
        self.RunFreq.clicked.connect(lambda checked, n=nama, p=npm: self.run_frequency_response(n, p))
        self.RunCDRL.clicked.connect(lambda checked,n=nama, p=npm: self.run_cd_root_locus(n, p))
        self.RunCDFreq.clicked.connect(lambda checked, n=nama, p=npm: self.run_cd_frequency_response(n, p))
        self.RunStateSpace.clicked.connect(lambda checked, n=nama, p=npm: self.run_state_space(n, p))
        self.RunCOD.clicked.connect(lambda checked, n=nama, p=npm: self.run_cod(n, p))
        self.RunDCOD.clicked.connect(lambda checked, n=nama, p=npm: self.run_dcod(n, p))
        self.RunMotor.clicked.connect(lambda checked, n=nama, p=npm, k=kelompok: self.run_motor(n, p, k))

        self.WelcomeText.setText(f"Welcome {nama}!")
        self.Kelompok.setText(kelompok)
        
        self.Nilai.clicked.connect(lambda checked, p=npm: self.check_nilai(p))
        self.Back.clicked.connect(lambda: self.Stacked.setCurrentWidget(self.Main))

        self.btn23.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul23))
        self.btn4.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul4))
        self.btn5.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul5))
        self.btn6.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul6))
        self.btn7.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul7))
        self.btn8.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul8))
        self.btn910.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul910))
        self.btn11.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul11))

        self.Refresh.clicked.connect(lambda checked, p=npm: self.refresh_nilai(p))

        self._children = {}

        self.show()

    def run_root_locus(self, nama, npm):
        print("Running RL")
    
    def run_frequency_response(self, nama, npm):
        print("Running FR")
    
    def run_cd_root_locus(self, nama, npm):
        print("Running CDRL")
        w = exec_CDRL(nama, npm)
        key = f"Modul4-{npm}"
        self._children[key] = w
        
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_cd_frequency_response(self, nama, npm):
        print("Running CDFR")

        w = exec_CDFR(nama, npm)
        key = f"Modul5-{npm}"
        self._children[key] = w
        
        w.destroyed.connect(lambda: self._children.pop(key, None))
    
    def run_state_space(self, nama, npm):
        print("Running SS")
    
    def run_cod(self, nama, npm):
        print("Running COD")
        w = exec_COD(nama, npm)
        key = f"Modul7-{npm}"
        self._children[key] = w
        
        w.destroyed.connect(lambda: self._children.pop(key, None))
    
    def run_dcod(self, nama, npm):
        print("Running DCOD")
    
    def run_motor(self, nama, npm,kelompok):
        print("Running DMMCD")
        w = exec_DMMCD(nama, npm)
        key = f"Modul910-{npm}"
        self._children[key] = w
        
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def generate_charts(self, npm, doc_data, out_dir="Nilai"):
        nama = doc_data.get("Nama", npm)
        os.makedirs(out_dir, exist_ok=True)

        # ====== Chart Per Modul ======
        modul_groups = {
            "Modul 2&3"     : ["(Modul 2&3) Tugas Pendahuluan", "(Modul 2&3) Borang Simulasi", "(Modul 2&3) Borang Analisis", "(Modul 2&3) Tugas Tambahan"],
            "Modul 4"       : ["(Modul 4) Tugas Pendahuluan", "(Modul 4) Borang Simulasi", "(Modul 4) Borang Analisis", "(Modul 4) Tugas Tambahan"],
            "Modul 5"       : ["(Modul 5) Tugas Pendahuluan", "(Modul 5) Borang Simulasi", "(Modul 5) Borang Analisis", "(Modul 5) Tugas Tambahan"],
            "Modul 6"       : ["(Modul 6) Tugas Pendahuluan", "(Modul 6) Borang Simulasi", "(Modul 6) Borang Analisis", "(Modul 6) Tugas Tambahan"],
            "Modul 7"       : ["(Modul 7) Tugas Pendahuluan", "(Modul 7) Borang Simulasi", "(Modul 7) Borang Analisis", "(Modul 7) Tugas Tambahan"],
            "Modul 8"       : ["(Modul 8) Tugas Pendahuluan", "(Modul 8) Borang Simulasi", "(Modul 8) Borang Analisis", "(Modul 8) Tugas Tambahan"],
            "Modul 9&10"    : ["(Modul 9&10) Tugas Pendahuluan", "(Modul 9&10) Borang Simulasi", "(Modul 9&10) Borang Analisis", "(Modul 9&10) Tugas Tambahan"],
            "Modul 11"      : ["(Modul 11) Project Concept", "(Modul 11) Project Complexity", "(Modul 11) Project Readability", "(Modul 11) Scene Arragement", "(Modul 11) Project Explanation", "(Modul 11) Program Explanation", "(Modul 11) Simulation"]
        }

        def shorten_label(lbl):
            mapping = {
                "Tugas Pendahuluan": "TP",
                "Borang Simulasi": "Simulasi",
                "Borang Analisis": "Analisis",
                "Tugas Tambahan": "Tutam",
                "Project Concept": "Project\nConcept",
                "Project Complexity": "Project\nComplexity",
                "Project Readability": "Project\nReadability",
                "Scene Arragement": "Scene\nArragement",
                "Project Explanation": "Project\nExplanation",
                "Program Explanation": "Program\nExplanation",
                "Simulation": "Simulation",
                "Pretest": "Pretest",
                "Post-Test": "PostTest"
            }
            for k, v in mapping.items():
                if k in lbl:
                    return v
            return lbl

        def style_bar_chart(ax, bars, values):
            ax.set_facecolor("none")
            ax.figure.patch.set_alpha(0.0)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for spine in ["left", "bottom"]:
                ax.spines[spine].set_color("white")
                ax.spines[spine].set_linewidth(2)

            ax.tick_params(axis="x", colors="white", labelsize=8)
            ax.tick_params(axis="y", colors="white", left=False, labelleft=False)

            ax.set_ylim(0, 100)

            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, val + 1,
                        f"{val:.0f}", ha="center", va="bottom", color="white", fontsize=8)

        # per modul
        for modul, keys in modul_groups.items():
            values = [doc_data.get(k, 0) for k in keys]
            short_labels = [shorten_label(k) for k in keys]

            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(short_labels, values, color="white")
            style_bar_chart(ax, bars, values)

            ax.set_ylabel(modul, color="white", fontsize=12, rotation=90, labelpad=15)

            safe_name = modul.replace(" ", "_").replace("&", "")
            plt.tight_layout()
            # fig.savefig(f"{out_dir}/{safe_name}.png", transparent=True)
            plt.close(fig)

        # ====== Hitung skor modul & total ======
        def hitung_modul(modul):
            if modul == "Modul 11":
                return (
                    0.10*doc_data.get("(Modul 11) Project Concept",0) +
                    0.175*doc_data.get("(Modul 11) Project Complexity",0) +
                    0.075*doc_data.get("(Modul 11) Project Readability",0) +
                    0.15*doc_data.get("(Modul 11) Scene Arragement",0) +
                    0.15*doc_data.get("(Modul 11) Project Explanation",0) +
                    0.15*doc_data.get("(Modul 11) Program Explanation",0) +
                    0.20*doc_data.get("(Modul 11) Simulation",0)
                )
            else:
                tp = doc_data.get(f"({modul}) Tugas Pendahuluan",0)
                bs = doc_data.get(f"({modul}) Borang Simulasi",0)
                ba = doc_data.get(f"({modul}) Borang Analisis",0)
                tt = doc_data.get(f"({modul}) Tugas Tambahan",0)
                return 0.20*tp + 0.35*bs + 0.25*ba + 0.20*tt

        modul_list = ["Modul 2&3", "Modul 4", "Modul 5", "Modul 6", "Modul 7", "Modul 8", "Modul 9&10", "Modul 11"]
        modul_scores = [hitung_modul(m) for m in modul_list]

        pretest = doc_data.get("Pretest",0)
        posttest = (
            0.20*doc_data.get("Post-Test Modul 2&3",0) +
            0.10*doc_data.get("Post-Test Modul 4",0) +
            0.10*doc_data.get("Post-Test Modul 5",0) +
            0.10*doc_data.get("Post-Test Modul 6",0) +
            0.10*doc_data.get("Post-Test Modul 7",0) +
            0.10*doc_data.get("Post-Test Modul 8",0) +
            0.20*doc_data.get("Post-Test Modul 9&10",0) +
            0.10*doc_data.get("Post-Test Bonus",0)
        )

        # ====== Detail Nilai (bar chart) ======
        labels = ["Pretest"] + modul_list + ["Post-Test"]
        scores = [pretest] + modul_scores + [posttest]
        short_labels = [shorten_label(lbl) for lbl in labels]

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(short_labels, scores, color="white")
        style_bar_chart(ax, bars, scores)

        plt.tight_layout()
        # fig.savefig(f"{out_dir}/DetailNilai.png", transparent=True)
        plt.close(fig)

        # ====== Pie Chart Total Nilai ======
        total = 0.05*pretest + 0.15*posttest + sum([0.10*s for s in modul_scores])

        grade = "E"
        ranges = [("A",85,100),("A-",80,85),("B+",75,80),("B",70,75),("B-",65,70),("C+",60,65),("C",55,60),("D",40,55),("E",0,40)]
        for g,minv,maxv in ranges:
            if minv <= total < maxv or (g=="A" and total==100):
                grade = g
                break

        fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(aspect="equal"))
        ax.set_facecolor("none")
        fig.patch.set_alpha(0.0)

        filled = total/100
        wedges = [filled, 1-filled]
        colors = [(214/255, 0, 0), (214/255, 0, 0, 0.3)]  # merah solid & merah transparan

        ax.pie(
            wedges,
            startangle=90,
            counterclock=False,
            colors=colors,
            wedgeprops=dict(width=0.4)
        )

        ax.text(
            0, 0, grade,
            ha="center", va="center",
            fontsize=80, fontweight="bold",
            color=(214/255, 0, 0) 
        )

        plt.tight_layout()
        # fig.savefig(f"{out_dir}/TotalNilai.png", transparent=True)
        plt.close(fig)
        plt.close('all')

        print(f"Charts untuk {nama} ({npm}) sudah disimpan di folder {out_dir}/")

        self.DetailNilai.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/DetailNilai.png') 
            }
        """)

        self.TotalNilai.setStyleSheet("""
            QFrame {
                image: url(pages/Home/Nilai_home/TotalNilai.png);
                background-color: rgb(255, 255, 255);
                border-radius : 10px;
            }
        """)

        self.Graph23.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/Modul_23.png') 
            }
        """)

        self.Graph4.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/Modul_4.png')
            }
        """)

        self.Graph5.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/Modul_5.png')
            }
        """)

        self.Graph6.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/Modul_6.png')
            }
        """)

        self.Graph7.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/Modul_7.png')
            }
        """)

        self.Graph8.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/Modul_8.png')
            }
        """)

        self.Graph910.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/Modul_910.png')
            }
        """)

        self.Graph11.setStyleSheet("""
            QFrame {
                image: url('pages/Home/Nilai_home/Modul_11.png')
            }
        """)

    def refresh_nilai(self, npm):
        doc_ref = db.collection("Nilai").document(npm)
        doc = doc_ref.get()
        if doc.exists:
            self.generate_charts(npm, doc.to_dict())
        else:
            print(f"NPM {npm} tidak ada di Firestore.")

    def check_nilai(self, npm):
        doc_ref = db.collection("Nilai").document(npm)
        doc = doc_ref.get()
        if doc.exists:
            self.generate_charts(npm, doc.to_dict())
        else:
            print(f"NPM {npm} tidak ada di Firestore.")
        
        self.Stacked.setCurrentWidget(self.NilaiPage)

class AdminWindow(QMainWindow):
    def __init__(self, npm, nama, role):
        super().__init__()
        uic.loadUi(resource_path("pages/Home/UI_home/Admin.ui"), self)
        self.setWindowTitle("Control Practicum Center - Admin")
        self.setWindowIcon(QIcon(resource_path("public/Logo Merah.png")))

        self.WelcomeText.setText(f"Welcome {nama}!")
        
        self.show()

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
        GITHUB_TOKEN = "***REMOVED***"
        
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

class UpdaterDialog(QDialog):
    def __init__(self, parent, asset):
        super().__init__(parent)
        self.setWindowTitle("Downloading Update...")
        self.setModal(True)
        self.resize(520, 320)

        self.label = QLabel(f"Target: {asset['name']}")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.btnCancel = QPushButton("Cancel")
        self.btnClose  = QPushButton("Close")
        self.btnClose.setEnabled(False)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btnCancel)
        btns.addWidget(self.btnClose)

        lay = QVBoxLayout(self)
        lay.addWidget(self.label)
        lay.addWidget(self.bar)
        lay.addWidget(self.log, 1)
        lay.addLayout(btns)

        self.worker = DownloadWorker(asset)
        self.worker.progress.connect(self.bar.setValue)
        self.worker.status.connect(self._append)
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)

        self.btnCancel.clicked.connect(self._cancel)
        self.btnClose.clicked.connect(self.accept)

        self.worker.start()

    def _append(self, text: str):
        self.log.append(text)

    def _done(self, filename: str):
        self.bar.setValue(100)
        self.btnCancel.setEnabled(False)
        self.btnClose.setEnabled(True)
        self.setWindowTitle("Update installed")

    def _failed(self, err: str):
        self._append(f"Failed: {err}")
        self.btnCancel.setEnabled(False)
        self.btnClose.setEnabled(True)
        self.setWindowTitle("Failed install update")
        
    def _cancel(self):
        self.btnCancel.setEnabled(False)
        self._append("Cancelling update...")
        self.worker.cancel()
        time.sleep(2)
        QApplication.quit()

class Login(QMainWindow):
    def __init__(self):
        super(Login, self).__init__()
        uic.loadUi(resource_path("pages/Home/UI_home/Login.ui"), self)
        self.setWindowTitle(f"Control Practicum Center {updaterFunc.get_local_version()}")
        self.setWindowIcon(QIcon(resource_path("public/Logo Merah.png")))

        self.Login.clicked.connect(self.login)
        self.ChangePass.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.ChangePassPage))

        self.Change.clicked.connect(self.change_password)
        self.Back.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.LoginPage))

        self.Pass.setValidator(self.NoSpaceValidator(self))

        self._version_check_scheduled = False
        self.show()

        if not self._version_check_scheduled:
            self._version_check_scheduled = True
            QTimer.singleShot(0, self.checkVersion)

    def checkVersion(self):
        print("Checking Version (async)...")

        self.worker = updaterFunc.VersionChecker()
        self.worker.result.connect(self._on_version_checked)
        self.worker.error.connect(lambda err: QMessageBox.critical(self, "Error: Checking Release Version", f"Consult to your lab assistant:\n{err}"))
        self.worker.start()

    def _on_version_checked(self, outdated, local, remote):
        print(f"{local} (local) <===> {remote} (remote)")

        if outdated:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Update Available")
            msg.setText(f"New version in release: {remote}")
            msg.setInformativeText("Press update to download the new releases and replace the old files. The update is mandatory for the app.")
            update_btn = msg.addButton("Update Now", QMessageBox.AcceptRole)
            later_btn = msg.addButton("Close App", QMessageBox.RejectRole)
            msg.setDefaultButton(update_btn)
            msg.exec_()

            if msg.clickedButton() is update_btn:
                try:
                    tag, assets = updaterFunc.list_assets()
                    asset = next((a for a in assets if "NT" in a["name"]), None)
                    if not asset:
                        QMessageBox.warning(self, "Tidak ditemukan", "Asset NT tidak ditemukan di rilis ini.")
                        return

                    dlg = UpdaterDialog(self, asset)
                    dlg.exec_()
                except Exception as e:
                    QMessageBox.critical(self, "Gagal Update", f"Terjadi error saat update:\n{e}")

            elif msg.clickedButton() is later_btn:
                QApplication.quit()

    class NoSpaceValidator(QValidator):
        def __init__(self, parent=None):
            super().__init__(parent)

        def validate(self, input_text, pos):
            if " " in input_text:
                return (QValidator.Invalid, input_text, pos)
            return (QValidator.Acceptable, input_text, pos)

        def fixup(self, input_text):
            return input_text.replace(" ", "")
    
    def is_valid_npm(self, npm):
        return npm.isdigit() and len(npm) >= 10

    def login(self):
        npm = self.NPM.text().strip()
        password = self.Pass.text().strip().replace(' ', '')

        if not self.is_valid_npm(npm):
            QMessageBox.warning(self, "Login Failed", "ID Number is Invalid.")
            return

        try:
            doc_ref = db.collection('Account').document(npm)
            user_data_doc = doc_ref.get() 
            
            if not user_data_doc.exists:
                QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Pass.")
                return

            user_data = user_data_doc.to_dict()

            if user_data is None:
                QMessageBox.critical(self, "Login Failed", "Unknown Login")
                return

            stored_pass = user_data.get('Pass')
            nama = user_data.get('Nama')
            role = user_data.get('Role')
            kelompok = user_data.get('Kelompok')

            if stored_pass == password:
                
                if role == 'Mahasiswa':
                    self.main_window = MainWindow(npm, nama, role, kelompok) 
                    self.main_window.show()
                elif role == 'Assisten':
                    self.main_window = AdminWindow(npm, nama, role) 
                    self.main_window.show()
                
                self.close()
                
            else:
                QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Password.")

        except Exception as e:
            print("Firebase error:", e)  # debug di console
    
    def change_password(self):
        npm = self.NPM.text().strip()
        password = self.Pass.text().strip().replace(' ', '')

        if not self.is_valid_npm(npm):
            QMessageBox.warning(self, "Failed", "ID Number is Invalid.")
            return

        try:
            doc_ref = db.collection('Account').document(npm)
            user_data_doc = doc_ref.get()

            if not user_data_doc.exists:
                QMessageBox.critical(self, "Failed", "Invalid ID Number or Password.")
                return
            
            user_data = user_data_doc.to_dict()

            stored_pass = user_data.get('Pass')
            nama = user_data.get('Nama')
            role = user_data.get('Role')

            if stored_pass == password:
                if self.NewPass.text() != self.ConfirmPass.text():
                    QMessageBox.warning(self, "Failed", "Wrong Confirm Password.")
                    return
                
                new_password = self.NewPass.text().strip().replace(' ', '')

                doc_ref.update({'Pass': new_password})

                QMessageBox.information(self, "Success", "Password has successfully changed.")

                if role == 'Mahasiswa':
                    self.main_window = MainWindow(npm, nama, role)
                    self.main_window.show()
                elif role == 'Assisten':
                    self.main_window = AdminWindow(npm, nama, role) 
                    self.main_window.show()
                
                self.close()
                
            else:
                QMessageBox.critical(self, "Failed", "Invalid ID Number or Password.")

        except Exception as e:
            print("Firebase error:", e)  # debug di console
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to Database: {e}")


def main():
    app = QApplication(sys.argv)

    window = Login()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()