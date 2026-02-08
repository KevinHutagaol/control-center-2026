import os

import requests
from PyQt5 import uic
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from matplotlib import pyplot as plt

from func import updaterFunc as updaterFunc
from pages.Home.Login import Login
from pages.Home.main import project_id, id_token
from pages.Home.installerUtils import resource_path
from pages.Modul4.mainCDRL import exec_CDRL
from pages.Modul5.mainCDFR import exec_CDFR
from pages.Modul6.mainSSM import exec_SSM
from pages.Modul7.mainCOD import exec_COD
from pages.Modul8.mainDCOD import exec_DCOD
from pages.Modul910.mainDMMCD import exec_DMMCD


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
        self.RunDCOD.clicked.connect(lambda checked, n=nama, p=npm, k=kelompok: self.run_motor(n, p, k))
        self.RunMotor.clicked.connect(lambda checked, n=nama, p=npm: self.run_dcod(n, p))

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
        w = exec_SSM(nama, npm)
        key = f"Modul6-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_cod(self, nama, npm):
        print("Running Controller and Observer Design")
        w = exec_COD(nama, npm)
        key = f"Modul7-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_dcod(self, nama, npm):
        print("Running Discrete Controller and Observer Design")
        w = exec_DCOD(nama, npm)
        key = f"Modul8-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_motor(self, nama, npm, kelompok):
        print("Running DC Motor Modeling and Controller Design")
        w = exec_DMMCD(nama, npm, kelompok)
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

            # rows = []
            # for d in db.collection('Nilai').stream():
            #     data = d.to_dict() or {}
            #     total_d = compute_total(data)
            #     name = data.get("Nama", d.id)
            #     rows.append((name, d.id, total_d))

            url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/Nilai"
            headers = {"Authorization": f"Bearer {id_token}"}

            try:
                r = requests.get(url, headers=headers, timeout=10)
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Error fetching collection: {e}")
                return []

            docs = r.json().get("documents", [])
            rows = []

            for doc in docs:
                # Extract doc ID
                doc_id = doc["name"].split("/")[-1]
                # Extract fields and flatten Firestore type wrappers
                fields = doc.get("fields", {})
                data = {k: list(v.values())[0] for k, v in fields.items()}

                # Your total computation function
                total_d = compute_total(data)
                name = data.get("Nama", doc_id)

                rows.append((name, doc_id, total_d))

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
