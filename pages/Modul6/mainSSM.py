import sys, time, csv
import numpy as np
from collections import deque
from PyQt5 import QtCore, QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon, QValidator
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy import signal
import serial, serial.tools.list_ports
from pathlib import Path


import pages.Modul6.resource_rc6 as resource_rc6

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


# ---------------- Serial Worker ----------------
class SerialWorker(QtCore.QThread):
    sample_ready = QtCore.pyqtSignal(float, float, float)  # t, IL, VC2
    finished = QtCore.pyqtSignal()

    def __init__(self, port, baud=115200, parent=None):
        super().__init__(parent)
        self.port = port
        self.baud = baud
        self._running = False

    def run(self):
        try:
            ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)
            ser.reset_input_buffer()
            ser.write(b"MEASURE\n")   # trigger ESP
            self._running = True

            while self._running:
                line = ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue
                if line.upper() == "DONE":
                    break
                parts = line.split(",")
                if len(parts) >= 3:
                    try:
                        ts = float(parts[0])
                        il = float(parts[1])
                        vc2 = float(parts[2])
                        self.sample_ready.emit(ts, il, vc2)
                    except:
                        pass
            ser.close()
        except Exception as e:
            print("Serial error:", e)
        self.finished.emit()

    def stop(self):
        self._running = False

# ---------------- Matplotlib Canvas ----------------
class MplCanvas(FigureCanvas):
    def __init__(self):
        fig = Figure(figsize=(6,5), dpi=100, facecolor="none")
        self.ax1 = fig.add_subplot(211)
        self.ax2 = fig.add_subplot(212, sharex=self.ax1)
        fig.tight_layout(pad=2)
        super().__init__(fig)

