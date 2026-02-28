import io
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QMainWindow, QApplication, QVBoxLayout, QMessageBox, QDialog, QToolBar, QAction)
import control as ct
import pages.Modul2.resourcesmodul2

from pages.Modul2.ui.ui_MainModul2 import Ui_MainWindow

class FullScreenPlot(QDialog):
    def __init__(self, parent=None, title="Full Screen Plot"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)
        
        # Layout
        self.layout = QVBoxLayout(self)
        
        # Matplotlib Setup
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)
        
    def plot_data(self, t, y, title, xlabel, ylabel, plot_type="step", 
                  plant_poles=None, plant_zeros=None, 
                  ctrl_poles=None, ctrl_zeros=None, 
                  current_poles=None): 
        self.ax.clear()
        
        if plot_type == "step":
            self.ax.plot(t, y, linewidth=2)
            self.ax.grid(True)
            
        elif plot_type == "rlocus":
            self.ax.plot(t, y, linewidth=1, alpha=1) # Garis lintasan
            
            # --- Plot Plant Poles & Zeros ---
            if plant_poles is not None and len(plant_poles) > 0:
                self.ax.scatter(np.real(plant_poles), np.imag(plant_poles), 
                              marker='x', color='red', s=50, label='Plant Poles')
            
            if plant_zeros is not None and len(plant_zeros) > 0:
                self.ax.scatter(np.real(plant_zeros), np.imag(plant_zeros), 
                              marker='o', color='blue', s=50, label='Plant Zeros')

            # --- Plot Controller Poles & Zeros ---
            if ctrl_poles is not None and len(ctrl_poles) > 0:
                self.ax.scatter(np.real(ctrl_poles), np.imag(ctrl_poles), 
                              marker='x', color='green', s=70, label='Ctrl Poles')
                
            if ctrl_zeros is not None and len(ctrl_zeros) > 0:
                self.ax.scatter(np.real(ctrl_zeros), np.imag(ctrl_zeros), 
                              marker='o', color='orange', s=70, label='Ctrl Zeros')

            # --- Plot Current Closed-Loop Poles ---
            if current_poles is not None and len(current_poles) > 0:
                self.ax.scatter(np.real(current_poles), np.imag(current_poles), 
                              marker='s', color='magenta', s=80, label='CL Poles (Current)', zorder=10)

            self.ax.axhline(0, color='black', lw=1, linestyle='--')
            self.ax.axvline(0, color='black', lw=1, linestyle='--')
            self.ax.legend(loc='best', fontsize='small') 
            self.ax.grid(True)
            
        self.ax.set_title(title)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        self.canvas.draw()


