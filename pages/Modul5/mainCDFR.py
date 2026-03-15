# app.py
import sys, warnings, os, io
import numpy as np
import control as ct
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# Pastikan import fungsi utilitas yang diperlukan (sesuaikan dengan path project kamu)
from func.sendWithEmail import create_zip_in_memory, sendWithEmail
from func.UserContext import user_context
from func.saveToZip import saveToZip

from pages.Modul5.Modul5New import Ui_MainWindow
import pages.Modul5.myQRC # noqa

os.system("cls" if os.name == "nt" else "clear")

OMEGA_RANGE = np.logspace(-4, 4, 2000)

def db(x):
    with np.errstate(divide='ignore'):
        return 20*np.log10(x)

def safe_margin(sys):
    """Kembalikan (gm, pm, wg, wp) sudah dipastikan float, dan gm_db aman."""
    try:
        gm, pm, wg, wp = ct.margin(sys)
        gm = float(gm) if np.ndim(gm) == 0 else gm[0]
        pm = float(pm) if np.ndim(pm) == 0 else pm[0]
        wg = float(wg) if np.ndim(wg) == 0 else wg[0]
        wp = float(wp) if np.ndim(wp) == 0 else wp[0]
    except Exception:
        gm = np.inf; pm = np.nan; wg = np.nan; wp = np.nan
    gm_db = db(gm) if np.isfinite(gm) else np.inf
    if np.isnan(pm): pm = 0.0
    return gm, pm, wg, wp, gm_db

def _to_float_txt(s, default=0.0):
    try:
        return float(str(s).strip().replace(',', '.'))
    except Exception:
        return default

def is_template_triplet(kc_txt, zc_txt, pc_txt, tol=1e-12):
    kc = _to_float_txt(kc_txt, 1.0)
    zc = _to_float_txt(zc_txt, 0.0)
    pc = _to_float_txt(pc_txt, 0.0)
    return abs(kc - 1.0) < tol and abs(zc) < tol and abs(pc) < tol

class ControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Kunci ukuran & nonaktifkan maximize
        self.setFixedSize(1298, 720)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)

        self.set_default_values()
        
        # --- DICTIONARY UNTUK MENYIMPAN GRAFIK YANG DI-GENERATE ---
        self.generated_plots = {}

        # Ambil axes dari MplWidget yang dipromote
        try:
            self.ax_atas = self.ui.plot_atas.figure.subplots()
            self.ax_bawah = self.ui.plot_bawah.figure.subplots()
        except AttributeError:
            print("ERROR: Promote QWidget 'plot_atas' & 'plot_bawah' -> MplWidget (module: mplwidget)")
            sys.exit(1)

        self.ui.plot_atas.canvas.mpl_connect('button_press_event', self._on_main_canvas_click)
        self.ui.plot_bawah.canvas.mpl_connect('button_press_event', self._on_main_canvas_click)

        self.connect_signals()

        self.show()

        self.ui.CLButton.setChecked(True)
        self.plot_system()

    def _on_main_canvas_click(self, event):
        # Left-click inside either axes opens a popup
        if event is None or event.button != 1 or event.inaxes is None:
            return
        if event.inaxes in (self.ax_atas, self.ax_bawah):
            self._open_popup_from_axes(event.inaxes)

    def _open_popup_from_axes(self, src_ax):
        # Build a popup window that clones the clicked axes
        self._popup = PlotPopup(self, src_ax)
        self._popup.show()


    def set_default_values(self):
        self.ui.lineEdit.setText("0")       # n3
        self.ui.lineEdit_1.setText("0")     # n2
        self.ui.lineEdit_2.setText("0")     # n1
        self.ui.lineEdit_3.setText("1")     # n0

        self.ui.lineEdit_4.setText("0")     # d3
        self.ui.lineEdit_5.setText("0")     # d2
        self.ui.lineEdit_6.setText("1")     # d1
        self.ui.lineEdit_7.setText("1")     # d0

        # Lag default (Zc > Pc)
        self.ui.lineEdit_8.setText("1")     # Kc_lag
        self.ui.lineEdit_9.setText("0")     # Zc_lag
        self.ui.lineEdit_10.setText("0")    # Pc_lag

        # Lead default (Pc > Zc)
        self.ui.lineEdit_12.setText("1")    # Kc_lead
        self.ui.lineEdit_13.setText("0")    # Zc_lead
        self.ui.lineEdit_11.setText("0")     # Pc_lead

    def connect_signals(self):
        self.ui.CLButton.clicked.connect(self.plot_system)                  # Closed-Loop
        self.ui.bodeButton.clicked.connect(self.plot_system)                # Bode
        # self.ui.nyquistButton.clicked.connect(self.plot_system)             # Nyquist

        self.ui.lagCompensatorButton.clicked.connect(self.plot_system)      # Lag
        self.ui.leadCompensatorButton.clicked.connect(self.plot_system)     # Lead
        # self.ui.lagleadCompensatorButton.clicked.connect(self.plot_system)  # Lag-Lead

        # Koneksi tombol Save & Email
        self.ui.btnSaveZip.clicked.connect(self.onSaveZipBtnClicked)       
        self.ui.btnSendEmail.clicked.connect(self.onSendEmailBtnClicked) 

    def get_plant_tf(self):
        """Bangun TF plant dari isian koefisien."""
        try:
            n3 = float(self.ui.lineEdit.text() or '0')
            n2 = float(self.ui.lineEdit_1.text() or '0')
            n1 = float(self.ui.lineEdit_2.text() or '0')
            n0 = float(self.ui.lineEdit_3.text() or '0')
            num = [n3, n2, n1, n0]

            d3 = float(self.ui.lineEdit_4.text() or '0')
            d2 = float(self.ui.lineEdit_5.text() or '0')
            d1 = float(self.ui.lineEdit_6.text() or '0')
            d0 = float(self.ui.lineEdit_7.text() or '0')
            den = [d3, d2, d1, d0]

            # Hindari pembagi nol total
            if not np.any(den):
                den = [1.0]

            G = ct.tf(num, den)
            return G
        except Exception as e:
            print(f"Error TF plant: {e}")
            return None

    def get_compensator_tf(self):
        """Bentuk TF kompensator dari UI."""
        try:
            if self.ui.leadCompensatorButton.isChecked():  # Lead
                Kc = float(self.ui.lineEdit_12.text() or '1.0')
                Zc = float(self.ui.lineEdit_13.text() or '10.0')
                Pc = float(self.ui.lineEdit_11.text() or '1.0')
                return Kc * ct.tf([1, Zc], [1, Pc]), "Lead Compensated"

            if self.ui.lagCompensatorButton.isChecked():  # Lag
                Kc = float(self.ui.lineEdit_8.text() or '1.0')
                Zc = float(self.ui.lineEdit_9.text() or '1.0')
                Pc = float(self.ui.lineEdit_10.text() or '10.0')
                return Kc * ct.tf([1, Zc], [1, Pc]), "Lag Compensated"

            if self.ui.lagleadCompensatorButton.isChecked():  # Lag-Lead
                K_lead = float(self.ui.lineEdit_12.text() or '1.0')
                Z_lead = float(self.ui.lineEdit_13.text() or '1.0')
                P_lead = float(self.ui.lineEdit_11.text()  or '10.0')
                G_lead = K_lead * ct.tf([1, Z_lead], [1, P_lead])

                K_lag = float(self.ui.lineEdit_8.text() or '1.0')
                Z_lag = float(self.ui.lineEdit_9.text() or '10.0')
                P_lag = float(self.ui.lineEdit_10.text() or '1.0')
                G_lag  = K_lag  * ct.tf([1, Z_lag],  [1, P_lag])

                Gc = ct.series(G_lag, G_lead)
                return Gc, "Lag-Lead Compensated"
        except Exception as e:
            print(f"Error TF kompensator: {e}")

        return None, "Uncompensated"
    
    def _plot_bode_top_bottom(self, G, Gc=None, comp_label="Compensated"):
        self.ax_atas.clear()
        self.ax_bawah.clear()

        mag, ph, w = ct.bode(G, omega=OMEGA_RANGE, plot=False)
        self.ax_atas.semilogx(w, db(mag), label="Uncompensated")
        self.ax_bawah.semilogx(w, np.degrees(ph), label="Uncompensated")

        if Gc is not None:
            L = ct.series(Gc, G)
            mag2, ph2, w2 = ct.bode(L, omega=OMEGA_RANGE, plot=False)
            self.ax_atas.semilogx(w2, db(mag2), '--', label=comp_label)
            self.ax_bawah.semilogx(w2, np.degrees(ph2), '--', label=comp_label)

        self.ax_atas.set_title("Bode Plot (Magnitude)")
        self.ax_atas.set_ylabel("Magnitude (dB)")
        self.ax_atas.grid(True, which='both')
        self.ax_atas.legend(loc='best', fontsize=8, framealpha=0.8, fancybox=True)

        self.ax_bawah.set_title("Bode Plot (Phase)")
        self.ax_bawah.set_ylabel("Phase (deg)")
        self.ax_bawah.set_xlabel("Frequency (rad/s)")
        self.ax_bawah.grid(True, which='both')
        self.ax_bawah.legend(loc='best', fontsize=8, framealpha=0.8, fancybox=True)

        self.ui.plot_bawah.setVisible(True)
        self.ui.line.setVisible(True)

    def _set_main_aspect(self, equal: bool):
        ax = self.ax_atas
        if equal:
            ax.set_aspect('equal', adjustable='box')
        else:
            try:
                ax.set_box_aspect(None)
            except Exception:
                pass
            ax.set_aspect('auto', adjustable='box')
        ax.autoscale(enable=True, axis='both', tight=False)

    def _capture_current_plots(self):
        """Menyimpan plot yang sedang tampil ke dalam dictionary memory."""
        # Tentukan nama file berdasarkan tombol radio mana yang aktif
        if self.ui.CLButton.isChecked():
            name_top = "Closed_Loop_Step_Response.png"
            name_bot = None
        elif self.ui.bodeButton.isChecked():
            name_top = "Uncompensated_Bode_Mag.png"
            name_bot = "Uncompensated_Bode_Phase.png"
        elif self.ui.nyquistButton.isChecked():
            name_top = "Nyquist_Plot.png"
            name_bot = None
        elif self.ui.lagCompensatorButton.isChecked():
            name_top = "Lag_Compensated_Bode_Mag.png"
            name_bot = "Lag_Compensated_Bode_Phase.png"
        elif self.ui.leadCompensatorButton.isChecked():
            name_top = "Lead_Compensated_Bode_Mag.png"
            name_bot = "Lead_Compensated_Bode_Phase.png"
        elif self.ui.lagleadCompensatorButton.isChecked():
            name_top = "LagLead_Comp_Bode_Mag.png"
            name_bot = "LagLead_Comp_Bode_Phase.png"
        else:
            return

        # Capture plot atas
        buf_top = io.BytesIO()
        self.ui.plot_atas.figure.savefig(buf_top, format='png', bbox_inches='tight')
        self.generated_plots[name_top] = buf_top.getvalue()

        # Capture plot bawah jika sedang tampil (Bode plots)
        if name_bot and self.ui.plot_bawah.isVisible():
            buf_bot = io.BytesIO()
            self.ui.plot_bawah.figure.savefig(buf_bot, format='png', bbox_inches='tight')
            self.generated_plots[name_bot] = buf_bot.getvalue()

    def generate_report_text(self):
        G = self.get_plant_tf()
        Gc, comp_label = self.get_compensator_tf() 
        
        lines = []
        lines.append("=" * 45)
        lines.append("   CONTROL SYSTEM ANALYSIS REPORT (MODUL 5)")
        lines.append("=" * 45)
        lines.append(f"\nBase Plant Transfer Function (G):\n{G}")
        
        lines.append(f"\nCompensator Type: {comp_label}")
        
        kc_lag = self.ui.lineEdit_8.text() or '0'
        zc_lag = self.ui.lineEdit_9.text() or '0'
        pc_lag = self.ui.lineEdit_10.text() or '0'
        
        lines.append("\n[Lag Compensator Parameters]")
        lines.append(f"  Gain : {kc_lag}")
        lines.append(f"  Zero : {zc_lag}")
        lines.append(f"  Pole : {pc_lag}")

        kc_lead = self.ui.lineEdit_12.text() or '0'
        zc_lead = self.ui.lineEdit_13.text() or '0'
        pc_lead = self.ui.lineEdit_11.text() or '0'
        
        lines.append("\n[Lead Compensator Parameters]")
        lines.append(f"  Gain : {kc_lead}")
        lines.append(f"  Zero : {zc_lead}")
        lines.append(f"  Pole : {pc_lead}")

        lines.append("\nGrafik yang berhasil direkam pada sesi ini:")
        for key in self.generated_plots.keys():
            lines.append(f"  - {key}")
            
        lines.append("\n\n<i> Semangat mengerjakan borang analisis dan tugasnya gaiss :))!!!</i>")
        lines.append("<i>-Control Lab Assistant 2026</i>")
        lines.append("\n" + "=" * 45)
        
        return "\n".join(lines)

    def onSaveZipBtnClicked(self):
        if not self.generated_plots:
            QMessageBox.warning(self, "Belum Ada Grafik", "Belum ada grafik yang di-generate. Silakan pilih dan plot grafik terlebih dahulu!")
            return

        file_list = "\n".join([f"• {k}" for k in self.generated_plots.keys()])
        msg = f"Grafik berikut telah terekam dan akan disimpan ke dalam ZIP:\n\n{file_list}\n\nLanjutkan proses Save?"
        
        reply = QMessageBox.question(self, "Konfirmasi Save ZIP", msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Siapkan data zip
            files_to_save = [{"file_name": k, "file_data": v} for k, v in self.generated_plots.items()]
            report_txt = self.generate_report_text()
            files_to_save.append({"file_name": "System_Details_Modul5.txt", "file_data": report_txt})

            saveToZip(self, "System_Analysis_Modul5.zip", files_to_save)

    def onSendEmailBtnClicked(self):
        if not self.generated_plots:
            QMessageBox.warning(self, "Belum Ada Grafik", "Belum ada grafik yang di-generate. Silakan pilih dan plot grafik terlebih dahulu sebelum mengirim email!")
            return

        file_list = "\n".join([f"• {k}" for k in self.generated_plots.keys()])
        msg = f"Grafik berikut telah terekam dan siap dikirim ke email:\n\n{file_list}\n\nLanjutkan mengirim email?"
        
        reply = QMessageBox.question(self, "Konfirmasi Kirim Email", msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            report_txt = self.generate_report_text()

            # Format data untuk create_zip_in_memory (butuh file_data dlm bentuk bytes)
            files_to_zip = [{"file_name": k, "file_data": v} for k, v in self.generated_plots.items()]
            files_to_zip.append({"file_name": "System_Details_Modul5.txt", "file_data": report_txt.encode('utf-8')})

            try:
                zip_bytes = create_zip_in_memory(files_to_zip)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal mengompresi file zip: {e}")
                return

            if len(zip_bytes) > 900 * 1024:
                print("Warning: Zip file is large. Firestore email might fail due to 1MB limit.")

            # Ambil nama user kalau tersedia, kalau error fallback ke "Praktikan"
            try:
                display_name = user_context.display_name
            except Exception:
                display_name = "Praktikan"

            formatted_report = report_txt.replace('\n', '<br>')
            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333;">
                <div style="background-color: #081d38; color: white; padding: 20px; text-align: center;">
                    <h2>Control Systems Simulation Report</h2>
                    <p>Module 5: Frequency Response & Compensator Design</p>
                </div>
                <div style="padding: 20px;">
                    <p>Haloo {display_name},</p>
                    <p>Selamat sudah menyelesaikan sesi praktikum pada minggu ini, berikut sebuah <strong>ZIP</strong> yang isinya grafik-grafik yang kamu buat selama praktikum beserta detail sistemnya.</p>
                    <hr style="border: 0; border-top: 1px solid #eee;">
                    <h3>System Summary</h3>
                    <div style="background-color: #f7f7f7; padding: 15px; border-left: 5px solid #081d38; font-family: monospace; font-size: 12px;">
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
                subject="Lab Report: Modul 5 Frequency Response Results",
                html_body=html_content,
                text_body=report_txt,
                attachments=[
                    {"filename": "System_Analysis_Modul5.zip", "content": zip_bytes}
                ]
            )

            QApplication.restoreOverrideCursor()

            if success:
                QMessageBox.information(self, "Email Sent", "Berhasil dikirim!\n" + message)
            else:
                QMessageBox.critical(self, "Sending Failed", f"Gagal mengirim email.\nError: {message}")

    def plot_system(self):
        G = self.get_plant_tf()
        if G is None: return

        Gc, comp_label = self.get_compensator_tf()

        self.ax_atas.clear()
        self.ax_bawah.clear()
        show_bawah = False

        try:
            # Closed-loop
            if self.ui.CLButton.isChecked():
                self.ax_atas.clear()
                self._set_main_aspect(equal=False)
                print("CDFR: Plotting Closed Loop Step Response")
                t = np.linspace(0.0, 20.0, 1000)

                STEP_STYLES = {
                    "Uncompensated": dict(color="#2563eb", linestyle="-",  linewidth=2.0),
                    "Lag":            dict(color="#22c55e", linestyle="-.", linewidth=1.8),
                    "Lead":           dict(color="#f59e0b", linestyle="--", linewidth=1.8),
                    "Lag-Lead":       dict(color="#ef4444", linestyle=":",  linewidth=2.0),
                    "Step":           dict(color="black",   linestyle=":",  linewidth=1.2)
                }

                T_unc = ct.feedback(G, 1)
                t, y = ct.step_response(T_unc, T=t)
                self.ax_atas.plot(t, y, label="Uncompensated", **STEP_STYLES["Uncompensated"])

                lagIsTemplate = is_template_triplet(self.ui.lineEdit_12.text(), self.ui.lineEdit_13.text(), self.ui.lineEdit_11.text())
                leadIsTemplate = is_template_triplet(self.ui.lineEdit_8.text(), self.ui.lineEdit_9.text(), self.ui.lineEdit_10.text())
                
                if not lagIsTemplate:
                    Kc = float(self.ui.lineEdit_12.text())
                    Zc = float(self.ui.lineEdit_13.text())
                    Pc = float(self.ui.lineEdit_11.text())
                    GLag = Kc * ct.tf([1, Zc], [1, Pc])
                    L = ct.series(GLag, G)
                    T_cmp = ct.feedback(L, 1)
                    t2, y2 = ct.step_response(T_cmp, T=t)
                    self.ax_atas.plot(t2, y2, label="Lead Compensation", **STEP_STYLES["Lag"])

                if not leadIsTemplate:
                    Kc = float(self.ui.lineEdit_8.text())
                    Zc = float(self.ui.lineEdit_9.text())
                    Pc = float(self.ui.lineEdit_10.text())
                    GLead = Kc * ct.tf([1, Zc], [1, Pc])
                    L = ct.series(GLead, G)
                    T_cmp = ct.feedback(L, 1)
                    t2, y2 = ct.step_response(T_cmp, T=t)
                    self.ax_atas.plot(t2, y2, label="Lag Compensation", **STEP_STYLES["Lead"])

                if not leadIsTemplate and not lagIsTemplate:
                    Gc = ct.series(GLead, GLag)
                    L = ct.series(GLead, G)
                    T_cmp = ct.feedback(L, 1)
                    t2, y2 = ct.step_response(T_cmp, T=t)
                    self.ax_atas.plot(t2, y2, label="Lag-Lead Compensation", **STEP_STYLES["Lag-Lead"])

                self.ax_atas.plot([0, 0, 20], [0, 1, 1], label="Step Input", **STEP_STYLES["Step"])

                self.ax_atas.set_title("Closed-Loop Step Response")
                self.ax_atas.set_xlabel("Time (s)")
                self.ax_atas.set_ylabel("Amplitude")
                self.ax_atas.grid(True)
                self.ax_atas.legend(loc='lower right', fontsize=8, framealpha=0.8, fancybox=True)

            # Bode
            elif self.ui.bodeButton.isChecked():
                self.ax_atas.clear()
                self._set_main_aspect(equal=False)
                print("CDFR: Bode Plot")
                show_bawah = True

                mag, ph, w = ct.bode(G, omega=OMEGA_RANGE, plot=False)
                self.ax_atas.semilogx(w, db(mag), label="Uncompensated")
                self.ax_bawah.semilogx(w, np.degrees(ph), label="Uncompensated")

                if Gc is not None:
                    L = ct.series(Gc, G)
                    mag2, ph2, w2 = ct.bode(L, omega=OMEGA_RANGE, plot=False)
                    self.ax_atas.semilogx(w2, db(mag2), '--', label=comp_label)
                    self.ax_bawah.semilogx(w2, np.degrees(ph2), '--', label=comp_label)

                self.ax_atas.set_title("Bode Plot (Magnitude)")
                self.ax_atas.set_ylabel("Magnitude (dB)")
                self.ax_atas.grid(True, which='both')
                self.ax_atas.legend(loc='best', fontsize=8, framealpha=0.8, fancybox=True)

                self.ax_bawah.set_title("Bode Plot (Phase)")
                self.ax_bawah.set_ylabel("Phase (deg)")
                self.ax_bawah.set_xlabel("Frequency (rad/s)")
                self.ax_bawah.grid(True, which='both')
                self.ax_bawah.legend(loc='best', fontsize=8, framealpha=0.8, fancybox=True)

            # Nyquist
            elif self.ui.nyquistButton.isChecked():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                self.ax_atas.clear()
                self._set_main_aspect(equal=True)

                STEP_STYLES = {
                    "Uncompensated": dict(color="#2563eb", linewidth=1.8),
                    "Lag":           dict(color="#22c55e", linewidth=1.8),
                    "Lead":          dict(color="#f59e0b", linewidth=1.8),
                    "Lag-Lead":      dict(color="#ef4444", linewidth=1.8),
                }

                print("CDFR: Nyquist Plot")
                ct.nyquist_plot(G, omega=OMEGA_RANGE, ax=self.ax_atas, label="Uncompensated", **STEP_STYLES["Uncompensated"])

                lagIsTemplate  = is_template_triplet(self.ui.lineEdit_12.text(), self.ui.lineEdit_13.text(), self.ui.lineEdit_11.text())
                leadIsTemplate = is_template_triplet(self.ui.lineEdit_8.text(), self.ui.lineEdit_9.text(), self.ui.lineEdit_10.text())

                GLag = GLead = None

                if not lagIsTemplate:
                    Kc = float(self.ui.lineEdit_12.text())
                    Zc = float(self.ui.lineEdit_13.text())
                    Pc = float(self.ui.lineEdit_11.text())
                    GLag = Kc * ct.tf([1, Zc], [1, Pc])
                    L = ct.series(GLag, G)
                    ct.nyquist_plot(L, omega=OMEGA_RANGE, ax=self.ax_atas, label="Lag Compensation", **STEP_STYLES["Lag"])

                if not leadIsTemplate:
                    Kc = float(self.ui.lineEdit_8.text())
                    Zc = float(self.ui.lineEdit_9.text())
                    Pc = float(self.ui.lineEdit_10.text())
                    GLead = Kc * ct.tf([1, Zc], [1, Pc])
                    L = ct.series(GLead, G)
                    ct.nyquist_plot(L, omega=OMEGA_RANGE, ax=self.ax_atas, label="Lead Compensation", **STEP_STYLES["Lead"])

                if (GLag is not None) and (GLead is not None):
                    Gc_ll = ct.series(GLag, GLead)
                    L = ct.series(Gc_ll, G)
                    ct.nyquist_plot(L, omega=OMEGA_RANGE, ax=self.ax_atas, label="Lag-Lead Compensation", **STEP_STYLES["Lag-Lead"])

                self.ax_atas.set_title("Nyquist Plot")
                self.ax_atas.grid(True)
                try:
                    self.ax_atas.set_aspect('equal', adjustable='box')
                except Exception:
                    pass
                h, l = self.ax_atas.get_legend_handles_labels()
                by = dict(zip(l, h))
                self.ax_atas.legend(by.values(), by.keys(), fontsize=8, framealpha=0.8, fancybox=True)

            elif self.ui.lagCompensatorButton.isChecked():
                self.ax_atas.clear()
                self._set_main_aspect(equal=False)
                show_bawah = True
                self._plot_bode_top_bottom(G, *self.get_compensator_tf())

            elif self.ui.leadCompensatorButton.isChecked():
                self.ax_atas.clear()
                self._set_main_aspect(equal=False)
                show_bawah = True
                self._plot_bode_top_bottom(G, *self.get_compensator_tf())

            elif self.ui.lagleadCompensatorButton.isChecked():
                self.ax_atas.clear()
                self._set_main_aspect(equal=False)
                show_bawah = True
                self._plot_bode_top_bottom(G, *self.get_compensator_tf())

        except Exception as e:
            self.ax_atas.clear(); self.ax_bawah.clear()
            self.ax_atas.text(0.5, 0.5, f"Error plotting:\n{e}", ha='center', va='center', color='red')

        self.ui.plot_bawah.setVisible(show_bawah)
        self.ui.line.setVisible(show_bawah)

        self.ui.plot_atas.canvas.draw()
        self.ui.plot_bawah.canvas.draw()
        
        # --- PANGGIL FUNGSI CAPTURE SETIAP KALI PLOT SELESAI DIGAMBAR ---
        self._capture_current_plots()

class PlotPopup(QMainWindow):
    def __init__(self, parent, src_ax):
        super().__init__(parent)
        self.setWindowTitle("Interactive Plot")
        self.resize(900, 600)

        self.fig = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        self.toolbar = NavigationToolbar(self.canvas, self)
        from PyQt5.QtWidgets import QWidget, QVBoxLayout
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setCentralWidget(central)

        self._clone_axes(src_ax)

        self.ann = self.ax.annotate(
            "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->")
        )
        self.ann.set_visible(False)

        self._cid_move = self.canvas.mpl_connect('motion_notify_event', self._on_move)

        self.canvas.draw()

    def _clone_axes(self, src):
        self.ax.set_xscale(src.get_xscale())
        self.ax.set_yscale(src.get_yscale())

        for line in src.get_lines():
            xd, yd = line.get_xdata(orig=False), line.get_ydata(orig=False)
            (new_line,) = self.ax.plot(
                xd, yd,
                linestyle=line.get_linestyle(),
                linewidth=line.get_linewidth(),
                marker=line.get_marker(),
                markersize=line.get_markersize(),
                label=line.get_label(),
            )
            try:
                new_line.set_color(line.get_color())
            except Exception:
                pass

        self.ax.set_title(src.get_title())
        self.ax.set_xlabel(src.get_xlabel())
        self.ax.set_ylabel(src.get_ylabel())
        try:
            self.ax.set_xlim(src.get_xlim())
            self.ax.set_ylim(src.get_ylim())
        except Exception:
            pass
        self.ax.grid(True, which='both')

        handles, labels = self.ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            self.ax.legend(by_label.values(), by_label.keys())

    def _nearest_point_on_lines(self, event):
        if event.xdata is None or event.ydata is None:
            return None
        logx = (self.ax.get_xscale() == 'log')
        ex = event.xdata if not logx else (np.log10(event.xdata) if event.xdata > 0 else None)
        if logx and ex is None:
            return None
        ey = event.ydata
        best = None
        best_dist = np.inf
        for line in self.ax.get_lines():
            if not line.get_visible():
                continue
            x = np.asarray(line.get_xdata(), float)
            y = np.asarray(line.get_ydata(), float)
            m = np.isfinite(x) & np.isfinite(y)
            if not np.any(m):
                continue
            x, y = x[m], y[m]
            xx = np.log10(x) if logx else x
            yy = y
            d = (xx - ex) ** 2 + (yy - ey) ** 2
            i = np.argmin(d)
            if d[i] < best_dist:
                best_dist = d[i]
                best = (x[i] if not logx else 10**xx[i], yy[i])
        return best

    def _on_move(self, event):
        if event.inaxes != self.ax:
            self.ann.set_visible(False)
            self.canvas.draw_idle()
            return

        res = self._nearest_point_on_lines(event)
        if res is None:
            self.ann.set_visible(False)
            self.canvas.draw_idle()
            return

        x, y = res
        self.ann.xy = (x, y)
        self.ann.set_text(f"x = {x:.6g}\ny = {y:.6g}")
        self.ann.set_visible(True)
        self.canvas.draw_idle()

def exec_CDFR(nama, npm):
    app = QApplication.instance() or QApplication(sys.argv)
    window = ControlApp()
    

    return window