# ---------------- Main App ----------------
class MainApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path("Main.ui"), self)
        print(resource_path("Main.ui"))
        self.setWindowTitle("RLC Meter - Circuit Modeling")
        self.setWindowIcon(QIcon("Asset/Logo Merah.png"))

        # plot
        self.canvas = MplCanvas()
        layout = QtWidgets.QVBoxLayout(self.PlotFrame)
        layout.addWidget(self.canvas)

        # buffer
        self.tbuf = deque(maxlen=5000)
        self.ilbuf = deque(maxlen=5000)
        self.vc2buf = deque(maxlen=5000)

        self.worker = None
        self.model_t, self.model_il, self.model_vc2 = None, None, None

        # tombol
        self.Run.clicked.connect(self.run_clicked)
        self.Chart.clicked.connect(self.save_chart)
        self.CSV.clicked.connect(self.save_csv)

        self.RangkaianA.clicked.connect(self.rangkaian_a)
        self.RangkaianB.clicked.connect(self.rangkaian_b)

        # timer redraw
        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.redraw)
        self.timer.start()

        # scan COM
        self.scan_com()


        self.show()

    
    def rangkaian_a(self):
        self.DOT1.setText(f"dIL")
        self.DOT2.setText(f"dVC1")
        self.DOT3.setText(f"dVC2")

        self.State1.setText(f"IL")
        self.State2.setText(f"VC1")
        self.State3.setText(f"VC2")

        self.OutputState1.setText(f"IL")
        self.OutputState2.setText(f"VC1")
        self.OutputState3.setText(f"VC2")

    def rangkaian_b(self):
        self.DOT1.setText(f"dIL1")
        self.DOT2.setText(f"dIL2")
        self.DOT3.setText(f"dVC")

        self.State1.setText(f"IL1")
        self.State2.setText(f"IL2")
        self.State3.setText(f"VC")

        self.OutputState1.setText(f"IL1")
        self.OutputState2.setText(f"IL2")
        self.OutputState3.setText(f"VC")

    # ---------------- Helper ----------------
    def scan_com(self):
        self.COMlist.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.COMlist.addItem(p.device)

    def get_matrix(self):
        try:
            A = np.array([[float(self.A1.text()), float(self.A2.text()), float(self.A3.text())],
                          [float(self.A4.text()), float(self.A5.text()), float(self.A6.text())],
                          [float(self.A7.text()), float(self.A8.text()), float(self.A9.text())]])
            B = np.array([[float(self.B1.text())],
                          [float(self.B2.text())],
                          [float(self.B3.text())]])
            C = np.array([[float(self.C1.text()), float(self.C2.text()), float(self.C3.text())],
                          [float(self.C4.text()), float(self.C5.text()), float(self.C6.text())],
                          [float(self.C7.text()), float(self.C8.text()), float(self.C9.text())]])
            D = np.array([[float(self.D1.text())],
                          [float(self.D2.text())],
                          [float(self.D3.text())]])
            return A,B,C,D
        except:
            return None

    # ---------------- Run ----------------
    def run_clicked(self):
        com = self.COMlist.currentText()
        matrices = self.get_matrix()
        if not com or matrices is None:
            QMessageBox.warning(self, "Error", "Pilih COM dan isi semua matriks.")
            return

        # clear buffer
        self.tbuf.clear(); self.ilbuf.clear(); self.vc2buf.clear()

        # jalankan worker
        self.worker = SerialWorker(com)
        self.worker.sample_ready.connect(self.on_sample)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

        # hitung respon model step
        A,B,C,D = matrices
        try:
            sys_ss = signal.StateSpace(A,B,C,D)
            t = np.linspace(0,10,1000)
            t_out, y_out = signal.step(sys_ss, T=t)
            # asumsi output[0] = IL, output[2] = VC2
            self.model_t = t_out
            self.model_il = y_out[:,0]
            self.model_vc2 = y_out[:,2]
        except Exception as e:
            QMessageBox.critical(self,"Error",f"Gagal hitung step response:\n{e}")

    def on_sample(self, t, il, vc2):
        self.tbuf.append(t)
        self.ilbuf.append(il)
        self.vc2buf.append(vc2)
        self.NoAmpmeter.display(round(il,3))
        self.NoVoltmeter.display(round(vc2,3))

    def on_finished(self):
        QMessageBox.information(self,"Info","Pengukuran selesai")

    def redraw(self):
        self.canvas.ax1.cla()
        self.canvas.ax2.cla()

        if len(self.tbuf) > 2:
            t = np.array(self.tbuf)
            il = np.array(self.ilbuf)
            vc2 = np.array(self.vc2buf)
            self.canvas.ax1.plot(t, il, color="white")
            self.canvas.ax2.plot(t, vc2, color="white")

        if self.model_t is not None:
            if self.model_il is not None:
                self.canvas.ax1.plot(self.model_t, self.model_il, '--', color="white")
            if self.model_vc2 is not None:
                self.canvas.ax2.plot(self.model_t, self.model_vc2, '--', color="white")

        # Label sumbu
        self.canvas.ax1.set_ylabel("Ampere Meter", color="white")
        self.canvas.ax2.set_ylabel("Volt Meter", color="white")

        # 🔹 Tambah batas Y
        self.canvas.ax1.set_ylim(-2, 2)
        self.canvas.ax2.set_ylim(0, 25)

        # 🔹 Custom tick: hanya dua angka (setengah & max)
        self.canvas.ax1.set_yticks([-1.5, -1, -0.5, 0, 0.5, 1, 1.5 ])
        self.canvas.ax2.set_yticks([3, 6, 9, 12, 15, 18, 21, 24])

        # 🔹 Warna teks & ticks putih
        self.canvas.ax1.tick_params(colors="white")
        self.canvas.ax2.tick_params(colors="white")

        # 🔹 Hapus legend
        # (tidak dipanggil legend)

        # 🔹 Spines transparan & border style
        for ax in [self.canvas.ax1, self.canvas.ax2]:
            ax.set_facecolor("none")  # transparan
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_linewidth(2)
            ax.spines["bottom"].set_linewidth(2)
            for spine in ax.spines.values():
                spine.set_color("white")

        self.canvas.draw()



    def save_csv(self):
        if not self.tbuf:
            return
        fname,_ = QtWidgets.QFileDialog.getSaveFileName(self,"Save","data.csv","CSV Files (*.csv)")
        if not fname: return
        with open(fname,"w",newline="") as f:
            w=csv.writer(f)
            w.writerow(["t","IL","VC2"])
            for a,b,c in zip(self.tbuf,self.ilbuf,self.vc2buf):
                w.writerow([a,b,c])
    
    def save_chart(self):
        if not self.tbuf:
            return
        fname,_ = QtWidgets.QFileDialog.getSaveFileName(self,"Save","chart.png","PNG Files (*.png);;JPEG Files (*.jpg)")
        if not fname: return
        self.canvas.fig.savefig(fname)

# ---------------- Main ----------------
def exec_SSM(nama, npm):
    app=QtWidgets.QApplication(sys.argv)
    w=MainApp()
    w.show()

    return w    