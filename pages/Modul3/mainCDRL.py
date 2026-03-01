# ==============================================
#        ROOT LOCUS CONTROLLER DESIGN
#              Version 2.0.0
#             October 3rd,2025  
# ----------------------------------------------
#   Attafahqi Amirtha Dariswan - Elektro 2022
# ==============================================

import os
import sys
import json
import hashlib
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QPushButton, QGraphicsDropShadowEffect, QWidget
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon
import sympy as sp
from sympy import symbols, expand
import numpy as np
import matplotlib
matplotlib.use("Qt5Agg") 
import matplotlib.pyplot as plt
import control as ctrl
import math
import pandas as pd


import pages.Modul3.Asset.Resource # noqa

from pages.Modul3.ui.ui_MainNoHD import Ui_MainWindow as Ui_MainNoHD
from pages.Modul3.ui.ui_PIDparam import Ui_MainWindow as Ui_PIDparam
from pages.Modul3.ui.ui_ReferencePoint import Ui_MainWindow as Ui_ReferencePoint
from pages.Modul3.ui.ui_TransferFunction import Ui_MainWindow as Ui_TransferFunction

s = symbols('s')

ADMIN_NPM = "2206817396"
TOTAL_STUDENT = 149

class HoverButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_size = None 
        self.default_pos = None  
        self.shadow_effect = None  

    def enterEvent(self, event):
        if self.default_size is None:
            self.default_size = self.size()  
            self.default_pos = self.pos()  
            self.hover_size = QSize(int(self.default_size.width() * 1.05), 
                                    int(self.default_size.height() * 1.05))  

        shift_x = (self.hover_size.width() - self.default_size.width()) // 2
        shift_y = (self.hover_size.height() - self.default_size.height()) // 2
        self.move(self.default_pos.x() - shift_x, self.default_pos.y() - shift_y)

        self.setFixedSize(self.hover_size)  
        self.setCursor(QCursor(Qt.PointingHandCursor))  

        if self.shadow_effect is None:
            self.shadow_effect = QGraphicsDropShadowEffect(self)
            self.shadow_effect.setBlurRadius(20)  
            self.shadow_effect.setXOffset(5)  
            self.shadow_effect.setYOffset(5)  
            self.shadow_effect.setColor(QColor(0, 0, 0, 100)) 
            self.setGraphicsEffect(self.shadow_effect)

        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.default_size and self.default_pos:
            self.setFixedSize(self.default_size)  
            self.move(self.default_pos)  
        self.setCursor(QCursor(Qt.ArrowCursor))  

        if self.shadow_effect:
            self.setGraphicsEffect(None)
            self.shadow_effect = None 

        super().leaveEvent(event)


