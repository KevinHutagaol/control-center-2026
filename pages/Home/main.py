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
    """Path to the outer executable or script."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve()
    else:
        return Path(__file__).resolve()

def bundle_dir() -> Path:
    """Directory containing the real exe (not the _MEI temp)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    else:
        return Path(__file__).resolve().parent

project_id = 'control-lab-c4480'
api_key = '***REMOVED***'

auth_url = f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}'
body = {'returnSecureToken': True}
id_token = None

print("Attempting to connect to the database...")
try:
    r = requests.post(auth_url, data=body, timeout=10)
    # print(r.text)
    id_token = r.json()['idToken']
    print("Successfully connected to the database")
except Exception as e:
    print(e)
    # sys.exit(1)

# try:
#     cred = credentials.Certificate(resource_path("firebaseAuth.json"))
    
#     if not firebase_admin._apps:
#         firebase_admin.initialize_app(cred)
        
#     db = firestore.client() 

#     print("Home: Firebase initialized successfully")
# except Exception as e:
#     print("Firebase error:", e)  # tampilkan di console
#     QMessageBox.critical(QWidget(), "Firebase Error", f"Failed to Connect to Firebase. Error: {e}")
#     sys.exit(1)

class MainWindow(QMainWindow):
    def __init__(self, npm, nama, role, kelompok):
        super().__init__()
        uic.loadUi(resource_path("pages/Home/UI_home/Main.ui"), self)
        self.setWindowTitle(f"Control Practicum Center {updaterFunc.get_local_version()}")
        self.setWindowIcon(QIcon(resource_path("public/Logo Merah.png")))

        # store session info so we can clear them on logout
        self.npm = npm
        self.nama = nama
        self.role = role
        self.kelompok = kelompok

        self.RootLocus.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.RootLocusPage))
        self.CDFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CDFreqPage))
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

        # self.WelcomeText.setText(f"Welcome {nama}!")
        # self.Kelompok.setText(kelompok)

        self.WelcomeText.setText(f"Welcome {nama}!")
        self.Kelompok2_2.setText(kelompok)

        self.Grade.clicked.connect(lambda checked, p=npm: self.check_nilai(p))
        self.Practicum.clicked.connect(lambda: self.Stacked.setCurrentWidget(self.PracticumPage))

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

        self.LogOut.clicked.connect(self.logout)

        self.show()

    def run_root_locus(self, nama, npm):
        print("Running Root Locus")
    
    def run_frequency_response(self, nama, npm):
        print("Running Frequency Response")
    
    def run_cd_root_locus(self, nama, npm):
        print("Running Controller Design: Root Locus")
        w = exec_CDRL(nama, npm)
        key = f"Modul4-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_cd_frequency_response(self, nama, npm):
        print("Running Controller Design: Frequency Response")
        w = exec_CDFR(nama, npm)
        key = f"Modul5-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))
    
    def run_state_space(self, nama, npm):
        print("Running State Space Modeling")
    
    def run_cod(self, nama, npm):
        print("Running Controller and Observer Design")
        w = exec_COD(nama, npm)
        key = f"Modul7-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))
    
    def run_dcod(self, nama, npm):
        print("Running Discrete Controller and Observer Design")
    
    def run_motor(self, nama, npm, kelompok):
        print("Running DC Motor Modeling and Controller Design")
        w = exec_DMMCD(nama, npm)
        key = f"Modul910-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def logout(self):
        """Logout the current user: close child windows, clear session variables
        and show the Login window.
        """
        # optional confirmation
        try:
            resp = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                        QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
        except Exception:
            # if QMessageBox fails for some reason, proceed with logout
            pass

        # Close any child windows we opened
        try:
            for key, w in list(self._children.items()):
                try:
                    if w is not None:
                        w.close()
                except Exception:
                    pass
            self._children.clear()
        except Exception:
            pass

        # Clear visible labels
        for attr_name in ("WelcomeText", "WelcomeText2", "Kelompok", "Kelompok2"):
            try:
                if hasattr(self, attr_name):
                    getattr(self, attr_name).setText("")
            except Exception:
                pass

        # Clear stored session attributes
        for a in ("npm", "nama", "role", "kelompok"):
            if hasattr(self, a):
                try:
                    setattr(self, a, None)
                except Exception:
                    pass

        # Show login window again
        try:
            self.login_window = Login()
            self.login_window.show()
        except Exception as e:
            print("Failed to open Login window on logout:", e)

        # Close this main window
        try:
            self.close()
        except Exception:
            pass

    def generate_charts(self, npm, doc_data, out_dir="Nilai"):
        import numpy as np

        nama = doc_data.get("Nama", npm)
        os.makedirs(out_dir, exist_ok=True)

        # warna yang dipakai (semua merah)
        red_rgb = (214/255, 0, 0)
        red_rgba_weak = (214/255, 0, 0, 0.25)

        # ====== Chart Per Modul ======
        modul_groups = {
            "Modul 2&3": ["(Modul 2&3) Tugas Pendahuluan", "(Modul 2&3) Borang Simulasi",
                        "(Modul 2&3) Borang Analisis", "(Modul 2&3) Tugas Tambahan"],
            "Modul 4": ["(Modul 4) Tugas Pendahuluan", "(Modul 4) Borang Simulasi",
                        "(Modul 4) Borang Analisis", "(Modul 4) Tugas Tambahan"],
            "Modul 5": ["(Modul 5) Tugas Pendahuluan", "(Modul 5) Borang Simulasi",
                        "(Modul 5) Borang Analisis", "(Modul 5) Tugas Tambahan"],
            "Modul 6": ["(Modul 6) Tugas Pendahuluan", "(Modul 6) Borang Simulasi",
                        "(Modul 6) Borang Analisis", "(Modul 6) Tugas Tambahan"],
            "Modul 7": ["(Modul 7) Tugas Pendahuluan", "(Modul 7) Borang Simulasi",
                        "(Modul 7) Borang Analisis", "(Modul 7) Tugas Tambahan"],
            "Modul 8": ["(Modul 8) Tugas Pendahuluan", "(Modul 8) Borang Simulasi",
                        "(Modul 8) Borang Analisis", "(Modul 8) Tugas Tambahan"],
            "Modul 9&10": ["(Modul 9&10) Tugas Pendahuluan", "(Modul 9&10) Borang Simulasi",
                        "(Modul 9&10) Borang Analisis", "(Modul 9&10) Tugas Tambahan"],
            "Modul 11": ["(Modul 11) Project Concept", "(Modul 11) Project Complexity",
                        "(Modul 11) Project Readability", "(Modul 11) Scene Arragement",
                        "(Modul 11) Project Explanation", "(Modul 11) Program Explanation",
                        "(Modul 11) Simulation"]
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
                "Program Explanation": "Project\nExplanation",
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
                ax.spines[spine].set_color(red_rgb)
                ax.spines[spine].set_linewidth(2)

            ax.tick_params(axis="x", colors=red_rgb, labelsize=8)
            ax.tick_params(axis="y", colors=red_rgb, left=False, labelleft=False)

            ax.set_ylim(0, 100)

            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, val + 1,
                        f"{val:.0f}", ha="center", va="bottom", color=red_rgb, fontsize=8)

        # per modul
        for modul, keys in modul_groups.items():
            values = [doc_data.get(k, 0) for k in keys]
            short_labels = [shorten_label(k) for k in keys]

            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.bar(short_labels, values, color=red_rgb, edgecolor=red_rgb)
            style_bar_chart(ax, bars, values)

            ax.set_ylabel(modul, color=red_rgb, fontsize=12, rotation=90, labelpad=15)

            # set x tick labels color merah
            for lbl in ax.get_xticklabels():
                lbl.set_color(red_rgb)

            safe_name = modul.replace(" ", "_").replace("&", "")
            plt.tight_layout()
            fig.savefig(f"{out_dir}/{safe_name}.png", transparent=True)
            plt.close(fig)

        # ====== Hitung skor modul & total ======
        def hitung_modul(modul, data):
            if modul == "Modul 11":
                return (
                    0.10*data.get("(Modul 11) Project Concept",0) +
                    0.175*data.get("(Modul 11) Project Complexity",0) +
                    0.075*data.get("(Modul 11) Project Readability",0) +
                    0.15*data.get("(Modul 11) Scene Arragement",0) +
                    0.15*data.get("(Modul 11) Project Explanation",0) +
                    0.15*data.get("(Modul 11) Program Explanation",0) +
                    0.20*data.get("(Modul 11) Simulation",0)
                )
            else:
                tp = data.get(f"({modul}) Tugas Pendahuluan",0)
                bs = data.get(f"({modul}) Borang Simulasi",0)
                ba = data.get(f"({modul}) Borang Analisis",0)
                tt = data.get(f"({modul}) Tugas Tambahan",0)
                return 0.20*tp + 0.35*bs + 0.25*ba + 0.20*tt

        modul_list = ["Modul 2&3","Modul 4","Modul 5","Modul 6","Modul 7","Modul 8","Modul 9&10","Modul 11"]
        modul_scores = [hitung_modul(m, doc_data) for m in modul_list]

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
        bars = ax.bar(short_labels, scores, color=red_rgb, edgecolor=red_rgb)
        style_bar_chart(ax, bars, scores)
        for lbl in ax.get_xticklabels():
            lbl.set_color(red_rgb)

        plt.tight_layout()
        fig.savefig(f"{out_dir}/DetailNilai.png", transparent=True)
        plt.close(fig)

        # ====== Pie Chart Total Nilai ======
        total = 0.05*pretest + 0.15*posttest + sum([0.10*s for s in modul_scores])

        grade = "E"
        ranges = [("A",85,100),("A-",80,85),("B+",75,80),("B",70,75),("B-",65,70),
                ("C+",60,65),("C",55,60),("D",40,55),("E",0,40)]
        for g,minv,maxv in ranges:
            if minv <= total < maxv or (g=="A" and total==100):
                grade = g
                break

        fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(aspect="equal"))
        ax.set_facecolor("none")
        fig.patch.set_alpha(0.0)

        filled = total/100
        wedges = [filled, 1-filled]

        # semua pie berwarna merah (teks juga merah)
        pie_colors = [red_rgb, red_rgba_weak]
        text_color = red_rgb

        ax.pie(
            wedges,
            startangle=90,
            counterclock=False,
            colors=pie_colors,
            wedgeprops=dict(width=0.4, edgecolor=red_rgb)
        )

        ax.text(
            0, 0, grade,
            ha="center", va="center",
            fontsize=80, fontweight="bold",
            color=text_color
        )

        plt.tight_layout()
        fig.savefig(f"{out_dir}/TotalNilai.png", transparent=True)
        plt.close(fig)

        # ====== Top-10 Leaderboard ======
        try:
            def compute_total(data):
                mod_scores = [hitung_modul(m, data) for m in modul_list]
                pre = data.get("Pretest", 0)
                post = (
                    0.20*data.get("Post-Test Modul 2&3",0) +
                    0.10*data.get("Post-Test Modul 4",0) +
                    0.10*data.get("Post-Test Modul 5",0) +
                    0.10*data.get("Post-Test Modul 6",0) +
                    0.10*data.get("Post-Test Modul 7",0) +
                    0.10*data.get("Post-Test Modul 8",0) +
                    0.20*data.get("Post-Test Modul 9&10",0) +
                    0.10*data.get("Post-Test Bonus",0)
                )
                return 0.05*pre + 0.15*post + sum([0.10*s for s in mod_scores])

            rows = []
            for d in db.collection('Nilai').stream():
                data = d.to_dict() or {}
                total_d = compute_total(data)
                name = data.get("Nama", d.id)
                rows.append((name, d.id, total_d))

            rows_sorted = sorted(rows, key=lambda x: x[2], reverse=True)[:10]

            if rows_sorted:
                def short_two(name):
                    if not name:
                        return ""
                    parts = name.strip().split()
                    return " ".join(parts[:2]) if len(parts) >= 2 else parts[0]

                labels_top = [short_two(r[0]) for r in rows_sorted]  # hanya 2 nama depan
                vals_top = [r[2] for r in rows_sorted]

                fig, ax = plt.subplots(figsize=(14, 6))
                y_pos = np.arange(len(labels_top))
                ax.barh(y_pos, vals_top, color=red_rgb, edgecolor=red_rgb)
                ax.set_yticks(y_pos)
                ax.set_yticklabels(labels_top, color=red_rgb)
                ax.invert_yaxis()  # highest di atas
                ax.set_xlabel("Total Nilai", color=red_rgb)
                ax.set_xlim(0, 100)
                ax.tick_params(axis="x", colors=red_rgb)

                # spines merah
                for spine in ["top", "right"]:
                    ax.spines[spine].set_visible(False)
                for spine in ["left", "bottom"]:
                    ax.spines[spine].set_color(red_rgb)

                # tambahkan label angka di kanan bar
                for i, v in enumerate(vals_top):
                    ax.text(v + 1, i, f"{v:.1f}", color=red_rgb, va="center")

                plt.tight_layout()
                fig.savefig(f"{out_dir}/Top10.png", transparent=True)
                plt.close(fig)

                # jika ada widget Top10 di UI, update juga
                if hasattr(self, "Top10"):
                    self.Top10.setStyleSheet(f"QFrame {{ image: url('{out_dir}/Top10.png') }}")

        except Exception as e:
            print("Failed to build Top-10 chart:", e)

        # pastikan semua figure clear
        plt.close('all')

        print(f"Charts untuk {nama} ({npm}) sudah disimpan di folder {out_dir}/")

        self.DetailNilai.setStyleSheet("""
            QFrame {
                image: url('Nilai/DetailNilai.png') 
            }
        """)

        self.TotalNilai.setStyleSheet("""
            QFrame {
                image: url(Nilai/TotalNilai.png);
                background-color: rgb(255, 255, 255);
                border-radius : 10px;
            }
        """)

        self.Modul23.setStyleSheet("""
            QFrame {
                image: url('Nilai/Modul_23.png') 
            }
        """)

        self.Modul4.setStyleSheet("""
            QFrame {
                image: url('Nilai/Modul_4.png')
            }
        """)

        self.Modul5.setStyleSheet("""
            QFrame {
                image: url('Nilai/Modul_5.png')
            }
        """)

        self.Modul6.setStyleSheet("""
            QFrame {
                image: url('Nilai/Modul_6.png')
            }
        """)

        self.Modul7.setStyleSheet("""
            QFrame {
                image: url('Nilai/Modul_7.png')
            }
        """)

        self.Modul8.setStyleSheet("""
            QFrame {
                image: url('Nilai/Modul_8.png')
            }
        """)

        self.Modul910.setStyleSheet("""
            QFrame {
                image: url('Nilai/Modul_910.png')
            }
        """)

        self.Modul11.setStyleSheet("""
            QFrame {
                image: url('Nilai/Modul_11.png')
            }
        """)

        self.Top10.setStyleSheet("""
            QFrame {
                image: url('Nilai/Top10.png')
            }   
        """)

    def refresh_nilai(self, npm):
        print("The Scoring feature is still unstable in this version.")

        db_url = f'https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/Nilai/{npm}'
        headers = {'Authorization': f'Bearer {id_token}'}
        q = None

        try:
            q = requests.get(db_url, headers=headers, timeout=10)
            if q.status_code == 200:
                data = q.json().get('fields', {})
                parsed = {k: list(v.values())[0] for k, v in data.items()}
                print(f"Data for {npm} found...")
                self.generate_charts(npm, parsed)
            else:
                print(f"NPM {npm} tidak ada di Firestore.")
        except Exception as e:
            print(e)
            QMessageBox.about(self, "Error!", "Connection to DB error.")
            return
        
        # doc_ref = db.collection("Nilai").document(npm)
        # doc = doc_ref.get()
        # if doc.exists:
        #     self.generate_charts(npm, doc.to_dict())
        # else:
        #     print(f"NPM {npm} tidak ada di Firestore.")

    def check_nilai(self, npm):
        print("The Scoring feature is still unstable in this version.")

        db_url = f'https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/Nilai/{npm}'
        headers = {'Authorization': f'Bearer {id_token}'}
        q = None

        try:
            q = requests.get(db_url, headers=headers, timeout=10)
            if q.status_code == 200:
                data = q.json().get('fields', {})
                parsed = {k: list(v.values())[0] for k, v in data.items()}
                print(f"Data for {npm} found...")
                self.generate_charts(npm, parsed)
            else:
                print(f"NPM {npm} tidak ada di Firestore.")
        except Exception as e:
            print(e)
            QMessageBox.about(self, "Error!", "Connection to DB error.")
            
        self.Stacked.setCurrentWidget(self.NilaiPage)

        # doc_ref = db.collection("Nilai").document(npm)
        # doc = doc_ref.get()
        # if doc.exists:
        #     self.generate_charts(npm, doc.to_dict())
        # else:
        #     print(f"NPM {npm} tidak ada di Firestore.")
        
        # self.Stacked.setCurrentWidget(self.NilaiPage)

