import sys, time, csv
import numpy as np
from collections import deque
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon, QValidator
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy import signal
import serial, serial.tools.list_ports
from pathlib import Path


import pages.Modul6.resource_rc6 as resource_rc6

from pages.Modul6.UI6.ui_Main import Ui_MainWindow

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


# ---------------- Matplotlib Canvas ----------------
class MplCanvas(FigureCanvas):
    def __init__(self):
        fig = Figure(figsize=(6,5), dpi=100, facecolor="none")
        self.fig = fig
        self.ax1 = fig.add_subplot(211)
        self.ax2 = fig.add_subplot(212, sharex=self.ax1)
        fig.tight_layout(pad=2)
        super().__init__(fig)


# ---------------- Main App ----------------
class MainApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("RLC State Space Simulation (Realtime)")
        self.setWindowIcon(QIcon("Asset/Logo Merah.png"))

        # Canvas untuk grafik
        self.canvas = MplCanvas()
        layout = QtWidgets.QVBoxLayout(self.PlotFrame)
        layout.addWidget(self.canvas)

        # Data simulasi
        self.model_t, self.model_il, self.model_vc2 = None, None, None
        self.current_index = 0
        self.running = False

        # Tombol
        self.Run.clicked.connect(self.run_clicked)
        self.Chart.clicked.connect(self.save_chart)
        self.CSV.clicked.connect(self.save_csv)
        self.RangkaianA.clicked.connect(self.rangkaian_a)
        self.RangkaianB.clicked.connect(self.rangkaian_b)

        # Timer animasi realtime
        self.sim_timer = QtCore.QTimer()
        self.sim_timer.setInterval(50)  # update tiap 50 ms (~20 fps)
        self.sim_timer.timeout.connect(self.update_simulation)

        # Deteksi otomatis display meter (biar gak error kalau beda nama)
        self.amp_meter = getattr(self, "NoAmpmeter", None)
        self.volt_meter = getattr(self, "NoVoltmeter", None)

        self.show()


    # ---------- Label State ----------
    def rangkaian_a(self):
        self.DOT1.setText("dIL")
        self.DOT2.setText("dVC1")
        self.DOT3.setText("dVC2")
        self.State1.setText("IL")
        self.State2.setText("VC1")
        self.State3.setText("VC2")
        self.OutputState1.setText("IL")
        self.OutputState2.setText("VC1")
        self.OutputState3.setText("VC2")

    def rangkaian_b(self):
        self.DOT1.setText("dIL1")
        self.DOT2.setText("dIL2")
        self.DOT3.setText("dVC")
        self.State1.setText("IL1")
        self.State2.setText("IL2")
        self.State3.setText("VC")
        self.OutputState1.setText("IL1")
        self.OutputState2.setText("IL2")
        self.OutputState3.setText("VC")


    # ---------- Ambil Matriks ----------
    def get_matrix(self):
        try:
            A = np.array([
                [float(self.A1.text()), float(self.A2.text()), float(self.A3.text())],
                [float(self.A4.text()), float(self.A5.text()), float(self.A6.text())],
                [float(self.A7.text()), float(self.A8.text()), float(self.A9.text())]
            ])
            B = np.array([
                [float(self.B1.text())],
                [float(self.B2.text())],
                [float(self.B3.text())]
            ])
            C = np.array([
                [float(self.C1.text()), float(self.C2.text()), float(self.C3.text())],
                [float(self.C4.text()), float(self.C5.text()), float(self.C6.text())],
                [float(self.C7.text()), float(self.C8.text()), float(self.C9.text())]
            ])
            D = np.array([
                [float(self.D1.text())],
                [float(self.D2.text())],
                [float(self.D3.text())]
            ])
            return A,B,C,D
        except:
            return None


    # ---------- Jalankan Simulasi ----------
    def run_clicked(self):
        matrices = self.get_matrix()
        if matrices is None:
            QMessageBox.warning(self, "Error", "Isi semua matriks terlebih dahulu.")
            return

        A,B,C,D = matrices
        try:
            sys_ss = signal.StateSpace(A,B,C,D)

            # 10 detik, step 12V mulai t>1s
            self.model_t = np.linspace(0,10,1000)
            u = np.zeros_like(self.model_t)
            u[self.model_t > 1] = 12.0
            _, y_out, _ = signal.lsim(sys_ss, U=u, T=self.model_t)
            self.model_il = y_out[:,0]
            self.model_vc2 = y_out[:,2]

            # Reset tampilan
            self.canvas.ax1.cla()
            self.canvas.ax2.cla()
            self.current_index = 0
            self.running = True
            self.sim_start_time = time.time()

            self.sim_timer.start()

        except Exception as e:
            QMessageBox.critical(self,"Error",f"Gagal hitung step response:\n{e}")


    # ---------- Update animasi realtime ----------
    def update_simulation(self):
        if not self.running or self.model_t is None:
            return

        elapsed = time.time() - self.sim_start_time
        if elapsed > 10.0:
            self.sim_timer.stop()
            self.running = False
            return

        idx = np.searchsorted(self.model_t, elapsed)
        if idx >= len(self.model_t):
            idx = len(self.model_t)-1
        self.current_index = idx

        t = self.model_t[:idx]
        il = self.model_il[:idx]
        vc2 = self.model_vc2[:idx]

        # ✅ Update live meter display
        if self.amp_meter:
            self.amp_meter.display(round(self.model_il[idx], 3))
        if self.volt_meter:
            self.volt_meter.display(round(self.model_vc2[idx], 3))

        # Gambar grafik
        self.canvas.ax1.cla()
        self.canvas.ax2.cla()
        self.canvas.ax1.plot(t, il, color="white")
        self.canvas.ax2.plot(t, vc2, color="white")

        self.canvas.ax1.set_ylabel("Arus (A)", color="white")
        self.canvas.ax2.set_ylabel("Tegangan (V)", color="white")
        self.canvas.ax1.relim(); self.canvas.ax1.autoscale()
        self.canvas.ax2.relim(); self.canvas.ax2.autoscale()
        self.canvas.ax1.tick_params(colors="white")
        self.canvas.ax2.tick_params(colors="white")
        for ax in [self.canvas.ax1, self.canvas.ax2]:
            ax.set_facecolor("none")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            for spine in ax.spines.values():
                spine.set_color("white")

        self.canvas.draw()


    # ---------- Simpan Data ----------
    def save_csv(self):
        if self.model_t is None:
            return
        fname,_ = QtWidgets.QFileDialog.getSaveFileName(self,"Save","data.csv","CSV Files (*.csv)")
        if not fname: return
        with open(fname,"w",newline="") as f:
            w=csv.writer(f)
            w.writerow(["t","IL","VC2"])
            for a,b,c in zip(self.model_t,self.model_il,self.model_vc2):
                w.writerow([a,b,c])

    def save_chart(self):
        if self.model_t is None:
            return
        fname,_ = QtWidgets.QFileDialog.getSaveFileName(self,"Save","chart.png","PNG Files (*.png);;JPEG Files (*.jpg)")
        if not fname: return
        self.canvas.figure.savefig(fname)


# ---------------- Main ----------------
def exec_SSM(nama, npm):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    w = MainApp()
    w.show()
    return w