class Leaderboard(QMainWindow):
    def __init__(self):
        super(Leaderboard, self).__init__()
        screen = QApplication.primaryScreen()
        screen_rect = screen.geometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()
        ui_file = ("ui/Leaderboard.ui" if screen_width >= 1920 and screen_height >= 1080 else "ui/LeaderboardNoHD.ui")
        uic.loadUi(ui_file, self)
        self.setWindowTitle("Root Locus Controller Design")
        self.setWindowIcon(QIcon("Asset/Logo Control.png"))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.last_data_snapshot = None
        # buat direktori Hasil jika belum ada
        if not os.path.exists("Hasil"):
            os.makedirs("Hasil")
        self.auto_grade("Hasil/graded_results.csv")
        self.start_auto_update(output_csv="Hasil/graded_results.csv")
        self.show()

    def start_auto_update(self, output_csv):
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.check_and_update(output_csv))
        self.timer.start(5000)  # Cek setiap 5 detik

    def fetch_firestore_data(self):
        """
        Ambil semua dokumen di collection modul4 dan kembalikan dict {docid: docdict}
        """
        try:
            docs = db.collection("Modul4").stream()
        except Exception as e:
            print("Error fetching Firestore data:", e)
            return {}
        data = {}
        for doc in docs:
            try:
                data[doc.id] = doc.to_dict()
            except Exception:
                data[doc.id] = {}
        return data

    def check_and_update(self, output_csv):
        new_data = self.fetch_firestore_data()
        if self.data_changed(new_data):
            self.last_data_snapshot = new_data
            self.auto_grade(output_csv)

    def data_changed(self, new_data):
        if self.last_data_snapshot is None:
            return True
        old_hash = hashlib.md5(json.dumps(self.last_data_snapshot, sort_keys=True).encode()).hexdigest()
        new_hash = hashlib.md5(json.dumps(new_data, sort_keys=True).encode()).hexdigest()
        return old_hash != new_hash

    def auto_grade(self, output_csv):
        data = self.fetch_firestore_data()
        if not data:
            # kalau kosong, set tampilan default (kosong)
            print("No data in  Modul collection yet.")
            return

        extracted_data = []
        for id_number, details in data.items():
            if isinstance(details, dict) and ("avg_error" in details or "Avg error" in details):
                # support both field name variants just in case
                avg = details.get("avg_error", details.get("Avg error"))
                extracted_data.append({"NPM": id_number, "Avg error": avg, "Nama": details.get("nama", details.get("Nama", ""))})

        if not extracted_data:
            print("No valid 'avg_error' fields in modul4 documents.")
            return

        df = pd.DataFrame(extracted_data)
        df["Avg error"] = pd.to_numeric(df["Avg error"], errors='coerce')
        df = df.dropna()
        if df.empty:
            print("All avg_error entries invalid.")
            return

        # --- GRADING ---
        min_error = df["Avg error"].min()
        max_error = df["Avg error"].max()
        if min_error == max_error:
            df["Grade"] = 100
        else:
            df["Grade"] = 60 + (40 * np.exp(-2 * (df["Avg error"] - min_error) / (max_error - min_error)))
        df["Grade"] = df["Grade"].round(2)
        df[["NPM", "Grade"]].to_csv(output_csv, index=False)

        # --- COUNT submitted / not submitted ---
        submitted = len(df)
        not_submitted = max(TOTAL_STUDENT - submitted, 0)

        # --- DONUT CHART (Submitted vs Not Submitted dari TOTAL_STUDENT tetap) ---
        percent = (submitted / TOTAL_STUDENT) * 100 if TOTAL_STUDENT > 0 else 0
        sizes = [submitted, not_submitted]
        colors = ['white', (0, 0, 0, 0.2)]

        fig, ax = plt.subplots(figsize=(6, 6), facecolor='none')
        wedges, _ = ax.pie(
            sizes,
            labels=None,
            startangle=90,
            counterclock=False,
            colors=colors,
            wedgeprops=dict(width=0.3, edgecolor='white')
        )

        ax.text(0, 0, f"{percent:.1f}%",
                color='white',
                fontsize=50,
                fontweight='bold',
                ha='center',
                va='center')
        ax.set_facecolor('none')
        plt.setp(wedges, linewidth=0)
        plt.tight_layout()
        # plt.savefig("Hasil/submission_donut.png", transparent=True)

        # update UI elements (as in original)
        try:
            self.Donut.setStyleSheet(f"border-image: url(Hasil/submission_donut.png);")
            self.Donut.repaint()
        except Exception:
            # jika widget tidak ada, abaikan
            pass

        # --- TOP 10 ---
        top10 = df.sort_values("Grade", ascending=False).head(10).reset_index(drop=True)
        colors = ['gold', 'silver', '#cd7f32'] + ['white'] * 7
        scales = [1.3, 1.2, 1.1] + [1.0] * 7
        top10 = top10[::-1].reset_index(drop=True)
        colors = colors[::-1]
        scales = scales[::-1]

