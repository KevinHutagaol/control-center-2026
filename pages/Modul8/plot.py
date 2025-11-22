# plot.py
from PyQt5 import QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class PlotWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        parent=None,
        title="Response",
        showObserver=False,
        y1_label="x₁",
        y2_label="x₂",
        x_max=1.0,
        ref_axis=None,     # 1 = axis atas, 2 = axis bawah
        ref_value=None     # nilai setpoint
    ):
        super().__init__(parent)

        self.setWindowTitle(title)
        self.resize(900, 600)

        self.showObserver = showObserver
        self.x_max = float(x_max)
        self.ref_axis = ref_axis
        self.ref_value = ref_value

        # ====== DATA ======
        self.t_data = []
        self.x1_data = []
        self.x2_data = []
        self.x1hat_data = []
        self.x2hat_data = []

        # ====== FIGURE ======
        self.fig = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.fig)

        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)

        # ====== LABEL AXIS ======
        self.ax1.set_ylabel(y1_label)
        self.ax2.set_ylabel(y2_label)
        self.ax2.set_xlabel("Time [s]")

        self.ax1.grid(True)
        self.ax2.grid(True)

        # ====== LINES STATE ======
        self.line_x1, = self.ax1.plot([], [], label="State 1")
        self.line_x2, = self.ax2.plot([], [], label="State 2")

        if showObserver:
            self.line_x1hat, = self.ax1.plot([], [], "--", label="State 1 hat")
            self.line_x2hat, = self.ax2.plot([], [], "--", label="State 2 hat")
        else:
            self.line_x1hat = None
            self.line_x2hat = None

        # ====== SETPOINT LINE (REF) ======
        self.ref_line1 = None
        self.ref_line2 = None
        if (self.ref_axis == 1) and (self.ref_value is not None):
            self.ref_line1 = self.ax1.axhline(
                self.ref_value, linestyle="--", color="gray", label="Setpoint"
            )
        elif (self.ref_axis == 2) and (self.ref_value is not None):
            self.ref_line2 = self.ax2.axhline(
                self.ref_value, linestyle="--", color="gray", label="Setpoint"
            )

        # Legend setelah semua line dibuat
        self.ax1.legend()
        self.ax2.legend()

        # Layout
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(self.canvas)
        self.setCentralWidget(central)

        self.resetPlot()

    def resetPlot(self):
        self.t_data.clear()
        self.x1_data.clear()
        self.x2_data.clear()
        self.x1hat_data.clear()
        self.x2hat_data.clear()

        self.line_x1.set_data([], [])
        self.line_x2.set_data([], [])

        if self.line_x1hat is not None:
            self.line_x1hat.set_data([], [])
            self.line_x2hat.set_data([], [])

        # X fixed dari 0 sampai x_max (durasi simulasi)
        self.ax1.set_xlim(-1, self.x_max)
        self.ax2.set_xlim(-1, self.x_max)

        # initial Y
        self.ax1.set_ylim(-1, 1)
        self.ax2.set_ylim(-1, 1)

        self.canvas.draw_idle()

    def appendSample(self, t, x1, x2, x1_hat=None, x2_hat=None):
        # simpan data
        self.t_data.append(float(t))
        self.x1_data.append(float(x1))
        self.x2_data.append(float(x2))

        if self.showObserver and x1_hat is not None:
            self.x1hat_data.append(float(x1_hat))
            self.x2hat_data.append(float(x2_hat))

        # update garis utama
        self.line_x1.set_data(self.t_data, self.x1_data)
        self.line_x2.set_data(self.t_data, self.x2_data)

        # update observer
        if self.showObserver and self.line_x1hat is not None:
            self.line_x1hat.set_data(self.t_data, self.x1hat_data)
            self.line_x2hat.set_data(self.t_data, self.x2hat_data)

        # X TIDAK DI-AUTOSCALE lagi, tetap 0..x_max

        # autoscale Y state 1
        y1_vals = self.x1_data.copy()
        if self.showObserver:
            y1_vals += self.x1hat_data
        if y1_vals:
            ymin = min(y1_vals)
            ymax = max(y1_vals)
            if ymin == ymax:
                ymin -= 1.0
                ymax += 1.0
            pad = 0.1 * (ymax - ymin)
            self.ax1.set_ylim(ymin - pad, ymax + pad)

        # autoscale Y state 2
        y2_vals = self.x2_data.copy()
        if self.showObserver:
            y2_vals += self.x2hat_data
        if y2_vals:
            ymin = min(y2_vals)
            ymax = max(y2_vals)
            if ymin == ymax:
                ymin -= 1.0
                ymax += 1.0
            pad = 0.1 * (ymax - ymin)
            self.ax2.set_ylim(ymin - pad, ymax + pad)

        self.canvas.draw_idle()
