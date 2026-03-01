import sys
import numpy as np
from PyQt5.QtWidgets import QApplication,  QMainWindow, QMessageBox, QDesktopWidget, QLineEdit
from PyQt5.QtGui import QIcon, QDoubleValidator
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot

from pages.Modul7.session import moduleCOD_session
from pages.Modul7.ss_controller_plot import simulate_and_plot
import pages.Modul7.UI.resource # noqa

from pages.Modul7.UI.ui_Main import Ui_MainWindow as Ui_Main
from pages.Modul7.UI.ui_Amatrix import Ui_MainWindow as Ui_AMatrix
from pages.Modul7.UI.ui_Bmatrix import Ui_MainWindow as Ui_BMatrix
from pages.Modul7.UI.ui_Cmatrix import Ui_MainWindow as Ui_CMatrix
from pages.Modul7.UI.ui_Dmatrix import Ui_MainWindow as Ui_DMatrix
from pages.Modul7.UI.ui_Controller import Ui_MainWindow as Ui_Controller
from pages.Modul7.UI.ui_PreGain import Ui_MainWindow as Ui_PreGain


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


class MainWindow(QMainWindow, Ui_Main):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("State Space Controller Design")
        self.setFixedSize(1280, 720)

        self.open_windows = []

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
        self.open_windows.append(amatrix)

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
        R_user = moduleCOD_session.get("R_user")
        N_user = moduleCOD_session.get("N_user")

        if R_user is None and N_user is not None:
            QMessageBox.warning(None, "Warning", "Please set R values before running the simulation.")
            moduleCOD_session["runSim"] = False
            return

        moduleCOD_session["runSim"] = True
        QMessageBox.information(None, "Info", "Successful!")

    def run_simulation(self):
        R_user = moduleCOD_session.get("R_user")
        N_user = moduleCOD_session.get("N_user")

        if moduleCOD_session["runSim"] is True:
            simulate_and_plot(R_user, N_user)
            moduleCOD_session["runSim"] = False
        else:
            QMessageBox.warning(None, "Warning", "Please run the simulation.")


class AMatrix(QMainWindow, Ui_AMatrix):
    def __init__(self):
        super(AMatrix, self).__init__()
        self.setupUi(self)

        self.setWindowTitle("A Matrix")
        self.inputs: list[list[QLineEdit]] = [[getattr(self, f"a{x}{y}") for y in range(1, 4)] for x in range(1, 4)]
        validator = QDoubleValidator()
        for row in self.inputs:
            for el in row:
                el.setValidator(validator)
                el.setPlaceholderText("0.0")

        if moduleCOD_session["A_user"] is not None:
            A_user = moduleCOD_session["A_user"]
            for i, row in enumerate(self.inputs):
                for j, el in enumerate(row):
                    el.setText(str(A_user[i][j]))

        self.updateA.clicked.connect(self.update_matrix)

    @pyqtSlot()
    def update_matrix(self):
        A_vals = [[el.text().strip() for el in row] for row in self.inputs]
        if any("" in row for row in A_vals):
            QMessageBox.warning(None, "Input Error", "Missing values of A matrix")
            return
        moduleCOD_session["A_user"] = np.array(np.array([[float(num) for num in row] for row in A_vals]))
        print(moduleCOD_session["A_user"])
        self.close()