class MainWindow(QMainWindow, Ui_MainNoHD):
    def __init__(self, Nama, NPM):
        super(MainWindow, self).__init__()

        self.setupUi(self)
        self.setWindowTitle("Practicum Software : Virtual PID")
        self.setWindowIcon(QIcon("../../public/Logo Merah.png"))
        self.Nama = Nama
        self.NPM = NPM
        
        self.replace_buttons()

        self.Kp = 1
        self.Ki = 0
        self.Kd = 0

        self.SP = 1
        self.ST = 1

        last_five = str(self.NPM)[-5:]

        
        # Replace '0' with '1' and convert back to integers
        A, B, C, D, E = map(lambda x: int(x) if x != '0' else 1, last_five)

        self.num = C 
        den = (s + D) * (s + E)

        self.den = expand(den)

        self.num_coeff = [1]
        den_exp = self.den.as_poly(s).all_coeffs()
        self.den_coeff = [float(c) for c in den_exp]  

        self.t_cont = None
        self.setpoint = None
        self.tz = None
        self.setpoint_z = None
        self.y_out_cont = None
        self.y_out_z = None
        self.error_signal_cont = None

        self.os = A + 10

        self.TS = (B + E) * 0.1

        self.TimeS.setText(str(self.TS))
        self.Overshoot.setText(str(self.os) + "%" )

        self.show()

    def trueValue(self):
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Are you sure you want to submit this parameter?\nKp: {self.Kp}, Ki: {self.Ki}, Kd: {self.Kd}",
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Yes  # Default button
        )

        if reply != QMessageBox.Yes:
            return
        
        s = sp.Symbol('s')

        numerator_expanded = sp.expand(self.num)
        denominator_expanded = sp.expand(self.den)

        poles = sp.solve(self.den, s)

        Mp_fraction = self.os / 100 
        zeta = -np.log(Mp_fraction) / np.sqrt(np.pi**2 + (np.log(Mp_fraction))**2)
        omega_n = 4 / (self.TS * zeta)

        real = -zeta * omega_n
        imaginary = omega_n * np.sqrt(1 - zeta**2)
        pole_1 = complex(real, imaginary)

        def calculate_angle(pole, point):
            angle = 180 - np.angle(point - pole, deg=True)
            return angle

        def find_zero_using_angle_criterion(poles, dominant_pole):
            total_angle_from_poles = 0
            for pole in poles:
                angle = calculate_angle(pole, dominant_pole)
                total_angle_from_poles += angle

            required_angle_for_zero = -180 + total_angle_from_poles

            denominator = dominant_pole.real  
            numerator = dominant_pole.imag    
            angle_radians = math.radians(required_angle_for_zero)
            tan_value = math.tan(angle_radians)
            
            # hindari pembagian nol
            if tan_value == 0:
                tan_value = 1e-9

            value = numerator / tan_value
            zero = denominator + value
            return zero

        poles_complex = [complex(pole, 0) for pole in poles]

        zero = abs(find_zero_using_angle_criterion(poles_complex, pole_1))

        def calculate_KD(zero, numerator_expanded, denominator_expanded, pole):
            Gcd_s = pole + zero
            
            numerator_value = numerator_expanded.subs(s, pole)
            denominator_value = denominator_expanded.subs(s, pole)
            
            G_s = numerator_value / denominator_value if denominator_value != 0 else float('inf')

            product = Gcd_s * G_s
            absolute_value = abs(product.evalf()) 
            
            KD = 1 / absolute_value if absolute_value != 0 else float('inf')  # Handle pembagi nol

            return KD

        KD_value = calculate_KD(zero, numerator_expanded, denominator_expanded, pole_1)

        def calculate_KI(zero, numerator_expanded, denominator_expanded, pole):
            Gci_s = (pole + 0.5)/pole
            Gpd_s = KD_value * (pole + zero)

            numerator_value = numerator_expanded.subs(s, pole)
            denominator_value = denominator_expanded.subs(s, pole)
            
            G_s = numerator_value / denominator_value if denominator_value != 0 else float('inf')

            product = Gci_s * Gpd_s * G_s

            absolute_value = abs(product.evalf()) 
            
            KI = 1 / absolute_value if absolute_value != 0 else float('inf')  # Handle pembagi nol
        

            return KI

        KI_value = calculate_KI(zero, numerator_expanded, denominator_expanded, pole_1)

        expression = (s + 0.5) * (s + zero)
        expanded = sp.expand(expression)
        
        x = abs(expanded.coeff(s, 1))  
        y = abs(expanded.coeff(s, 0))  

        Kd_true = KI_value * KD_value
        Ki_true = KI_value * KD_value * y
        Kp_true = KI_value * KD_value * x

        error_Kp = abs(Kp_true - self.Kp)
        error_Ki = abs(Ki_true - self.Ki)
        error_Kd = abs(Kd_true - self.Kd)

        error = (error_Kp + error_Ki + error_Kd) / 3

        try:
            # TODO: FIX DATABASE
            # doc_ref = db.collection("Modul4").document(str(self.NPM))
            # doc_ref.set({
            #     "error_kp": float(error_Kp),
            #     "error_ki": float(error_Ki),
            #     "error_kd": float(error_Kd),
            #     "avg_error": float(error),
            #     "nama": str(self.Nama),
            # })
            pass
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save to Firestore: {e}")
            return

        QApplication.quit()


    def controller(self):
        if hasattr(self, "controller_window") and self.controller_window.isVisible():
            self.controller_window.activateWindow() 
            
        else:
            self.controller_window = PID(self)
            self.controller_window.show()

    def reference(self):
        if hasattr(self, "reference_window") and self.reference_window.isVisible():
            self.reference_window.activateWindow() 
            
        else:
            self.reference_window = References(self)
            self.reference_window.show()
    
    def TransferFunction(self):
        if hasattr(self, "plant_window") and self.plant_window.isVisible():
            self.reference_window.activateWindow() 
            
        else:
            self.reference_window = TransferFunction(self)
            self.reference_window.show()
        
    def simulation(self):
        s = ctrl.TransferFunction.s
        Ts = 0.1  # Sampling time for Z-transform

        # Continuous PID Controller
        C = self.Kp + self.Ki / s + self.Kd * s

        # Continuous Plant G(s)
        G = ctrl.TransferFunction(self.num_coeff, self.den_coeff)

        # Closed-loop system in continuous time
        T_cont = ctrl.feedback(C * G, 1)

        # Convert G(s) to G(z) using Zero-Order Hold (ZOH)
        Gz = ctrl.sample_system(G, Ts, method='zoh')

        # Time vectors
        self.t_cont = np.linspace(0, 10, 1000)  # Continuous time
        self.tz = np.arange(0, 10, Ts)  # Discrete time

        # Define setpoint signal
        self.setpoint_cont = np.piecewise(self.t_cont, 
            [self.t_cont < self.ST, self.t_cont >= self.ST], 
            [0, self.SP]
        )
        self.setpoint_z = np.piecewise(self.tz, 
            [self.tz < self.ST, self.tz >= self.ST], 
            [0, self.SP]
        )

        # Simulate continuous-time response
        self.t_cont, self.y_out_cont = ctrl.forced_response(T_cont, T=self.t_cont, U=self.setpoint_cont)

        # Simulate hybrid response (Continuous PID, Discrete Plant)
        self.u_out = self.Kp * self.setpoint_z + self.Ki * np.cumsum(self.setpoint_z) * Ts + self.Kd * np.gradient(self.setpoint_z, Ts)  # ✅ Fixed
        self.tz, self.y_out_z = ctrl.forced_response(Gz, T=self.tz, U=self.u_out)

        # Compute error signals
        self.error_signal_cont = self.setpoint_cont - self.y_out_cont
        self.error_signal_z = self.setpoint_z - self.y_out_z

        QMessageBox.warning(self, "Simulation", "Simulation completed!")



    def outputResponse (self):
        if self.y_out_cont is None:
            QMessageBox.warning(self, "No Simulation", "Run simulation first!")
            return
        
        plt.figure(figsize=(8, 4))
        plt.plot(self.t_cont, self.setpoint_cont, 'r--', label="Setpoint")
        plt.plot(self.t_cont, self.y_out_cont, 'b', label="System Output (Continuous)")
        plt.xlabel("Time (s)")
        plt.ylabel("Output")
        plt.title("Output Response (PID(s) + Plant(s))")
        plt.legend()
        plt.grid()
        plt.show()
    
    def errorResponse (self):
        if self.error_signal_cont is None:
            QMessageBox.warning(self,"No Simulation", "Run simulation first!")
            return

        plt.figure(figsize=(8, 4))
        plt.plot(self.t_cont, self.error_signal_cont, 'g', label="Error Signal")
        plt.xlabel("Time (s)")
        plt.ylabel("Error")
        plt.title("Error Signal (PID(s) + Plant(s))")
        plt.legend()
        plt.grid()
        plt.show()

    def outputResponse_discrete(self):
        if self.y_out_z is None:
            QMessageBox.warning(self, "No Simulation", "Run simulation first!")
            return
        
        plt.figure(figsize=(8, 4))
        plt.step(self.tz, self.setpoint_z, 'r--', where='post', label="Setpoint")
        plt.step(self.tz, self.y_out_z, 'b', where='post', label="System Output (Hybrid)")
        plt.xlabel("Time (s)")
        plt.ylabel("Output")
        plt.title("Output Response (PID(s) + Plant(z))")
        plt.legend()
        plt.grid()
        plt.show()


    def replace_buttons(self):
        for button_name in ["Submit", "runSim", "Refrensi", "Controller", "Plant", "scopeOutput", "scopeController", "scopeOutput_Diskrit"]:
            button = self.findChild(QPushButton, button_name)
            if button:
                hover_button = HoverButton(button.text(), self)
                hover_button.setGeometry(button.geometry())
                hover_button.setStyleSheet(button.styleSheet())  
                hover_button.setObjectName(button.objectName())  
                
                # Reconnect signals
                if button_name == "Controller": hover_button.clicked.connect(self.controller)
                elif button_name == "runSim": hover_button.clicked.connect(self.simulation)
                elif button_name == "Refrensi": hover_button.clicked.connect(self.reference)
                elif button_name == "Plant": hover_button.clicked.connect(self.TransferFunction)
                elif button_name == "scopeOutput": hover_button.clicked.connect(self.outputResponse)
                elif button_name == "scopeController": hover_button.clicked.connect(self.errorResponse)
                elif button_name == "Submit": hover_button.clicked.connect(self.trueValue)
                elif button_name == "scopeOutput_Diskrit": hover_button.clicked.connect(self.outputResponse_discrete)

                button.deleteLater()



