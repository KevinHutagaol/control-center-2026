from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import  QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from appConfig import firebaseConfig, firestoreConfig
from func.Auth import AuthWorker

from pages.Home.UI_home.ui_Login import Ui_MainWindow

from pages.Home.MainWindow import MainWindow

from func.FirebaseAuthedSession import authed_session

PROJECT_ID = firebaseConfig['projectId']

KKI_DATABASE_ID = firestoreConfig["kkiDatabaseId"]

class Login(QMainWindow, Ui_MainWindow):
    sig_start_google = pyqtSignal()
    sig_start_password = pyqtSignal(str, str)

    def __init__(self):
        super(Login, self).__init__()
        self.worker = None
        self.main_window = None
        self.setupUi(self)
        self.setWindowTitle(f"Control Laboratory - Control Center")
        self.setWindowIcon(QIcon("public/Logo Merah.png"))

        self.Login.clicked.connect(self.loginEmailPassword)
        self.LoginGoogle.clicked.connect(self.loginGoogle)
        self.ChangePass.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.ChangePassPage))

        self.Back.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.LoginPage))

        self.show()

        self.auth_worker = AuthWorker()
        self.auth_thread = QThread()

        self.auth_worker.moveToThread(self.auth_thread)
        self.sig_start_google.connect(self.auth_worker.loginWithGoogle)
        self.sig_start_password.connect(self.auth_worker.loginWithPassword)

        self.auth_worker.finished.connect(self.on_auth_finished)
        self.auth_thread.start()

    def loginGoogle(self):
        self.Login.setEnabled(False)
        self.LoginGoogle.setEnabled(False)

        self.sig_start_google.emit()

    def loginEmailPassword(self):
        self.Login.setEnabled(False)
        self.LoginGoogle.setEnabled(False)

        email = self.Email.text().strip()
        password = self.Pass.text().strip()

        self.sig_start_password.emit(email, password)

    @pyqtSlot(bool, dict)
    def on_auth_finished(self, success, result):
        self.Login.setEnabled(True)
        self.LoginGoogle.setEnabled(True)

        if success:
            self.proceedToMain()
        else:
            QMessageBox.warning(self, "Access Denied", result['msg'])

    def proceedToMain(self):
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        uid = authed_session.uid
        url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/{KKI_DATABASE_ID}/documents/users/{uid}"
        response = authed_session.get(url)

        if response.status_code != 200:
            QMessageBox.warning(self, "Access Denied", f"Error: {response.status_code}, {response.text}")
            return

        response_fields = response.json().get('fields')

        curNama = response_fields.get('displayName').get('stringValue')
        curRole = response_fields.get('role').get('stringValue')
        curKelompok = response_fields.get('group').get('integerValue') # this expects a string
        npm = response_fields.get('npm').get('stringValue')

        self.main_window = MainWindow(npm, curNama, curRole, curKelompok)
        self.main_window.sig_logout_clicked.connect(self.logout)
        self.main_window.show()
        QtWidgets.QApplication.restoreOverrideCursor()
        self.close()

        # elif curRole == 'Assisten':
        #     self.main_window = AdminWindow(npm, curNama, curRole)
        #     self.main_window.sig_logout_clicked.connect(self.logout)
        #     self.main_window.show()
        #     self.close()

    @pyqtSlot(QMainWindow)
    def logout(self, mainWindow):
        """Logout the current user: close child windows, clear session variables
        and show the Login window.
        """
        # optional confirmation
        try:
            resp = QMessageBox.question(mainWindow, "Logout", "Are you sure you want to logout?",
                                        QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
        except Exception as e:
            # if QMessageBox fails for some reason, proceed with logout
            print(e)



        # Close any child windows we opened
        try:
            for key, w in list(mainWindow._children.items()):
                try:
                    if w is not None:
                        w.close()
                except Exception:
                    pass
            mainWindow._children.clear()
        except Exception as e:
            print(e)

        # Clear visible labels
        for attr_name in ("WelcomeText", "WelcomeText2", "Kelompok", "Kelompok2"):
            try:
                if hasattr(mainWindow, attr_name):
                    getattr(mainWindow, attr_name).setText("")
            except Exception as e:
                print(e)

        # Clear stored session attributes
        for a in ("npm", "nama", "role", "kelompok"):
            if hasattr(mainWindow, a):
                try:
                    setattr(mainWindow, a, None)
                except Exception as e:
                    print(e)

        authed_session.set_credentials("", "", "", 0)

        # Show login window again
        try:
            mainWindow.login_window = Login()
            mainWindow.login_window.show()
        except Exception as e:
            print("Failed to open Login window on logout:", e)

        # Close this main window
        try:
            mainWindow.close()
        except Exception as e:
            print(e)
