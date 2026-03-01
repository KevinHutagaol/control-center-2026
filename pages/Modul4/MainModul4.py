import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QMainWindow, QApplication, QVBoxLayout, QMessageBox, QDialog, QToolBar, QAction)
import control as ct

import pages.Modul4.resourcesmodul4 # noqa

from pages.Modul4.ui.ui_MainModul4 import Ui_MainWindow

class FullScreenPlot(QDialog):
    def __init__(self, parent=None, title="Full Screen Plot"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 800) # Agak gedean dikit buat Bode
        
        # Layout
        self.layout = QVBoxLayout(self)
        
        # Matplotlib Setup Awal (Default 1 axes)
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        
    def plot_data(self, data_pack, title, plot_type="step"): 
        self.fig.clear() # Bersihkan figure lama
        
        if plot_type == "step":
            t, y, xlabel, ylabel = data_pack
            ax = self.fig.add_subplot(111)
            ax.plot(t, y, linewidth=2)
            ax.set_title(title)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(True)
            
        elif plot_type == "bode":
            # Unpack data Bode
            omega, mag_db, phase_deg = data_pack
            
            # Subplot 1: Magnitude
            ax_mag = self.fig.add_subplot(211)
            ax_mag.semilogx(omega, mag_db, 'b', linewidth=2)
            ax_mag.set_title(f"{title} - Bode Plot")
            ax_mag.set_ylabel("Magnitude (dB)")
            ax_mag.grid(True, which="both", ls="-")
            ax_mag.tick_params(labelbottom=False) # Hilangkan label x di grafik atas

            # Subplot 2: Phase
            ax_phase = self.fig.add_subplot(212, sharex=ax_mag)
            ax_phase.semilogx(omega, phase_deg, 'r', linewidth=2)
            ax_phase.set_xlabel("Frequency (rad/s)")
            ax_phase.set_ylabel("Phase (deg)")
            ax_phase.grid(True, which="both", ls="-")

        self.canvas.draw()