class PID(QMainWindow, Ui_PIDparam):
    def __init__(self, main_window):
        super(PID, self).__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon("../../public/Logo Merah.png"))
        self.setWindowTitle("PID Parameter")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.main_window = main_window

        self.LKp.setText(str(self.main_window.Kp))
        self.LKi.setText(str(self.main_window.Ki))
        self.LKd.setText(str(self.main_window.Kd))

        self.show()

        self.updatePID.clicked.connect(self.updateParam)

    def updateParam(self):
        Kp = self.LKp.text().strip()
        Ki = self.LKi.text().strip()
        Kd = self.LKd.text().strip()

        if not Kp.replace('.', '', 1).isdigit() or not Ki.replace('.', '', 1).isdigit() or not Kd.replace('.', '', 1).isdigit():
            QMessageBox.warning(self, "Update Failed", "PID parameters must be numbers!") 
            return
        
        self.main_window.Kp = float(Kp)
        self.main_window.Ki = float(Ki)
        self.main_window.Kd = float(Kd)

        self.close()


class References(QMainWindow, Ui_ReferencePoint):
    def __init__(self, main_window):
        super(References, self).__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon("../../public/Logo Merah.png"))
        self.setWindowTitle("Reference Point")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.main_window = main_window

        self.SetPoint.setText(str(self.main_window.SP))
        self.SetTime.setText(str(self.main_window.ST))

        self.show()

        self.updateSP.clicked.connect(self.updateSetPoint)

    def updateSetPoint(self):
        SP = self.SetPoint.text().strip()
        ST = self.SetTime.text().strip()

        if not SP.replace('.', '', 1).isdigit() or not ST.replace('.', '', 1).isdigit():
            QMessageBox.warning(self, "Update Failed", "Set Point must be numbers!")
            return
        
        self.main_window.SP = float(SP)
        self.main_window.ST = float(ST)

        self.close()


class TransferFunction(QMainWindow, Ui_TransferFunction):
    def __init__(self, main_window):
        super(TransferFunction, self).__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon("../../public/Logo Merah.png"))
        self.setWindowTitle("System Transfer Function")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.main_window = main_window

        self.Num.setText(str(self.main_window.num))
        self.Den.setText(str(self.main_window.den))

        self.show()


def exec_CDRL(nama, npm):
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(nama, npm)
    window.show()
    
    # do NOT call app.exec_() here when launched from the main app
    return window