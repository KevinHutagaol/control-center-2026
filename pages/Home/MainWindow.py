from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow

from pages.Home.installerUtils import resource_path
from pages.Modul4.mainCDRL import exec_CDRL
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
        self.setWindowIcon(QIcon(resource_path("public/Logo Merah.png")))

        # store session info so we can clear them on logout
        self.npm = npm
        self.nama = nama
        self.role = role
        self.kelompok = kelompok

        self.RootLocus.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.RootLocusPage))
        self.CDFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CDFreqPage))
        self.CDRootLocus.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CDRootLocusPage))
        self.CDFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CDFreqPage))
        self.StateSpace.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.StateSpacePage))
        self.COD.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.CODPage))
        self.DCOD.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.DCODPage))
        self.DCMotor.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.MotorPage))

        self.RunRL.clicked.connect(lambda checked, n=nama, p=npm: self.run_root_locus(n, p))
        self.RunFreq.clicked.connect(lambda checked, n=nama, p=npm: self.run_frequency_response(n, p))
        self.RunCDRL.clicked.connect(lambda checked,n=nama, p=npm: self.run_cd_root_locus(n, p))
        self.RunCDFreq.clicked.connect(lambda checked, n=nama, p=npm: self.run_cd_frequency_response(n, p))
        self.RunStateSpace.clicked.connect(lambda checked, n=nama, p=npm: self.run_state_space(n, p))
        self.RunCOD.clicked.connect(lambda checked, n=nama, p=npm: self.run_cod(n, p))
        self.RunDCOD.clicked.connect(lambda checked, n=nama, p=npm, k=kelompok: self.run_motor(n, p, k))
        self.RunMotor.clicked.connect(lambda checked, n=nama, p=npm: self.run_dcod(n, p))

        # self.WelcomeText.setText(f"Welcome {nama}!")
        # self.Kelompok.setText(kelompok)

        self.WelcomeText.setText(f"Welcome {nama}!")
        self.Kelompok2_2.setText(kelompok)

        self.Practicum.clicked.connect(lambda: self.Stacked.setCurrentWidget(self.PracticumPage))

        self.btn23.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul23))
        self.btn4.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul4))
        self.btn5.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul5))
        self.btn6.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul6))
        self.btn7.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul7))
        self.btn8.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul8))
        self.btn910.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul910))
        self.btn11.clicked.connect(lambda: self.stackedNilai.setCurrentWidget(self.Modul11))

        self._children = {}

        self.LogOut.clicked.connect(lambda: self.sig_logout_clicked.emit(self))

        self.show()

    def run_root_locus(self, nama, npm):
        print("Running Root Locus")

    def run_frequency_response(self, nama, npm):
        print("Running Frequency Response")

    def run_cd_root_locus(self, nama, npm):
        print("Running Controller Design: Root Locus")
        w = exec_CDRL(nama, npm)
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

    # def logout(self):
    #     """Logout the current user: close child windows, clear session variables
    #     and show the Login window.
    #     """
    #     # optional confirmation
    #     try:
    #         resp = QMessageBox.question(self, "Logout", "Are you sure you want to logout?",
    #                                     QMessageBox.Yes | QMessageBox.No)
    #         if resp != QMessageBox.Yes:
    #             return
    #     except Exception:
    #         # if QMessageBox fails for some reason, proceed with logout
    #         pass
    #
    #     # Close any child windows we opened
    #     try:
    #         for key, w in list(self._children.items()):
    #             try:
    #                 if w is not None:
    #                     w.close()
    #             except Exception:
    #                 pass
    #         self._children.clear()
    #     except Exception:
    #         pass
    #
    #     # Clear visible labels
    #     for attr_name in ("WelcomeText", "WelcomeText2", "Kelompok", "Kelompok2"):
    #         try:
    #             if hasattr(self, attr_name):
    #                 getattr(self, attr_name).setText("")
    #         except Exception:
    #             pass
    #
    #     # Clear stored session attributes
    #     for a in ("npm", "nama", "role", "kelompok"):
    #         if hasattr(self, a):
    #             try:
    #                 setattr(self, a, None)
    #             except Exception:
    #                 pass
    #
    #     # Show login window again
    #     try:
    #         self.login_window = Login()
    #         self.login_window.show()
    #     except Exception as e:
    #         print("Failed to open Login window on logout:", e)
    #
    #     # Close this main window
    #     try:
    #         self.close()
    #     except Exception:
    #         pass

