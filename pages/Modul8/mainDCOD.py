import io
import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator

import pages.Modul8.gambar_rc # noqa
from pages.Modul8.calc import *
from pages.Modul8.plot import PlotWindow
from pages.Modul8.ui_8.ui_main import Ui_MainWindow

from func.UserContext import user_context
from func.saveToZip import saveToZip
from func.sendWithEmail import create_zip_in_memory, sendWithEmail

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        self.setupValidators()

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

        self.btnSaveZip.clicked.connect(self.onSaveZipBtnClicked)
        self.btnSendEmail.clicked.connect(self.onSendEmailBtnClicked)

        self.plant_png_bytes = None
        self.plant_obs_png_bytes = None
        self.plant_ctrl_png_bytes = None
        self.plant_obs_ctrl_png_bytes = None

        self.sim_data = {
            "plant": {"time": [], "x1": [], "x2": []},
            "plant_obs": {"time": [], "x1": [], "x2": [], "x1_hat": [], "x2_hat": []},
            "plant_ctrl": {"time": [], "x1": [], "x2": []},
            "plant_obs_ctrl": {"time": [], "x1": [], "x2": []}
        }

        self.stats_data = {
            "plant": {},
            "plant_obs": {},
            "plant_ctrl": {},
            "plant_obs_ctrl": {}
        }

        self.fig_export = None

        self.setPage(0)
        self.setupStackedNavigation()
        self.setupModelButtons()
        self.setupValidators()


    def setupValidators(self):
        val_double = QDoubleValidator()
        val_double.setNotation(QDoubleValidator.StandardNotation)
        
        self.a11.setValidator(val_double)
        self.a12.setValidator(val_double)
        self.a21.setValidator(val_double)
        self.a22.setValidator(val_double)
        
        self.b11.setValidator(val_double)
        self.b21.setValidator(val_double)
        
        self.l1.setValidator(val_double)
        self.l2.setValidator(val_double)
        
        self.r1.setValidator(val_double)
        self.r2.setValidator(val_double)
        
        self.n.setValidator(val_double)
        self.setpoint.setValidator(val_double)


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

            if np.linalg.matrix_rank(B) == 0:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid Matrix",
                    "Matrix B tidak valid (tidak bisa nol semua)."
                )
                return

            if R.shape[1] != A.shape[0]:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Invalid Matrix",
                    f"Dimension mismatch: R harus berukuran {A.shape[0]}x{A.shape[0]}."
                )
                return

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
        
        # reset simulation data for current mode
        mode_key = mode
        if mode_key == "plant_obs":
            self.sim_data[mode_key] = {"time": [], "x1": [], "x2": [], "x1_hat": [], "x2_hat": []}
        elif mode_key in self.sim_data:
            self.sim_data[mode_key] = {"time": [], "x1": [], "x2": []}

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
            
            try:
                setpoint = getattr(self, "setpointValue", 1.0)
                
                if self.currentMode == "plant":
                    time_data = self.sim_data["plant"]["time"]
                    x1_data = self.sim_data["plant"]["x1"]
                    if len(x1_data) > 0:
                        self.stats_data["plant"] = calculate_statistics(time_data, x1_data, setpoint)
                        
                elif self.currentMode == "plant_obs":
                    time_data = self.sim_data["plant_obs"]["time"]
                    x1_data = self.sim_data["plant_obs"]["x1"]
                    if len(x1_data) > 0:
                        self.stats_data["plant_obs"] = calculate_statistics(time_data, x1_data, setpoint)
                        
                elif self.currentMode == "plant_ctrl":
                    time_data = self.sim_data["plant_ctrl"]["time"]
                    x1_data = self.sim_data["plant_ctrl"]["x1"]
                    if len(x1_data) > 0:
                        self.stats_data["plant_ctrl"] = calculate_statistics(time_data, x1_data, setpoint)
                        
                elif self.currentMode == "plant_obs_ctrl":
                    time_data = self.sim_data["plant_obs_ctrl"]["time"]
                    x1_data = self.sim_data["plant_obs_ctrl"]["x1"]
                    if len(x1_data) > 0:
                        self.stats_data["plant_obs_ctrl"] = calculate_statistics(time_data, x1_data, setpoint)
            except Exception as e:
                print(f"Statistics calculation error: {e}")

            if self.plantPlot is not None:
                png_bytes = self.plantPlot.get_figure_as_bytes()
                
                if self.currentMode == "plant":
                    self.plant_png_bytes = png_bytes
                    self.lblStatusPlant.setText("● Plant: Ready")
                    self.lblStatusPlant.setStyleSheet("color: #00FF00; font-weight: bold;")
                elif self.currentMode == "plant_obs":
                    self.plant_obs_png_bytes = png_bytes
                    self.lblStatusObserver.setText("● Observer: Ready")
                    self.lblStatusObserver.setStyleSheet("color: #00FF00; font-weight: bold;")
                elif self.currentMode == "plant_ctrl":
                    self.plant_ctrl_png_bytes = png_bytes
                    self.lblStatusController.setText("● Controller: Ready")
                    self.lblStatusController.setStyleSheet("color: #00FF00; font-weight: bold;")
                elif self.currentMode == "plant_obs_ctrl":
                    self.plant_obs_ctrl_png_bytes = png_bytes
                    self.lblStatusController.setText("● Observer+Controller: Ready")
                    self.lblStatusController.setStyleSheet("color: #00FF00; font-weight: bold;")
            
            return

        # jalankan 1 step sesuai mode (pakai fungsi-fungsi di calc.py)
        try:
            self.stepFunc()
        except Exception as e:
            self.plantTimer.stop()
            QtWidgets.QMessageBox.critical(self, "Simulation Error", f"Simulation crashed: {str(e)}")
            return

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
            
            self.sim_data["plant_obs"]["time"].append(t)
            self.sim_data["plant_obs"]["x1"].append(x1)
            self.sim_data["plant_obs"]["x2"].append(x2)
            self.sim_data["plant_obs"]["x1_hat"].append(x1_hat)
            self.sim_data["plant_obs"]["x2_hat"].append(x2_hat)

        elif self.currentMode == "plant_obs_ctrl":
            # untuk mode observer+controller, kamu minta gunakan x observer,
            # dan di grafik cuma 1 kurva per state (x̂)
            x1_hat = float(self.simXHat[0, 0])
            x2_hat = float(self.simXHat[1, 0]) if self.simXHat.shape[0] > 1 else 0.0

            if self.plantPlot is not None:
                self.plantPlot.appendSample(t, x1_hat, x2_hat)
            
            self.sim_data["plant_obs_ctrl"]["time"].append(t)
            self.sim_data["plant_obs_ctrl"]["x1"].append(x1_hat)
            self.sim_data["plant_obs_ctrl"]["x2"].append(x2_hat)

        else:
            # mode "plant" dan "plant_ctrl": pakai x sebenarnya
            x1 = float(self.simX[0, 0])
            x2 = float(self.simX[1, 0]) if self.simX.shape[0] > 1 else 0.0

            if self.plantPlot is not None:
                self.plantPlot.appendSample(t, x1, x2)
            
            if self.currentMode == "plant":
                self.sim_data["plant"]["time"].append(t)
                self.sim_data["plant"]["x1"].append(x1)
                self.sim_data["plant"]["x2"].append(x2)
            elif self.currentMode == "plant_ctrl":
                self.sim_data["plant_ctrl"]["time"].append(t)
                self.sim_data["plant_ctrl"]["x1"].append(x1)
                self.sim_data["plant_ctrl"]["x2"].append(x2)

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

    def generate_report_text(self):
        lines = ["=" * 50, "   DISCRETE CONTROL SYSTEM REPORT", "=" * 50, ""]

        if hasattr(self, 'A') and hasattr(self, 'B'):
            lines.append("--- MODEL MATRICES ---")
            lines.append(f"A = [{self.A[0,0]:.4f}  {self.A[0,1]:.4f}]")
            lines.append(f"    [{self.A[1,0]:.4f}  {self.A[1,1]:.4f}]")
            lines.append(f"B = [{self.B[0,0]:.4f}]")
            lines.append(f"    [{self.B[1,0]:.4f}]")
            if hasattr(self, 'L'):
                lines.append(f"L = [{self.L[0,0]:.4f}, {self.L[1,0]:.4f}]")
            if hasattr(self, 'R'):
                lines.append(f"R = [{self.R[0,0]:.4f}, {self.R[0,1]:.4f}]")
            if hasattr(self, 'N'):
                lines.append(f"N = [{self.N[0,0]:.4f}]")
            if hasattr(self, 'setpointValue'):
                lines.append(f"Setpoint: {self.setpointValue}")
            lines.append("")
        
        lines.append("--- SIMULATION STATISTICS ---")
        
        def format_stats(stats_dict, name):
            if not stats_dict:
                return f"  {name}: No data"
            return (f"  {name}: "
                    f"Overshoot={stats_dict.get('overshoot_after', 'N/A')}, "
                    f"Settling={stats_dict.get('settling_time_after', 'N/A')}, "
                    f"Peak Time={stats_dict.get('peak_time_after', 'N/A')}, "
                    f"SS Error={stats_dict.get('steady_state_error', 'N/A')}")
        
        lines.append(format_stats(self.stats_data.get("plant", {}), "Plant Only"))
        lines.append(format_stats(self.stats_data.get("plant_obs", {}), "Plant + Observer"))
        lines.append(format_stats(self.stats_data.get("plant_ctrl", {}), "Plant + Controller"))
        lines.append(format_stats(self.stats_data.get("plant_obs_ctrl", {}), "Plant + Observer + Controller"))
        
        lines.append("\n" + "=" * 50 + "\n")

        return "\n".join(lines)

    def get_html_matrices(self):
        def fmt(val):
            return f"{val:.4f}"
        
        html = "<table style='border-collapse: collapse; width: auto;'>"
        
        html += "<tr><td style='padding: 4px; font-weight: bold;'>A =</td><td style='padding: 4px;'>"
        html += f"[{fmt(self.A[0,0])}  {fmt(self.A[0,1])}]<br>[{fmt(self.A[1,0])}  {fmt(self.A[1,1])}]"
        html += "</td></tr>"
        
        html += "<tr><td style='padding: 4px; font-weight: bold;'>B =</td><td style='padding: 4px;'>"
        html += f"[{fmt(self.B[0,0])}]<br>[{fmt(self.B[1,0])}]"
        html += "</td></tr>"
        
        if hasattr(self, 'L'):
            html += "<tr><td style='padding: 4px; font-weight: bold;'>L =</td><td style='padding: 4px;'>"
            html += f"[{fmt(self.L[0,0])}, {fmt(self.L[1,0])}]"
            html += "</td></tr>"
        
        if hasattr(self, 'R'):
            html += "<tr><td style='padding: 4px; font-weight: bold;'>R =</td><td style='padding: 4px;'>"
            html += f"[{fmt(self.R[0,0])}, {fmt(self.R[0,1])}]"
            html += "</td></tr>"
        
        if hasattr(self, 'N'):
            html += "<tr><td style='padding: 4px; font-weight: bold;'>N =</td><td style='padding: 4px;'>"
            html += f"[{fmt(self.N[0,0])}]"
            html += "</td></tr>"
        
        if hasattr(self, 'setpointValue'):
            html += f"<tr><td style='padding: 4px; font-weight: bold;'>Setpoint</td><td style='padding: 4px;'>{fmt(self.setpointValue)}</td></tr>"
        
        html += "</table>"
        return html

    def get_html_statistics(self):
        html = "<table style='border-collapse: collapse; width: 100%; margin-top: 10px;'>"
        html += "<tr style='background-color: #0078d7; color: white;'><th style='padding: 8px;'>Simulation Mode</th><th style='padding: 8px;'>Overshoot</th><th style='padding: 8px;'>Settling Time</th><th style='padding: 8px;'>Peak Time</th><th style='padding: 8px;'>SS Error</th></tr>"
        
        def add_row(name, stats):
            if not stats:
                return f"<tr><td style='padding: 6px;'>{name}</td><td colspan='4' style='padding: 6px;'>No data</td></tr>"
            overshoot = stats.get('overshoot_after', 'N/A')
            settling = stats.get('settling_time_after', 'N/A')
            peak = stats.get('peak_time_after', 'N/A')
            ss_err = stats.get('steady_state_error', 'N/A')
            return f"<tr><td style='padding: 6px;'>{name}</td><td style='padding: 6px;'>{overshoot}</td><td style='padding: 6px;'>{settling}</td><td style='padding: 6px;'>{peak}</td><td style='padding: 6px;'>{ss_err}</td></tr>"
        
        html += add_row("Plant Only", self.stats_data.get("plant", {}))
        html += add_row("Plant + Observer", self.stats_data.get("plant_obs", {}))
        html += add_row("Plant + Controller", self.stats_data.get("plant_ctrl", {}))
        html += add_row("Plant + Observer + Controller", self.stats_data.get("plant_obs_ctrl", {}))
        
        html += "</table>"
        return html

    def onSaveZipBtnClicked(self):
        if not (self.plant_png_bytes or self.plant_obs_png_bytes or 
                self.plant_ctrl_png_bytes or self.plant_obs_ctrl_png_bytes):
            QtWidgets.QMessageBox.warning(self, "Incomplete System", 
                                          "Please generate at least one plot before saving!")
            return

        files_to_zip = []

        if self.plant_png_bytes:
            files_to_zip.append({"file_name": "Plant_Response.png", "file_data": self.plant_png_bytes})
        if self.plant_obs_png_bytes:
            files_to_zip.append({"file_name": "Plant_With_Observer.png", "file_data": self.plant_obs_png_bytes})
        if self.plant_ctrl_png_bytes:
            files_to_zip.append({"file_name": "Plant_With_Controller.png", "file_data": self.plant_ctrl_png_bytes})
        if self.plant_obs_ctrl_png_bytes:
            files_to_zip.append({"file_name": "Plant_With_Observer_Controller.png", "file_data": self.plant_obs_ctrl_png_bytes})

        report_txt = self.generate_report_text()
        files_to_zip.append({"file_name": "System_Details.txt", "file_data": report_txt.encode('utf-8')})

        saveToZip(self, "Discrete_Control_Report.zip", files_to_zip)

    def onSendEmailBtnClicked(self):
        if not (self.plant_png_bytes or self.plant_obs_png_bytes or 
                self.plant_ctrl_png_bytes or self.plant_obs_ctrl_png_bytes):
            QtWidgets.QMessageBox.warning(self, "Incomplete System", 
                                          "Please generate at least one plot before sending!")
            return

        files_to_zip = []

        if self.plant_png_bytes:
            files_to_zip.append({"file_name": "Plant_Response.png", "file_data": self.plant_png_bytes})
        if self.plant_obs_png_bytes:
            files_to_zip.append({"file_name": "Plant_With_Observer.png", "file_data": self.plant_obs_png_bytes})
        if self.plant_ctrl_png_bytes:
            files_to_zip.append({"file_name": "Plant_With_Controller.png", "file_data": self.plant_ctrl_png_bytes})
        if self.plant_obs_ctrl_png_bytes:
            files_to_zip.append({"file_name": "Plant_With_Observer_Controller.png", "file_data": self.plant_obs_ctrl_png_bytes})

        report_txt = self.generate_report_text()
        files_to_zip.append({"file_name": "System_Details.txt", "file_data": report_txt.encode('utf-8')})

        try:
            zip_bytes = create_zip_in_memory(files_to_zip)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to compress files: {e}")
            return

        if len(zip_bytes) > 900 * 1024:
            print("Warning: Zip file is large. Email might fail due to 1MB limit.")

        matrices_html = self.get_html_matrices() if hasattr(self, 'A') else "No matrices available"
        stats_html = self.get_html_statistics()
        
        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333;">
            <div style="background-color: #0078d7; color: white; padding: 20px; text-align: center;">
                <h2>Discrete Control Systems Simulation Report</h2>
                <p>Module 8: State-Space Control & Observer</p>
            </div>
            <div style="padding: 20px;">
                <p>Hello {user_context.display_name},</p>
                <p>Your simulation has been successfully processed. Attached is the <strong>ZIP file</strong> containing:</p>
                <ul>
                    <li>Plant Response Plots</li>
                    <li>Plant with Observer Plots</li>
                    <li>Plant with Controller Plots</li>
                    <li>Plant with Observer and Controller Plots</li>
                    <li>System Parameters (Text File)</li>
                </ul>
                <hr style="border: 0; border-top: 1px solid #eee;">
                <h3>Model Matrices</h3>
                <div style="background-color: #f9f9f9; padding: 15px; border-left: 5px solid #0078d7; font-family: monospace; font-size: 12px;">
                    {matrices_html}
                </div>
                <h3>Simulation Statistics</h3>
                <div style="background-color: #f9f9f9; padding: 15px; border-left: 5px solid #0078d7;">
                    {stats_html}
                </div>
                <br>
                <p><em>Control Laboratory 2026</em></p>
                <p>Departemen Teknik Elektro Universitas Indonesia</p>
            </div>
        </body>
        </html>
        """

        QtWidgets.QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        success, message = sendWithEmail(
            subject="Lab Report: Discrete Control System Results",
            html_body=html_content,
            text_body=report_txt,
            attachments=[
                {"filename": "Discrete_Control_Report.zip", "content": zip_bytes}
            ]
        )

        QtWidgets.QApplication.restoreOverrideCursor()

        if success:
            QtWidgets.QMessageBox.information(self, "Email Sent", message)
        else:
            QtWidgets.QMessageBox.critical(self, "Sending Failed", f"Could not send email.\nError: {message}")

def exec_DCOD(nama, npm):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()

    return window
