import requests
from PyQt5 import uic
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon, QValidator
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QApplication

from func import updaterFunc as updaterFunc
from func.Auth import runPasswordAuth, runGoogleAuth, AuthWorker
from pages.Home.installerUtils import resource_path


class Login(QMainWindow):
    sig_start_google = pyqtSignal()
    sig_start_password = pyqtSignal(str, str)

    def __init__(self):
        super(Login, self).__init__()
        uic.loadUi(resource_path("pages/Home/UI_home/Login.ui"), self)
        self.setWindowTitle(f"Control Laboratory - Control Center")
        self.setWindowIcon(QIcon(resource_path("public/Logo Merah.png")))

        self.Login.clicked.connect(self.loginEmailPassword)
        self.LoginGoogle.clicked.connect(self.loginGoogle)
        self.ChangePass.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.ChangePassPage))

        self.Back.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.LoginPage))

        self._version_check_scheduled = False
        self.show()

        if not self._version_check_scheduled:
            self._version_check_scheduled = True
            QTimer.singleShot(0, self.checkVersion)

        self.auth_worker = AuthWorker()
        self.auth_thread = QThread()

        self.auth_worker.moveToThread(self.auth_thread)
        self.sig_start_google.connect(self.auth_worker.loginWithGoogle)
        self.sig_start_password.connect(self.auth_worker.loginWithPassword)

        self.auth_worker.finished.connect(self.on_auth_finished)
        self.auth_thread.start()

    def checkVersion(self):
        print("Checking Version (async)...")

        self.worker = updaterFunc.VersionChecker()
        self.worker.result.connect(self._on_version_checked)
        self.worker.error.connect(lambda err: QMessageBox.critical(self, "Error: Checking Release Version",
                                                                   f"Consult to your lab assistant:\n{err}"))
        self.worker.start()

    def _on_version_checked(self, outdated, local, remote):
        # TODO: QUICK FIX FOR CIRCULAR IMPORT, IDEALLY SHOULD IMPLEMENT CONTROLLER CLASS
        from pages.Home.UpdaterDialog import UpdaterDialog

        print(f"{local} (local) <===> {remote} (remote)")

        if outdated:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Update Available")
            msg.setText(f"New version in release: {remote}")
            msg.setInformativeText(
                "Press update to download the new releases and replace the old files. The update is mandatory for the app.")
            update_btn = msg.addButton("Update Now", QMessageBox.AcceptRole)
            later_btn = msg.addButton("Close App", QMessageBox.RejectRole)
            msg.setDefaultButton(update_btn)
            msg.exec_()

            if msg.clickedButton() is update_btn:
                try:
                    tag, assets = updaterFunc.list_assets()
                    asset = next((a for a in assets if "NT" in a["name"]), None)
                    if not asset:
                        QMessageBox.warning(self, "Tidak ditemukan", "Asset NT tidak ditemukan di rilis ini.")
                        return

                    dlg = UpdaterDialog(self, asset)
                    dlg.exec_()
                except Exception as e:
                    QMessageBox.critical(self, "Gagal Update", f"Terjadi error saat update:\n{e}")

            elif msg.clickedButton() is later_btn:
                QApplication.quit()

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
        from pages.Home.MainWindow import MainWindow
        from pages.Home.AdminWindow import AdminWindow

        # TODO: User Data (Obviously)
        curNama, curRole, curKelompok, npm = "Test", "Mahasiswa", "32", "12345"

        if curRole == 'Mahasiswa':
            self.main_window = MainWindow(npm, curNama, curRole, curKelompok)
            self.main_window.show()
            self.close()
        elif curRole == 'Assisten':
            self.main_window = AdminWindow(npm, curNama, curRole)
            self.main_window.show()
            self.close()