class BMatrix(QMainWindow, Ui_BMatrix):
    def __init__(self):
        super(BMatrix, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("B Matrix")

        self.inputs: list[list[QLineEdit]] = [[getattr(self, f"b{x}1")] for x in range(1, 4)]

        validator = QDoubleValidator()
        for row in self.inputs:
            for el in row:
                el.setValidator(validator)
                el.setPlaceholderText("0.0")

        if moduleCOD_session.get("B_user") is not None:
            data = moduleCOD_session["B_user"]

            for i, row in enumerate(self.inputs):
                for j, el in enumerate(row):
                    el.setText(str(data[i][j]))

        self.updateB.clicked.connect(self.update_matrix)

    @pyqtSlot()
    def update_matrix(self):
        B_vals = [[el.text().strip() for el in row] for row in self.inputs]
        if any("" in row for row in B_vals):
            QMessageBox.warning(None, "Input Error", "Missing values of B matrix.")
            return
        moduleCOD_session["B_user"] = np.array(np.array([[float(num) for num in row] for row in B_vals]))
        print(moduleCOD_session["B_user"])
        self.close()


class CMatrix(QMainWindow, Ui_CMatrix):
    def __init__(self):
        super(CMatrix, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("C Matrix")

        self.inputs: list[list[QLineEdit]] = [[getattr(self, f"c1{y}") for y in range(1, 4)]]

        validator = QDoubleValidator()
        for row in self.inputs:
            for el in row:
                el.setValidator(validator)
                el.setPlaceholderText("0.0")

        if moduleCOD_session.get("C_user") is not None:
            data = moduleCOD_session["C_user"]

            for i, row in enumerate(self.inputs):
                for j, el in enumerate(row):
                    el.setText(str(data[i][j]))

        self.updateC.clicked.connect(self.update_matrix)

    @pyqtSlot()
    def update_matrix(self):
        C_vals = [[el.text().strip() for el in row] for row in self.inputs]
        if any("" in row for row in C_vals):
            QMessageBox.warning(None, "Input Error", "Missing values of C matrix.")
            return
        moduleCOD_session["C_user"] = np.array([[float(num) for num in row] for row in C_vals])
        print(moduleCOD_session["C_user"])
        self.close()


class DMatrix(QMainWindow, Ui_DMatrix):
    def __init__(self):
        super(DMatrix, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("D Matrix")

        self.inputs: list[list[QLineEdit]] = [[self.d11]]

        self.d11.setValidator(QDoubleValidator())
        self.d11.setPlaceholderText("0.0")

        if moduleCOD_session.get("D_user") is not None:
            data = moduleCOD_session["D_user"]

            self.d11.setText(str(data[0][0]))

        self.updateD.clicked.connect(self.update_matrix)

    @pyqtSlot()
    def update_matrix(self):
        val = self.d11.text().strip()
        if not val:
            QMessageBox.warning(None, "Input Error", "Missing value for D.")
            return
        moduleCOD_session["D_user"] = np.array([[float(val)]])
        print(moduleCOD_session["D_user"])
        self.close()


class Controller(QMainWindow, Ui_Controller):
    def __init__(self):
        super(Controller, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Controller")
        self.setFixedSize(548, 207)

        validator = QDoubleValidator()
        self.r11.setValidator(validator)
        self.r11.setPlaceholderText("0.0")
        self.r12.setValidator(validator)
        self.r12.setPlaceholderText("0.0")
        self.r13.setValidator(validator)
        self.r13.setPlaceholderText("0.0")

        # Pre-fill if R_user was already saved
        if moduleCOD_session["R_user"] is not None:
            R_user = moduleCOD_session["R_user"]
            self.r11.setText(str(R_user[0][0]))
            self.r12.setText(str(R_user[0][1]))
            self.r13.setText(str(R_user[0][2]))

        self.updateR.clicked.connect(self.update_matrix)

    def update_matrix(self):
        r11 = self.r11.text().strip()
        r12 = self.r12.text().strip()
        r13 = self.r13.text().strip()

        if r11 == "" and r12 == "" and r13 == "":
            moduleCOD_session["R_user"] = None
            self.close()
            return

        try:
            r11 = float(r11)
            r12 = float(r12)
            r13 = float(r13)
            R_user = np.array([[r11, r12, r13]])
            print(R_user)
            moduleCOD_session["R_user"] = R_user
            self.close()
        except ValueError:
            QMessageBox.warning(None, "Input Error", "Please enter valid numbers.")
            self.r11.clear()
            self.r12.clear()
            self.r13.clear()


class PreGain(QMainWindow, Ui_PreGain):
    def __init__(self):
        super(PreGain, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Pre Gain")
        self.setFixedSize(275, 165)

        self.N.setValidator(QDoubleValidator())
        self.N.setPlaceholderText("0.0")

        # Pre-fill if N_user was already saved
        if moduleCOD_session["N_user"] is not None:
            N_user = moduleCOD_session["N_user"]
            self.N.setText(str(N_user))

        self.updateN.clicked.connect(self.update_pregain)

    def update_pregain(self):
        text = self.N.text().strip()

        if text == "":
            # User wants to clear the pre-gain
            moduleCOD_session["N_user"] = None
            self.close()
            return

        try:
            N_user = float(text)
            print(N_user)
            moduleCOD_session["N_user"] = N_user
            self.close()
        except ValueError:
            QMessageBox.warning(None, "Input Error", "Please enter a valid number.")
            self.N.clear()


def exec_COD(nama, npm):
    moduleCOD_session["npm"] = npm

    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()

    widget = QtWidgets.QStackedWidget()
    widget.setWindowIcon(QIcon("../../public/Logo Merah.png"))
    widget.addWidget(window)
    widget.setCurrentWidget(window)
    widget.resize(window.minimumSize())
    widget.show()
    center_widget(widget)

    # do NOT call app.exec_() here when launched from the main app
    return widget