class MainModul4(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        
        self.setupUi(self)

        # 2. Setup Grafik Matplotlib
        self.init_matplotlib_canvas()

        # 3. Koneksi Tombol
        self.btnGeneratePlot.clicked.connect(self.run_open_loop)
        self.btnPlotWithController.clicked.connect(self.run_closed_loop)

        self.last_rl_data = None
        self.last_step_data = None
        self.is_closed_loop = False

        self.setWindowTitle("Control System Analyzer - v1.0")
        self.setFixedSize(1360, 800)

    def init_matplotlib_canvas(self):
        # --- UBAHAN DISINI: Setup Bode Plot (2 Subplots) ---
        self.layout_bode = QVBoxLayout(self.BodePlotWidget)
        
        # Kita pakai plt.subplots dengan 2 baris, 1 kolom
        self.fig_bode, (self.ax_mag, self.ax_phase) = plt.subplots(2, 1, sharex=True)
        self.fig_bode.set_facecolor('#f0f0f0')
        self.fig_bode.subplots_adjust(hspace=0.3, bottom=0.15) # Atur jarak antar plot
        
        self.canvas_bode = FigureCanvas(self.fig_bode)
        self.layout_bode.addWidget(self.canvas_bode)
        
        # Judul awal
        self.ax_mag.set_title("Bode Plot (Magnitude)")
        self.ax_phase.set_title("Bode Plot (Phase)")
        self.ax_mag.grid(True)
        self.ax_phase.grid(True)

        # Event click untuk Bode (biar bisa fullscreen)
        self.canvas_bode.mpl_connect('button_press_event', self.on_bode_click)

        # --- Setup Step Response ---
        self.layout_sr = QVBoxLayout(self.stepResponsePlotWidget)
        self.fig_sr, self.ax_sr = plt.subplots()
        self.fig_sr.set_facecolor('#f0f0f0')
        self.canvas_sr = FigureCanvas(self.fig_sr)
        self.layout_sr.addWidget(self.canvas_sr)
        self.ax_sr.set_title("Step Response (Empty)")
        self.ax_sr.grid(True)

        # Event click untuk Step Response
        self.canvas_sr.mpl_connect('button_press_event', self.on_sr_click)

    def get_plant_tf(self):
        try:
            def get_val(line_edit):
                txt = line_edit.text().strip()
                return float(txt) if txt else 0.0


            num = [get_val(self.num_s3), get_val(self.num_s2), get_val(self.num_s1), get_val(self.num_s0)]
            den = [get_val(self.den_s3), get_val(self.den_s2), get_val(self.den_s1), get_val(self.den_s0)]

            while len(num) > 1 and num[0] == 0: num.pop(0)
            while len(den) > 1 and den[0] == 0: den.pop(0)

            if all(v == 0 for v in den):
                raise ValueError("Denominator cannot be zero!")

            G = ct.tf(num, den)
            return G
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", f"Check inputs: {e}")
            return None

    def update_metrics(self, t, y):
        try:
            info = ct.step_info(y, T=t)
            
            os_val = info['Overshoot']
            ts_val = info['SettlingTime']
            tp_val = info['PeakTime']

            # Fungsi helper buat handle nilai NaN (Not a Number) biar gak error
            def format_val(val, unit=""):
                if val is None or np.isnan(val) or np.isinf(val):
                    return "N/A"
                return f"{val:.2f}{unit}"

            # Update Label
            self.lblOvershoot.setText(f"Overshoot: {format_val(os_val, '%')}")
            self.lblSettlingTime.setText(f"Settling Time: {format_val(ts_val, 's')}")
            self.lblPeakTime.setText(f"Peak Time: {format_val(tp_val, 's')}")

        except Exception as e:
            self.lblOvershoot.setText("Overshoot: -")
            self.lblSettlingTime.setText("Settling Time: -")
            self.lblPeakTime.setText("Peak Time: -")
            print(f"Metrics Error: {e}")

    def run_open_loop(self):
        G = self.get_plant_tf()
        if G is None: return

        self.is_closed_loop = False
        print("Plotting Open Loop Bode & Step...")

        # 1. Plot BODE (Open Loop) - GANTI ROOT LOCUS
        self.ax_mag.clear()
        self.ax_phase.clear()
        
        # Hitung Frequency Response
        # ct.bode mengembalikan: mag, phase, omega
        omega_range = np.logspace(-2, 2, 1000)
        mag, phase, omega = ct.bode(G, omega=omega_range, plot=False)
        
        # Konversi ke dB dan Derajat
        mag_db = 20 * np.log10(mag)
        phase_deg = np.degrees(phase)
        
        # Plot Magnitude
        self.ax_mag.semilogx(omega, mag_db, color='blue', lw=2)
        self.ax_mag.set_title("Bode Plot (Open Loop G)")
        self.ax_mag.set_ylabel("Magnitude (dB)")
        self.ax_mag.grid(True, which="both", linestyle='-', alpha=0.6)
        self.ax_mag.tick_params(labelbottom=False) # Hide x label for top plot
        
        # Plot Phase
        self.ax_phase.semilogx(omega, phase_deg, color='red', lw=2)
        self.ax_phase.set_ylabel("Phase (deg)")
        self.ax_phase.set_xlabel("Frequency (rad/s)")
        self.ax_phase.grid(True, which="both", linestyle='-', alpha=0.6)
        
        self.canvas_bode.draw()

        # Simpan data Bode untuk fullscreen
        self.last_bode_data = (omega, mag_db, phase_deg)

        # 2. Plot Step Response (Open Loop) - TETAP
        self.ax_sr.clear()
        t, y = ct.step_response(G)
        self.ax_sr.plot(t, y, 'b-', linewidth=2, label='Open Loop')
        self.ax_sr.set_title("Step Response (Open Loop)")
        self.ax_sr.grid(True)
        self.ax_sr.legend()
        self.canvas_sr.draw()

        # Simpan data Step untuk fullscreen
        self.last_step_data = (t, y, "Time (s)", "Amplitude")

        self.update_metrics(t, y)


    # --- Logic 2: Plot with Controller (CLOSED LOOP) ---
    def run_closed_loop(self):
        G = self.get_plant_tf()
        if G is None: return

        try:
            kp = float(self.inputP.text()) if self.inputP.text() else 0.0
            ki = float(self.inputI.text()) if self.inputI.text() else 0.0
            kd = float(self.inputD.text()) if self.inputD.text() else 0.0
            gain = float(self.inputGain.text()) if self.inputGain.text() else 1.0

            if ki == 0 and kd == 0 and kp == 0:
                C_total = gain * 1
            else:
                num_pid = [kd, kp, ki]
                den_pid = [1, 0] 
                C_pid = ct.tf(num_pid, den_pid)
                C_total = gain * C_pid

            # Loop Transfer Function (L) -> Biasanya Bode dilihat dari Loop Function untuk cek Stability Margin
            L = ct.series(C_total, G)
            # Closed Loop Transfer Function (T) -> Untuk Step Response
            T = ct.feedback(L, 1)

            self.is_closed_loop = True
            print(f"Plotting Closed Loop T(s) with Gain={gain}...")

            # =========================================
            # A. PLOT BODE (Loop Transfer Function L)
            # =========================================
            self.ax_mag.clear()
            self.ax_phase.clear()
            
            # Hitung Bode dari L (C * G)
            omega_range = np.logspace(-2, 2, 1000)
            mag, phase, omega = ct.bode(G, omega=omega_range, plot=False)
            
            mag_db = 20 * np.log10(mag)
            phase_deg = np.degrees(phase)
            
            # Plot Mag
            self.ax_mag.semilogx(omega, mag_db, color='blue', lw=2, label='L(s)')
            self.ax_mag.set_title(f"Bode Plot (Loop Function L = C*G)")
            self.ax_mag.set_ylabel("Mag (dB)")
            self.ax_mag.grid(True, which="both", ls='-', alpha=0.6)
            self.ax_mag.tick_params(labelbottom=False)
            
            # Plot Phase
            self.ax_phase.semilogx(omega, phase_deg, color='red', lw=2, label='L(s)')
            self.ax_phase.set_ylabel("Phase (deg)")
            self.ax_phase.set_xlabel("Frequency (rad/s)")
            self.ax_phase.grid(True, which="both", ls='-', alpha=0.6)
            
            # (Opsional) Tampilkan Gain Margin / Phase Margin lines jika perlu
            # Tapi untuk sekarang polos dulu biar rapi
            
            self.canvas_bode.draw()
            
            # Simpan Data Bode
            self.last_bode_data = (omega, mag_db, phase_deg)

            # =========================================
            # B. PLOT STEP RESPONSE
            # =========================================
            self.ax_sr.clear()
            t, y = ct.step_response(T)
            self.ax_sr.plot(t, y, 'r-', linewidth=2, label='Closed Loop')
            self.ax_sr.axhline(1, color='green', linestyle=':', label='Setpoint')
            
            self.ax_sr.set_title("Step Response (Closed Loop)")
            self.ax_sr.set_xlabel("Time (s)")
            self.ax_sr.set_ylabel("Amplitude")
            self.ax_sr.grid(True)
            self.ax_sr.legend()
            self.canvas_sr.draw()
            
            self.last_step_data = (t, y, "Time (s)", "Amplitude")

            self.update_metrics(t, y)

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Pastikan nilai PID/Gain valid.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Terjadi kesalahan: {str(e)}")
            print(e) 

    # --- Click Events ---
    def on_bode_click(self, event):
        if event.inaxes is not None and self.last_bode_data: 
             self.show_fullscreen("Bode Plot Analysis", "bode")

    def on_sr_click(self, event):
        if event.inaxes is not None and self.last_step_data:
             self.show_fullscreen("Step Response Analysis", "step")

    def show_fullscreen(self, title, plot_type):
        dialog = FullScreenPlot(self, title)
        
        if plot_type == "step":
            if self.last_step_data:
                dialog.plot_data(self.last_step_data, title, plot_type="step")
                
        elif plot_type == "bode":
            if self.last_bode_data:
                dialog.plot_data(self.last_bode_data, title, plot_type="bode")
                
        dialog.exec_()

def launch_modul4():
    window = MainModul4()
    window.show()

    return window

if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = MainModul4()
    window.show()
    sys.exit(app.exec_())