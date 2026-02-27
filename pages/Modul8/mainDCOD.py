import numpy as np
import sys
from pathlib import Path
from PyQt5 import QtWidgets, QtCore

import pages.Modul8.gambar_rc
from pages.Modul8.calc import *
from pages.Modul8.plot import PlotWindow
from pages.Modul8.ui_8.ui_main import Ui_MainWindow

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.plantPlot = None
        self.plantTimer = QtCore.QTimer(self)
        self.plantTimer.timeout.connect(self.updatePlantSimulation)

        self.simX = None
        self.simXHat = None
        self.simStep = 0
        self.simTs = 0.01
        duration = 3.0
        self.simMaxSteps = int(duration / self.simTs)
        self.stepFunc = None
        self.simMode = None
        self.currentMode = None

        self.plant.clicked.connect(self.plotPlant)
        self.plantwobsv.clicked.connect(self.plotPlantWithObserver)
        self.plantwctrl.clicked.connect(self.plotPlantWithController)
        self.plantwobsvwctrl.clicked.connect(self.plotPlantWithObserverAndController)

        self.setPage(0)
        self.setupStackedNavigation()
        self.setupModelButtons()


    def setPage(self, index: int):
        self.stackedWidget.setCurrentIndex(index)

        unit_map = {
            0: "RPM",
            1: "Meter",
            2: "Volt"
        }
        self.unitLabel.setText(unit_map.get(index, ""))

    def setupStackedNavigation(self):
        self.motorButton.clicked.connect(lambda: self.setPage(0))
        self.leftMotorPG.clicked.connect(lambda: self.setPage(2))
        self.rightMotorPG.clicked.connect(lambda: self.setPage(1))

        self.damperButton.clicked.connect(lambda: self.setPage(1))
        self.leftDamperPG.clicked.connect(lambda: self.setPage(0))
        self.rightDamperPG.clicked.connect(lambda: self.setPage(2))

        self.buckButton.clicked.connect(lambda: self.setPage(2))
        self.leftBuckPG.clicked.connect(lambda: self.setPage(1))
        self.rightBuckPG.clicked.connect(lambda: self.setPage(0))

    def setupModelButtons(self):
        self.saveButton.clicked.connect(self.setDiscreteModel)
        self.clearButton.clicked.connect(self.resetDiscreteModel)

    def readNumber(self, lineEdit):
        text = lineEdit.text().strip()

        if text == "":
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "Isi semua nilai sebelum melanjutkan."
            )
            raise ValueError("empty")

        try:
            return float(text)
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "Input hanya boleh berisi angka."
            )
            raise ValueError("non-numeric")

    def setDiscreteModel(self):
        try:
            A = np.array([
                [self.readNumber(self.a11), self.readNumber(self.a12)],
                [self.readNumber(self.a21), self.readNumber(self.a22)],
            ])

            B = np.array([
                [self.readNumber(self.b11)],
                [self.readNumber(self.b21)],
            ])

            L = np.array([
                [self.readNumber(self.l1)],
                [self.readNumber(self.l2)],
            ])

            R = np.array([
                [self.readNumber(self.r1), self.readNumber(self.r2)],
            ])

            N_val = self.readNumber(self.n)
            N = np.array([[N_val]])

            setpoint = self.readNumber(self.setpoint)

            print("A:", A)
            print("B:", B)
            print("L:", L)
            print("R:", R)
            print("N:", N)
            print("Setpoint:", setpoint)

        except ValueError:
            return

        self.A = A
        self.B = B
        self.L = L
        self.R = R
        self.N = N
        self.setpointValue = setpoint

        self.C = np.array([[1.0, 0.0]])
        self.D = np.zeros((1, 1))

    def resetDiscreteModel(self):
        self.a11.setText("")
        self.a12.setText("")
        self.a21.setText("")
        self.a22.setText("")

        self.b11.setText("")
        self.b21.setText("")

        self.l1.setText("")
        self.l2.setText("")

        self.r1.setText("")
        self.r2.setText("")

        self.n.setText("")
        self.setpoint.setText("")

    ## Mode Plot

    def plotPlant(self):
        self.startPlot(mode="plant")

    def plotPlantWithObserver(self):
        self.startPlot(mode="plant_obs")

    def plotPlantWithController(self):
        self.startPlot(mode="plant_ctrl")

    def plotPlantWithObserverAndController(self):
        self.startPlot(mode="plant_obs_ctrl")

    def startPlot(self, mode: str):
        if not hasattr(self, "A") or not hasattr(self, "B"):
            QtWidgets.QMessageBox.warning(
                self,
                "Model belum siap",
                "Simpan discrete model terlebih dahulu."
            )
            return

        self.currentMode = mode

        # inisialisasi state
        self.simX = np.zeros((self.A.shape[0], 1))
        self.simXHat = np.array([[0.5],
                                 [0.0]])
        self.simStep = 0

        # pilih fungsi step + judul
        if mode == "plant":
            self.stepFunc = self.stepPlantOnly
            showObserver = False
            title = "Plant Response"
        elif mode == "plant_obs":
            self.stepFunc = self.stepPlantWithObserver
            showObserver = True
            title = "Plant + Observer Response"
        elif mode == "plant_ctrl":
            self.stepFunc = self.stepPlantWithController
            showObserver = False
            title = "Plant + Controller Response"
        elif mode == "plant_obs_ctrl":
            self.stepFunc = self.stepPlantWithObserverAndControllerStep
            showObserver = False
            title = "Plant + Observer + Controller Response"
        else:
            self.stepFunc = None
            showObserver = False
            title = "Response"

        if self.stepFunc is None:
            QtWidgets.QMessageBox.warning(self, "Error", "Mode simulasi tidak dikenal.")
            return

        # ====== LABEL Y BERDASARKAN PAGE ======
        page_idx = self.stackedWidget.currentIndex()
        if page_idx == 0:
            # Motor
            y1_label = "ω (rpm)"
            y2_label = "Current (A)"
        elif page_idx == 1:
            # Damper / translational
            y1_label = "Position (m)"
            y2_label = "Velocity (m/s)"
        elif page_idx == 2:
            # Buck converter
            y1_label = "Current (A)"
            y2_label = "Voltage (V)"
        else:
            y1_label = "State 1"
            y2_label = "State 2"

        # ====== X MAX (durasi tetap) ======
        x_max = self.simMaxSteps * self.simTs

        # ====== SETPOINT REFERENCE LINE ======
        ref_value = getattr(self, "setpointValue", None)
        if page_idx in (0, 1):
            ref_axis = 1      # state 1 (grafik atas)
        elif page_idx == 2:
            ref_axis = 2      # state 2 (grafik bawah)
        else:
            ref_axis = None

        # buka / reset window plot
        if self.plantPlot is None or not self.plantPlot.isVisible():
            self.plantPlot = PlotWindow(
                self,
                title=title,
                showObserver=showObserver,
                y1_label=y1_label,
                y2_label=y2_label,
                x_max=x_max,
                ref_axis=ref_axis,
                ref_value=ref_value
            )
            self.plantPlot.show()
        else:
            self.plantPlot.close()
            self.plantPlot = PlotWindow(
                self,
                title=title,
                showObserver=showObserver,
                y1_label=y1_label,
                y2_label=y2_label,
                x_max=x_max,
                ref_axis=ref_axis,
                ref_value=ref_value
            )
            self.plantPlot.show()

        # start timer (ms)
        self.plantTimer.start(int(self.simTs * 1000))

    def stepPlantOnly(self):
        rk = getattr(self, "setpointValue", 0.0)
        uk = rk
        self.simX, yk = runDiscretePlant(self.simX, uk, self.A, self.B, self.C, self.D)

    def stepPlantWithObserver(self):
        rk = getattr(self, "setpointValue", 0.0)
        uk = rk
        self.simX, yk = runDiscretePlant(self.simX, uk, self.A, self.B, self.C, self.D)
        if yk is None:
            yk = self.C @ self.simX
        self.simXHat = runObserver(self.simXHat, uk, yk, self.A, self.B, self.C, self.L)

    def stepPlantWithController(self):
        rk = self.setpointValue
        uk = runStateFeedback(self.simX, rk, self.R, self.N)
        self.simX, yk = runDiscretePlant(self.simX, uk, self.A, self.B, self.C, self.D)

    def stepPlantWithObserverAndControllerStep(self):
        rk = self.setpointValue
        self.simX, self.simXHat, uk, yk = stepClosedLoop(
            self.simX,
            self.simXHat,
            rk,
            self.A,
            self.B,
            self.C,
            self.D,
            self.L,
            self.R,
            self.N
        )


    #  ENGINE UPDATE PLOT
    def updatePlantSimulation(self):
        if self.simStep >= self.simMaxSteps or self.stepFunc is None:
            self.plantTimer.stop()
            return

        # jalankan 1 step sesuai mode (pakai fungsi-fungsi di calc.py)
        self.stepFunc()

        # waktu dalam detik
        t = self.simStep * self.simTs

        # ambil 2 state pertama sesuai mode
        if self.currentMode == "plant_obs":
            # plot x dan x_hat
            x1 = float(self.simX[0, 0])
            x2 = float(self.simX[1, 0]) if self.simX.shape[0] > 1 else 0.0
            x1_hat = float(self.simXHat[0, 0])
            x2_hat = float(self.simXHat[1, 0]) if self.simXHat.shape[0] > 1 else 0.0

            if self.plantPlot is not None:
                self.plantPlot.appendSample(t, x1, x2, x1_hat, x2_hat)

        elif self.currentMode == "plant_obs_ctrl":
            # untuk mode observer+controller, kamu minta gunakan x observer,
            # dan di grafik cuma 1 kurva per state (x̂)
            x1_hat = float(self.simXHat[0, 0])
            x2_hat = float(self.simXHat[1, 0]) if self.simXHat.shape[0] > 1 else 0.0

            if self.plantPlot is not None:
                self.plantPlot.appendSample(t, x1_hat, x2_hat)

        else:
            # mode "plant" dan "plant_ctrl": pakai x sebenarnya
            x1 = float(self.simX[0, 0])
            x2 = float(self.simX[1, 0]) if self.simX.shape[0] > 1 else 0.0

            if self.plantPlot is not None:
                self.plantPlot.appendSample(t, x1, x2)

        self.simStep += 1

    def closeEvent(self, event):
        # Tutup ProblemMotorWindow kalau terbuka
        if hasattr(self, "problemMotorWindow") and self.problemMotorWindow is not None:
            if self.problemMotorWindow.isVisible():
                self.problemMotorWindow.close()

        # Tutup PlotWindow kalau terbuka
        if self.plantPlot is not None and self.plantPlot.isVisible():
            self.plantPlot.close()

        event.accept()
    
    def centerOnScreen(self, window):
        fg = QtWidgets.QDesktopWidget().availableGeometry().center()
        geo = window.frameGeometry()
        geo.moveCenter(fg)
        window.move(geo.topLeft())

def exec_DCOD(nama, npm):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    return window
