import io
import os
import zipfile
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (QMainWindow, QApplication, QVBoxLayout, QMessageBox, QDialog, QToolBar, QAction)
import control as ct
from PyQt5.QtCore import QStandardPaths, QRegExp, Qt
from PyQt5.QtGui import QDoubleValidator, QRegExpValidator
from func.sendWithEmail import create_zip_in_memory, sendWithEmail
from func.UserContext import user_context
from func.saveToZip import saveToZip

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

        # Validator
        val_double = QDoubleValidator(-15000.0, 15000.0, 4)
        val_double.setNotation(QDoubleValidator.StandardNotation)

        # fail safe biar gak crash
        self.num_s3.setValidator(val_double)
        self.num_s2.setValidator(val_double)
        self.num_s1.setValidator(val_double)
        self.num_s0.setValidator(val_double)

        self.den_s3.setValidator(val_double)
        self.den_s2.setValidator(val_double)
        self.den_s1.setValidator(val_double)
        self.den_s0.setValidator(val_double)


        self.bod_plot_open_png_bytes = None
        self.step_response_open_png_bytes = None

        # 2. Setup Grafik Matplotlib
        self.init_matplotlib_canvas()

        # 3. Koneksi Tombol
        self.btnGeneratePlot.clicked.connect(self.run_open_loop)
        self.btnSendEmail.clicked.connect(self.onSendEmailBtnClicked)
        self.btnSaveZip.clicked.connect(self.onSaveZipClicked)

        self.last_rl_data = None
        self.last_step_data = None
        self.is_closed_loop = False

        self.system_details = {
            "plant_G": "", "plant_poles": "", "plant_zeros": "",
            "ol_step_metrics": None, "ol_bode_metrics": None,
            "ctrl_P": "", "ctrl_I": "", "ctrl_D": "", "ctrl_gain": "",
            "cl_poles": "", "cl_step_metrics": None, "cl_bode_metrics": None
        }

        self.setWindowTitle("Control System Analyzer - v1.0")
        self.setFixedSize(1360, 675)

    def grab_figures_as_images(self, is_closed_loop=False):
        """Grabs Matplotlib data and generates high-res (fullscreen) images in background"""
        with io.BytesIO() as bd_buff, io.BytesIO() as sr_buf:
            
            # Generate Fullscreen Bode Plot di Background
            bode_data = getattr(self, 'last_bode_data', None)
            if bode_data:
                # Bikin 'kertas' baru ukuran besar (10x8 inch)
                fig_bode_large = plt.figure(figsize=(10, 8))
                omega, mag_db, phase_deg = bode_data
                
                ax_mag = fig_bode_large.add_subplot(211)
                ax_mag.semilogx(omega, mag_db, 'b', linewidth=2)
                ax_mag.set_title("Bode Plot Analysis")
                ax_mag.set_ylabel("Magnitude (dB)")
                ax_mag.grid(True, which="both", ls="-")
                ax_mag.tick_params(labelbottom=False)

                ax_phase = fig_bode_large.add_subplot(212, sharex=ax_mag)
                ax_phase.semilogx(omega, phase_deg, 'r', linewidth=2)
                ax_phase.set_xlabel("Frequency (rad/s)")
                ax_phase.set_ylabel("Phase (deg)")
                ax_phase.grid(True, which="both", ls="-")
                
                # Simpan ke buffer, lalu hancurkan fig_bode_large biar RAM aman
                fig_bode_large.savefig(bd_buff, format='png', bbox_inches='tight')
                plt.close(fig_bode_large)

            # Generate Fullscreen Step Response di Background
            step_data = getattr(self, 'last_step_data', None)
            if step_data:
                # Bikin 'kertas' baru ukuran besar
                fig_sr_large = plt.figure(figsize=(10, 8))
                t, y, xlabel, ylabel = step_data
                
                ax_sr = fig_sr_large.add_subplot(111)
                ax_sr.plot(t, y, linewidth=2)
                ax_sr.set_title("Step Response Analysis")
                ax_sr.set_xlabel(xlabel)
                ax_sr.set_ylabel(ylabel)
                ax_sr.grid(True)
                
                fig_sr_large.savefig(sr_buf, format='png', bbox_inches='tight')
                plt.close(fig_sr_large)

            # --- 3. Ekstrak Bytes untuk ZIP / Email ---
            if not is_closed_loop:
                self.bod_plot_open_png_bytes = bd_buff.getvalue() if bode_data else None
                self.step_response_open_png_bytes = sr_buf.getvalue() if step_data else None
            else:
                self.bod_plot_closed_png_bytes = bd_buff.getvalue() if bode_data else None
                self.step_response_closed_png_bytes = sr_buf.getvalue() if step_data else None

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
                # fail safe jadi ngeganti koma jadi titik, kalo misalnya pake koma desimal
                txt = txt.replace(',', '.')
                return float(txt) if txt else 0.0

            num = [get_val(self.num_s3), get_val(self.num_s2), get_val(self.num_s1), get_val(self.num_s0)]
            den = [get_val(self.den_s3), get_val(self.den_s2), get_val(self.den_s1), get_val(self.den_s0)]

            # Pangkas angka 0 yang tidak penting di depan
            while len(num) > 1 and num[0] == 0: num.pop(0)
            while len(den) > 1 and den[0] == 0: den.pop(0)

            if all(v == 0 for v in den):
                raise ValueError("Denominator tidak boleh nol semua!")
            
            if all(v == 0 for v in num):
                raise ValueError("Numerator (pembilang) tidak boleh nol semua!")

            # fail safe kalo order num > dari denum
            if len(num) > len(den):
                raise ValueError("Orde Numerator tidak boleh lebih besar dari orde Denominator!\n(Sistem tidak proper).")

            G = ct.tf(num, den)
            return G
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", f"Periksa input Anda:\n{e}")
            return None

    def update_metrics(self, t, y):
        try:
            info = ct.step_info(y, T=t)
            
            os_val = info['Overshoot']
            ts_val = info['SettlingTime']
            tp_val = info['PeakTime']

            def format_val(val, unit=""):
                if val is None or np.isnan(val) or np.isinf(val):
                    return "N/A"
                return f"{val:.2f}{unit}"

            metrics_dict = {
                "Overshoot": format_val(os_val, '%'),
                "Settling Time": format_val(ts_val, 's'),
                "Peak Time": format_val(tp_val, 's')
            }

            # Update Label UI
            self.lblOvershoot.setText(f"Overshoot: {metrics_dict['Overshoot']}")
            self.lblSettlingTime.setText(f"Settling Time: {metrics_dict['Settling Time']}")
            self.lblPeakTime.setText(f"Peak Time: {metrics_dict['Peak Time']}")

            return metrics_dict # Return dictionary-nya

        except Exception as e:
            self.lblOvershoot.setText("Overshoot: -")
            self.lblSettlingTime.setText("Settling Time: -")
            self.lblPeakTime.setText("Peak Time: -")
            print(f"Metrics Error: {e}")
            return {"Overshoot": "N/A", "Settling Time": "N/A", "Peak Time": "N/A"}

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

        step_metrics = self.update_metrics(t, y)
        
        # Ekstrak Margin dari Bode Plot
        gm, pm, wg, wp = ct.margin(G)
        gm_db = 20 * np.log10(gm) if gm > 0 and not np.isinf(gm) else float('inf')

        self.system_details["plant_G"] = str(G).replace('\n', ' ')
        self.system_details["plant_poles"] = str(np.round(ct.poles(G), 2))
        self.system_details["plant_zeros"] = str(np.round(ct.zeros(G), 2))
        self.system_details["ol_step_metrics"] = step_metrics
        self.system_details["ol_bode_metrics"] = {
            "Gain Margin": f"{gm_db:.2f} dB" if not np.isinf(gm_db) else "Infinity",
            "Phase Margin": f"{pm:.2f} deg" if not np.isnan(pm) else "N/A",
            "Phase Crossover Freq": f"{wg:.2f} rad/s" if not np.isnan(wg) else "N/A",
            "Gain Crossover Freq": f"{wp:.2f} rad/s" if not np.isnan(wp) else "N/A"
        }

        self.grab_figures_as_images(is_closed_loop=False)
        
        self.lblStatusBasePlant.setText("● Base Plant: Ready")
        self.lblStatusBasePlant.setStyleSheet("color: green; font-weight: bold;")


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

    def generate_report_text(self):
        lines = []
        lines = ["=" * 40, "   CONTROL SYSTEM ANALYSIS REPORT", "=" * 40, ""]
        # --- Report Open Loop ---
        if self.system_details["plant_G"]:
            lines.append("--- BASE PLANT (OPEN LOOP) ---")
            lines.append(f"Transfer Function : {self.system_details['plant_G']}")
            lines.append(f"Plant Poles       : {self.system_details['plant_poles']}")
            lines.append(f"Plant Zeros       : {self.system_details['plant_zeros']}")
            
            if self.system_details["ol_bode_metrics"]:
                lines.append("\n[Bode Plot Stability Margins]")
                for k, v in self.system_details["ol_bode_metrics"].items():
                    lines.append(f"  - {k:<22}: {v}")

            if self.system_details["ol_step_metrics"]:
                lines.append("\n[Step Response Metrics]")
                for k, v in self.system_details["ol_step_metrics"].items():
                    lines.append(f"  - {k:<22}: {v}")

            
            lines.append("\nNOTE: GRAFIK STEP RESPONSE TIDAK DI PAKI DI MODUL INI")    

            lines.append("\n\n<i> Semangat mengerjakan borang analisis dan tutam nya nya gaiss :))!!!</i>")
            lines.append("<i>-Control Lab Assistant 2026</i>")
                    
            lines.append("\n" + "=" * 50 + "\n")

        # --- Report Closed Loop ---
        # if self.system_details["ctrl_gain"]:
        #     lines.append("--- CONTROLLED PLANT (CLOSED LOOP) ---")
        #     lines.append(f"PID Parameters : P={self.system_details['ctrl_P']}, I={self.system_details['ctrl_I']}, D={self.system_details['ctrl_D']}")
        #     lines.append(f"Global Gain    : {self.system_details['ctrl_gain']}")
        #     lines.append(f"Closed Loop Poles : {self.system_details['cl_poles']}")
            
        #     if self.system_details["cl_bode_metrics"]:
        #         lines.append("\n[Loop Function (L=C*G) Margins]")
        #         for k, v in self.system_details["cl_bode_metrics"].items():
        #             lines.append(f"  - {k:<22}: {v}")

        #     if self.system_details["cl_step_metrics"]:
        #         lines.append("\n[Step Response Metrics]")
        #         for k, v in self.system_details["cl_step_metrics"].items():
        #             lines.append(f"  - {k:<22}: {v}")
                    
        #     lines.append("\n" + "=" * 50 + "\n")

        return "\n".join(lines)

    def onSaveZipClicked(self):
        if not self.bod_plot_open_png_bytes or not self.step_response_open_png_bytes:
            QMessageBox.warning(self, "Incomplete System",
                                "Please generate open loop plots before saving as ZIP!")
            return

        report_txt = self.generate_report_text()

        saveToZip(self, "System_Analysis_Report_Modul4.zip", [
            {"file_name": "Open_Loop_Bode_Plot.png", "file_data": self.bod_plot_open_png_bytes},
            {"file_name": "Open_Loop_Step_Response.png", "file_data": self.step_response_open_png_bytes},
            {"file_name": "System_Details.txt", "file_data": report_txt},
        ])

    def onSendEmailBtnClicked(self):

        if not self.bod_plot_open_png_bytes or not self.step_response_open_png_bytes:
            QMessageBox.warning(self, "Incomplete System",
                                "Please generate open loop plots before sending!")
            return

        report_txt = self.generate_report_text()

        files_to_zip = [
            {"file_name": "Open_Loop_Bode_Plot.png", "file_data": self.bod_plot_open_png_bytes},
            {"file_name": "Open_Step_Response.png", "file_data": self.step_response_open_png_bytes},
            {"file_name": "System_Details.txt", "file_data": report_txt.encode('utf-8')},
        ]

        try:
            zip_bytes = create_zip_in_memory(files_to_zip)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to compress files: {e}")
            return

        if len(zip_bytes) > 900 * 1024:
            print("Warning: Zip file is large. Firestore email might fail due to 1MB limit.")

        formatted_report = report_txt.replace('\n', '<br>')
        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333;">
            <div style="background-color: #0078d7; color: white; padding: 20px; text-align: center;">
                <h2>Control Systems Simulation Report</h2>
                <p>Module 4: System Analysis</p>
            </div>
            <div style="padding: 20px;">
                <p>Hello {user_context.display_name},</p>
                <p>Your simulation has been successfully processed. Attached is the <strong>ZIP file</strong> containing:</p>
                <ul>
                    <li>Open/Closed Loop Root Locus Plots</li>
                    <li>Open/Closed Loop Step Response Plots</li>
                    <li>Detailed System Parameters (Text File)</li>
                </ul>
                <hr style="border: 0; border-top: 1px solid #eee;">
                <h3>System Summary</h3>
                <div style="background-color: #f9f9f9; padding: 15px; border-left: 5px solid #0078d7; font-family: monospace; font-size: 12px;">
                    {formatted_report}
                </div>
                <br>
                <p><em>Control Laboratory 2026</em></p>
                <p>Departemen Teknik Elektro Universitas Indonesia</p>
            </div>
        </body>
        </html>
        """

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        success, message = sendWithEmail(
            subject="Lab Report: System Analysis Results",
            html_body=html_content,
            text_body=report_txt,
            attachments=[
                {"filename": "System_Analysis_Report.zip", "content": zip_bytes}
            ]
        )

        # 8. Restore UI
        QApplication.restoreOverrideCursor()

        if success:
            QMessageBox.information(self, "Email Sent", message)
        else:
            QMessageBox.critical(self, "Sending Failed", f"Could not send email.\nError: {message}")

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
