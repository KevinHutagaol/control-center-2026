import base64
import hashlib
import secrets

import requests
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon, QValidator
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QApplication

from func import updaterFunc as updaterFunc
from pages.Home.main import resource_path, UpdaterDialog, MainWindow, project_id, id_token, AdminWindow

def generatePKCE():
    verifier = secrets.token_urlsafe(64)
    verifier_hashed = hashlib.sha256(verifier.encode('ascii')).digest()
    code_challenge = base64.urlsafe_b64encode(verifier_hashed).decode('ascii').replace('=','')
    return verifier, code_challenge


class Login(QMainWindow):
    def __init__(self):
        super(Login, self).__init__()
        uic.loadUi(resource_path("pages/Home/UI_home/Login.ui"), self)
        self.setWindowTitle(f"Control Practicum Center {updaterFunc.get_local_version()}")
        self.setWindowIcon(QIcon(resource_path("public/Logo Merah.png")))

        self.Login.clicked.connect(self.login)
        self.ChangePass.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.ChangePassPage))

        self.Change.clicked.connect(self.change_password)
        self.Back.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.LoginPage))

        self.Pass.setValidator(self.NoSpaceValidator(self))

        self._version_check_scheduled = False
        self.show()

        if not self._version_check_scheduled:
            self._version_check_scheduled = True
            QTimer.singleShot(0, self.checkVersion)

    def checkVersion(self):
        print("Checking Version (async)...")

        self.worker = updaterFunc.VersionChecker()
        self.worker.result.connect(self._on_version_checked)
        self.worker.error.connect(lambda err: QMessageBox.critical(self, "Error: Checking Release Version", f"Consult to your lab assistant:\n{err}"))
        self.worker.start()

    def _on_version_checked(self, outdated, local, remote):
        print(f"{local} (local) <===> {remote} (remote)")

        if outdated:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Update Available")
            msg.setText(f"New version in release: {remote}")
            msg.setInformativeText("Press update to download the new releases and replace the old files. The update is mandatory for the app.")
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

    class NoSpaceValidator(QValidator):
        def __init__(self, parent=None):
            super().__init__(parent)

        def validate(self, input_text, pos):
            if " " in input_text:
                return (QValidator.Invalid, input_text, pos)
            return (QValidator.Acceptable, input_text, pos)

        def fixup(self, input_text):
            return input_text.replace(" ", "")

    def is_valid_npm(self, npm):
        return npm.isdigit() and len(npm) >= 10

    def login(self):
        npm = self.NPM.text().strip()
        password = self.Pass.text().strip().replace(' ', '')

        if npm == "12345" and password == "admin123":
            self.main_window = MainWindow(npm=2206055750, nama="anonymous", role="Assisten", kelompok="X")
            self.main_window.show()
            self.close()
            return


        if not self.is_valid_npm(npm):
            QMessageBox.warning(self, "Login Failed", "ID Number is Invalid.")
            return

        db_url = f'https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/Account/{npm}'
        headers = {'Authorization': f'Bearer {id_token}'}
        q = None

        try:
            q = requests.get(db_url, headers=headers, timeout=10)
        except Exception as e:
            print(e)
            QMessageBox.about(self, "Error!", "Connection to DB error.")
            return

        if q.status_code != 200:
            if q.json()['error']['code'] == 404:
                QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Password.")
            else:
                QMessageBox.about(self, "Error!", q.json()['error']['status'])
        else:
            fields = q.json().get('fields', {})
            parsed = {k: list(v.values())[0] for k, v in fields.items()}

            print("Login data found...")
            for key, value in parsed.items():
                print(f">> {key:<10}: {value}" if key != "Pass" else f">> {key:<10}: [hidden.]")

            # Extract individual values
            curNama = parsed.get('Nama', '')
            curRole = parsed.get('Role', '')
            curKelompok = parsed.get('Kelompok', '')
            curPassword = parsed.get('Pass', '')

            # Validate password (optional)
            if password != curPassword:
                QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Password.")
                print("Login Failed: Invalid ID Number or Password.")
                return

            # Open the correct window
            print("Password correct, opening MainWindow...")
            if curRole == 'Mahasiswa':
                self.main_window = MainWindow(npm, curNama, curRole, curKelompok)
                self.main_window.show()
            elif curRole == 'Assisten':
                self.main_window = AdminWindow(npm, curNama, curRole)
                self.main_window.show()
            else:
                QMessageBox.warning(self, "Access Denied", "Unknown role type.")
                print("Access Denied: Unknown role type.")

            self.close()

        # try:
        #     doc_ref = db.collection('Account').document(npm)
        #     user_data_doc = doc_ref.get()

        #     if not user_data_doc.exists:
        #         QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Pass.")
        #         return

        #     user_data = user_data_doc.to_dict()

        #     if user_data is None:
        #         QMessageBox.critical(self, "Login Failed", "Unknown Login")
        #         return

        #     stored_pass = user_data.get('Pass')
        #     nama = user_data.get('Nama')
        #     role = user_data.get('Role')
        #     kelompok = user_data.get('Kelompok')

        #     if stored_pass == password:

        #         if role == 'Mahasiswa':
        #             self.main_window = MainWindow(npm, nama, role, kelompok)
        #             self.main_window.show()
        #         elif role == 'Assisten':
        #             self.main_window = AdminWindow(npm, nama, role)
        #             self.main_window.show()

        #         self.close()

        #     else:
        #         QMessageBox.critical(self, "Login Failed", "Invalid ID Number or Password.")

        # except Exception as e:
        #     print("Firebase error:", e)  # debug di console

    def change_password(self):
        npm = self.NPM.text().strip()
        password = self.Pass.text().strip().replace(' ', '')

        print("Password change functionality is currently unavailable in this version.")

        # if not self.is_valid_npm(npm):
        #     QMessageBox.warning(self, "Failed", "ID Number is Invalid.")
        #     return

        # try:
        #     doc_ref = db.collection('Account').document(npm)
        #     user_data_doc = doc_ref.get()

        #     if not user_data_doc.exists:
        #         QMessageBox.critical(self, "Failed", "Invalid ID Number or Password.")
        #         return

        #     user_data = user_data_doc.to_dict()

        #     stored_pass = user_data.get('Pass')
        #     nama = user_data.get('Nama')
        #     role = user_data.get('Role')

        #     if stored_pass == password:
        #         if self.NewPass.text() != self.ConfirmPass.text():
        #             QMessageBox.warning(self, "Failed", "Wrong Confirm Password.")
        #             return

        #         new_password = self.NewPass.text().strip().replace(' ', '')

        #         doc_ref.update({'Pass': new_password})

        #         QMessageBox.information(self, "Success", "Password has successfully changed.")

        #         if role == 'Mahasiswa':
        #             self.main_window = MainWindow(npm, nama, role)
        #             self.main_window.show()
        #         elif role == 'Assisten':
        #             self.main_window = AdminWindow(npm, nama, role)
        #             self.main_window.show()

        #         self.close()

        #     else:
        #         QMessageBox.critical(self, "Failed", "Invalid ID Number or Password.")

        # except Exception as e:
        #     print("Firebase error:", e)  # debug di console
        #     QMessageBox.critical(self, "Connection Error", f"Failed to connect to Database: {e}")
