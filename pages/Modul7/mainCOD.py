import sys
import numpy as np
from PyQt5.QtWidgets import QApplication,  QMainWindow, QMessageBox, QDesktopWidget, QLineEdit
from PyQt5.QtGui import QIcon, QDoubleValidator
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot

from pages.Modul7.session import moduleCOD_session
from pages.Modul7.ss_controller_plot import simulate_and_plot
import pages.Modul7.UI.resource # noqa

from func.sendWithEmail import create_zip_in_memory, sendWithEmail
from func.UserContext import user_context
from func.saveToZip import saveToZip

from pages.Modul7.UI.MainWindowUI import Ui_MainWindow as Ui_Main
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
        self.generated_plots = {}

        self.Abtn.clicked.connect(self.open_amatrix)
        self.Bbtn.clicked.connect(self.open_bmatrix)
        self.Cbtn.clicked.connect(self.open_cmatrix)
        self.Dbtn.clicked.connect(self.open_dmatrix)
        self.Rbtn.clicked.connect(self.open_controller)
        self.Nbtn.clicked.connect(self.open_pregain)
        self.runBtn.clicked.connect(self.submit_data)
        self.scopebtn.clicked.connect(self.run_simulation)
        self.sendEmailBtn.clicked.connect(self.send_email)

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
            simulate_and_plot(self, R_user, N_user)
            moduleCOD_session["runSim"] = False
        else:
            QMessageBox.warning(None, "Warning", "Please run the simulation.")

    def generate_report_text(self):
        """Membuat ringkasan parameter sistem State Space."""
        lines = []
        lines.append("=" * 45)
        lines.append("   STATE SPACE CONTROLLER ANALYSIS (MODUL 6&7)")
        lines.append("=" * 45)
        
        lines.append(f"\nMatrix A:\n{moduleCOD_session.get('A_user')}")
        lines.append(f"\nMatrix B:\n{moduleCOD_session.get('B_user')}")
        lines.append(f"\nMatrix C:\n{moduleCOD_session.get('C_user')}")
        lines.append(f"\nMatrix D:\n{moduleCOD_session.get('D_user')}")
        
        R_user = moduleCOD_session.get("R_user")
        if R_user is not None:
            lines.append(f"\nController Matrix (R):\n{R_user}")
            
        N_user = moduleCOD_session.get("N_user")
        if N_user is not None:
            lines.append(f"\nPre-Gain (N):\n{N_user}")

        lines.append("\nGrafik yang berhasil direkam pada sesi ini:")
        for key in self.generated_plots.keys():
            lines.append(f"  - {key}")

        lines.append("\n\n<i> Semangat mengerjakan borang analisis dan tugasnya gaiss :))!!!</i>")
        lines.append("<i>-Control Lab Assistant 2026</i>")
        lines.append("<i>Fun Fact: bang NA suka mendaki gunung lohh!!</i>")
        lines.append("\n" + "=" * 45)
        return "\n".join(lines)

    def send_email(self):
        if not hasattr(self, 'generated_plots') or not self.generated_plots:
            QMessageBox.warning(None, "Belum Ada Grafik", "Belum ada grafik yang di-generate. Silakan Run Simulation terlebih dahulu!")
            return

        file_list = "\n".join([f"• {k}" for k in self.generated_plots.keys()])
        msg = f"Grafik berikut telah terekam dan siap dikirim ke email:\n\n{file_list}\n\nLanjutkan mengirim email?"
        
        clean_popup_style = """
            QMessageBox, QMessageBox * {
                border-image: none !important;
                background-image: none !important;
            }
            QMessageBox {
                background-color: #ffffff;
            }
            QMessageBox QLabel {
                color: #000000;
                background: transparent;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #e0e0e0;
                color: #000000;
                border: 1px solid #b0b0b0;
                padding: 6px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 60px;
            }
            QMessageBox QPushButton:hover {
                background-color: #d0d0d0;
            }
        """

        # Kustomisasi QMessageBox
        msg_box = QMessageBox(None)
        msg_box.setWindowTitle("Konfirmasi Kirim Email")
        msg_box.setText(msg)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        # Nggak perlu style yang super ribet tadi, cukup yang simple aja:
        msg_box.setStyleSheet("background-color: white; color: black;")
        
        reply = msg_box.exec_()

        if reply == QMessageBox.Yes:

            report_txt = self.generate_report_text()

            # Bungkus semua file menjadi zip memory
            files_to_zip = [{"file_name": k, "file_data": v} for k, v in self.generated_plots.items()]
            files_to_zip.append({"file_name": "System_Details_Modul67.txt", "file_data": report_txt.encode('utf-8')})

            try:
                zip_bytes = create_zip_in_memory(files_to_zip)
            except Exception as e:
                # Bikin pop up error custom juga biar ga kena background merah
                err_box = QMessageBox(self)
                err_box.setIcon(QMessageBox.Critical)
                err_box.setWindowTitle("Error")
                err_box.setText(f"Gagal mengompresi file zip: {e}")
                err_box.setStyleSheet(clean_popup_style)
                err_box.exec_()
                return

            if len(zip_bytes) > 900 * 1024:
                print("Warning: Zip file is large. Firestore email might fail due to 1MB limit.")

            try:
                display_name = user_context.display_name
            except Exception:
                display_name = "Praktikan"

            formatted_report = report_txt.replace('\n', '<br>')
            
            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333;">
                <div style="background-color: #081d38; color: white; padding: 20px; text-align: center;">
                    <h2>Control Systems Simulation Report</h2>
                    <p>Module 6&7: State Space Controller Design</p>
                </div>
                <div style="padding: 20px;">
                    <p>Haloo {display_name},</p>
                    <p>Selamat sudah menyelesaikan sesi praktikum pada minggu ini, berikut sebuah <strong>ZIP</strong> yang isinya grafik-grafik yang kamu buat selama praktikum beserta detail sistemnya.</p>
                    <hr style="border: 0; border-top: 1px solid #eee;">
                    <h3>System Summary</h3>
                    <div style="background-color: #f7f7f7; padding: 15px; border-left: 5px solid #081d38; font-family: monospace; font-size: 12px;">
                        {formatted_report}
                    </div>
                    <br>
                    <p><em>Control Laboratory 2026</em></p>
                    <p>Departemen Teknik Elektro Universitas Indonesia</p>
                </div>
            </body>
            </html>
            """

            # Ubah kursor jadi loading pas proses ngirim
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            
            success, message = sendWithEmail(
                subject="Lab Report: Modul 6&7 State Space Results",
                html_body=html_content,
                text_body=report_txt,
                attachments=[
                    {"filename": "System_Analysis_Modul67.zip", "content": zip_bytes}
                ]
            )

            # Balikin kursor jadi normal
            QApplication.restoreOverrideCursor()

            if success:
                success_box = QMessageBox(self)
                success_box.setWindowTitle("Email Sent")
                success_box.setText("Berhasil dikirim!\n" + message)
                success_box.setStyleSheet(clean_popup_style)
                success_box.exec_()
            else:
                error_box = QMessageBox(self)
                error_box.setWindowTitle("Sending Failed")
                error_box.setText(f"Gagal mengirim email.\nError: {message}")
                error_box.setStyleSheet(clean_popup_style)
                error_box.exec_()


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
        try:
            A_vals = []
            for row in self.inputs:
                row_vals = []
                for el in row:
                    # Ganti koma jadi titik, lalu hapus spasi
                    txt = el.text().strip().replace(',', '.')
                    if not txt:
                        raise ValueError("Kotak tidak boleh kosong")
                    row_vals.append(float(txt))
                A_vals.append(row_vals)
                
            moduleCOD_session["A_user"] = np.array(A_vals)
            print(moduleCOD_session["A_user"])
            self.close()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Periksa kembali input Matrix A. Pastikan semua terisi angka yang valid (contoh: 1.5 atau 1,5).")


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
        try:
            B_vals = []
            for row in self.inputs:
                row_vals = []
                for el in row:
                    txt = el.text().strip().replace(',', '.')
                    if not txt:
                        raise ValueError("Kotak tidak boleh kosong")
                    row_vals.append(float(txt))
                B_vals.append(row_vals)
                
            moduleCOD_session["B_user"] = np.array(B_vals)
            print(moduleCOD_session["B_user"])
            self.close()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Periksa kembali input Matrix B. Pastikan semua terisi angka yang valid.")


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
        try:
            C_vals = []
            for row in self.inputs:
                row_vals = []
                for el in row:
                    txt = el.text().strip().replace(',', '.')
                    if not txt:
                        raise ValueError("Kotak tidak boleh kosong")
                    row_vals.append(float(txt))
                C_vals.append(row_vals)
                
            moduleCOD_session["C_user"] = np.array(C_vals)
            print(moduleCOD_session["C_user"])
            self.close()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Periksa kembali input Matrix C. Pastikan semua terisi angka yang valid.")


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
        try:
            val = self.d11.text().strip().replace(',', '.')
            if not val:
                raise ValueError("Kotak tidak boleh kosong")
                
            moduleCOD_session["D_user"] = np.array([[float(val)]])
            print(moduleCOD_session["D_user"])
            self.close()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Periksa kembali input Matrix D. Pastikan berisi angka yang valid.")


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
        r11_txt = self.r11.text().strip().replace(',', '.')
        r12_txt = self.r12.text().strip().replace(',', '.')
        r13_txt = self.r13.text().strip().replace(',', '.')

        # Kalau dikosongin semua, anggap user pengen hapus controller
        if r11_txt == "" and r12_txt == "" and r13_txt == "":
            moduleCOD_session["R_user"] = None
            self.close()
            return

        try:
            r11 = float(r11_txt)
            r12 = float(r12_txt)
            r13 = float(r13_txt)
            R_user = np.array([[r11, r12, r13]])
            print(R_user)
            moduleCOD_session["R_user"] = R_user
            self.close()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Gagal menyimpan Controller. Pastikan semua kotak terisi angka yang valid (contoh: 1.5 atau 1,5).")


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
        text = self.N.text().strip().replace(',', '.')

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
            QMessageBox.warning(self, "Input Error", "Gagal menyimpan Pre-Gain. Masukkan angka yang valid.")

    
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