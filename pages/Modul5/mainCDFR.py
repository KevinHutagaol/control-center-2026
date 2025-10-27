# app.py
import sys, warnings, os
import numpy as np
import control as ct
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from pages.Modul5.Modul5New import Ui_MainWindow
import pages.Modul5.myQRC

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
        self.ui.nyquistButton.clicked.connect(self.plot_system)             # Nyquist

        self.ui.lagCompensatorButton.clicked.connect(self.plot_system)      # Lag
        self.ui.leadCompensatorButton.clicked.connect(self.plot_system)     # Lead
        self.ui.lagleadCompensatorButton.clicked.connect(self.plot_system)  # Lag-Lead

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

            if self.ui.lagleadCompensatorButton.isChecked():  # Lag-Lead = Lag * Lead (seri)
                # Lead params
                K_lead = float(self.ui.lineEdit_12.text() or '1.0')
                Z_lead = float(self.ui.lineEdit_13.text() or '1.0')
                P_lead = float(self.ui.lineEdit_11.text()  or '10.0')
                G_lead = K_lead * ct.tf([1, Z_lead], [1, P_lead])

                # Lag params
                K_lag = float(self.ui.lineEdit_8.text() or '1.0')
                Z_lag = float(self.ui.lineEdit_9.text() or '10.0')
                P_lag = float(self.ui.lineEdit_10.text() or '1.0')
                G_lag  = K_lag  * ct.tf([1, Z_lag],  [1, P_lag])

                Gc = ct.series(G_lag, G_lead)  # urutan seri: lag lalu lead (boleh dibalik)
                return Gc, "Lag-Lead Compensated"
        except Exception as e:
            print(f"Error TF kompensator: {e}")

        return None, "Uncompensated"
    
    def _plot_bode_top_bottom(self, G, Gc=None, comp_label="Compensated"):
        """Gambar Bode (mag atas, phase bawah) untuk Uncompensated vs (opsional) Compensated."""
        self.ax_atas.clear()
        self.ax_bawah.clear()

        # Uncompensated (open-loop plant G)
        mag, ph, w = ct.bode(G, omega=OMEGA_RANGE, plot=False)
        self.ax_atas.semilogx(w, db(mag), label="Uncompensated")
        self.ax_bawah.semilogx(w, np.degrees(ph), label="Uncompensated")

        # Compensated (open-loop L = Gc*G), jika ada
        if Gc is not None:
            L = ct.series(Gc, G)
            mag2, ph2, w2 = ct.bode(L, omega=OMEGA_RANGE, plot=False)
            self.ax_atas.semilogx(w2, db(mag2), '--', label=comp_label)
            self.ax_bawah.semilogx(w2, np.degrees(ph2), '--', label=comp_label)

        # Atas: magnitude
        self.ax_atas.set_title("Bode Plot (Magnitude)")
        self.ax_atas.set_ylabel("Magnitude (dB)")
        self.ax_atas.grid(True, which='both')
        self.ax_atas.legend(
            loc='best',
            fontsize=8,
            framealpha=0.8,
            fancybox=True
        )

        # Bawah: phase
        self.ax_bawah.set_title("Bode Plot (Phase)")
        self.ax_bawah.set_ylabel("Phase (deg)")
        self.ax_bawah.set_xlabel("Frequency (rad/s)")
        self.ax_bawah.grid(True, which='both')
        self.ax_bawah.legend(
            loc='best',
            fontsize=8,
            framealpha=0.8,
            fancybox=True
        )

        # Tampilkan panel bawah
        self.ui.plot_bawah.setVisible(True)
        self.ui.line.setVisible(True)

    def _set_main_aspect(self, equal: bool):
        ax = self.ax_atas
        if equal:
            ax.set_aspect('equal', adjustable='box')
        else:
            # reset any equal/box-aspect from Nyquist
            try:
                ax.set_box_aspect(None)  # mpl ≥ 3.3
            except Exception:
                pass
            ax.set_aspect('auto', adjustable='box')
        ax.autoscale(enable=True, axis='both', tight=False)

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
                    "Uncompensated": dict(color="#2563eb", linestyle="-",  linewidth=2.0),  # blue solid
                    "Lag":            dict(color="#22c55e", linestyle="-.", linewidth=1.8),  # green dash-dot
                    "Lead":           dict(color="#f59e0b", linestyle="--", linewidth=1.8),  # orange dashed
                    "Lag-Lead":       dict(color="#ef4444", linestyle=":",  linewidth=2.0),  # red dotted
                    "Step":           dict(color="black",   linestyle=":",  linewidth=1.2)   # black dotted
                }

                # Uncompensated
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
                    self.ax_atas.plot(t2, y2, label="Lag Compensation", **STEP_STYLES["Lag"])

                if not leadIsTemplate:
                    Kc = float(self.ui.lineEdit_8.text())
                    Zc = float(self.ui.lineEdit_9.text())
                    Pc = float(self.ui.lineEdit_10.text())

                    GLead = Kc * ct.tf([1, Zc], [1, Pc])

                    L = ct.series(GLead, G)
                    T_cmp = ct.feedback(L, 1)
                    t2, y2 = ct.step_response(T_cmp, T=t)
                    self.ax_atas.plot(t2, y2, label="Lead Compensation", **STEP_STYLES["Lead"])

                if not leadIsTemplate and not lagIsTemplate:
                    Gc = ct.series(GLead, GLag)
                    L = ct.series(GLead, G)
                    T_cmp = ct.feedback(L, 1)
                    t2, y2 = ct.step_response(T_cmp, T=t)
                    self.ax_atas.plot(t2, y2, label="Lag-Lead Compensation", **STEP_STYLES["Lag-Lead"])

                self.ax_atas.plot([0, 0, 20], [0, 1, 1], label="Step Input", **STEP_STYLES["Step"])

                # Formatting
                self.ax_atas.set_title("Closed-Loop Step Response")
                self.ax_atas.set_xlabel("Time (s)")
                self.ax_atas.set_ylabel("Amplitude")
                self.ax_atas.grid(True)
                self.ax_atas.legend(
                    loc='lower right',
                    fontsize=8,
                    framealpha=0.8,
                    fancybox=True
                )

            # Bode
            elif self.ui.bodeButton.isChecked():
                self.ax_atas.clear()
                self._set_main_aspect(equal=False)
                print("CDFR: Bode Plot")
                show_bawah = True

                gm, pm, wg, wp, gm_db = safe_margin(G)
                status = f"Uncompensated: PM={pm:.2f}°, GM={gm_db:.2f} dB"

                mag, ph, w = ct.bode(G, omega=OMEGA_RANGE, plot=False)
                self.ax_atas.semilogx(w, db(mag), label="Uncompensated")
                self.ax_bawah.semilogx(w, np.degrees(ph), label="Uncompensated")

                if Gc is not None:
                    L = ct.series(Gc, G)
                    gm2, pm2, wg2, wp2, gm2_db = safe_margin(L)
                    status += f"  ||  {comp_label}: PM={pm2:.2f}°, GM={gm2_db:.2f} dB"
                    mag2, ph2, w2 = ct.bode(L, omega=OMEGA_RANGE, plot=False)
                    self.ax_atas.semilogx(w2, db(mag2), '--', label=comp_label)
                    self.ax_bawah.semilogx(w2, np.degrees(ph2), '--', label=comp_label)

                # self.statusBar().showMessage(status)

                self.ax_atas.set_title("Bode Plot (Magnitude)")
                self.ax_atas.set_ylabel("Magnitude (dB)")
                self.ax_atas.grid(True, which='both'); self.ax_atas.legend()

                self.ax_bawah.set_title("Bode Plot (Phase)")
                self.ax_bawah.set_ylabel("Phase (deg)")
                self.ax_bawah.set_xlabel("Frequency (rad/s)")
                self.ax_bawah.grid(True, which='both')
                self.axbaw.legend(
                    loc='best',
                    fontsize=8,
                    framealpha=0.8,
                    fancybox=True
                )

            elif self.ui.nyquistButton.isChecked():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                ct.nyquist_plot(G, omega=OMEGA_RANGE, ax=self.ax_atas, label="Uncompensated")
                if Gc is not None:
                    L = ct.series(Gc, G)
                    ct.nyquist_plot(L, omega=OMEGA_RANGE, ax=self.ax_atas, label=comp_label)

                self.ax_atas.set_title("Nyquist Plot")
                self.ax_atas.grid(True)
                h, l = self.ax_atas.get_legend_handles_labels()
                by = dict(zip(l, h))
                self.ax_atas.legend(by.values(), by.keys())

            elif self.ui.lagCompensatorButton.isChecked():
                show_bawah = True

                self._plot_bode_top_bottom(G, *self.get_compensator_tf())

            elif self.ui.leadCompensatorButton.isChecked():
                show_bawah = True

                self._plot_bode_top_bottom(G, *self.get_compensator_tf())

            elif self.ui.lagleadCompensatorButton.isChecked():
                show_bawah = True

                self._plot_bode_top_bottom(G, *self.get_compensator_tf())


        except Exception as e:
            self.ax_atas.clear(); self.ax_bawah.clear()
            self.ax_atas.text(0.5, 0.5, f"Error plotting:\n{e}", ha='center', va='center', color='red')

        # Visibilitas panel bawah
        self.ui.plot_bawah.setVisible(show_bawah)
        self.ui.line.setVisible(show_bawah)

        # Redraw
        self.ui.plot_atas.canvas.draw()
        self.ui.plot_bawah.canvas.draw()
        # atau: canvas.draw_idle()

class PlotPopup(QMainWindow):
    def __init__(self, parent, src_ax):
        super().__init__(parent)
        self.setWindowTitle("Interactive Plot")
        self.resize(900, 600)

        # Figure + Canvas
        self.fig = Figure(constrained_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)

        # Toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        from PyQt5.QtWidgets import QWidget, QVBoxLayout
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setCentralWidget(central)

        # Copy data/style from source axis
        self._clone_axes(src_ax)

        # Hover annotation
        self.ann = self.ax.annotate(
            "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->")
        )
        self.ann.set_visible(False)

        # Connect only motion event
        self._cid_move = self.canvas.mpl_connect('motion_notify_event', self._on_move)

        self.canvas.draw()

    def _clone_axes(self, src):
        self.ax.set_xscale(src.get_xscale())
        self.ax.set_yscale(src.get_yscale())

        # Copy lines
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