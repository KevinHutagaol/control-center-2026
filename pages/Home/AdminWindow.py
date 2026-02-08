import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from matplotlib import pyplot as plt

from pages.Home.Login import Login
from pages.Home.installerUtils import resource_path
from pages.Modul4.mainCDRL import exec_CDRL
from pages.Modul5.mainCDFR import exec_CDFR
from pages.Modul7.mainCOD import exec_COD
from pages.Modul910.mainDMMCD import exec_DMMCD


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

    def run_motor(self, nama, npm, kelompok, id_token):
        print("Running DMMCD")
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