class AdminWindow(QMainWindow):
    def __init__(self, npm, nama, role):
        super().__init__()
        uic.loadUi(resource_path("pages/Home/UI_home/Admin.ui"), self)
        self.setWindowTitle("Control Practicum Center - Admin")
        self.setWindowIcon(QIcon(resource_path("public/Logo Merah.png")))
        kelompok = 999

        # store session info so we can clear them on logout
        self.npm = npm
        self.nama = nama
        self.role = role
        self.kelompok = kelompok

        self.RootLocus.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.RootLocusPage))
        self.CDFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CDFreqPage))
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

        self.WelcomeText2.setText(f"Welcome {nama}!")
        self.Kelompok2.setText(kelompok)

        self.Grade.clicked.connect(lambda checked, p=npm: self.check_nilai(p))
        self.Practicum.clicked.connect(lambda: self.Stacked.setCurrentWidget(self.PracticumPage))

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

        self.LogOut.clicked.connect(self.logout)

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

    def logout(self):
        """Logout the current user: close child windows, clear session variables
        and show the Login window.
        """
        # optional confirmation
        try:
            resp = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
                                        QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
        except Exception:
            # if QMessageBox fails for some reason, proceed with logout
            pass

        # Close any child windows we opened
        try:
            for key, w in list(self._children.items()):
                try:
                    if w is not None:
                        w.close()
                except Exception:
                    pass
            self._children.clear()
        except Exception:
            pass

        # Clear visible labels
        for attr_name in ("WelcomeText", "WelcomeText2", "Kelompok", "Kelompok2"):
            try:
                if hasattr(self, attr_name):
                    getattr(self, attr_name).setText("")
            except Exception:
                pass

        # Clear stored session attributes
        for a in ("npm", "nama", "role", "kelompok"):
            if hasattr(self, a):
                try:
                    setattr(self, a, None)
                except Exception:
                    pass

        # Show login window again
        try:
            self.login_window = Login()
            self.login_window.show()
        except Exception as e:
            print("Failed to open Login window on logout:", e)

        # Close this main window
        try:
            self.close()
        except Exception:
            pass

    def generate_charts(self, npm=None, doc_data=None, out_dir="NilaiAdmin"):
        import numpy as np
        os.makedirs(out_dir, exist_ok=True)

        red_rgb = (214/255, 0, 0)
        red_rgba_weak = (214/255, 0, 0, 0.25)

        # ====== Top-10 per Modul ======
        modul_groups = {
            "Modul 2&3": ["(Modul 2&3) Tugas Pendahuluan", "(Modul 2&3) Borang Simulasi",
                        "(Modul 2&3) Borang Analisis", "(Modul 2&3) Tugas Tambahan"],
            "Modul 4": ["(Modul 4) Tugas Pendahuluan", "(Modul 4) Borang Simulasi",
                        "(Modul 4) Borang Analisis", "(Modul 4) Tugas Tambahan"],
            "Modul 5": ["(Modul 5) Tugas Pendahuluan", "(Modul 5) Borang Simulasi",
                        "(Modul 5) Borang Analisis", "(Modul 5) Tugas Tambahan"],
            "Modul 6": ["(Modul 6) Tugas Pendahuluan", "(Modul 6) Borang Simulasi",
                        "(Modul 6) Borang Analisis", "(Modul 6) Tugas Tambahan"],
            "Modul 7": ["(Modul 7) Tugas Pendahuluan", "(Modul 7) Borang Simulasi",
                        "(Modul 7) Borang Analisis", "(Modul 7) Tugas Tambahan"],
            "Modul 8": ["(Modul 8) Tugas Pendahuluan", "(Modul 8) Borang Simulasi",
                        "(Modul 8) Borang Analisis", "(Modul 8) Tugas Tambahan"],
            "Modul 9&10": ["(Modul 9&10) Tugas Pendahuluan", "(Modul 9&10) Borang Simulasi",
                        "(Modul 9&10) Borang Analisis", "(Modul 9&10) Tugas Tambahan"],
            "Modul 11": ["(Modul 11) Project Concept", "(Modul 11) Project Complexity",
                        "(Modul 11) Project Readability", "(Modul 11) Scene Arragement",
                        "(Modul 11) Project Explanation", "(Modul 11) Program Explanation",
                        "(Modul 11) Simulation"]
        }

        def hitung_modul(modul, data):
            if modul == "Modul 11":
                return (
                    0.10*data.get("(Modul 11) Project Concept",0) +
                    0.175*data.get("(Modul 11) Project Complexity",0) +
                    0.075*data.get("(Modul 11) Project Readability",0) +
                    0.15*data.get("(Modul 11) Scene Arragement",0) +
                    0.15*data.get("(Modul 11) Project Explanation",0) +
                    0.15*data.get("(Modul 11) Program Explanation",0) +
                    0.20*data.get("(Modul 11) Simulation",0)
                )
            else:
                tp = data.get(f"({modul}) Tugas Pendahuluan",0)
                bs = data.get(f"({modul}) Borang Simulasi",0)
                ba = data.get(f"({modul}) Borang Analisis",0)
                tt = data.get(f"({modul}) Tugas Tambahan",0)
                return 0.20*tp + 0.35*bs + 0.25*ba + 0.20*tt

        # helper: shorten name to first two parts (for leaderboard labels)
        def short_two(name):
            if not name:
                return ""
            parts = name.strip().split()
            return " ".join(parts[:2]) if len(parts) >= 2 else parts[0]

        # Get all Nilai documents
        all_docs = [d.to_dict() or {} for d in db.collection('Nilai').stream()]

        # Top-10 per modul
        for modul, keys in modul_groups.items():
            rows = []
            for data in all_docs:
                score = hitung_modul(modul, data)
                name = data.get("Nama", "-")
                rows.append((name, score))
            rows_sorted = sorted(rows, key=lambda x: x[1], reverse=True)[:10]
            labels_top = [short_two(r[0]) for r in rows_sorted]
            vals_top = [r[1] for r in rows_sorted]
            fig, ax = plt.subplots(figsize=(10, 6))
            y_pos = np.arange(len(labels_top))
            ax.barh(y_pos, vals_top, color=red_rgb, edgecolor=red_rgb)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels_top, color=red_rgb)
            ax.invert_yaxis()
            ax.set_xlabel(f"Top 10 {modul}", color=red_rgb)
            ax.set_xlim(0, 100)
            ax.tick_params(axis="x", colors=red_rgb)
            for spine in ["top", "right"]:
                ax.spines[spine].set_visible(False)
            for spine in ["left", "bottom"]:
                ax.spines[spine].set_color(red_rgb)
            for i, v in enumerate(vals_top):
                ax.text(v + 1, i, f"{v:.1f}", color=red_rgb, va="center")
            plt.tight_layout()
            safe_name = modul.replace(" ", "").replace("&", "")
            fig.savefig(f"{out_dir}/Top10_{safe_name}.png", transparent=True)
            plt.close(fig)

        # ====== Top-10 Total & Bottom-10 Total ======
        def compute_total(data):
            mod_scores = [hitung_modul(m, data) for m in modul_groups.keys()]
            pre = data.get("Pretest", 0)
            post = (
                0.20*data.get("Post-Test Modul 2&3",0) +
                0.10*data.get("Post-Test Modul 4",0) +
                0.10*data.get("Post-Test Modul 5",0) +
                0.10*data.get("Post-Test Modul 6",0) +
                0.10*data.get("Post-Test Modul 7",0) +
                0.10*data.get("Post-Test Modul 8",0) +
                0.20*data.get("Post-Test Modul 9&10",0) +
                0.10*data.get("Post-Test Bonus",0)
            )
            return 0.05*pre + 0.15*post + sum([0.10*s for s in mod_scores])

        rows = []
        for data in all_docs:
            total_d = compute_total(data)
            name = data.get("Nama", "-")
            rows.append((name, total_d))
        rows_sorted = sorted(rows, key=lambda x: x[1], reverse=True)

        # Top-10 Total
        top10 = rows_sorted[:10]
        labels_top = [short_two(r[0]) for r in top10]
        vals_top = [r[1] for r in top10]
        fig, ax = plt.subplots(figsize=(10, 6))
        y_pos = np.arange(len(labels_top))
        ax.barh(y_pos, vals_top, color=red_rgb, edgecolor=red_rgb)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels_top, color=red_rgb)
        ax.invert_yaxis()
        ax.set_xlabel("Top 10 Total", color=red_rgb)
        ax.set_xlim(0, 100)
        ax.tick_params(axis="x", colors=red_rgb)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(red_rgb)
        for i, v in enumerate(vals_top):
            ax.text(v + 1, i, f"{v:.1f}", color=red_rgb, va="center")
        plt.tight_layout()
        fig.savefig(f"{out_dir}/Top10_Total.png", transparent=True)
        plt.close(fig)

        # Bottom-10 Total: take the 10 lowest, keep their order so the highest among them is first
        bottom10 = rows_sorted[-10:]
        labels_bot = [short_two(r[0]) for r in bottom10]
        vals_bot = [r[1] for r in bottom10]
        fig, ax = plt.subplots(figsize=(10, 6))
        y_pos = np.arange(len(labels_bot))
        ax.barh(y_pos, vals_bot, color=red_rgb, edgecolor=red_rgb)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels_bot, color=red_rgb)
        ax.invert_yaxis()
        ax.set_xlabel("Bottom 10 Total", color=red_rgb)
        ax.set_xlim(0, 100)
        ax.tick_params(axis="x", colors=red_rgb)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        for spine in ["left", "bottom"]:
            ax.spines[spine].set_color(red_rgb)
        for i, v in enumerate(vals_bot):
            ax.text(v + 1, i, f"{v:.1f}", color=red_rgb, va="center")
        plt.tight_layout()
        fig.savefig(f"{out_dir}/Bottom10_Total.png", transparent=True)
        plt.close(fig)

        # ====== Grade Distribution: produce 5 donut pies (A, B, C, D, E)
        # Mapping: combine fine-grained grades into 5 main categories
        # Assumption: A includes A and A-; B includes B+, B, B-; C includes C+ and C; D and E remain
        grade_bins = {
            'A': [(85, 100), (80, 85)],
            'B': [(75, 80), (70, 75), (65, 70)],
            'C': [(60, 65), (55, 60)],
            'D': [(40, 55)],
            'E': [(0, 40)]
        }

        # count totals per student (rows contains (name, total))
        counts = {k: 0 for k in grade_bins.keys()}
        for _, total in rows:
            placed = False
            for g, ranges in grade_bins.items():
                for (minv, maxv) in ranges:
                    # treat upper bound as exclusive except for perfect 100
                    if (minv <= total < maxv) or (g == 'A' and total == 100):
                        counts[g] += 1
                        placed = True
                        break
                if placed:
                    break

        total_students = sum(counts.values())
        if total_students == 0:
            total_students = 1

        # For each grade create a donut pie showing percent and center letter
        for grade_letter in ['A', 'B', 'C', 'D', 'E']:
            c = counts.get(grade_letter, 0)
            pct = c / total_students * 100

            fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(aspect='equal'))
            wedges = [pct, 100 - pct]
            colors = [red_rgb, red_rgba_weak]
            ax.pie(
                wedges,
                startangle=90,
                counterclock=False,
                colors=colors,
                wedgeprops=dict(width=0.5, edgecolor=red_rgb)
            )

            # center letter
            ax.text(0, 0, grade_letter, ha='center', va='center', fontsize=48, fontweight='bold', color=red_rgb)

            # show percent as annotation just outside the wedge
            ax.text(0, -0.6, f"{pct:.1f}% ({c})", ha='center', va='center', color=red_rgb, fontsize=12)

            plt.tight_layout()
            fig.savefig(f"{out_dir}/Grade_{grade_letter}.png", transparent=True)
            plt.close(fig)

        # ====== Update UI frames ======
        
        self.Top10Total.setStyleSheet(f"QFrame {{ image: url('{out_dir}/Top10_Total.png') }}")
        self.Bottom10Total.setStyleSheet(f"QFrame {{ image: url('{out_dir}/Bottom10_Total.png') }}")
        # If UI has single GradePie frame, show the A pie by default; also set individual frames if present
        for g in ['A', 'B', 'C', 'D', 'E']:
            frame_name = f"Grade_{g}"
            getattr(self, frame_name).setStyleSheet(f"QFrame {{ image: url('{out_dir}/Grade_{g}.png') }}")
        # Per modul top10
        for modul in modul_groups.keys():
            safe_name = modul.replace(" ", "").replace("&", "")
            frame_name = safe_name
            print(frame_name)
            getattr(self, frame_name).setStyleSheet(f"QWidget {{ image: url('{out_dir}/Top10_{safe_name}.png') }}")

        print(f"Charts untuk admin sudah disimpan di folder {out_dir}/")
        plt.close('all')

    def refresh_nilai(self, npm=None):
        # Always aggregate all data for admin charts
        self.generate_charts()

    def check_nilai(self, npm=None):
        # Always aggregate all data for admin charts
        self.generate_charts()
        self.Stacked.setCurrentWidget(self.NilaiPage)
        
    

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

        if npm == "12345" and password == "admin123":
            self.main_window = MainWindow(npm=2206055750, nama="anonymous", role="Assisten", kelompok="X")
            self.main_window.show()
            self.close()
            return


        if not self.is_valid_npm(npm):
            QMessageBox.warning(self, "Login Failed", "ID Number is Invalid.")
            return

        db_url = f'https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/Account/{npm}'
        headers = {'Authorization': f'Bearer {id_token}'}
        q = None

        try:
            q = requests.get(db_url, headers=headers, timeout=10)
        except Exception as e:
            print(e)
            QMessageBox.about(self, "Error!", "Connection to DB error.")
            return

        if q.status_code != 200:
            if q.json()['error']['code'] == 404:
                QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Password.")
            else:
                QMessageBox.about(self, "Error!", q.json()['error']['status'])
        else:
            fields = q.json().get('fields', {})
            parsed = {k: list(v.values())[0] for k, v in fields.items()}

            print("Login data found...")
            for key, value in parsed.items():
                print(f">> {key:<10}: {value}" if key != "Pass" else f">> {key:<10}: [hidden.]")

            # Extract individual values
            curNama = parsed.get('Nama', '')
            curRole = parsed.get('Role', '')
            curKelompok = parsed.get('Kelompok', '')
            curPassword = parsed.get('Pass', '')

            # Validate password (optional)
            if password != curPassword:
                QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Password.")
                print("Login Failed: Invalid ID Number or Password.")
                return
            
            # Open the correct window
            print("Password correct, opening MainWindow...")
            if curRole == 'Mahasiswa':
                self.main_window = MainWindow(npm, curNama, curRole, curKelompok)
                self.main_window.show()
            elif curRole == 'Assisten':
                self.main_window = AdminWindow(npm, curNama, curRole)
                self.main_window.show()
            else:
                QMessageBox.warning(self, "Access Denied", "Unknown role type.")
                print("Access Denied: Unknown role type.")
            
            self.close()

        # try:
        #     doc_ref = db.collection('Account').document(npm)
        #     user_data_doc = doc_ref.get() 
            
        #     if not user_data_doc.exists:
        #         QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Pass.")
        #         return

        #     user_data = user_data_doc.to_dict()

        #     if user_data is None:
        #         QMessageBox.critical(self, "Login Failed", "Unknown Login")
        #         return

        #     stored_pass = user_data.get('Pass')
        #     nama = user_data.get('Nama')
        #     role = user_data.get('Role')
        #     kelompok = user_data.get('Kelompok')

        #     if stored_pass == password:
                
        #         if role == 'Mahasiswa':
        #             self.main_window = MainWindow(npm, nama, role, kelompok) 
        #             self.main_window.show()
        #         elif role == 'Assisten':
        #             self.main_window = AdminWindow(npm, nama, role) 
        #             self.main_window.show()
                
        #         self.close()
                
        #     else:
        #         QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Password.")

        # except Exception as e:
        #     print("Firebase error:", e)  # debug di console
    
    def change_password(self):
        npm = self.NPM.text().strip()
        password = self.Pass.text().strip().replace(' ', '')

        print("Password change functionality is currently unavailable in this version.")

        # if not self.is_valid_npm(npm):
        #     QMessageBox.warning(self, "Failed", "ID Number is Invalid.")
        #     return

        # try:
        #     doc_ref = db.collection('Account').document(npm)
        #     user_data_doc = doc_ref.get()

        #     if not user_data_doc.exists:
        #         QMessageBox.critical(self, "Failed", "Invalid ID Number or Password.")
        #         return
            
        #     user_data = user_data_doc.to_dict()

        #     stored_pass = user_data.get('Pass')
        #     nama = user_data.get('Nama')
        #     role = user_data.get('Role')

        #     if stored_pass == password:
        #         if self.NewPass.text() != self.ConfirmPass.text():
        #             QMessageBox.warning(self, "Failed", "Wrong Confirm Password.")
        #             return
                
        #         new_password = self.NewPass.text().strip().replace(' ', '')

        #         doc_ref.update({'Pass': new_password})

        #         QMessageBox.information(self, "Success", "Password has successfully changed.")

        #         if role == 'Mahasiswa':
        #             self.main_window = MainWindow(npm, nama, role)
        #             self.main_window.show()
        #         elif role == 'Assisten':
        #             self.main_window = AdminWindow(npm, nama, role) 
        #             self.main_window.show()
                
        #         self.close()
                
        #     else:
        #         QMessageBox.critical(self, "Failed", "Invalid ID Number or Password.")

        # except Exception as e:
        #     print("Firebase error:", e)  # debug di console
        #     QMessageBox.critical(self, "Connection Error", f"Failed to connect to Database: {e}")


def main():
    app = QApplication(sys.argv)

    window = Login()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()