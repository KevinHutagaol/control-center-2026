import sys
import os
import random
import numpy as np
import requests
import UI.resource
from PyQt5.QtWidgets import QApplication, QDialog, QWidget, QMainWindow, QMessageBox, QDesktopWidget
from PyQt5.QtGui import QIcon
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5 import uic
from problems import problem_set
from session import session
from ss_controller_plot import simulate_and_plot

FIREBASE_BASE_URL = "https://state-space-controller-design-default-rtdb.firebaseio.com/"

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and PyInstaller bundled """
    try:
        # PyInstaller creates a temp folder and stores the path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)

def center_widget(widget):
    qr = widget.frameGeometry()
    cp = QDesktopWidget().availableGeometry().center()
    qr.moveCenter(cp)
    widget.move(qr.topLeft())

def mae_percentage_accuracy(user_matrix, correct_matrix):
    diff = np.abs(user_matrix - correct_matrix)
    mae = np.mean(diff)

    # Normalize MAE by dividing with the mean of the correct values
    norm_factor = np.mean(np.abs(correct_matrix))

    # Avoid division by zero
    if norm_factor == 0:
        return 100.0 if mae == 0 else 0.0

    error_percentage = (mae / norm_factor) * 100
    accuracy_percentage = 100 - error_percentage
    return max(0.0, min(100.0, accuracy_percentage))  # Clamp between 0 and 100

def mae(user_matrix, correct_matrix):
    diff = np.abs(user_matrix - correct_matrix)
    return np.mean(diff)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi(resource_path("Modul 7/UI/Main.ui"), self)
        self.setWindowTitle("State Space Controller Design")
        self.setMinimumSize(1280, 720)
        self.setMaximumSize(1280, 720)
        npm = os.getenv('NPM')
        response = requests.get(FIREBASE_BASE_URL + f"students/{npm}.json")
        
        if response.status_code == 200:
            user_data = response.json()

            if user_data:  # Check if user exists
                print("User exists! Proceed.")
                session["npm"] = npm

                # Check if problem_set already exists
                if "problem_set" not in user_data:
                    selected_problem = random.randint(1, 10)
                    update_url = FIREBASE_BASE_URL + f"students/{npm}/problem_set.json"
                    requests.put(update_url, json=selected_problem)
                    session["problem_set"] = selected_problem
                    print(f"Assigned problem set {selected_problem}")
                else:
                    existing_problem = user_data["problem_set"]
                    session["problem_set"] = existing_problem
                    print(f"User already has problem set: {existing_problem}")

            else:
                print("User not found!")
                QMessageBox.warning(None, "Warning", "User not found!")
                self.NPM.clear()
                self.NPM.setFocus()

        else:
            print("Failed to connect to Firebase!")
            QMessageBox.critical(None, "Error", "Unable to connect to Firebase.")

        self.label_1.setText(str(problem_set[session["problem_set"]]["spec-1"]))
        self.label_2.setText(str(problem_set[session["problem_set"]]["spec-2"]))

        self.open_windows = []  # Keep a list of opened matrix windows

        self.Abtn.clicked.connect(self.open_amatrix)
        self.Bbtn.clicked.connect(self.open_bmatrix)
        self.Cbtn.clicked.connect(self.open_cmatrix)
        self.Dbtn.clicked.connect(self.open_dmatrix)
        self.Rbtn.clicked.connect(self.open_controller)
        self.Nbtn.clicked.connect(self.open_pregain)
        self.runBtn.clicked.connect(self.submit_data)
        self.scopebtn.clicked.connect(self.run_simulation)

    def open_amatrix(self):
        amatrix = AMatrix()
        amatrix.show()
        self.open_windows.append(amatrix)   # Keep reference so it's not garbage collected

    def open_bmatrix(self):
        bmatrix = BMatrix()
        bmatrix.show()
        self.open_windows.append(bmatrix)

    def open_cmatrix(self):
        cmatrix = CMatrix()
        cmatrix.show()
        self.open_windows.append(cmatrix)

    def open_dmatrix(self):
        dmatrix = DMatrix()
        dmatrix.show()
        self.open_windows.append(dmatrix)

    def open_controller(self):
        controller = Controller()
        controller.show()
        self.open_windows.append(controller)
    
    def open_pregain(self):
        pregain = PreGain()
        pregain.show()
        self.open_windows.append(pregain)

    def submit_data(self):
        R_user = session.get("R_user")
        N_user = session.get("N_user")

        if R_user is None and N_user is not None:
            QMessageBox.warning(None, "Warning", "Please set R values before running the simulation.")
            session["runSim"] = False
            return
        
        session["runSim"] = True
        QMessageBox.information(None, "Info", "Successful!")

        if R_user is not None or N_user is not None:
            if R_user is not None:
                R_mae = mae(R_user, problem_set[session["problem_set"]]["R"])
                R_acc = mae_percentage_accuracy(R_user, problem_set[session["problem_set"]]["R"])
                # Update R_user data in Firebase
                update_url = FIREBASE_BASE_URL + f"students/{session['npm']}/R_user.json"
                requests.put(update_url, json=R_user.tolist())

                # Update R_mae and R_acc
                requests.put(FIREBASE_BASE_URL + f"students/{session['npm']}/R_mae.json", json=R_mae)
                requests.put(FIREBASE_BASE_URL + f"students/{session['npm']}/R_acc.json", json=R_acc)
            if N_user is not None:
                N_mae = mae(np.array(N_user).reshape(-1, 1), problem_set[session["problem_set"]]["N"])
                N_acc = mae_percentage_accuracy(np.array(N_user).reshape(-1, 1), problem_set[session["problem_set"]]["N"])
                # Update N_user data in Firebase
                update_url = FIREBASE_BASE_URL + f"students/{session['npm']}/N_user.json"
                requests.put(update_url, json=N_user)

                # Update N_mae and N_acc
                requests.put(FIREBASE_BASE_URL + f"students/{session['npm']}/N_mae.json", json=N_mae)
                requests.put(FIREBASE_BASE_URL + f"students/{session['npm']}/N_acc.json", json=N_acc)

    def run_simulation(self):
        R_user = session.get("R_user")
        N_user = session.get("N_user")

        if session["runSim"] is True:
            simulate_and_plot(session["problem_set"], R_user, N_user)
            session["runSim"] = False
        else:
            QMessageBox.warning(None, "Warning", "Please run the simulation.")

class AMatrix(QMainWindow):
    def __init__(self):
        super(AMatrix, self).__init__()
        uic.loadUi(resource_path("Modul 7/UI/Amatrix.ui"), self)
        self.setWindowTitle("A Matrix")
        self.setFixedSize(220, 220)
        A = problem_set[session["problem_set"]]["A"]
        self.a11.setText(str(A[0][0]))
        self.a12.setText(str(A[0][1]))
        self.a13.setText(str(A[0][2]))
        self.a21.setText(str(A[1][0]))
        self.a22.setText(str(A[1][1]))
        self.a23.setText(str(A[1][2]))
        self.a31.setText(str(A[2][0]))
        self.a32.setText(str(A[2][1]))
        self.a33.setText(str(A[2][2]))

class BMatrix(QMainWindow):
    def __init__(self):
        super(BMatrix, self).__init__()
        uic.loadUi(resource_path("Modul 7/UI/Bmatrix.ui"), self)
        self.setWindowTitle("B Matrix")
        self.setFixedSize(220, 220)
        B = problem_set[session["problem_set"]]["B"]
        self.b11.setText(str(B[0][0]))
        self.b21.setText(str(B[1][0]))
        self.b31.setText(str(B[2][0]))

class CMatrix(QMainWindow):
    def __init__(self):
        super(CMatrix, self).__init__()
        uic.loadUi(resource_path("Modul 7/UI/Cmatrix.ui"), self)
        self.setWindowTitle("C Matrix")
        self.setFixedSize(220, 220)
        C = problem_set[session["problem_set"]]["C"]
        self.c11.setText(str(C[0][0]))
        self.c12.setText(str(C[0][1]))
        self.c13.setText(str(C[0][2]))

class DMatrix(QMainWindow):
    def __init__(self):
        super(DMatrix, self).__init__()
        uic.loadUi(resource_path("Modul 7/UI/Dmatrix.ui"), self)
        self.setWindowTitle("D Matrix")
        self.setFixedSize(220, 220)
        D = problem_set[session["problem_set"]]["D"]
        self.d.setText(str(D[0][0]))

class Controller(QMainWindow):
    def __init__(self):
        super(Controller, self).__init__()
        uic.loadUi(resource_path("Modul 7/UI/Controller.ui"), self)
        self.setWindowTitle("Controller")
        self.setFixedSize(548, 207)

        # Pre-fill if R_user was already saved
        if session["R_user"] is not None:
            R_user = session["R_user"]
            self.r11.setText(str(R_user[0][0]))
            self.r12.setText(str(R_user[0][1]))
            self.r13.setText(str(R_user[0][2]))

        self.updateR.clicked.connect(self.update_matrix)

    def update_matrix(self):
        r11 = self.r11.text().strip()
        r12 = self.r12.text().strip()
        r13 = self.r13.text().strip()

        if r11 == "" and r12 == "" and r13 == "":
            session["R_user"] = None
            self.close()
            return

        try:
            r11 = float(r11)
            r12 = float(r12)
            r13 = float(r13)
            R_user = np.array([[r11, r12, r13]])
            print(R_user)
            session["R_user"] = R_user
            self.close()
        except ValueError:
            QMessageBox.warning(None, "Input Error", "Please enter valid numbers.")
            self.r11.clear()
            self.r12.clear()
            self.r13.clear()


class PreGain(QMainWindow):
    def __init__(self):
        super(PreGain, self).__init__()
        uic.loadUi(resource_path("Modul 7/UI/PreGain.ui"), self)
        self.setWindowTitle("Pre Gain")
        self.setFixedSize(275, 165) 

        # Pre-fill if N_user was already saved
        if session["N_user"] is not None:
            N_user = session["N_user"]
            self.N.setText(str(N_user))

        self.updateN.clicked.connect(self.update_pregain)

    def update_pregain(self):
        text = self.N.text().strip()

        if text == "":
            # User wants to clear the pre-gain
            session["N_user"] = None
            self.close()
            return

        try:
            N_user = float(text)
            print(N_user)
            session["N_user"] = N_user
            self.close()
        except ValueError:
            QMessageBox.warning(None, "Input Error", "Please enter a valid number.")
            self.N.clear()


# main
app = QApplication(sys.argv)
main_window = MainWindow()
widget = QtWidgets.QStackedWidget()
widget.setWindowIcon(QIcon(resource_path("Asset/Logo Merah.png")))
widget.addWidget(main_window)
widget.setCurrentWidget(main_window)
widget.resize(main_window.minimumSize())
widget.show()
center_widget(widget)

try:
    sys.exit(app.exec_())
except:
    print("Exiting")


# Push data to Firebase
#db.push(data)
