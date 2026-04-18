import sys
import random
import math
from collections import deque
from datetime import datetime
from PyQt5 import QtWidgets, QtChart, QtCore, QtGui
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import control as ctrl
import pandas as pd
import io
import zipfile
import base64

from func.sendWithEmail import create_zip_in_memory, sendWithEmail
from func.UserContext import user_context

import pages.Modul910.asset.resources  # noqa

from pages.Modul910.ui_910.ui_main import Ui_MainWindow as Ui_main
from pages.Modul910.ui_910.ui_sa import Ui_MainWindow as Ui_sa
from pages.Modul910.ui_910.ui_clc import Ui_MainWindow as Ui_clc
from pages.Modul910.ui_910.ui_olc import Ui_MainWindow as Ui_olc
from pages.Modul910.ui_910.ui_lrc import Ui_MainWindow as Ui_lrc
from pages.Modul910.ui_910.ui_linlog import Ui_MainWindow as Ui_linlog
from pages.Modul910.ui_910.ui_calibration import Ui_MainWindow as Ui_calibration
from pages.Modul910.ui_910.ui_progressbar import Ui_Dialog as Ui_progressbar

MOTOR_STATES = {
    1: {
        'K': 200, 'tau1': 0.15, 'tau2': 0.008, 'L': 0.04,
        'voltage': 12, 'ppr': 385,
        'minLinRPM': 500, 'maxLinRPM': 2200, 'max_rpm': 3000,
    },
    2: {
        'K': 250, 'tau1': 0.20, 'tau2': 0.012, 'L': 0.06,
        'voltage': 12, 'ppr': 360,
        'minLinRPM': 600, 'maxLinRPM': 2700, 'max_rpm': 3600,
    },
    3: {
        'K': 150, 'tau1': 0.28, 'tau2': 0.015, 'L': 0.08,
        'voltage': 12, 'ppr': 330,
        'minLinRPM': 400, 'maxLinRPM': 1600, 'max_rpm': 2200,
    },
    4: {
        'K': 275, 'tau1': 0.12, 'tau2': 0.005, 'L': 0.03,
        'voltage': 12, 'ppr': 400,
        'minLinRPM': 700, 'maxLinRPM': 3000, 'max_rpm': 4000,
    },
}


class MainWindow(QtWidgets.QMainWindow, Ui_main):
    def __init__(self, kelompok, nama='', npm=''):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Practicum Software : DC Motor Modeling and Control (Simulation)")
        self.setWindowIcon(QtGui.QIcon("../../public/Logo Merah.png"))

        state_num = random.choice(list(MOTOR_STATES.keys()))
        self.motor_state = MOTOR_STATES[state_num]
        ms = self.motor_state
        self.nama = nama
        self.npm = npm
        self.kelompok = kelompok

        self.speed_constant = ms['ppr']
        self.max_rpm = ms['max_rpm']
        self.lrc_min_pwm = None
        self.lrc_max_pwm = None
        self.lrc_min_rpm = ms['minLinRPM']
        self.lrc_max_rpm = ms['maxLinRPM']

        self.ppr.setText(f"{ms['ppr']}")
        self.maxRPM.setText(f"{ms['max_rpm']}")
        self.set_status("green")

        self.child_windows = {}

        self.olc.clicked.connect(self.olcClicked)
        self.clc.clicked.connect(self.clcClicked)
        self.sa.clicked.connect(self.saClicked)
        self.encoder.clicked.connect(self._disabled_clicked)
        self.log.clicked.connect(self._disabled_clicked)
        self.lrc.clicked.connect(self._disabled_clicked)

        self.ports.setEnabled(False)
        self.ports.clear()
        self.ports.addItem("Simulation Mode")
        self.ports.setCurrentIndex(0)

        for btn in [self.encoder, self.log, self.lrc]:
            btn.setEnabled(False)

    def _disabled_clicked(self):
        QtWidgets.QMessageBox.information(
            self, "Simulation Mode",
            "This feature is not available in simulation mode.\n"
            "Motor parameters are pre-configured automatically."
        )

    def set_status(self, status):
        self.statusIndicator.setProperty("status", status)
        self.statusIndicator.style().unpolish(self.statusIndicator)
        self.statusIndicator.style().polish(self.statusIndicator)
        self.statusIndicator.update()

    def close_other_windows(self, keep=[]):
        for name, win in list(self.child_windows.items()):
            if name not in keep and win is not None:
                win.close()
                self.child_windows.pop(name, None)

    def saClicked(self):
        self.child_windows["sa"] = sa(self)
        self.child_windows["sa"].show()

    def olcClicked(self):
        self.close_other_windows(keep=["sa"])
        self.child_windows["olc"] = olc(self)
        self.child_windows["olc"].show()

    def clcClicked(self):
        self.close_other_windows(keep=["sa"])
        self.child_windows["clc"] = clc(self)
        self.child_windows["clc"].show()

    def closeEvent(self, event):
        event.accept()


class Encoder(QtWidgets.QMainWindow, Ui_calibration):
    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.setupUi(self)
        self.main_window = main_window
        self.setWindowTitle("Encoder Calibration")
        QtWidgets.QMessageBox.information(
            self, "Simulation Mode",
            "Encoder calibration is not available in simulation mode.\n"
            "Motor parameters are pre-configured automatically."
        )
        self.close()


class ProgressBar(QtWidgets.QDialog, Ui_progressbar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)


class LogWindow(QtWidgets.QMainWindow, Ui_linlog):
    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.setupUi(self)
        self.main_window = main_window
        self.setWindowTitle("Motor Logging")
        QtWidgets.QMessageBox.information(
            self, "Simulation Mode",
            "Motor logging is not available in simulation mode."
        )
        self.close()


class LRC(QtWidgets.QMainWindow, Ui_lrc):
    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.setupUi(self)
        self.main_window = main_window
        self.setWindowTitle("Linear Region Configuration")
        QtWidgets.QMessageBox.information(
            self, "Simulation Mode",
            "Linear region configuration is not available in simulation mode.\n"
            "Motor parameters are pre-configured automatically."
        )
        self.close()