class MainModul(QMainWindow, Ui_MainWindow):
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
        self.setFixedSize(1360, 750)

        self.root_locus_open_png_bytes = None
        self.step_response_open_png_bytes = None

    def grab_figures_as_images(self):
        rl_buf = io.BytesIO()
        sr_buf = io.BytesIO()

        self.fig_rl.savefig(rl_buf, format='png', bbox_inches='tight')
        self.fig_sr.savefig(sr_buf, format='png', bbox_inches='tight')

        self.root_locus_open_png_bytes = rl_buf.getvalue()
        self.step_response_open_png_bytes = sr_buf.getvalue()

        rl_buf.close()
        sr_buf.close()

        print("Grabbed Figures as Variables")

        # TODO: This is for testing, remove later
        with open("saved_root_locus.png", "wb") as f:
            f.write(self.root_locus_open_png_bytes)

    def init_matplotlib_canvas(self):
        # --- Setup Root Locus ---
        self.layout_rl = QVBoxLayout(self.rootLocusPlotWidget)
        self.fig_rl, self.ax_rl = plt.subplots()
        self.fig_rl.set_facecolor('#f0f0f0')
        self.canvas_rl = FigureCanvas(self.fig_rl)
        self.layout_rl.addWidget(self.canvas_rl)
        self.ax_rl.set_title("Root Locus (Empty)")
        self.ax_rl.grid(True)

        # Event click untuk Root Locus
        self.canvas_rl.mpl_connect('button_press_event', self.on_rl_click)

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

    # --- Logic 1: Generate Plot (OPEN LOOP) ---
    def run_open_loop(self):
        G = self.get_plant_tf()
        if G is None: return

        self.is_closed_loop = False
        print("Plotting Open Loop G(s)...")

        # 1. Plot Root Locus (Open Loop)
        self.ax_rl.clear()
        rlist, klist = ct.root_locus(G, plot=False)
        
        self.ax_rl.plot(np.real(rlist), np.imag(rlist))
        
        poles = ct.poles(G)
        zeros = ct.zeros(G)
        self.ax_rl.scatter(np.real(poles), np.imag(poles), marker='x', color='red', s=50, label='Poles')
        self.ax_rl.scatter(np.real(zeros), np.imag(zeros), marker='o', color='blue', s=50, label='Zeros')
        
        self.ax_rl.axhline(0, color='black', lw=1, linestyle='--')
        self.ax_rl.axvline(0, color='black', lw=1, linestyle='--')
        self.ax_rl.set_title("Root Locus (Open Loop Plant)")
        self.ax_rl.grid(True)
        self.canvas_rl.draw()

        # Simpan data untuk fullscreen
        self.last_rl_data = (np.real(rlist), np.imag(rlist), poles, zeros, [], [], None)

        # 2. Plot Step Response (Open Loop)
        self.ax_sr.clear()
        t, y = ct.step_response(G)
        self.ax_sr.plot(t, y, 'b-', linewidth=2, label='Open Loop')
        self.ax_sr.set_title("Step Response (Open Loop)")
        self.ax_sr.grid(True)
        self.ax_sr.legend()
        self.canvas_sr.draw()

        # Simpan data untuk fullscreen
        self.last_step_data = (t, y)

        # 3. Update Metrics
        self.update_metrics(t, y)

        # TODO: This is for testing, remove later
        self.grab_figures_as_images()


    # --- Logic 2: Plot with Controller (CLOSED LOOP) ---
    def run_closed_loop(self):
        G = self.get_plant_tf() # Ambil Transfer Function Plant
        if G is None: return

        try:
            # Fungsi helper kecil untuk membaca input string seperti "-2, -3.5"
            # dan mengubahnya menjadi list float [-2.0, -3.5]
            def parse_roots(text):
                if not text.strip():
                    return []
                # Tambahkan tanda minus (-) di depan float()
                return [-float(x.strip()) for x in text.split(',')]

            # --- 1. Ambil Parameter Controller ---
            # inputP sekarang jadi Poles, inputI jadi Zeros
            c_poles = parse_roots(self.inputP.text()) 
            c_zeros = parse_roots(self.inputI.text()) 
            gain = float(self.inputGain.text()) if self.inputGain.text() else 1.0
            
            # inputD diabaikan sesuai request lu

            # --- 2. Buat Transfer Function Controller (Pole-Zero) ---
            # np.poly([r1, r2]) akan membuat koefisien (s - r1)(s - r2)
            num_c = np.poly(c_zeros) 
            den_c = np.poly(c_poles) 
            
            # C(s) = Gain * (Zeros / Poles)
            C_tf = ct.tf(num_c, den_c)
            C_total = gain * C_tf

            # --- 3. Hitung Loop & Closed Loop ---
            # L(s) = C(s) * G(s) -> Open Loop (untuk gambar Root Locus)
            L = ct.series(C_total, G)

            # T(s) = L(s) / (1 + L(s)) -> Closed Loop (untuk Step Response)
            T = ct.feedback(L, 1)

            self.is_closed_loop = True
            print(f"Plotting Closed Loop T(s) with Gain={gain}, Poles={c_poles}, Zeros={c_zeros}...")

            # =========================================
            # A. PLOT ROOT LOCUS
            # =========================================
            self.ax_rl.clear()
            
            # 1. Gambar Garis Lintasan (Trajectory) dari L(s)
            rlist, klist = ct.root_locus(L, plot=False)
            self.ax_rl.plot(np.real(rlist), np.imag(rlist), linewidth=1, alpha=0.5)
            
            # 2. Plot Poles & Zeros PLANT (G)
            p_plant = ct.poles(G)
            z_plant = ct.zeros(G)
            
            if len(p_plant) > 0:
                self.ax_rl.scatter(np.real(p_plant), np.imag(p_plant), 
                                 marker='x', color='red', s=50, label='Plant Poles')
            if len(z_plant) > 0:
                self.ax_rl.scatter(np.real(z_plant), np.imag(z_plant), 
                                 marker='o', color='blue', s=50, label='Plant Zeros')

            # 3. Plot Poles & Zeros CONTROLLER (C)
            # c_poles dan c_zeros diambil langsung dari input text (list of floats)
            if len(c_poles) > 0:
                self.ax_rl.scatter(np.real(c_poles), np.imag(c_poles), 
                                 marker='x', color='green', s=70, label='Ctrl Poles')
            if len(c_zeros) > 0:
                # Pakai warna orange/kuning gelap biar beda sama zero plant yang biru
                self.ax_rl.scatter(np.real(c_zeros), np.imag(c_zeros), 
                                 marker='o', color='orange', s=70, label='Ctrl Zeros')
            
            # 4. Plot POLES SAAT INI (Closed Loop T) akibat Gain
            current_cl_poles = ct.poles(T)
            self.ax_rl.scatter(np.real(current_cl_poles), np.imag(current_cl_poles), 
                               marker='s', color='magenta', s=80, 
                               label=f'CL Poles (Current)', zorder=10)
            
            # 5. Kosmetik Grafik
            self.ax_rl.axhline(0, color='black', lw=1, linestyle='--')
            self.ax_rl.axvline(0, color='black', lw=1, linestyle='--')
            self.ax_rl.set_title("Root Locus (L = C*G)")
            self.ax_rl.grid(True)
            
            # Biar legendanya gak nutupin grafik, kita taruh dengan rapi
            self.ax_rl.legend(loc='best', fontsize='small')
            self.canvas_rl.draw()

            # 6. SIMPAN DATA UNTUK FULLSCREEN
            # Kita tetap simpan poles(L) dan zeros(L) gabungan agar class FullScreenPlot yang 
            # lama tidak error, karena dia cuma nerima 1 set parameter poles & zeros.
            self.last_rl_data = (np.real(rlist), np.imag(rlist), p_plant, z_plant, c_poles, c_zeros, current_cl_poles)

            # =========================================
            # B. PLOT STEP RESPONSE
            # =========================================
            self.ax_sr.clear()
            
            t, y = ct.step_response(T)
            
            self.ax_sr.plot(t, y, 'r-', linewidth=2, label='Closed Loop')
            self.ax_sr.axhline(1, color='green', linestyle=':', label='Setpoint (1.0)')
            
            self.ax_sr.set_title("Step Response (Closed Loop)")
            self.ax_sr.set_xlabel("Time (s)")
            self.ax_sr.set_ylabel("Amplitude")
            self.ax_sr.grid(True)
            self.ax_sr.legend()
            self.canvas_sr.draw()
            
            self.last_step_data = (t, y)

            # =========================================
            # C. UPDATE METRICS
            # =========================================
            self.update_metrics(t, y)

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Pastikan nilai Poles/Zeros/Gain adalah angka yang valid (gunakan koma untuk >1 nilai).")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Terjadi kesalahan: {str(e)}")
            print(e)

    # --- Fitur Full Screen saat Klik ---
    def on_rl_click(self, event):
        if event.inaxes is not None and self.last_rl_data: 
             self.show_fullscreen("Root Locus", "Real Axis", "Imag Axis", "rlocus")

    def on_sr_click(self, event):
        if event.inaxes is not None and self.last_step_data:
             self.show_fullscreen("Step Response", "Time (s)", "Amplitude", "step")

    def show_fullscreen(self, title, xlabel, ylabel, plot_type):
        dialog = FullScreenPlot(self, title)
        
        if plot_type == "step":
            if self.last_step_data:
                t, y = self.last_step_data
                dialog.plot_data(t, y, title, xlabel, ylabel, plot_type)
                
        elif plot_type == "rlocus":
            if self.last_rl_data:
                # Cek panjang tuple untuk kompatibilitas (Open Loop vs Closed Loop)
                if len(self.last_rl_data) == 7:
                    real, imag, p_plant, z_plant, c_poles, c_zeros, current_poles = self.last_rl_data
                    dialog.plot_data(real, imag, title, xlabel, ylabel, plot_type, 
                                   plant_poles=p_plant, plant_zeros=z_plant,
                                   ctrl_poles=c_poles, ctrl_zeros=c_zeros,
                                   current_poles=current_poles)
                elif len(self.last_rl_data) == 5: # Fallback untuk Open Loop
                    real, imag, poles, zeros, current_poles = self.last_rl_data
                    dialog.plot_data(real, imag, title, xlabel, ylabel, plot_type, 
                                   plant_poles=poles, plant_zeros=zeros, 
                                   current_poles=current_poles)
                
        dialog.exec_()

def launch_modul2():
    window = MainModul()
    window.show()

    return window

if __name__ == "__main__":
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = MainModul()
    window.show()
    sys.exit(app.exec_())