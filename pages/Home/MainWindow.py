from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from func.Auth import logOutGoogleSession
from func.FirebaseAuthedSession import authed_session
from pages.Modul2.MainModul2 import launch_modul2
from pages.Modul3.mainCDRL import exec_CDRL
from pages.Modul4.MainModul4 import launch_modul4
from pages.Modul5.mainCDFR import exec_CDFR
from pages.Modul6.mainSSM import exec_SSM
from pages.Modul7.mainCOD import exec_COD
from pages.Modul8.mainDCOD import exec_DCOD
from pages.Modul910.mainDMMCD import exec_DMMCD

from pages.Home.UI_home.ui_Main import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    sig_logout_clicked = pyqtSignal(QMainWindow)

    def __init__(self, npm, nama, role, kelompok):
        super().__init__()
        self.login_window = None
        self.setupUi(self)
        self.setWindowTitle(f"Control Laboratory - Control Center")
        self.setWindowIcon(QIcon("public/Logo Merah.png"))

        # store session info so we can clear them on logout
        self.npm = npm
        self.nama = nama
        self.role = role
        self.kelompok = kelompok

        self._is_logging_out = False

        self.RootLocus.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.RootLocusPage))
        self.FreqResponse.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.FreqResponsePage))
        self.CDFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CDFreqPage))
        self.COD.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.ShouldBeEmptyPage))
        self.DiscreteCOD.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.DiscreteCDPage))
        self.DCMotor.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.DCMotorModelAndDesignPage))

        self.RunRL.clicked.connect(lambda checked, n=nama, p=npm: self.run_root_locus(n, p))
        self.RunCDRL.clicked.connect(lambda checked, n=nama, p=npm: self.run_cd_root_locus(n, p))
        self.RunFreq.clicked.connect(lambda checked, n=nama, p=npm: self.run_frequency_response(n, p))
        self.RunCDFreq.clicked.connect(lambda checked, n=nama, p=npm: self.run_cd_frequency_response(n, p))
        self.RunCOD.clicked.connect(lambda checked, n=nama, p=npm: self.run_cod(n, p))
        self.RunDCOD.clicked.connect(lambda checked, n=nama, p=npm,: self.run_dcod(n, p))
        self.RunMotor.clicked.connect(lambda checked, n=nama, p=npm, k=kelompok: self.run_motor(n, p, k))

        # self.WelcomeText.setText(f"Welcome {nama}!")
        # self.Kelompok.setText(kelompok)

        self.WelcomeText.setText(f"Welcome {nama}!")
        self.Kelompok2_2.setText(kelompok)

        self.Practicum.clicked.connect(lambda: self.Stacked.setCurrentWidget(self.PracticumPage))

        self._children = {}

        self.LogOut.clicked.connect(self.on_logout_button_clicked)

        self.show()

    def on_logout_button_clicked(self):
        self._is_logging_out = True
        self.sig_logout_clicked.emit(self)

    def closeEvent(self, event):
        if self._is_logging_out:
            event.accept()
            return

        reply = QMessageBox.question(self, 'Exit',
                                     "Are you sure you want to close? This will log you out.",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

            authed_session.clear_credentials()
            logOutGoogleSession()

            QtWidgets.QApplication.restoreOverrideCursor()
            event.accept()
            QtWidgets.QApplication.quit()
        else:
            event.ignore()

    def run_root_locus(self, nama, npm):
        print("Running Root Locus")
        w = launch_modul2()
        key = f"Modul2-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_cd_root_locus(self, nama, npm):
        print("Running Controller Design: Root Locus")
        w = exec_CDRL(nama, npm)
        key = f"Modul3-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_frequency_response(self, nama, npm):
        print("Running Frequency Response")
        w = launch_modul4()
        key = f"Modul4-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_cd_frequency_response(self, nama, npm):
        print("Running Controller Design: Frequency Response")
        w = exec_CDFR(nama, npm)
        key = f"Modul5-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_state_space(self, nama, npm):
        print("Running State Space Modeling")
        w = exec_SSM(nama, npm)
        key = f"Modul6-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_cod(self, nama, npm):
        print("Running Controller and Observer Design")
        w = exec_COD(nama, npm)
        key = f"Modul7-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_dcod(self, nama, npm):
        print("Running Discrete Controller and Observer Design")
        w = exec_DCOD(nama, npm)
        key = f"Modul8-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

    def run_motor(self, nama, npm, kelompok):
        print("Running DC Motor Modeling and Controller Design")
        w = exec_DMMCD(nama, npm, kelompok)
        key = f"Modul910-{npm}"
        self._children[key] = w
        w.destroyed.connect(lambda: self._children.pop(key, None))