class olc(QtWidgets.QMainWindow, Ui_olc):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setupUi(self)
        self.setWindowTitle("DC Motor Open Loop Control")
        self.setWindowIcon(QtGui.QIcon("../../public/Logo Merah.png"))

        self.main_window = main_window
        ms = main_window.motor_state

        self.minLinRPM = ms['minLinRPM']
        self.maxLinRPM = ms['maxLinRPM']
        self.maxRPM = ms['max_rpm']

        self.MinLinRPMDisp.setText(f"{self.minLinRPM:.2f}")
        self.MaxLinRPMDisp.setText(f"{self.maxLinRPM:.2f}")
        self.MaxRPMDisp.setText(f"{self.maxRPM:.2f}")

        self.start.clicked.connect(self.startClicked)
        self.analyze.clicked.connect(self.analyzeClicked)
        self.popup.clicked.connect(self.popupClicked)
        self.fopdt.clicked.connect(self.fopdtClicked)
        self.popup_2.clicked.connect(self.popup2Clicked)

        self.chart = QtChart.QChart()
        self.speedSeries = QtChart.QLineSeries()
        self.targetSeries = QtChart.QLineSeries()
        self.fopdtSeries = QtChart.QLineSeries()

        self.speedSeries.setPointsVisible(True)

        self.chart.addSeries(self.speedSeries)
        self.chart.addSeries(self.targetSeries)
        self.chart.addSeries(self.fopdtSeries)
        self.speedSeries.setColor(QtGui.QColor("blue"))
        self.targetSeries.setColor(QtGui.QColor("red"))
        self.fopdtSeries.setColor(QtGui.QColor("green"))

        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(QtCore.Qt.AlignTop)
        self.chart.legend().setFont(QtGui.QFont("Arial", 10))
        self.speedSeries.setName("Speed (RPM)")
        self.targetSeries.setName("Target (RPM)")
        self.fopdtSeries.setName("FOPDT Model")

        self.chart.createDefaultAxes()
        self.chart.axisX().setTitleText("Time (ms)")
        self.chart.axisY().setTitleText("Speed (RPM)")
        self.chart.setTitle("Motor Transient Response")

        self.chartView = QtChart.QChartView(self.chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        layout = self.olcgraph.layout()
        if not layout:
            layout = QtWidgets.QGridLayout(self.olcgraph)
        layout.addWidget(self.chartView, 0, 0, 2, 1)

        self.speedSeries.hovered.connect(self.on_hover)
        self.targetSeries.hovered.connect(self.on_hover)

        self.tooltip = QtWidgets.QLabel(self.chartView)
        self.tooltip.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip.hide()

        self.chart2 = QtChart.QChart()
        self.controllerSeries = QtChart.QLineSeries()
        self.errorSeries = QtChart.QLineSeries()
        self.controllerSeries.setPointsVisible(True)
        self.errorSeries.setPointsVisible(True)
        self.chart2.addSeries(self.controllerSeries)
        self.chart2.addSeries(self.errorSeries)
        self.controllerSeries.setColor(QtGui.QColor("green"))
        self.errorSeries.setColor(QtGui.QColor("red"))
        self.chart2.legend().setVisible(True)
        self.chart2.legend().setAlignment(QtCore.Qt.AlignTop)
        self.chart2.legend().setFont(QtGui.QFont("Arial", 10))
        self.controllerSeries.setName("Controller Output (PWM)")
        self.errorSeries.setName("Error (RPM)")

        self.chart2.createDefaultAxes()
        self.chart2.axisX().setTitleText("Time (ms)")
        self.chart2.axisY().setTitleText("Controller Output (PWM)")
        self.chart2.setTitle("Controller Output Over Time")

        self.chartView2 = QtChart.QChartView(self.chart2)
        self.chartView2.setRenderHint(QtGui.QPainter.Antialiasing)
        layout2 = self.controlgraph.layout()
        if not layout2:
            layout2 = QtWidgets.QGridLayout(self.controlgraph)
        layout2.addWidget(self.chartView2, 0, 0, 2, 1)

        self.controllerSeries.hovered.connect(self.on_hover2)
        self.tooltip2 = QtWidgets.QLabel(self.chartView2)
        self.tooltip2.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip2.hide()

        self.save_action = QtWidgets.QAction("Save Data", self)
        self.save_action.setShortcut(QtGui.QKeySequence.Save)
        self.save_action.triggered.connect(self.saveDataToCSV)
        self.addAction(self.save_action)

    def on_hover(self, point, state):
        if state:
            if hasattr(self, 'time_data') and hasattr(self, 'rpm_data'):
                hover_time = point.x()
                closest_index = 0
                min_distance = float('inf')
                for i, time_val in enumerate(self.time_data):
                    distance = abs(time_val - hover_time)
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
                actual_time = self.time_data[closest_index]
                actual_speed = self.rpm_data[closest_index]
                self.tooltip.setText(f"Time: {actual_time} ms\nSpeed: {actual_speed:.1f} RPM")
            else:
                self.tooltip.setText(f"Time: {point.x():.1f} ms\nSpeed: {point.y():.1f} RPM")
            self.tooltip.adjustSize()
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView.mapFromGlobal(cursor_pos)
            self.tooltip.move(widget_pos.x() - self.tooltip.width() - 10, widget_pos.y() - 20)
            self.tooltip.show()
        else:
            self.tooltip.hide()

    def on_hover2(self, point, state):
        if state:
            if hasattr(self, 'time_data') and hasattr(self, 'controller_data') and hasattr(self, 'error_data'):
                hover_time = point.x()
                closest_index = 0
                min_distance = float('inf')
                for i, time_val in enumerate(self.time_data):
                    distance = abs(time_val - hover_time)
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
                actual_time = self.time_data[closest_index]
                actual_pwm = self.controller_data[closest_index]
                actual_error = self.error_data[closest_index]
                self.tooltip2.setText(f"Time: {actual_time:.1f} ms\nPWM: {actual_pwm:.1f}\nError: {actual_error:.1f}")
            else:
                self.tooltip2.setText(f"Time: {point.x():.1f} ms\nPWM: {point.y():.1f}")
            self.tooltip2.adjustSize()
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView2.mapFromGlobal(cursor_pos)
            self.tooltip2.move(widget_pos.x() - self.tooltip2.width() - 10, widget_pos.y() - 20)
            self.tooltip2.show()
        else:
            self.tooltip2.hide()

    def startClicked(self):
        if not self.targetRPM.text().strip():
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Target RPM field cannot be empty.")
            return

        try:
            targetRPM = float(self.targetRPM.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for Target RPM.")
            return

        if targetRPM <= 0:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Target RPM must be positive.")
            return

        ms = self.main_window.motor_state
        min_lin_rpm = self.minLinRPM
        max_lin_rpm = self.maxLinRPM
        max_rpm = self.maxRPM

        is_in_linear_range = min_lin_rpm <= targetRPM <= max_lin_rpm
        is_at_max = abs(targetRPM - max_rpm) < 0.01

        if not (is_in_linear_range or is_at_max):
            if targetRPM > max_rpm:
                QtWidgets.QMessageBox.warning(
                    self, "Invalid Input",
                    f"Target RPM cannot exceed maximum RPM ({max_rpm:.2f})."
                )
                return
            QtWidgets.QMessageBox.warning(
                self, "Invalid Input",
                f"Target RPM must be either between {min_lin_rpm:.2f} and {max_lin_rpm:.2f}, "
                f"or equal to {max_rpm:.2f}."
            )
            return

        self.runSimulation(targetRPM)

    def runSimulation(self, targetRPM):
        ms = self.main_window.motor_state
        K_v = ms['K']
        tau1 = ms['tau1']
        tau2 = ms['tau2']
        L = ms['L']
        voltage = ms['voltage']

        G1 = ctrl.tf([K_v], [tau1, 1])
        G2 = ctrl.tf([1], [tau2, 1])
        G_no_delay = ctrl.series(G1, G2)

        num_delay, den_delay = ctrl.pade(L, 2)
        Delay = ctrl.tf(num_delay, den_delay)
        G = ctrl.series(G_no_delay, Delay)

        duration = 10.0
        n_points = 1001
        T = np.linspace(0, duration, n_points)
        t, y = ctrl.step_response(G, T=T)

        rpm_response = y * voltage

        rpm_response = np.maximum(rpm_response, 0)

        steady_state = K_v * voltage
        noise_std = 0.005 * steady_state
        np.random.seed(None)
        rpm_noisy = rpm_response + np.random.normal(0, noise_std, len(rpm_response))
        rpm_noisy = np.maximum(rpm_noisy, 0)

        self.time_data = [int(round(t_i * 1000)) for t_i in t]
        self.rpm_data = [float(r) for r in rpm_noisy]
        self.target_data = [targetRPM] * len(self.time_data)
        self.controller_data = [255] * len(self.time_data)
        self.error_data = [targetRPM - r for r in self.rpm_data]

        self.speedSeries.clear()
        self.targetSeries.clear()
        self.controllerSeries.clear()
        self.errorSeries.clear()

        self._olc_anim_index = 0
        self._olc_anim_max_y = max(max(self.rpm_data), targetRPM) * 1.15
        self._olc_anim_max_y2 = max(max(self.controller_data), max(abs(e) for e in self.error_data)) * 1.15
        self._olc_anim_min_y2 = min(self.error_data) * 1.15 if min(self.error_data) < 0 else 0
        self.chart.axisX().setRange(0, max(self.time_data) + 100)
        self.chart.axisY().setRange(0, self._olc_anim_max_y)
        self.chart2.axisX().setRange(0, max(self.time_data) + 100)
        self.chart2.axisY().setRange(min(self._olc_anim_min_y2, 0), self._olc_anim_max_y2)

        if hasattr(self, '_olcAnimTimer') and self._olcAnimTimer is not None:
            self._olcAnimTimer.stop()
        self._olcAnimTimer = QtCore.QTimer(self)
        self._olcAnimTimer.timeout.connect(self._olcAnimStep)
        self._olcAnimTimer.start(10)

    def _olcAnimStep(self):
        steps_per_tick = 5
        for _ in range(steps_per_tick):
            if self._olc_anim_index >= len(self.time_data):
                self._olcAnimTimer.stop()
                self.main_window.olc_data = {
                    'time_data': self.time_data,
                    'rpm_data': self.rpm_data,
                    'target_data': self.target_data,
                    'controller_data': self.controller_data,
                    'error_data': self.error_data,
                }
                return
            i = self._olc_anim_index
            self.speedSeries.append(self.time_data[i], self.rpm_data[i])
            self.targetSeries.append(self.time_data[i], self.target_data[i])
            self.controllerSeries.append(self.time_data[i], self.controller_data[i])
            self.errorSeries.append(self.time_data[i], self.error_data[i])
            self._olc_anim_index += 1

    def fopdtClicked(self):
        if not hasattr(self, 'time_data') or not hasattr(self, 'rpm_data'):
            return

        if not self.k_fopdt.text().strip() or not self.tau_fopdt.text().strip() or \
           not self.targetRPM.text().strip() or not self.l_fopdt.text().strip():
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a value for K, Tau, and L.")
            return

        try:
            K_fopdt = float(self.k_fopdt.text())
            tau_fopdt = float(self.tau_fopdt.text())
            l_fopdt = float(self.l_fopdt.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for K, Tau, and L.")
            return

        if K_fopdt <= 0 or tau_fopdt <= 0 or l_fopdt < 0:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "K and Tau must be positive, L must be non-negative.")
            return

        self.fopdtSeries.clear()

        input_voltage = 12.0

        G_first = ctrl.TransferFunction([K_fopdt], [tau_fopdt, 1])
        pade_order = 2
        num_delay, den_delay = ctrl.pade(l_fopdt, pade_order)
        Delay_pade = ctrl.tf(num_delay, den_delay)
        G = ctrl.series(G_first, Delay_pade)

        real_time = np.array(self.time_data) / 1000.0

        t, y = ctrl.step_response(G, T=real_time)

        self.fopdt_output = y * input_voltage

        for i in range(len(t)):
            self.fopdtSeries.append(t[i] * 1000, y[i] * input_voltage)

    def popupClicked(self):
        if hasattr(self, 'time_data') and hasattr(self, 'rpm_data') and hasattr(self, 'target_data') and self.time_data:
            fig = plt.figure(figsize=(15, 6))
            gs = fig.add_gridspec(1, 2, width_ratios=[2.5, 1])

            ax1 = fig.add_subplot(gs[0])
            ax2 = fig.add_subplot(gs[1])
            ax2.axis('off')

            ax1.plot(self.time_data, self.rpm_data, '-', color='blue', linewidth=2, label='Actual Speed')
            ax1.plot(self.time_data, self.target_data, 'r--', linewidth=2, label='Target Speed')

            if hasattr(self, 'fopdt_output') and self.fopdt_output is not None and len(self.fopdt_output) > 0:
                ax1.plot(self.time_data, self.fopdt_output, 'g-.', linewidth=2, label='FOPDT Model')

            final_value = self.rpm_data[-1] if self.rpm_data else 0
            if final_value > 0:
                ax1.axhline(y=final_value, color='gray', linestyle=':', alpha=0.7)
                ax1.axhline(y=final_value * 0.632, color='green', linestyle=':', alpha=0.5)
                ax1.text(max(self.time_data) * 0.1, final_value + final_value * 0.05,
                         f"Final: {final_value:.1f} RPM", fontsize=9,
                         bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))

            ax1.grid(True, alpha=0.3)
            ax1.set_title("Motor Step Response Analysis", fontsize=14, fontweight='bold')
            ax1.set_xlabel("Time (ms)", fontsize=12)
            ax1.set_ylabel("Speed (RPM)", fontsize=12)
            ax1.legend()

            ax2.axis('off')

            rise_time_text = self.Tr.text().replace(" ms", "") if hasattr(self, 'Tr') and self.Tr.text() != "--" else "N/A"
            t28_text = self.t28.text().replace(" ms", "") if hasattr(self, 't28') and self.t28.text() != "--" else "N/A"
            t63_text = self.t63.text().replace(" ms", "") if hasattr(self, 't63') and self.t63.text() != "--" else "N/A"
            settling_time_text = self.Ts.text().replace(" ms", "") if hasattr(self, 'Ts') and self.Ts.text() != "--" else "N/A"
            fv_text = self.fv.text().replace(" RPM", "") if hasattr(self, 'fv') and self.fv.text() != "--" else "N/A"
            tau_text = self.tau.text().replace(" ms", "") if hasattr(self, 'tau') and self.tau.text() != "--" else "N/A"

            try:
                K_fopdt_text = self.k_fopdt.text() if self.k_fopdt.text().strip() else "N/A"
                tau_fopdt_text = self.tau_fopdt.text() if self.tau_fopdt.text().strip() else "N/A"
                l_fopdt_text = self.l_fopdt.text() if self.l_fopdt.text().strip() else "N/A"
            except Exception:
                K_fopdt_text = "N/A"
                tau_fopdt_text = "N/A"
                l_fopdt_text = "N/A"

            target_rpm = self.targetRPM.text() if self.targetRPM.text().strip() else "N/A"

            analysis_text = (
                f"{'Target RPM'.ljust(20)}{str(target_rpm).rjust(15)}{' RPM'}\n"
                f"{'Final Value'.ljust(20)}{str(fv_text).rjust(15)}{' RPM'}\n"
                f"{'Rise Time (Tr)'.ljust(20)}{str(rise_time_text).rjust(15)}{' ms'}\n"
                f"{'Time to 28.3%'.ljust(20)}{str(t28_text).rjust(15)}{' ms'}\n"
                f"{'Time to 63.2%'.ljust(20)}{str(t63_text).rjust(15)}{' ms'}\n"
                f"{'Settling Time (Ts)'.ljust(20)}{str(settling_time_text).rjust(15)}{' ms'}\n"
                f"{'Time Constant'.ljust(20)}{str(tau_text).rjust(15)}{' ms'}\n"
                f"\n"
                f"{'FOPDT PARAMETERS'.ljust(35)}\n"
                f"{'K (RPM/V)'.ljust(20)}{str(K_fopdt_text).rjust(15)}\n"
                f"{'tau (seconds)'.ljust(20)}{str(tau_fopdt_text).rjust(15)}\n"
                f"{'L (seconds)'.ljust(20)}{str(l_fopdt_text).rjust(15)}\n"
                f"\n"
            )

            ax2.text(
                x=0.1, y=0.1,
                s=analysis_text,
                fontsize=10, color="black", ha='left', family='monospace',
                transform=ax2.transAxes, verticalalignment='bottom'
            )

            plt.tight_layout()
            plt.show()
        else:
            QtWidgets.QMessageBox.information(self, "No Data", "No transient response data available to display.")

    def popup2Clicked(self):
        if hasattr(self, 'time_data') and hasattr(self, 'controller_data') and self.time_data and self.controller_data:
            plt.figure(figsize=(10, 6))
            plt.plot(self.time_data, self.controller_data, 'o-', color='green', linewidth=2, label='Controller Output (PWM)')
            plt.plot(self.time_data, self.error_data, '--', color='red', label='Error (RPM)')
            plt.grid(True)
            plt.xlabel('Time (ms)')
            plt.ylabel('Controller Output (PWM)')
            plt.title('Controller Output Over Time')
            plt.tight_layout()
            plt.legend()
            plt.show()
        else:
            QtWidgets.QMessageBox.information(self, "Log", "No data available to plot.")

    def analyzeClicked(self):
        if not hasattr(self, 'time_data') or not hasattr(self, 'rpm_data'):
            return

        if not self.rpm_data:
            return

        target = self.target_data[-1] if self.target_data else 0

        last_10pct = max(1, len(self.rpm_data) // 10)
        fv = sum(self.rpm_data[-last_10pct:]) / len(self.rpm_data[-last_10pct:])

        for i, target in enumerate(self.target_data):
            if target != 0:
                start_time = self.time_data[i]
                break
        else:
            start_time = 0

        overshoot = max(self.rpm_data) - fv if self.rpm_data else 0

        overshoot_time = None
        for i, speed in enumerate(self.rpm_data):
            if speed == max(self.rpm_data):
                overshoot_time = self.time_data[i] - start_time
                break

        threshold_10 = 0.1 * fv
        threshold_28_3 = 0.283 * fv
        threshold_63_2 = 0.632 * fv
        threshold_90 = 0.9 * fv

        rise_start = None
        time_28_3 = None
        time_63_2 = None
        rise_end = None

        for i, speed in enumerate(self.rpm_data):
            if rise_start is None and speed >= threshold_10:
                rise_start = self.time_data[i]
            if time_28_3 is None and speed >= threshold_28_3:
                time_28_3 = self.time_data[i]
            if time_63_2 is None and speed >= threshold_63_2:
                time_63_2 = self.time_data[i]
            if rise_start is not None and speed >= threshold_90:
                rise_end = self.time_data[i]
                break

        rise_time = (rise_end - rise_start) if rise_start and rise_end else 0
        t_28_3 = (time_28_3 - start_time) if start_time and time_28_3 else 0
        t_63_2 = (time_63_2 - start_time) if start_time and time_63_2 else 0

        gradient_at_tau = None
        dead_time = None
        if t_63_2:
            t_63_2_index = None
            for i, t_val in enumerate(self.time_data):
                if t_val >= t_63_2 + start_time:
                    t_63_2_index = i
                    break

            if t_63_2_index is not None and 0 < t_63_2_index < len(self.time_data) - 1:
                dt_before = self.time_data[t_63_2_index] - self.time_data[t_63_2_index - 1]
                dt_after = self.time_data[t_63_2_index + 1] - self.time_data[t_63_2_index]
                drpm_before = self.rpm_data[t_63_2_index] - self.rpm_data[t_63_2_index - 1]
                drpm_after = self.rpm_data[t_63_2_index + 1] - self.rpm_data[t_63_2_index]

                gradient_at_tau = ((drpm_before / dt_before) + (drpm_after / dt_after)) / 2.0

                if gradient_at_tau > 0:
                    y_intercept = self.rpm_data[t_63_2_index] - gradient_at_tau * self.time_data[t_63_2_index]
                    dead_time = -y_intercept / gradient_at_tau - start_time
                    if dead_time < 0:
                        dead_time = 0

        settling_time = 0
        if rise_end:
            upper_bound = fv * 1.05
            lower_bound = fv * 0.95
            for i in range(len(self.rpm_data) - 1, -1, -1):
                if not (lower_bound <= self.rpm_data[i] <= upper_bound):
                    settling_time = self.time_data[i + 1] - start_time if (i + 1) < len(self.time_data) else 0
                    break

        self.Tr.setText(f"{rise_time} ms" if rise_time else "--")
        self.t28.setText(f"{t_28_3} ms" if t_28_3 else "--")
        self.t63.setText(f"{t_63_2} ms" if t_63_2 else "--")
        self.Ts.setText(f"{settling_time} ms" if settling_time else "--")
        self.fv.setText(f"{fv:.2f} RPM" if fv else "--")
        self.tau.setText(f"{t_63_2:.2f} ms" if t_63_2 else "--")

        try:
            self.main_window.true_fopdt_K = fv / 12.0 if 12.0 != 0 else 0
            self.main_window.true_fopdt_tau = 1.5 * (t_63_2 - t_28_3) / 1000.0 if (t_63_2 and t_28_3) else 0
            self.main_window.true_fopdt_L = dead_time / 1000.0 if dead_time and dead_time > 0 else 0.0
        except Exception as e:
            print(f"Error calculating FOPDT parameters: {e}")

    def saveDataToCSV(self):
        required_data = ['time_data', 'rpm_data', 'target_data', 'error_data', 'controller_data', 'fopdt_output']
        missing_data = []

        for data_name in required_data:
            if data_name == 'fopdt_output':
                if not ((hasattr(self, 'fopdt_output') and self.fopdt_output is not None and len(self.fopdt_output) > 0)):
                    missing_data.append(data_name)
                continue
            if not hasattr(self, data_name) or not getattr(self, data_name):
                missing_data.append(data_name)

        if missing_data:
            QtWidgets.QMessageBox.information(
                self, "Incomplete Data",
                f"Cannot save data. Missing or empty data series:\n" +
                "\n".join([f"  {data.replace('_', ' ').title()}" for data in missing_data]) +
                "\n\nPlease run a complete test first to collect all data."
            )
            return

        data_lengths = {
            'Time': len(self.time_data),
            'Speed': len(self.rpm_data),
            'Target': len(self.target_data),
            'Error': len(self.error_data),
            'Controller': len(self.controller_data),
            'FOPDT': len(self.fopdt_output)
        }

        if len(set(data_lengths.values())) > 1:
            QtWidgets.QMessageBox.warning(
                self, "Data Length Mismatch",
                f"Data series have different lengths:\n" +
                "\n".join([f"  {name}: {length} points" for name, length in data_lengths.items()])
            )
            return

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save OLC Data",
            f"olc_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            data_dict = {
                'Time_ms': self.time_data,
                'Target_Speed_RPM': self.target_data,
                'Actual_Speed_RPM': self.rpm_data,
                'Error_RPM': self.error_data,
                'Controller_Output_PWM': self.controller_data,
                'FOPDT_Model_RPM': self.fopdt_output
            }
            df = pd.DataFrame(data_dict)

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write(f"# OLC Data Export\n")
                f.write(f"# Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Target RPM: {self.target_data[-1] if self.target_data else 'N/A'}\n")
                f.write(f"# Final Speed: {self.rpm_data[-1]:.2f} RPM\n")
                f.write(f"# Data Points: {len(self.time_data)}\n")
                f.write(f"# Duration: {max(self.time_data) - min(self.time_data):.0f} ms\n")
                f.write("#\n")
                df.to_csv(f, index=False)

            QtWidgets.QMessageBox.information(
                self, "Save Successful",
                f"Data saved successfully to:\n{file_path}\n\n"
                f"Summary:\n"
                f"  Records saved: {len(self.time_data)}\n"
                f"  Target RPM: {self.target_data[-1]:.1f}\n"
                f"  Final Speed: {self.rpm_data[-1]:.1f} RPM\n"
                f"  Test Duration: {max(self.time_data) - min(self.time_data):.0f} ms"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Save Error",
                f"Error saving data to CSV:\n{str(e)}"
            )

    def closeEvent(self, event):
        event.accept()


class clc(QtWidgets.QMainWindow, Ui_clc):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setupUi(self)
        self.setWindowTitle("DC Motor Closed Loop Control")
        self.setWindowIcon(QtGui.QIcon("asset/Logo Control.png"))

        self.main_window = main_window

        self.start.clicked.connect(self.startClicked)
        self.analyze.clicked.connect(self.analyzeClicked)
        self.popup.clicked.connect(self.popupClicked)
        self.popup_2.clicked.connect(self.popup2Clicked)

        self.chart = QtChart.QChart()
        self.speedSeries = QtChart.QLineSeries()
        self.targetSeries = QtChart.QLineSeries()

        self.speedSeries.setPointsVisible(True)

        self.chart.addSeries(self.speedSeries)
        self.chart.addSeries(self.targetSeries)
        self.speedSeries.setColor(QtGui.QColor("blue"))
        self.targetSeries.setColor(QtGui.QColor("red"))

        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(QtCore.Qt.AlignTop)
        self.chart.legend().setFont(QtGui.QFont("Arial", 10))
        self.speedSeries.setName("Speed (RPM)")
        self.targetSeries.setName("Target (RPM)")

        self.chart.createDefaultAxes()
        self.chart.axisX().setTitleText("Time (ms)")
        self.chart.axisY().setTitleText("Speed (RPM)")
        self.chart.setTitle("Motor Transient Response")

        self.chartView = QtChart.QChartView(self.chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        layout = self.clcgraph.layout()
        if not layout:
            layout = QtWidgets.QGridLayout(self.clcgraph)
        layout.addWidget(self.chartView, 0, 0, 2, 1)

        self.speedSeries.hovered.connect(self.on_hover)
        self.targetSeries.hovered.connect(self.on_hover)

        self.tooltip = QtWidgets.QLabel(self.chartView)
        self.tooltip.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip.hide()

        self.chart2 = QtChart.QChart()
        self.controllerSeries = QtChart.QLineSeries()
        self.errorSeries = QtChart.QLineSeries()
        self.controllerSeries.setPointsVisible(True)
        self.errorSeries.setPointsVisible(True)
        self.chart2.addSeries(self.controllerSeries)
        self.chart2.addSeries(self.errorSeries)
        self.controllerSeries.setColor(QtGui.QColor("green"))
        self.errorSeries.setColor(QtGui.QColor("red"))
        self.chart2.legend().setVisible(True)
        self.chart2.legend().setAlignment(QtCore.Qt.AlignTop)
        self.chart2.legend().setFont(QtGui.QFont("Arial", 10))
        self.controllerSeries.setName("Controller Output (PWM)")
        self.errorSeries.setName("Error (RPM)")

        self.chart2.createDefaultAxes()
        self.chart2.axisX().setTitleText("Time (ms)")
        self.chart2.axisY().setTitleText("Controller Output (PWM)")
        self.chart2.setTitle("Controller Output Over Time")

        self.chartView2 = QtChart.QChartView(self.chart2)
        self.chartView2.setRenderHint(QtGui.QPainter.Antialiasing)
        layout2 = self.controlgraph.layout()
        if not layout2:
            layout2 = QtWidgets.QGridLayout(self.controlgraph)
        layout2.addWidget(self.chartView2, 0, 0, 2, 1)

        self.controllerSeries.hovered.connect(self.on_hover2)
        self.tooltip2 = QtWidgets.QLabel(self.chartView2)
        self.tooltip2.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip2.hide()

        self.save_action = QtWidgets.QAction("Save Data", self)
        self.save_action.setShortcut(QtGui.QKeySequence.Save)
        self.save_action.triggered.connect(self.saveDataToCSV)
        self.addAction(self.save_action)

    def on_hover(self, point, state):
        if state:
            if hasattr(self, 'time_data') and hasattr(self, 'rpm_data'):
                hover_time = point.x()
                closest_index = 0
                min_distance = float('inf')
                for i, time_val in enumerate(self.time_data):
                    distance = abs(time_val - hover_time)
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
                actual_time = self.time_data[closest_index]
                actual_speed = self.rpm_data[closest_index]
                self.tooltip.setText(f"Time: {actual_time} ms\nSpeed: {actual_speed:.1f} RPM")
            else:
                self.tooltip.setText(f"Time: {point.x():.1f} ms\nSpeed: {point.y():.1f} RPM")
            self.tooltip.adjustSize()
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView.mapFromGlobal(cursor_pos)
            self.tooltip.move(widget_pos.x() - self.tooltip.width() - 10, widget_pos.y() - 20)
            self.tooltip.show()
        else:
            self.tooltip.hide()

    def on_hover2(self, point, state):
        if state:
            if hasattr(self, 'time_data') and hasattr(self, 'controller_data') and hasattr(self, 'error_data'):
                hover_time = point.x()
                closest_index = 0
                min_distance = float('inf')
                for i, time_val in enumerate(self.time_data):
                    distance = abs(time_val - hover_time)
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
                actual_time = self.time_data[closest_index]
                actual_pwm = self.controller_data[closest_index]
                actual_error = self.error_data[closest_index]
                self.tooltip2.setText(f"Time: {actual_time:.1f} ms\nPWM: {actual_pwm:.1f}\nError: {actual_error:.1f} RPM")
            else:
                self.tooltip2.setText(f"Time: {point.x():.1f} ms\nPWM: {point.y():.1f}")
            self.tooltip2.adjustSize()
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView2.mapFromGlobal(cursor_pos)
            self.tooltip2.move(widget_pos.x() - self.tooltip2.width() - 10, widget_pos.y() - 20)
            self.tooltip2.show()
        else:
            self.tooltip2.hide()

    def startClicked(self):
        try:
            targetRPM = float(self.targetRPM.text())
            k1 = float(self.k1.text())
            k2 = float(self.k2.text())
            k3 = float(self.k3.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for Target RPM, K1, K2, and K3.")
            return

        if self._10ms.isChecked():
            self.sampling_rate = 10
        elif self._50ms.isChecked():
            self.sampling_rate = 50
        elif self._100ms.isChecked():
            self.sampling_rate = 100
        elif self._500ms.isChecked():
            self.sampling_rate = 500
        elif self._1000ms.isChecked():
            self.sampling_rate = 1000
        else:
            self.sampling_rate = None

        if not self.sampling_rate:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please select a sampling rate.")
            return
        if targetRPM <= 0:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Target RPM must be positive.")
            return

        max_rpm_text = self.main_window.maxRPM.text()
        try:
            max_rpm = float(max_rpm_text)
        except ValueError:
            max_rpm = float('inf')

        if targetRPM > max_rpm:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", f"Target RPM cannot exceed maximum RPM ({max_rpm_text}).")
            return

        self.runSimulation(targetRPM, self.sampling_rate, k1, k2, k3)

    def runSimulation(self, targetRPM, sampling_rate, k1, k2, k3):
        ms = self.main_window.motor_state
        K_v = ms['K']
        tau1 = ms['tau1']
        tau2 = ms['tau2']
        L = ms['L']
        voltage_max = ms['voltage']
        pwm_max = 255.0

        Ts = sampling_rate / 1000.0
        duration = 10.0
        n_samples = int(duration / Ts)

        a1 = math.exp(-Ts / tau1)
        b1 = K_v * (1 - a1)
        a2 = math.exp(-Ts / tau2)
        b2 = 1 - a2

        delay_samples = max(1, round(L / Ts))
        y_buffer = deque([0.0] * delay_samples, maxlen=delay_samples)

        v = 0.0
        y = 0.0
        e_prev1 = 0.0
        e_prev2 = 0.0
        pwm_prev = 0.0

        steady_state = K_v * voltage_max
        noise_std = 0.005 * steady_state

        self.time_data = []
        self.rpm_data = []
        self.target_data = []
        self.controller_data = []
        self.error_data = []

        self._targetRPM_value = targetRPM

        for k in range(n_samples):
            y_delayed = y_buffer[0]

            # Velocity form PID: u[k] = u[k-1] + K1*e[k] + K2*e[k-1] + K3*e[k-2]
            e = targetRPM - y_delayed
            pwm = pwm_prev + k1 * e + k2 * e_prev1 + k3 * e_prev2
            pwm = max(0, min(pwm_max, pwm))

            voltage = pwm * voltage_max / pwm_max

            v_new = a1 * v + b1 * voltage
            y_new = a2 * y + b2 * v_new
            y_new = max(y_new, 0)

            y_buffer.append(y_new)

            y_noisy = y_new + np.random.normal(0, noise_std)
            y_noisy = max(y_noisy, 0)

            self.time_data.append(int(round(k * Ts * 1000)))
            self.rpm_data.append(float(y_noisy))
            self.target_data.append(targetRPM)
            self.controller_data.append(float(pwm))
            self.error_data.append(float(targetRPM - y_noisy))

            v = v_new
            y = y_new
            e_prev2 = e_prev1
            e_prev1 = e
            pwm_prev = pwm

        self.speedSeries.clear()
        self.targetSeries.clear()
        self.controllerSeries.clear()
        self.errorSeries.clear()

        self._clc_anim_index = 0
        self._clc_anim_max_y = max(max(self.rpm_data), targetRPM) * 1.15
        self._clc_anim_max_y2 = max(max(self.controller_data), max(abs(e) for e in self.error_data)) * 1.15
        self._clc_anim_min_y2 = min(self.error_data) * 1.15 if min(self.error_data) < 0 else 0
        self.chart.axisX().setRange(0, max(self.time_data) + 100)
        self.chart.axisY().setRange(0, self._clc_anim_max_y)
        self.chart2.axisX().setRange(0, max(self.time_data) + 100)
        self.chart2.axisY().setRange(min(self._clc_anim_min_y2, 0), self._clc_anim_max_y2)

        if hasattr(self, '_clcAnimTimer') and self._clcAnimTimer is not None:
            self._clcAnimTimer.stop()
        self._clcAnimTimer = QtCore.QTimer(self)
        self._clcAnimTimer.timeout.connect(self._clcAnimStep)
        self._clcAnimTimer.start(10)

    def _clcAnimStep(self):
        steps_per_tick = 5
        for _ in range(steps_per_tick):
            if self._clc_anim_index >= len(self.time_data):
                self._clcAnimTimer.stop()
                self.main_window.clc_data = {
                    'time_data': self.time_data,
                    'rpm_data': self.rpm_data,
                    'target_data': self.target_data,
                    'controller_data': self.controller_data,
                    'error_data': self.error_data,
                }
                return
            i = self._clc_anim_index
            self.speedSeries.append(self.time_data[i], self.rpm_data[i])
            self.targetSeries.append(self.time_data[i], self.target_data[i])
            self.controllerSeries.append(self.time_data[i], self.controller_data[i])
            self.errorSeries.append(self.time_data[i], self.error_data[i])
            self._clc_anim_index += 1

    def popupClicked(self):
        if hasattr(self, 'time_data') and hasattr(self, 'rpm_data') and hasattr(self, 'target_data') and self.time_data and self.rpm_data and self.target_data:
            fig = plt.figure(figsize=(15, 6))
            gs = fig.add_gridspec(1, 2, width_ratios=[2.5, 1])

            ax1 = fig.add_subplot(gs[0])
            ax2 = fig.add_subplot(gs[1])
            ax2.axis('off')

            ax1.plot(self.time_data, self.rpm_data, '-', color='blue', linewidth=2, label='Actual Speed')
            ax1.plot(self.time_data, self.target_data, 'r--', linewidth=2, label='Target Speed')

            final_value = self.rpm_data[-1] if self.rpm_data else 0
            final_speed = final_value
            max_speed = max(self.rpm_data) if self.rpm_data else 0

            if final_value > 0:
                ax1.axhline(y=final_value, color='gray', linestyle=':', alpha=0.7)
                ax1.axhline(y=max_speed, color='orange', linestyle=':', alpha=0.5)
                ax1.text(max(self.time_data) * 0.1, final_value + final_value * 0.05,
                         f"Final: {final_value:.1f} RPM", fontsize=9,
                         bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))
                if max_speed != final_value:
                    ax1.text(max(self.time_data) * 0.1, max_speed + max_speed * 0.05,
                             f"Peak: {max_speed:.1f} RPM", fontsize=9,
                             bbox=dict(boxstyle="round,pad=0.3", facecolor="orange", alpha=0.8))

            ax1.grid(True, alpha=0.3)
            ax1.set_title("Closed Loop Speed Response", fontsize=14, fontweight='bold')
            ax1.set_xlabel("Time (ms)", fontsize=12)
            ax1.set_ylabel("Speed (RPM)", fontsize=12)
            ax1.legend()

            ax2.axis('off')

            rise_time_text = self.Tr.text().replace(" ms", "") if hasattr(self, 'Tr') and self.Tr.text() != "--" else "N/A"
            peak_time_text = self.Tp.text().replace(" ms", "") if hasattr(self, 'Tp') and self.Tp.text() != "--" else "N/A"
            settling_time_text = self.Ts.text().replace(" ms", "") if hasattr(self, 'Ts') and self.Ts.text() != "--" else "N/A"
            overshoot_text = self.os.text().replace(" %", "") if hasattr(self, 'os') and self.os.text() != "--" else "N/A"

            k1 = float(self.k1.text()) if self.k1.text() else 0
            k2 = float(self.k2.text()) if self.k2.text() else 0
            k3 = float(self.k3.text()) if self.k3.text() else 0
            target_rpm = float(self.targetRPM.text()) if self.targetRPM.text() else 0

            controller_type = "PID" if k3 != 0 else ("PI" if k2 != 0 else "P")

            analysis_text = (
                f"{'Target RPM'.ljust(20)}{str(target_rpm).rjust(15)}\n"
                f"{'Final Speed'.ljust(20)}{f'{final_speed:.1f}'.rjust(15)}\n"
                f"{'Rise Time (Tr)'.ljust(20)}{str(rise_time_text).rjust(15)} ms\n"
                f"{'Peak Time (Tp)'.ljust(20)}{str(peak_time_text).rjust(15)} ms\n"
                f"{'Settling Time (Ts)'.ljust(20)}{str(settling_time_text).rjust(15)} ms\n"
                f"{'Overshoot'.ljust(20)}{str(overshoot_text).rjust(15)} %\n"
                f"\n"
                f"{'CONTROLLER PARAMETERS'.ljust(35)}\n"
                f"{'Type'.ljust(20)}{str(controller_type).rjust(15)}\n"
                f"{'K1'.ljust(20)}{f'{k1:.3f}'.rjust(15)}\n"
                f"{'K2'.ljust(20)}{f'{k2:.3f}'.rjust(15)}\n"
                f"{'K3'.ljust(20)}{f'{k3:.3f}'.rjust(15)}\n"
                f"{'Sampling Rate'.ljust(20)}{f'{self.sampling_rate}'.rjust(15)} ms\n"
                f"\n"
            )

            ax2.text(
                x=0.1, y=0.1,
                s=analysis_text,
                fontsize=10, color="black", ha='left', family='monospace',
                transform=ax2.transAxes, verticalalignment='bottom'
            )

            plt.tight_layout()
            plt.show()
        else:
            QtWidgets.QMessageBox.information(self, "No Data", "No closed loop response data available to display.")

    def popup2Clicked(self):
        if hasattr(self, 'time_data') and hasattr(self, 'controller_data') and self.time_data and self.controller_data:
            plt.figure(figsize=(10, 6))
            plt.plot(self.time_data, self.controller_data, 'o-', color='green', linewidth=2, label='Controller Output (PWM)')
            plt.plot(self.time_data, self.error_data, '--', color='red', label='Error (RPM)')
            plt.grid(True)
            plt.xlabel('Time (ms)')
            plt.ylabel('Controller Output (PWM)')
            plt.title('Controller Output Over Time')
            plt.tight_layout()
            plt.legend()
            plt.show()
        else:
            QtWidgets.QMessageBox.information(self, "Log", "No data available to plot.")

    def analyzeClicked(self):
        if not hasattr(self, 'time_data') or not hasattr(self, 'rpm_data') or not self.time_data or not self.rpm_data:
            return

        target = self.target_data[0] if self.target_data else 0

        last_10pct = max(1, len(self.rpm_data) // 10)
        fv = sum(self.rpm_data[-last_10pct:]) / len(self.rpm_data[-last_10pct:])

        for i, target in enumerate(self.target_data):
            if target != 0:
                start_time = self.time_data[i]
                break
        else:
            start_time = 0

        overshoot = max(self.rpm_data) - fv if self.rpm_data else 0

        overshoot_time = None
        for i, speed in enumerate(self.rpm_data):
            if speed == max(self.rpm_data):
                overshoot_time = self.time_data[i] - start_time
                break

        threshold_10 = 0.1 * fv
        threshold_90 = 0.9 * fv

        rise_start = None
        rise_end = None

        for i, speed in enumerate(self.rpm_data):
            if rise_start is None and speed >= threshold_10:
                rise_start = self.time_data[i]
            if rise_start is not None and speed >= threshold_90:
                rise_end = self.time_data[i]
                break

        rise_time = (rise_end - rise_start) if rise_start and rise_end else 0

        settling_time = 0
        if rise_end:
            upper_bound = fv * 1.05
            lower_bound = fv * 0.95
            for i in range(len(self.rpm_data) - 1, -1, -1):
                if not (lower_bound <= self.rpm_data[i] <= upper_bound):
                    settling_time = self.time_data[i + 1] - start_time if (i + 1) < len(self.time_data) else 0
                    break

        self.Tr.setText(f"{rise_time} ms" if rise_time else "--")
        self.Tp.setText(f"{overshoot_time} ms" if overshoot_time else "--")
        self.Ts.setText(f"{settling_time} ms" if settling_time else "--")
        self.os.setText(f"{overshoot / fv * 100:.2f} %" if overshoot and fv else "--")

    def saveDataToCSV(self):
        required_data = ['time_data', 'rpm_data', 'target_data', 'error_data', 'controller_data']
        missing_data = []

        for data_name in required_data:
            if not hasattr(self, data_name) or not getattr(self, data_name):
                missing_data.append(data_name)

        if missing_data:
            QtWidgets.QMessageBox.information(
                self, "Incomplete Data",
                f"Cannot save data. Missing or empty data series:\n" +
                "\n".join([f"  {data.replace('_', ' ').title()}" for data in missing_data]) +
                "\n\nPlease run a complete closed-loop test first to collect all data."
            )
            return

        data_lengths = {
            'Time': len(self.time_data),
            'Speed': len(self.rpm_data),
            'Target': len(self.target_data),
            'Error': len(self.error_data),
            'Controller': len(self.controller_data)
        }

        if len(set(data_lengths.values())) > 1:
            QtWidgets.QMessageBox.warning(
                self, "Data Length Mismatch",
                f"Data series have different lengths:\n" +
                "\n".join([f"  {name}: {length} points" for name, length in data_lengths.items()])
            )
            return

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save CLC Data",
            f"clc_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            data_dict = {
                'Time_ms': self.time_data,
                'Target_Speed_RPM': self.target_data,
                'Actual_Speed_RPM': self.rpm_data,
                'Error_RPM': self.error_data,
                'Controller_Output_PWM': self.controller_data
            }

            df = pd.DataFrame(data_dict)

            k1 = float(self.k1.text()) if self.k1.text() else 0
            k2 = float(self.k2.text()) if self.k2.text() else 0
            k3 = float(self.k3.text()) if self.k3.text() else 0
            controller_type = "PID" if k3 != 0 else ("PI" if k2 != 0 else "P")

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write(f"# CLC Data Export\n")
                f.write(f"# Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Target RPM: {self.target_data[-1] if self.target_data else 'N/A'}\n")
                f.write(f"# Final Speed: {self.rpm_data[-1]:.2f} RPM\n")
                f.write(f"# Data Points: {len(self.time_data)}\n")
                f.write(f"# Duration: {max(self.time_data) - min(self.time_data):.0f} ms\n")
                f.write(f"# Sampling Rate: {self.sampling_rate} ms\n")
                f.write(f"\n")
                f.write(f"# Controller Parameters:\n")
                f.write(f"#   Type: {controller_type}\n")
                f.write(f"#   K1: {k1:.3f}\n")
                f.write(f"#   K2: {k2:.3f}\n")
                f.write(f"#   K3: {k3:.3f}\n")
                f.write("#\n")
                df.to_csv(f, index=False)

            overshoot = max(self.rpm_data) - self.rpm_data[-1] if self.rpm_data else 0

            QtWidgets.QMessageBox.information(
                self, "Save Successful",
                f"Data saved successfully to:\n{file_path}\n\n"
                f"Summary:\n"
                f"  Records saved: {len(self.time_data)}\n"
                f"  Controller: {controller_type} (K1={k1:.2f}, K2={k2:.2f}, K3={k3:.2f})\n"
                f"  Target RPM: {self.target_data[-1]:.1f}\n"
                f"  Final Speed: {self.rpm_data[-1]:.1f} RPM\n"
                f"  Peak Overshoot: {overshoot:.1f} RPM\n"
                f"  Test Duration: {max(self.time_data) - min(self.time_data):.0f} ms"
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Save Error",
                f"Error saving data to CSV:\n{str(e)}"
            )

    def closeEvent(self, event):
        event.accept()


def _generate_plot_bytes(time_data, series_list, labels, colors, title, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(10, 6))
    for data, label, color in zip(series_list, labels, colors):
        ax.plot(time_data, data, color=color, linewidth=2, label=label)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


class sa(QtWidgets.QMainWindow, Ui_sa):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.setupUi(self)
        self.setWindowTitle("Submit Answers")
        self.setWindowIcon(QtGui.QIcon("../../public/Logo Merah.png"))

        self.main_window = main_window
        self.submit.clicked.connect(self.submitClicked)

    def submitClicked(self):
        try:
            submit_K_fopdt = float(self.K_fopdt.text())
            submit_tau_fopdt = float(self.tau_fopdt.text())
            submit_L_fopdt = float(self.L_fopdt.text())
            submit_K1 = float(self.K1.text())
            submit_K2 = float(self.K2.text())
            submit_K3 = float(self.K3.text())

            print(f"Submitted: K={submit_K_fopdt}, tau={submit_tau_fopdt}, L={submit_L_fopdt}, K1={submit_K1}, K2={submit_K2}, K3={submit_K3}")
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for all fields.")
            return
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"An error occurred: {e}")
            return

        ms = self.main_window.motor_state

        nama = getattr(self.main_window, 'nama', '')
        npm = getattr(self.main_window, 'npm', '')
        kelompok = getattr(self.main_window, 'kelompok', '')

        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
            <h2 style="color: #e20000;">DC Motor Modeling and Control - Lab Report</h2>
            <hr style="border: 1px solid #e20000;">
            <h3>Student Information</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>Name</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{nama}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>NPM</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{npm}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>Group</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{kelompok}</td></tr>
            </table>
            <h3>Motor Parameters (State {list(MOTOR_STATES.keys())[list(MOTOR_STATES.values()).index(ms)] if ms in MOTOR_STATES.values() else '?'})</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>Max RPM</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{ms['max_rpm']}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>PPR</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{ms['ppr']}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>Linear Range</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{ms['minLinRPM']} - {ms['maxLinRPM']} RPM</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>Input Voltage</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{ms['voltage']} V</td></tr>
            </table>
            <h3>Student Answers - FOPDT Parameters</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>K (RPM/V)</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{submit_K_fopdt:.4f}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>tau (seconds)</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{submit_tau_fopdt:.4f}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>L (seconds)</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{submit_L_fopdt:.4f}</td></tr>
            </table>
            <h3>Student Answers - Controller Parameters</h3>
            <table style="border-collapse: collapse; width: 100%;">
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>K1</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{submit_K1:.4f}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>K2</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{submit_K2:.4f}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>K3</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{submit_K3:.4f}</td></tr>
                <tr><td style="padding: 5px; border: 1px solid #ddd;"><strong>Type</strong></td><td style="padding: 5px; border: 1px solid #ddd;">{'PID' if submit_K3 != 0 else ('PI' if submit_K2 != 0 else 'P')}</td></tr>
            </table>
            <p><em>Control Laboratory 2026 - Departemen Teknik Elektro Universitas Indonesia</em></p>
        </div>
        """

        text_body = (
            f"DC Motor Modeling and Control - Lab Report\n"
            f"Name: {nama}\nNPM: {npm}\nGroup: {kelompok}\n\n"
            f"FOPDT: K={submit_K_fopdt}, tau={submit_tau_fopdt}, L={submit_L_fopdt}\n"
            f"Controller: K1={submit_K1}, K2={submit_K2}, K3={submit_K3}\n"
        )

        attachments = []

        olc_data = getattr(self.main_window, 'olc_data', None)
        if olc_data:
            try:
                olc_plot = _generate_plot_bytes(
                    olc_data['time_data'],
                    [olc_data['rpm_data'], olc_data['target_data']],
                    ['Actual Speed (RPM)', 'Target (RPM)'],
                    ['blue', 'red'],
                    'OLC - Motor Step Response',
                    'Time (ms)', 'Speed (RPM)'
                )
                attachments.append({"filename": "olc_response.png", "content": olc_plot})

                if 'fopdt_output' in olc_data and olc_data.get('fopdt_output'):
                    pass

                olc_csv_data = io.StringIO()
                olc_csv_data.write(f"# OLC Data Export\n")
                olc_csv_data.write(f"# Target RPM: {olc_data['target_data'][-1] if olc_data['target_data'] else 'N/A'}\n")
                olc_csv_data.write(f"# Final Speed: {olc_data['rpm_data'][-1]:.2f} RPM\n")
                df_olc = pd.DataFrame({
                    'Time_ms': olc_data['time_data'],
                    'Target_RPM': olc_data['target_data'],
                    'Actual_RPM': olc_data['rpm_data'],
                    'Error_RPM': olc_data['error_data'],
                    'PWM': olc_data['controller_data'],
                })
                olc_csv_data.write(df_olc.to_csv(index=False))
                olc_csv_bytes = olc_csv_data.getvalue().encode('utf-8')
                attachments.append({"filename": "olc_data.csv", "content": olc_csv_bytes})
            except Exception as e:
                print(f"Error attaching OLC data: {e}")

        clc_data = getattr(self.main_window, 'clc_data', None)
        if clc_data:
            try:
                clc_plot = _generate_plot_bytes(
                    clc_data['time_data'],
                    [clc_data['rpm_data'], clc_data['target_data']],
                    ['Actual Speed (RPM)', 'Target (RPM)'],
                    ['blue', 'red'],
                    'CLC - Closed Loop Response',
                    'Time (ms)', 'Speed (RPM)'
                )
                attachments.append({"filename": "clc_response.png", "content": clc_plot})

                clc_ctrl_plot = _generate_plot_bytes(
                    clc_data['time_data'],
                    [clc_data['controller_data'], clc_data['error_data']],
                    ['Controller Output (PWM)', 'Error (RPM)'],
                    ['green', 'red'],
                    'CLC - Controller Output',
                    'Time (ms)', 'Value'
                )
                attachments.append({"filename": "clc_controller.png", "content": clc_ctrl_plot})

                clc_csv_data = io.StringIO()
                clc_csv_data.write(f"# CLC Data Export\n")
                clc_csv_data.write(f"# Target RPM: {clc_data['target_data'][-1] if clc_data['target_data'] else 'N/A'}\n")
                df_clc = pd.DataFrame({
                    'Time_ms': clc_data['time_data'],
                    'Target_RPM': clc_data['target_data'],
                    'Actual_RPM': clc_data['rpm_data'],
                    'Error_RPM': clc_data['error_data'],
                    'PWM': clc_data['controller_data'],
                })
                clc_csv_data.write(df_clc.to_csv(index=False))
                clc_csv_bytes = clc_csv_data.getvalue().encode('utf-8')
                attachments.append({"filename": "clc_data.csv", "content": clc_csv_bytes})
            except Exception as e:
                print(f"Error attaching CLC data: {e}")

        if attachments:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for att in attachments:
                    zf.writestr(att['filename'], att['content'])
            zip_bytes = zip_buffer.getvalue()

            email_attachments = [{"filename": "DC_Motor_Lab_Report.zip", "content": zip_bytes}]
        else:
            email_attachments = []

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)

        success, message = sendWithEmail(
            subject=f"Lab Report: DC Motor Modeling and Control - {nama} ({npm})",
            html_body=html_body,
            text_body=text_body,
            attachments=email_attachments
        )

        QtWidgets.QApplication.restoreOverrideCursor()

        if success:
            QtWidgets.QMessageBox.information(self, "Email Sent", message)
        else:
            QtWidgets.QMessageBox.critical(self, "Sending Failed", f"Could not send email.\nError: {message}")


def exec_DMMCD(nama, npm, kelompok):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow(kelompok, nama, npm)
    window.show()
    return window