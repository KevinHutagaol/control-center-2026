import queue
import sys
import os
import subprocess
from datetime import datetime, timezone, timedelta
from PyQt5 import QtWidgets, uic, QtChart, QtCore, QtGui
import numpy as np
import serial.tools.list_ports
import matplotlib.pyplot as plt
import control as ctrl
import firebase_admin
from firebase_admin import credentials, firestore
from pathlib import Path
import queue
import pandas as pd
import requests

import pages.Modul910.asset.resources 

def resource_path(rel: str | Path) -> str:
    """
    Resolve a data file path that works in:
      - dev (walk up parents so files in project root are found),
      - PyInstaller --onedir,
      - PyInstaller --onefile (temp _MEIPASS),
      - PyInstaller v6 layout (data under _internal).
    Returns a string path. It does NOT create files.
    """
    rel_path = Path(rel)

    # 0) Absolute path: just return it (don’t prepend bases)
    if rel_path.is_absolute():
        return str(rel_path)

    candidates: list[Path] = []

    # 1) PyInstaller onefile: temp unpack dir
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        candidates += [base / rel_path, base / "_internal" / rel_path]

    # 2) PyInstaller onedir: beside the executable
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates += [exe_dir / rel_path, exe_dir / "_internal" / rel_path]

    # 3) Dev: walk upwards so root-level assets can be found from subpackages
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        candidates.append(parent / rel_path)
        candidates.append(parent / "_internal" / rel_path)

    # Pick the first existing candidate
    for c in candidates:
        if c.exists():
            return str(c)

    # Fallback: return the first candidate even if missing (caller can handle)
    return str(candidates[0])

class FirebaseManager:
    def __init__(self):
        """Initialize Firebase connection"""
        self.is_connected = False
        self.id_token = None
        self.initialize_firebase()

    def initialize_firebase(self):
        """Initialize Firebase with service account credentials"""
        api_key = 'AIzaSyCB1MgJAThfYxSVxEpuUjSgES15pUKEIME'

        auth_url = f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}'
        body = {'returnSecureToken': True}
        
        print("Attempting to connect to the database...")
        try:
            r = requests.post(auth_url, data=body, timeout=10)
            self.id_token = r.json()['idToken']
            print("Successfully connected to the database")
            self.is_connected = True
        except Exception as e:
            print(e)
            self.is_connected = False
            
    def upload_student_submission(self, student, student_name, submission_data):
        """Overwrite/update an existing student document in Firestore"""
        if not self.id_token:
            print("No id_token; user not authenticated")
            return False

        # Existing document path, since the doc already exists
        url = (
            "https://firestore.googleapis.com/v1/"
            f"projects/control-lab-c4480/databases/(default)/documents/Modul89/{student}"
        )

        headers = {
            "Authorization": f"Bearer {self.id_token}",
            "Content-Type": "application/json",
        }

        # ---------- Build your data in Python ----------
        timestamp = datetime.now(timezone(timedelta(hours=7))).isoformat()

        submitted_parameters = {
            "K_fopdt": submission_data.get("K_fopdt", 0),
            "tau_fopdt": submission_data.get("tau_fopdt", 0),
            "L_fopdt": submission_data.get("L_fopdt", 0),
            "K1": submission_data.get("K1", 0),
            "K2": submission_data.get("K2", 0),
            "K3": submission_data.get("K3", 0),
        }

        true_parameters = {
            "K_fopdt": submission_data.get("true_K_fopdt", 0),
            "tau_fopdt": submission_data.get("true_tau_fopdt", 0),
            "L_fopdt": submission_data.get("true_L_fopdt", 0),
            "k1": submission_data.get("true_k1", 0),
            "k2": submission_data.get("true_k2", 0),
            "k3": submission_data.get("true_k3", 0),
        }

        scores = {
            "model_score": submission_data.get("model_score", 0),
            "control_score": submission_data.get("control_score", 0),
            "final_score": submission_data.get("final_score", 0),
        }

        errors = {
            "K_fopdt_error_percent": submission_data.get("K_fopdt_error_percent", 0),
            "tau_fopdt_error_percent": submission_data.get("tau_fopdt_error_percent", 0),
            "L_fopdt_error_percent": submission_data.get("L_fopdt_error_percent", 0),
            "k1_error_percent": submission_data.get("k1_error_percent", 0),
            "k2_error_percent": submission_data.get("k2_error_percent", 0),
            "k3_error_percent": submission_data.get("k3_error_percent", 0),
        }

        # ---------- Helper converters to Firestore types ----------
        def num_field(value):
            return {"doubleValue": float(value)}

        def str_field(value):
            return {"stringValue": str(value)}

        def map_num_dict(d):
            return {
                "mapValue": {
                    "fields": {k: num_field(v) for k, v in d.items()}
                }
            }

        # ---------- Build Firestore document body ----------
        firestore_doc = {
            "fields": {
                "timestamp": {"timestampValue": timestamp},
                "controller_type": str_field(submission_data.get("controller_type", "Unknown")),
                "nama": str_field(student_name),
                "submitted_parameters": map_num_dict(submitted_parameters),
                "true_parameters": map_num_dict(true_parameters),
                "scores": map_num_dict(scores),
                "errors": map_num_dict(errors),
            }
        }

        # Optional: debug body
        # import json
        # print(json.dumps(firestore_doc, indent=2))

        # ---------- PATCH existing document ----------
        try:
            resp = requests.patch(url, headers=headers, json=firestore_doc, timeout=10)
            print("Firestore response status:", resp.status_code)
            print("Firestore response body:", resp.text)
            resp.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print("Error updating submission in Firestore:", e)
            if getattr(e, "response", None) is not None:
                print("Response text:", e.response.text)
            return False

    def find_student(self, group):
        """Check if a student document exists in Firebase"""
        if not self.is_connected:
            return []
        
        # print(self.id_token)
            
        url = f"https://firestore.googleapis.com/v1/projects/control-lab-c4480/databases/(default)/documents/Account"
        headers = {"Authorization": f"Bearer {self.id_token}"}
        
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching collection: {e}")
            return []
        
        docs = r.json().get("documents", [])
        rows = []

        for doc in docs:
            fields = doc.get("fields", {})

            kelompok_field = fields.get("Kelompok")
            if not kelompok_field:
                continue

            # Firestore REST: one of stringValue / integerValue / doubleValue / etc.
            kelompok_value = (
                kelompok_field.get("stringValue")
                or kelompok_field.get("integerValue")
                or kelompok_field.get("doubleValue")
            )

            # Compare as string to be safe
            if str(kelompok_value) == str(group):
                rows.append({
                    "NPM": doc.get("name").split('/')[-1],
                    "Name": doc.get("fields", {}).get("Nama")
                })

        print(rows)
        return rows
        

    def test_upload_student_submission(self):
        """Test function to upload a sample student submission"""
        sample_student = "0"
        sample_submission = {
            'K_fopdt': 69,
            'tau_fopdt': 67,
            'L_fopdt': 420,
            'K1': 0,
            'K2': 0,
            'K3': 0,
            'true_K_fopdt': 0,
            'true_tau_fopdt': 0,
            'true_L_fopdt': 0,
            'true_k1': 0,
            'true_k2': 0,
            'true_k3': 0,
            'model_score': 0,
            'control_score': 0,
            'final_score': 0,
            'K_fopdt_error_percent': 1,
            'tau_fopdt_error_percent': 0,
            'L_fopdt_error_percent': 0,
            'k1_error_percent': 0,
            'k2_error_percent': 0,
            'k3_error_percent': 0,
            'controller_type': 'PID'
        }

        self.upload_student_submission("2206055870", "Malik Al Hazazi Vanery", sample_submission)
class RefreshingComboBox(QtWidgets.QComboBox):
    """QComboBox that refreshes its items whenever opened."""
    def showPopup(self):
        self.refresh_ports()
        super().showPopup()  # call parent to actually open dropdown

    def get_available_ports(self):
        """Return a list of available serial ports."""
        ports = serial.tools.list_ports.comports()
        port_info_list = []

        for port in ports:
            port_info = {
                'device': port.device,
                'description': " ".join(part for part in port.description.split() if port.device.lower() not in part.lower()),
                'manufacturer': port.manufacturer,
                'vid': hex(port.vid).upper(),
                'pid': hex(port.pid).upper(),
                'serial_number': port.serial_number,
                'hwid': port.hwid
            }

            port_info_list.append(port_info)    
        return port_info_list

    def refresh_ports(self):
        port_info = self.get_available_ports()

        current = self.currentText()
        self.clear()

        # Add default "no selection" item first
        self.addItem("Select a port…")

        if port_info:
            self.addItems(f"{ports['device']} - {ports['description']}" for ports in port_info)
            # Restore selection if still valid
            if any(ports['device'] == current for ports in port_info):
                index = self.findText(current)
                self.setCurrentIndex(index)
            else:
                # reset back to default
                self.setCurrentIndex(0)
        else:
            self.addItem("No ports available")
            self.setCurrentIndex(0)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, kelompok):
        super().__init__()
        
        # print("Loading UI from:", resource_path("ui_910/main.ui"))

        uic.loadUi(resource_path("ui_910/main.ui"), self)
        self.setWindowTitle("Practicum Software : Motor SIM Modeling and Control")
        self.setWindowIcon(QtGui.QIcon(resource_path("../../public/Logo Merah.png")))

        self.serial_conn = None
        self.child_windows = {}
        group = kelompok

        # Initialize Firebase Manager
        self.firebase_manager = FirebaseManager()
        self.current_students = self.firebase_manager.find_student(group)  # Example group "A1"
        QtWidgets.QMessageBox.information(self, "Info", f"Found {len(self.current_students)} students in group {group}.")

        self.firebase_manager.test_upload_student_submission()

        self.olc.clicked.connect(self.olcClicked)
        self.clc.clicked.connect(self.clcClicked)
        self.sa.clicked.connect(self.saClicked)
        self.encoder.clicked.connect(self.encoderClicked)
        self.log.clicked.connect(self.logClicked)
        self.lrc.clicked.connect(self.lrcClicked)
        
        # Replace UI combobox with our refreshing one
        old_combo = self.ports
        layout = old_combo.parent().layout()
        self.ports.setObjectName("ports")
        self.ports = RefreshingComboBox(old_combo.parent())
        layout.replaceWidget(old_combo, self.ports)
        old_combo.deleteLater()

        # Set default text before refresh
        self.ports.addItem("Select a port…")
        self.ports.setCurrentIndex(0)

        self.ports.currentTextChanged.connect(self.on_port_selected)

    # Setup recursive function that will retry until data is available
    def try_read_motor_info(self, retry_count=0):
        if retry_count >= 10:  # Limit retries to avoid infinite loop
            QtWidgets.QMessageBox.information(self, "Info", "No motor info data found.")
            self.clear_serial_buffers()
            return
            
        if self.serial_conn and self.serial_conn.in_waiting > 0:
            self.readMotorInfo()
            self.clear_serial_buffers()
        else:
            # No data yet, resend request and try again
            self.serial_conn.write(b"i\n")
            QtCore.QTimer.singleShot(200, lambda: self.try_read_motor_info(retry_count + 1))

    def clear_serial_buffers(self):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()
        except Exception as e:
            print("Serial buffer clear error:", e)

    def on_port_selected(self, port_name):
        if (not port_name 
            or port_name in ["No ports available", "Select a port…"]):
            # Ignore invalid/default options
            return

        # Close existing connection if open
        if self.serial_conn and self.serial_conn.is_open:
            print(f"Closing {self.serial_conn.port}")
            self.serial_conn.close()

        try:
            # Try to open new connection
            real_port = port_name.split(" ")[0]  # Extract actual port name
            print(f"Opening {real_port} at 115200 baud")
            self.serial_conn = serial.Serial(port=real_port, baudrate=115200, timeout=1)
            # Send initial request
            self.serial_conn.write(b"i\n")
            
            # First attempt after 200ms
            QtCore.QTimer.singleShot(200, lambda: self.try_read_motor_info(0))
            
            # print(f"Opened {port_name} at 115200 baud")
            self.set_status("green")   
        except serial.SerialException as e:
            print(f"Failed to open {port_name}: {e}")
            self.serial_conn = None
            self.set_status("red")  

    def readMotorInfo(self):
        try:
            if not self.serial_conn or not self.serial_conn.in_waiting:
                return

            # Read the first line (status code: 0, 1, or 2)
            while True:
                status_line = self.serial_conn.readline().decode().strip()
                print(f"Status line: '{status_line}'")
                if not status_line:
                    return
                try:
                    status = int(status_line)
                    break  # Got a valid status, exit loop
                except ValueError:
                    continue  # Not a number, skip this line

            if status == 2:
                # Both calibration + motor char exist
                data_line = self.serial_conn.readline().decode().strip()
                print(f"Data line: '{data_line}'")
                ppr, maxRPM = data_line.split()
                self.ppr.setText(f"{ppr}")
                self.maxRPM.setText(f"{float(maxRPM):.2f}")

            elif status == 1:
                # Only calibration exists
                data_line = self.serial_conn.readline().decode().strip()
                print(f"Data line: '{data_line}'")
                ppr = data_line
                self.ppr.setText(f"{ppr}")
                self.maxRPM.setText("--")

            elif status == 0:
                # Nothing stored
                self.ppr.setText("--")
                self.maxRPM.setText("--")

        except Exception as e:
            print("Motor info read error:", e)

    def set_status(self, status):
        """Update QLabel statusIndicator with a given status string."""
        self.statusIndicator.setProperty("status", status)
        self.statusIndicator.style().unpolish(self.statusIndicator)
        self.statusIndicator.style().polish(self.statusIndicator)
        self.statusIndicator.update()

    def close_other_windows(self, keep=[]):
        """Close all child windows except those in 'keep' list."""
        for name, win in list(self.child_windows.items()):
            if name not in keep and win is not None:
                win.close()
                self.child_windows.pop(name, None)

    def saClicked(self):
        # Handle the SA button click event
        self.child_windows["sa"] = sa(self.serial_conn, self)  # Pass self as main_window
        self.child_windows["sa"].show()

    def olcClicked(self):
        # Handle the OLC button click event
        if self.serial_conn and self.serial_conn.is_open:
            self.close_other_windows(keep=["sa"])
            self.serial_conn.write(b"o\n")
            self.child_windows["olc"] = olc(self.serial_conn, self)  # Pass self as main_window
            self.child_windows["olc"].show()
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No serial port is open.")

    def clcClicked(self):
        # Handle the CLC button click event
        if self.serial_conn and self.serial_conn.is_open:
            self.close_other_windows(keep=["sa"])
            self.serial_conn.write(b"c\n")
            self.child_windows["clc"] = clc(self.serial_conn, self)  # Pass self as main_window
            self.child_windows["clc"].show()
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No serial port is open.")

    def encoderClicked(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.close_other_windows(keep=["sa"])
            self.serial_conn.write(b"e\n")
            self.child_windows["encoder"] = Encoder(self.serial_conn, self)  # Pass self as main_window
            self.child_windows["encoder"].show()
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No serial port is open.")
        
    def logClicked(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.close_other_windows(keep=["sa"])
            self.serial_conn.write(b"s\n")
            self.child_windows["logwindow"] = LogWindow(self.serial_conn, self)  # Pass self as main_window
            self.child_windows["logwindow"].show()
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No serial port is open.")

    def lrcClicked(self):
        # Handle the LRC button click event
        if self.serial_conn and self.serial_conn.is_open:
            self.close_other_windows(keep=["sa"])
            self.serial_conn.write(b"l\n")
            self.child_windows["lrc"] = LRC(self.serial_conn, self)  # Pass serial_conn
            self.child_windows["lrc"].show()
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No serial port is open.")

    def closeEvent(self, event):
        try:
            self.serial_conn.close()
        except Exception as e:
            print(e)
        event.accept()

class Encoder(QtWidgets.QMainWindow):
    def __init__(self, serial_conn, main_window=None):
        super().__init__(main_window)  # Pass parent for Qt hierarchy
        uic.loadUi(resource_path("ui_910/calibration.ui"), self)
        self.setWindowTitle("Encoder Calibration")
        self.setWindowIcon(QtGui.QIcon(resource_path("../../public/Logo Merah.png")))

        self.serial_conn = serial_conn
        self.main_window = main_window  # Store reference to main window
        self.serial_lock = QtCore.QMutex()
        self.cmd_queue = queue.Queue()
        
        # Connect buttons
        self.pls.pressed.connect(self.plsPressed)
        self.pls.released.connect(self.stopMotor)
        self.min.pressed.connect(self.minPressed)
        self.min.released.connect(self.stopMotor)
        self.done.clicked.connect(self.doneClicked)

        # 🔹 Timer for polling ESP32
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.requestTicks)
        self.timer.start(200)  # every 200 ms (5 Hz) request

    def safe_write(self, data):
        if not self.serial_conn or not self.serial_conn.is_open:
            QtWidgets.QMessageBox.critical(self, "Serial Error", "Serial connection lost.")
            self.close()
       
        if self.serial_lock.tryLock():
            try:
                self.serial_conn.write(data)           
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Serial Error", f"Serial error: {e}")
                self.close()
            finally:
                self.serial_lock.unlock()
                self.processQueue()
        else:
            self.cmd_queue.put(data)

    def processQueue(self):
        while not self.cmd_queue.empty():
            if self.serial_lock.tryLock():
                try:
                    data = self.cmd_queue.get()
                except Exception as e:
                    break

                try:
                    self.serial_conn.write(data)            
                except Exception as e:
                    QtWidgets.QMessageBox.critical(self, "Serial Error", f"Serial error: {e}")
                    self.close()
                finally:
                    self.serial_lock.unlock()

    def plsPressed(self):
        self.timer.stop()  
        self.safe_write(b"1")
        self.serial_conn.flush()
        self.timer.start(200)

    def minPressed(self):
        self.timer.stop()
        self.safe_write(b"-1")
        self.serial_conn.flush()
        self.timer.start(200)

    def stopMotor(self):
        self.timer.stop()
        self.safe_write(b"0")
        self.serial_conn.flush()
        self.timer.start(200)

    def doneClicked(self):
        self.timer.stop()
        try:
            value = float(self.rotation.text())
            # Validate the input
            if value <= 0:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Rotation value must be positive.")
                return
            #QtWidgets.QMessageBox.information(self, "Info", f"Storing PPR = {value} to flash.")
            self.serial_conn.write(f"3 {value}".encode())
            self.serial_conn.flush()
            if self.main_window:
                QtCore.QTimer.singleShot(200, self.main_window.try_read_motor_info)
            self.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Serial Error", f"Serial error: {e}")
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for rotation.")

    # In Encoder class
    def closeEvent(self, event):
        try:
            self.timer.stop()  # Stop polling timer
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(b"4")
                self.serial_conn.flush()
                self.clear_serial_buffers()
                
                # Refresh main window after a short delay to let ESP update
                if self.main_window:
                    QtCore.QTimer.singleShot(200, self.main_window.try_read_motor_info)

        except Exception:
            pass
        event.accept()
    
    def clear_serial_buffers(self):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()
        except Exception as e:
            print("Serial buffer clear error:", e)

    def requestTicks(self):
        self.safe_write(b"2")   # Ask ESP for ticks
        self.readSerial()

    def readSerial(self):
        try:
            if self.serial_conn and self.serial_conn.in_waiting:
                line = self.serial_conn.readline().decode("utf-8").strip()
                if line:
                    try:
                        ticks = int(line)
                        self.pulse.display(ticks)  # update LCD
                    except ValueError:
                        pass  # ignore garbage/debug lines
        except Exception as e:
            print("Serial read error:", e)

class ProgressBar(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(resource_path("ui_910/progressbar.ui"), self)  
        self.setWindowTitle("Loading ...")
        self.setWindowIcon(QtGui.QIcon(resource_path("../../public/Logo Merah.png")))

        self.setWindowModality(QtCore.Qt.ApplicationModal)

class LogWindow(QtWidgets.QMainWindow):
    def __init__(self, serial_conn, main_window=None):
        super().__init__(main_window)
        uic.loadUi(resource_path("ui_910/linlog.ui"), self)
        self.setWindowTitle("DC Motor vs PWM Linear Relation")
        self.setWindowIcon(QtGui.QIcon(resource_path("../../public/Logo Merah.png")))

        self.serial_conn = serial_conn
        self.main_window = main_window  # Store reference to main window

        # Create chart
        self.chart = QtChart.QChart()
        self.series = QtChart.QLineSeries()
        self.series.setPointsVisible(True)  # Show actual data points
        self.chart.addSeries(self.series)
        self.series.setName("Speed (RPM)")
        self.chart.createDefaultAxes()
        self.chart.setTitle("Motor Characteristic Curve")

        # Chart view
        self.chartView = QtChart.QChartView(self.chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        # Add chartView into graphFrame's existing grid layout
        layout = self.graphFrame.layout()  # get the QGridLayout already set in QtDesigner
        layout.addWidget(self.chartView, 0, 0, 2, 1)  # row=0, col=0, rowspan=2, colspan=1

        # Enable hover events for tooltips
        self.series.hovered.connect(self.on_hover)

        # Tooltip label
        self.tooltip = QtWidgets.QLabel(self.chartView)
        self.tooltip.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip.hide()

        # Generate new chart then plot when done
        self.newGraph.clicked.connect(self.newGraphClicked)
        self.popup.clicked.connect(self.popupClicked)

    # Setup recursive function that will retry until data is available
    def try_read_motor_char(self, retry_count=0):
        if retry_count >= 10:  # Limit retries to avoid infinite loop
            QtWidgets.QMessageBox.information(self, "Log", "No motor characteristic data found.")
            return
        
        if retry_count == 0:
            # Clear stale data on first attempt, then send request
            self.clear_serial_buffers()
            self.serial_conn.write(b"2")
            self.serial_conn.flush()
            # Wait a bit for first response
            QtCore.QTimer.singleShot(300, lambda: self.try_read_motor_char(retry_count + 1))
        elif self.serial_conn and self.serial_conn.in_waiting > 0:
            # Data is available, try to read it
            self.pwm, self.speed = self.read_motor_characteristic()
            if self.pwm and self.speed:
                # Successfully got data
                self.load_and_plot(self.pwm, self.speed)
            else:
                # Data was empty or returned None, retry
                self.serial_conn.write(b"2")
                self.serial_conn.flush()
                QtCore.QTimer.singleShot(200, lambda: self.try_read_motor_char(retry_count + 1))
        else:
            # No data yet, resend request and try again
            self.serial_conn.write(b"2")
            self.serial_conn.flush()
            QtCore.QTimer.singleShot(200, lambda: self.try_read_motor_char(retry_count + 1))

    def showEvent(self, event):
        """Called when window is shown"""
        super().showEvent(event)
        self.try_read_motor_char()

    def load_and_plot(self, pwm, speed):
        self.series.clear()

        if pwm and speed:
            for x, y in zip(pwm, speed):
                self.series.append(x, y)

            self.chart.axisX().setTitleText("PWM Value")
            self.chart.axisY().setTitleText("Speed (RPM)")

            # Set axis ranges
            self.chart.axisX().setRange(min(pwm), max(pwm))
            self.chart.axisY().setRange(0, max(speed) * 1.1)  # Add 10% margin
        else:
            QtWidgets.QMessageBox.information(self, "Log", "No motor characteristic file found.")

    def read_motor_characteristic(self):
        data_pwm, data_speed = [], []
        try:
            # Read until we get valid data or a status code
            while True:
                line = self.serial_conn.readline().decode("utf-8", errors='replace').strip()
                if not line:
                    continue
                    
                # Check if this is a status line (single digit: 0 or 1)
                if line == "0":
                    return None, None
                elif line == "1":
                    # Status 1 means data follows, but we may have already started reading it
                    continue
                else:
                    # Try to parse as data (PWM and Speed)
                    try:
                        parts = line.split()
                        if len(parts) == 2:
                            pwm, speed = map(float, parts)
                            data_pwm.append(pwm)
                            data_speed.append(speed)
                            break  # Successfully read first data line
                    except ValueError:
                        # Not a valid data line, skip it
                        continue
            
            # Now read remaining data lines
            while True:
                line = self.serial_conn.readline().decode("utf-8", errors='replace').strip()
                if not line:
                    continue
                    
                # Check if we've reached end of data (status code or command text)
                if line == "0" or line == "1" or "command" in line.lower() or "available" in line.lower():
                    break
                    
                try:
                    parts = line.split()
                    if len(parts) == 2:
                        pwm, speed = map(float, parts)
                        data_pwm.append(pwm)
                        data_speed.append(speed)
                except ValueError:
                    # Skip invalid lines
                    continue
                    
        except Exception as e:
            print(f"Error reading motor characteristic: {e}")
        return data_pwm, data_speed

    def on_hover(self, point, state):
        """Show tooltip when hovering points"""
        if state:
            self.tooltip.setText(f"PWM: {point.x():.1f} Speed: {point.y():.1f}")
            self.tooltip.adjustSize()

            # Position tooltip near mouse (top left instead of top right)
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView.mapFromGlobal(cursor_pos)
            self.tooltip.move(widget_pos.x() - self.tooltip.width() - 10, widget_pos.y() - 20)
            self.tooltip.show()
        else:
            self.tooltip.hide()

    def newGraphClicked(self):
        if self.serial_conn and self.serial_conn.is_open:
            # Tell ESP32 to start logging
            self.serial_conn.write(b"1")

            # Show modal progress bar
            self.progressDialog = ProgressBar(self)
            self.progressDialog.setModal(True)
            self.progressDialog.show()

            # Start a timer to poll serial port
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(self.readProgress)
            self.timer.start(100)  # check every 100 ms
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No serial port is open.")

    def readProgress(self):
        try:
            if self.serial_conn.in_waiting:
                line = self.serial_conn.readline().decode("utf-8").strip()
                if not line:
                    return

                try:
                    progress = float(line)
                    #print(f"Progress: {progress}%")
                    self.progressDialog.progressBar.setValue(int(progress))
                    self.progressDialog.progressBar.setFormat(f"{progress:.2f}%") 
                    
                    # if finished
                    if progress >= 100.0:
                        self.timer.stop()
                        self.progressDialog.progressBar.setValue(100)
                        self.progressDialog.progressBar.setFormat("100%")
                        self.timer.stop()
                    
                        # Delay 1 second before closing
                        QtCore.QTimer.singleShot(1000, lambda: (
                            self.try_read_motor_char(),  # Refresh graph
                            self.progressDialog.accept(),
                        ))
                except ValueError:
                    # ignore garbage/extra lines
                    pass

        except Exception as e:
            print("Serial error:", e)

    def popupClicked(self):
        if hasattr(self, 'pwm') and hasattr(self, 'speed') and self.pwm and self.speed:
            plt.figure(figsize=(10, 6))
            plt.plot(self.pwm, self.speed, 'o-', color='blue', linewidth=2)
            plt.grid(True)
            plt.xlabel('PWM Value')
            plt.ylabel('Speed (RPM)')
            plt.title('Motor Characteristic Curve')
            plt.tight_layout()
            plt.show(block=False)  # Non-blocking show - window persists when LogWindow closes
        else:
            QtWidgets.QMessageBox.information(self, "Log", "No data available to plot.")

    def closeEvent(self, event):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(b"4")
                self.serial_conn.flush()
                self.clear_serial_buffers()
                
                # Refresh main window after a short delay to let ESP update
                if self.main_window:
                    QtCore.QTimer.singleShot(200, self.main_window.try_read_motor_info)

        except Exception:
            pass
        event.accept()

    def clear_serial_buffers(self):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()
        except Exception as e:
            print("Serial buffer clear error:", e)

class LRC(QtWidgets.QMainWindow):
    def __init__(self, serial_conn, main_window=None):
        super().__init__(main_window)
        uic.loadUi(resource_path("ui_910/lrc.ui"), self)
        self.setWindowTitle("Linear Region Limit")
        self.setWindowIcon(QtGui.QIcon(resource_path("../../public/Logo Merah.png")))

        self.serial_conn = serial_conn
        self.main_window = main_window  # Store reference to main window

        #read existing linear info
        QtCore.QTimer.singleShot(200, self.readLinearInfo)  # wait 200 ms then read

        # Connect buttons
        self.done.clicked.connect(self.doneClicked)

    def readLinearInfo(self, retry_count=0):
        if retry_count >= 10:  # Limit retries to avoid infinite loop
            QtWidgets.QMessageBox.information(self, "Info", "No linear region data found.")
            return

        if self.serial_conn and self.serial_conn.in_waiting > 0:
            # Read the first line (status code: 0 or 1)
            while True:
                status_line = self.serial_conn.readline().decode().strip()
                if not status_line:
                    return
                try:
                    status = int(status_line)
                    break  # Got a valid status, exit loop
                except ValueError:
                    continue  # Not a number, skip this line

            if status == 1:
                # Both calibration + motor char exist
                data_line = self.serial_conn.readline().decode().strip()
                minLinPWM, maxLinPWM, minLinRPM, maxLinRPM = data_line.split()
                self.minLinDisp.setText(f"{minLinPWM}")
                self.maxLinDisp.setText(f"{maxLinPWM}")
                self.MinRPMDisp.setText(f"{float(minLinRPM):.2f}")
                self.MaxRPMDisp.setText(f"{float(maxLinRPM):.2f}")

            elif status == 0:
                # Nothing stored
                self.minLinDisp.setText("--")
                self.maxLinDisp.setText("--")
                self.MinRPMDisp.setText("--")
                self.MaxRPMDisp.setText("--")

            elif status == 2:
                # No data yet, resend request and try again
                self.serial_conn.write(b"2")
                QtCore.QTimer.singleShot(200, lambda: self.readLinearInfo(retry_count + 1))
        else:
            # No data yet, resend request and try again
            self.serial_conn.write(b"2")
            QtCore.QTimer.singleShot(200, lambda: self.readLinearInfo(retry_count + 1))

    def safe_write(self, data):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(data)
            else:
                QtWidgets.QMessageBox.critical(self, "Serial Error", "Serial connection lost.")
                self.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Serial Error", f"Serial error: {e}")
            self.close()

    def doneClicked(self):
        try:
            valueMin = int(self.minLinPWM.text())
            valueMax = int(self.maxLinPWM.text())
            valueRPMMin = float(self.minLinRPM.text())
            valueRPMMax = float(self.maxLinRPM.text())
            # Check for negative values
            if valueMin < 0 or valueMax < 0 or valueRPMMin < 0.0 or valueRPMMax < 0.0:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Negative values are not allowed.")
                return
            # Check if min > max
            if valueMin >= valueMax:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Minimum PWM must be less than maximum PWM.")
                return

            if valueRPMMin >= valueRPMMax:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Minimum RPM must be less than maximum RPM.")
                return
            self.safe_write(f"3 {valueMin} {valueMax} {valueRPMMin} {valueRPMMax}".encode())  # Save LRC
            self.serial_conn.flush()
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            self.readLinearInfo()  # Refresh display
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Serial Error", f"Serial error: {e}")
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers.")

    def closeEvent(self, event):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(b"4")
                self.serial_conn.flush()
                self.clear_serial_buffers()

                # Refresh main window after a short delay to let ESP update
                if self.main_window:
                    QtCore.QTimer.singleShot(200, self.main_window.try_read_motor_info)

        except Exception:
            pass
        event.accept()

    def clear_serial_buffers(self):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()
        except Exception as e:
            print("Serial buffer clear error:", e)

class olc(QtWidgets.QMainWindow):
    def __init__(self, serial_conn, main_window=None):
        super().__init__(main_window)
        uic.loadUi(resource_path("ui_910/olc.ui"), self)
        self.setWindowTitle("DC Motor Open Loop Control")
        self.setWindowIcon(QtGui.QIcon(resource_path("../../public/Logo Merah.png")))

        self.serial_conn = serial_conn
        self.main_window = main_window  # Store reference to main window
        QtCore.QTimer.singleShot(200, self.try_read_motor_characteristic)  # wait 200 ms then read

        # Connect buttons
        self.start.clicked.connect(self.startClicked)
        self.analyze.clicked.connect(self.analyzeClicked)
        self.popup.clicked.connect(self.popupClicked)
        self.fopdt.clicked.connect(self.fopdtClicked)
        self.popup_2.clicked.connect(self.popup2Clicked)

        # Create real-time chart for transient response
        self.chart = QtChart.QChart()
        self.speedSeries = QtChart.QLineSeries()  # Actual speed
        self.targetSeries = QtChart.QLineSeries()  # Target speed
        self.fopdtSeries = QtChart.QLineSeries()  # FOPDT model

        self.speedSeries.setPointsVisible(True)  # Show actual data points

        # Add series to chart
        self.chart.addSeries(self.speedSeries)
        self.chart.addSeries(self.targetSeries)
        self.chart.addSeries(self.fopdtSeries)
        self.speedSeries.setColor(QtGui.QColor("blue"))
        self.targetSeries.setColor(QtGui.QColor("red"))
        self.fopdtSeries.setColor(QtGui.QColor("green"))

        #self.speedSeries.setUseOpenGL(True)  # Enable OpenGL for better performance
        #self.targetSeries.setUseOpenGL(True)  # Enable OpenGL for better performance
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(QtCore.Qt.AlignTop)
        self.chart.legend().setFont(QtGui.QFont("Arial", 10))
        self.speedSeries.setName("Speed (RPM)")
        self.targetSeries.setName("Target (RPM)")
        self.fopdtSeries.setName("FOPDT Model")
        
        # Create axes
        self.chart.createDefaultAxes()
        self.chart.axisX().setTitleText("Time (ms)")
        self.chart.axisY().setTitleText("Speed (RPM)")
        self.chart.setTitle("Motor Transient Response")

        # Setup chart view
        self.chartView = QtChart.QChartView(self.chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)
        
        # Add chartView into olcgraph 
        layout = self.olcgraph.layout()
        if not layout:
            layout = QtWidgets.QGridLayout(self.olcgraph)
        layout.addWidget(self.chartView, 0, 0, 2, 1)  # row=0, col=0, rowspan=2, colspan=1

        # Enable hover events for tooltips
        self.speedSeries.hovered.connect(self.on_hover)
        self.targetSeries.hovered.connect(self.on_hover)

        # Tooltip label
        self.tooltip = QtWidgets.QLabel(self.chartView)
        self.tooltip.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip.hide()

        #Add a second graph
        self.chart2 = QtChart.QChart()
        self.controllerSeries = QtChart.QLineSeries()  # Controller output series
        self.errorSeries = QtChart.QLineSeries()  # Error series
        self.controllerSeries.setPointsVisible(True)  # Show actual data points
        self.errorSeries.setPointsVisible(True)  # Show actual data points
        self.chart2.addSeries(self.controllerSeries)
        self.chart2.addSeries(self.errorSeries)
        self.controllerSeries.setColor(QtGui.QColor("green"))
        self.errorSeries.setColor(QtGui.QColor("red"))
        self.chart2.legend().setVisible(True)
        self.chart2.legend().setAlignment(QtCore.Qt.AlignTop)
        self.chart2.legend().setFont(QtGui.QFont("Arial", 10))
        self.controllerSeries.setName("Controller Output (PWM)")
        self.errorSeries.setName("Error (RPM)")

        # Create axes
        self.chart2.createDefaultAxes()
        self.chart2.axisX().setTitleText("Time (ms)")
        self.chart2.axisY().setTitleText("Controller Output (PWM)")
        self.chart2.setTitle("Controller Output Over Time")
        # Setup chart view
        self.chartView2 = QtChart.QChartView(self.chart2)
        self.chartView2.setRenderHint(QtGui.QPainter.Antialiasing)
        # Add chartView2 into controllergraph
        layout2 = self.controlgraph.layout()
        if not layout2:
            layout2 = QtWidgets.QGridLayout(self.controlgraph)
        layout2.addWidget(self.chartView2, 0, 0, 2, 1)  # row=0, col=0, rowspan=2, colspan=1
        # Enable hover events for tooltips
        self.controllerSeries.hovered.connect(self.on_hover2)
        # Tooltip label for second chart
        self.tooltip2 = QtWidgets.QLabel(self.chartView2)
        self.tooltip2.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip2.hide()

        # Add Ctrl+S shortcut
        self.save_action = QtWidgets.QAction("Save Data", self)
        self.save_action.setShortcut(QtGui.QKeySequence.Save)  # Ctrl+S
        self.save_action.triggered.connect(self.saveDataToCSV)
        self.addAction(self.save_action)

    def saveDataToCSV(self):
        """Save collected data to CSV file - only if all data series are available"""
        # Check if we have ALL required data series
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
                self, 
                "Incomplete Data", 
                f"Cannot save data. Missing or empty data series:\n" + 
                "\n".join([f"• {data.replace('_', ' ').title()}" for data in missing_data]) +
                "\n\nPlease run a complete test first to collect all data."
            )
            return
        
        # Verify all data series have the same length
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
                self, 
                "Data Length Mismatch", 
                f"Data series have different lengths:\n" + 
                "\n".join([f"• {name}: {length} points" for name, length in data_lengths.items()]) +
                "\n\nCannot save inconsistent data."
            )
            return
        
        # Open file save dialog
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save OLC Data",
            f"olc_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Create DataFrame with all required data
            data_dict = {
                'Time_ms': self.time_data,
                'Target_Speed_RPM': self.target_data,
                'Actual_Speed_RPM': self.rpm_data,
                'Error_RPM': self.error_data,
                'Controller_Output_PWM': self.controller_data,
                'FOPDT_Model_RPM': self.fopdt_output
            }
            
            # Create DataFrame
            df = pd.DataFrame(data_dict)
            
            # Add metadata as comments (pandas will ignore these)
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                # Write metadata header
                f.write(f"# OLC Data Export\n")
                f.write(f"# Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Target RPM: {self.target_data[-1] if self.target_data else 'N/A'}\n")
                f.write(f"# Final Speed: {self.rpm_data[-1]:.2f} RPM\n")
                f.write(f"# Data Points: {len(self.time_data)}\n")
                f.write(f"# Duration: {max(self.time_data) - min(self.time_data):.0f} ms\n")
                f.write("#\n")  # Separator line
                
                # Write the actual CSV data
                df.to_csv(f, index=False)
            
            QtWidgets.QMessageBox.information(
                self, 
                "Save Successful", 
                f"Data saved successfully to:\n{file_path}\n\n"
                f"Summary:\n"
                f"• Records saved: {len(self.time_data)}\n"
                f"• Target RPM: {self.target_data[-1]:.1f}\n"
                f"• Final Speed: {self.rpm_data[-1]:.1f} RPM\n"
                f"• Test Duration: {max(self.time_data) - min(self.time_data):.0f} ms"
            )
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                "Save Error", 
                f"Error saving data to CSV:\n{str(e)}"
            )
    
    def fopdtClicked(self):
        if not hasattr(self, 'time_data') or not hasattr(self, 'rpm_data'):
            return

        if not self.k_fopdt.text().strip() or not self.tau_fopdt.text().strip() or not self.targetRPM.text().strip() or not self.l_fopdt.text().strip():
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a value for K, Tau, and L.")
            return

        try:
            K_fopdt = float(self.k_fopdt.text())
            tau_fopdt = float(self.tau_fopdt.text())
            l_fopdt = float(self.l_fopdt.text())
            target_rpm = float(self.targetRPM.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for K and Tau.")
            return

        if K_fopdt <= 0 or tau_fopdt <= 0 or l_fopdt < 0:  # L can be zero, but not negative
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "K and Tau must be positive, L must be non-negative.")
            return

        self.fopdtSeries.clear()
        
        #Transfer function
        G_first = ctrl.TransferFunction([K_fopdt], [tau_fopdt, 1])
        # Pade approximation for the delay: choose order n (higher => better approximation, but higher order)
        pade_order = 2
        num_delay, den_delay = ctrl.pade(l_fopdt, pade_order)
        Delay_pade = ctrl.tf(num_delay, den_delay)
        G = ctrl.series(G_first, Delay_pade)

        # Get the time vector for the step response
        real_time = np.array(self.time_data) / 1000.0  # Convert ms to seconds
        #print(real_time)
        
        #Step response
        
        # Calculate input PWM value for the model
        input_pwm = self.controller_data[-1] if hasattr(self, 'controller_data') and self.controller_data else 0

        t,y = ctrl.step_response(G, T=real_time)
        # Define delay (1 second)
        delay = 1.0  # seconds

        # Find how many samples correspond to the delay
        dt = t[1] - t[0]  # time step
        n_delay = int(delay / dt)

        # Create delayed response with same length
        y_delayed = np.zeros_like(y)

        if n_delay < len(y):
            y_delayed[n_delay:] = y[:-n_delay]  # shift right and cut the tail

        t_delayed = t  # time vector remains the same
        # Now scale by input PWM
        self.fopdt_output = y_delayed * input_pwm

        # Append to your data series (convert seconds → ms)
        for i in range(len(t_delayed)):
            self.fopdtSeries.append(t_delayed[i] * 1000, y_delayed[i] * input_pwm)        
        

    def on_hover(self, point, state):
        """Show tooltip when hovering points"""
        if state:
            # Find the closest data point in our dataset
            if hasattr(self, 'time_data') and hasattr(self, 'rpm_data'):
                # Get the x-coordinate from the hovered point
                hover_time = point.x()
                
                # Find the closest time in our actual data
                closest_index = 0
                min_distance = float('inf')
                
                for i, time_val in enumerate(self.time_data):
                    distance = abs(time_val - hover_time)
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
                
                # Get the actual values from our dataset
                actual_time = self.time_data[closest_index]
                actual_speed = self.rpm_data[closest_index]
                
                # Use actual data values in tooltip
                self.tooltip.setText(f"Time: {actual_time} ms\nSpeed: {actual_speed:.1f} RPM")
            else:
                # Fallback to chart coordinates if data not available
                self.tooltip.setText(f"Time: {point.x():.1f} ms\nSpeed: {point.y():.1f} RPM")

            self.tooltip.adjustSize()

            # Position tooltip near mouse (top left instead of top right)
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView.mapFromGlobal(cursor_pos)
            self.tooltip.move(widget_pos.x() - self.tooltip.width() - 10, widget_pos.y() - 20)
            self.tooltip.show()
        else:
            self.tooltip.hide()

    def on_hover2(self, point, state):
        """Show tooltip when hovering points in second chart"""
        if state:
            # Find the closest data point in our dataset
            if hasattr(self, 'time_data') and hasattr(self, 'controller_data') and hasattr(self, 'error_data'):
                # Get the x-coordinate from the hovered point
                hover_time = point.x()
                
                # Find the closest time in our actual data
                closest_index = 0
                min_distance = float('inf')
                
                for i, time_val in enumerate(self.time_data):
                    distance = abs(time_val - hover_time)
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
                
                # Get the actual values from our dataset
                actual_time = self.time_data[closest_index]
                actual_pwm = self.controller_data[closest_index]
                actual_error = self.error_data[closest_index]
                
                # Use actual data values in tooltip
                self.tooltip2.setText(f"Time: {actual_time:.1f} ms\nPWM: {actual_pwm:.1f}\nError: {actual_error:.1f}")
            else:
                # Fallback to chart coordinates if data not available
                self.tooltip2.setText(f"Time: {point.x():.1f} ms\nPWM: {point.y():.1f}")
            
            self.tooltip2.adjustSize()

            # Position tooltip near mouse (top left instead of top right)
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView2.mapFromGlobal(cursor_pos)
            self.tooltip2.move(widget_pos.x() - self.tooltip2.width() - 10, widget_pos.y() - 20)
            self.tooltip2.show()
        else:
            self.tooltip2.hide()

    def try_read_motor_characteristic(self, retry_count=0):
        if retry_count >= 10:
            QtWidgets.QMessageBox.warning(self, "Error", "Failed to read motor data.")
            return
        
        # Clear stale data first
        self.clear_serial_buffers()
        
        try:
            # Send command to ESP32 asking for motor info
            # (assuming '2' gets info based on your ESP32 code)
            self.safe_write(b"2")
            self.serial_conn.flush()
            
            # Now wait a moment and read the response
            QtCore.QTimer.singleShot(100, self.readMotorData)
        except Exception as e:
            print(f"Error sending command: {e}")
            QtCore.QTimer.singleShot(200, lambda: self.try_read_motor_characteristic(retry_count + 1))

    def readMotorData(self):
        try:
            if not self.serial_conn or not self.serial_conn.in_waiting:
                return

            # Read the first line (status code: 0, 1, or 2)
            while True:
                status_line = self.serial_conn.readline().decode().strip()
                if not status_line:
                    return
                try:
                    status = int(status_line)
                    break  # Got a valid status, exit loop
                except ValueError:
                    continue  # Not a number, skip this line

            if status == 2:
                # Both calibration + motor char exist
                data_line = self.serial_conn.readline().decode().strip()
                min_rpm_str, max_rpm_str, max_rpm_val_str = data_line.split()
                
                # Convert to float when storing
                self.minLinRPM = float(min_rpm_str)
                self.maxLinRPM = float(max_rpm_str)
                self.maxRPM = float(max_rpm_val_str)
                
                # Display values
                self.MinLinRPMDisp.setText(f"{self.minLinRPM:.2f}")
                self.MaxLinRPMDisp.setText(f"{self.maxLinRPM:.2f}")
                self.MaxRPMDisp.setText(f"{self.maxRPM:.2f}")

            elif status == 1:
                # Only calibration exists
                data_line = self.serial_conn.readline().decode().strip()
                self.maxRPM = float(data_line)
                self.MinLinRPMDisp.setText("--")
                self.MaxLinRPMDisp.setText("--")
                self.MaxRPMDisp.setText(f"{float(self.maxRPM):.2f}")

            elif status == 0:
                # Nothing stored
                self.MinLinRPMDisp.setText("--")
                self.MaxLinRPMDisp.setText("--")
                self.MaxRPMDisp.setText("--")
        except Exception as e:
            print("Serial read error olc:", e)
            print(self.serial_conn.readline())

    def startClicked(self):
        if self.serial_conn and self.serial_conn.is_open:
            # Check if field is empty
            if not self.targetRPM.text().strip():
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Target RPM field cannot be empty.")
                return
            
            try:
                targetRPM = float(self.targetRPM.text())
            except ValueError:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for Target RPM.")
                return

            # Validate input
            if targetRPM <= 0:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Target RPM must be positive.")
                return
            # Check if target RPM is within valid ranges
            try:
                # Check which data is available
                print(f"MinLinRPM: {self.minLinRPM}, MaxLinRPM: {self.maxLinRPM}, MaxRPM: {self.maxRPM}")
                has_linear_range = hasattr(self, 'minLinRPM') and hasattr(self, 'maxLinRPM')
                has_max_rpm = hasattr(self, 'maxRPM')
                
                if has_linear_range and has_max_rpm:
                    # Both linear range and max RPM are available
                    min_lin_rpm = float(self.minLinRPM)
                    max_lin_rpm = float(self.maxLinRPM)
                    max_rpm = float(self.maxRPM)
                    
                    # Check if target is between min and max linear RPM OR equals max RPM
                    is_in_linear_range = min_lin_rpm <= targetRPM <= max_lin_rpm
                    is_at_max = abs(targetRPM - max_rpm) < 0.01  # Small epsilon for float comparison
                    
                    if not (is_in_linear_range or is_at_max):
                        QtWidgets.QMessageBox.warning(
                            self, 
                            "Invalid Input", 
                            f"Target RPM must be either between {min_lin_rpm:.2f} and {max_lin_rpm:.2f}, or equal to {max_rpm:.2f}."
                        )
                        return
                    
                elif has_max_rpm:
                    # Only max RPM is available
                    max_rpm = float(self.maxRPM)
                    
                    if targetRPM > max_rpm:
                        QtWidgets.QMessageBox.warning(
                            self, 
                            "Invalid Input", 
                            f"Target RPM cannot exceed maximum RPM ({max_rpm:.2f})."
                        )
                        return
                    
                else:
                    # No motor data available
                    QtWidgets.QMessageBox.warning(
                        self, 
                        "Missing Data", 
                        "Motor characterization data not available. Run analysis first."
                    )
                    return
            except (ValueError, AttributeError):
                # Handle case where values aren't set yet or are invalid
                QtWidgets.QMessageBox.warning(
                    self, 
                    "Missing Data", 
                    "Motor characterization file not available. Run analysis first."
                )
                return
                
            # If we get here, targetRPM is valid, send it to ESP32
            self.readTransientResponse(targetRPM)
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No serial port is open.")

    def safe_write(self, data):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(data)
            else:
                QtWidgets.QMessageBox.critical(self, "Serial Error", "Serial connection lost.")
                self.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Serial Error", f"Serial error: {e}")
            self.close()

    def readTransientResponse(self, targetRPM):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.reset_input_buffer()

            #Prepare arrays
            self.time_data = []
            self.rpm_data = []
            self.target_data = []
            self.controller_data = []
            self.error_data = []

            self.speedSeries.clear()
            self.targetSeries.clear()
            self.controllerSeries.clear()
            self.errorSeries.clear()

            self.safe_write(f"1 {targetRPM}".encode())
            self.serial_conn.flush()

            # Start timer to poll for data
            self.responseTimer = QtCore.QTimer(self)
            self.responseTimer.timeout.connect(self.updateTransientPlot)
            self.responseTimer.start(10)  # Poll every 10ms for fast updates

    def updateTransientPlot(self):
        try:
            if not self.serial_conn or not self.serial_conn.is_open:
                self.responseTimer.stop()
                return
                
            if self.serial_conn.in_waiting > 0:
                line = self.serial_conn.readline().decode("utf-8").strip()
                
                # Check if data collection is complete
                if line == "DONE":
                    self.responseTimer.stop()
                    return

                 # Skip the header line
                if line == "time_ms,rpm,targetrpm,pwm,error":
                    print("Received header, starting data collection...")
                    return
                    
                try:
                    # Parse the CSV format: timestamp,actual_speed,target_speed
                    parts = line.split(',')
                    if len(parts) == 5:
                        timestamp = int(parts[0])  # milliseconds
                        actual_speed = float(parts[1])
                        target_speed = float(parts[2])
                        controller_output = float(parts[3])  # PWM value
                        error = float(parts[4])
                        
                        # Store data
                        self.time_data.append(timestamp)
                        self.rpm_data.append(actual_speed)
                        self.target_data.append(target_speed)
                        self.controller_data.append(controller_output)
                        self.error_data.append(error)
                        
                        # Add to chart series
                        self.speedSeries.append(timestamp, actual_speed)
                        self.targetSeries.append(timestamp, target_speed)
                        self.controllerSeries.append(timestamp, controller_output)
                        self.errorSeries.append(timestamp, error)
                        
                        # Update chart axes to fit data
                        self.chart.axisX().setRange(0, max(self.time_data) + 100)
                        self.chart2.axisX().setRange(0, max(self.time_data) + 100)
                        
                        # Calculate y-axis range to fit data with some margin
                        max_y = max(max(self.rpm_data, default=0), target_speed) * 1.1
                        min_y = min(self.rpm_data, default=-1) * 1.1
                        self.chart.axisY().setRange(min_y, max_y)

                        max_y2 = max(max(self.controller_data, default=0), max(self.error_data, default=0)) * 1.1
                        min_y2 = min(min(self.controller_data, default=-1), min(self.error_data, default=-1)) * 1.1
                        self.chart2.axisY().setRange(min_y2, max_y2)
                        
                except (ValueError, IndexError) as e:
                    print(f"Error parsing data: {e}")
                    # Skip invalid lines
                    pass
                    
        except Exception as e:
            print(f"Error in updateTransientPlot: {e}")
            self.responseTimer.stop()

    def popupClicked(self):
        if hasattr(self, 'time_data') and hasattr(self, 'rpm_data') and hasattr(self, 'target_data') and self.time_data:
            # Create figure with side-by-side layout
            fig = plt.figure(figsize=(15, 6))
            gs = fig.add_gridspec(1, 2, width_ratios=[2.5, 1])  # Plot gets 2.5x more space than text
            
            ax1 = fig.add_subplot(gs[0])  # Plot area
            ax2 = fig.add_subplot(gs[1])  # Text area
            ax2.axis('off')
            
            # Left plot - Step Response
            ax1.plot(self.time_data, self.rpm_data, '-', color='blue', linewidth=2, label='Actual Speed')
            ax1.plot(self.time_data, self.target_data, 'r--', linewidth=2, label='Target Speed')
            
            # Add FOPDT model if available
            # FIXED: Proper check for FOPDT model data
            if hasattr(self, 'fopdt_output') and self.fopdt_output is not None and len(self.fopdt_output) > 0:
                ax1.plot(self.time_data, self.fopdt_output, 'g-.', linewidth=2, label='FOPDT Model')
            
            # Add reference lines
            final_value = self.rpm_data[-1] if self.rpm_data else 0
            if final_value > 0:
                ax1.axhline(y=final_value, color='gray', linestyle=':', alpha=0.7)
                ax1.axhline(y=final_value * 0.632, color='green', linestyle=':', alpha=0.5)
                
                # Add annotations for final value
                ax1.text(max(self.time_data) * 0.1, final_value + final_value * 0.05, 
                        f"Final: {final_value:.1f} RPM", fontsize=9,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))
            
            ax1.grid(True, alpha=0.3)
            ax1.set_title("Motor Step Response Analysis", fontsize=14, fontweight='bold')
            ax1.set_xlabel("Time (ms)", fontsize=12)
            ax1.set_ylabel("Speed (RPM)", fontsize=12)
            ax1.legend()
            
            # Right panel - Analysis Text (same style as your training history)
            ax2.axis('off')
            
            # Get current analysis values from UI
            rise_time_text = self.Tr.text().replace(" ms", "") if self.Tr.text() != "--" else "N/A"
            t28_text = self.t28.text().replace(" ms", "") if self.t28.text() != "--" else "N/A"
            t63_text = self.t63.text().replace(" ms", "") if self.t63.text() != "--" else "N/A"
            settling_time_text = self.Ts.text().replace(" ms", "") if self.Ts.text() != "--" else "N/A"
            fv_text = self.fv.text().replace(" RPM", "") if self.fv.text() != "--" else "N/A"
            tau_text = self.tau.text().replace(" ms", "") if self.tau.text() != "--" else "N/A"
            
            # Get FOPDT parameters from input fields
            try:
                K_fopdt_text = self.k_fopdt.text() if self.k_fopdt.text().strip() else "N/A"
                tau_fopdt_text = self.tau_fopdt.text() if self.tau_fopdt.text().strip() else "N/A"
                l_fopdt_text = self.l_fopdt.text() if self.l_fopdt.text().strip() else "N/A"
            except:
                K_fopdt_text = "N/A"
                tau_fopdt_text = "N/A"
                l_fopdt_text = "N/A"
            
            # Get target RPM
            target_rpm = self.targetRPM.text() if self.targetRPM.text().strip() else "N/A"
            
            # Create formatted analysis text using the same style
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
                f"{'K (RPM/PWM)'.ljust(20)}{str(K_fopdt_text).rjust(15)}\n"
                f"{'τ (seconds)'.ljust(20)}{str(tau_fopdt_text).rjust(15)}\n"
                f"{'L (seconds)'.ljust(20)}{str(l_fopdt_text).rjust(15)}\n"
                f"\n"
            )
            
            # Add text to right panel with same formatting as your example
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

    def popupClicked(self):
        if hasattr(self, 'time_data') and hasattr(self, 'rpm_data') and hasattr(self, 'target_data') and self.time_data:
            # Create figure with side-by-side layout
            fig = plt.figure(figsize=(15, 6))
            gs = fig.add_gridspec(1, 2, width_ratios=[2.5, 1])  # Plot gets 2.5x more space than text
            
            ax1 = fig.add_subplot(gs[0])  # Plot area
            ax2 = fig.add_subplot(gs[1])  # Text area
            ax2.axis('off')
            
            # Left plot - Step Response
            ax1.plot(self.time_data, self.rpm_data, '-', color='blue', linewidth=2, label='Actual Speed')
            ax1.plot(self.time_data, self.target_data, 'r--', linewidth=2, label='Target Speed')
            
            # Add FOPDT model if available
            # FIXED: Proper check for FOPDT model data
            if hasattr(self, 'fopdt_output') and self.fopdt_output is not None and len(self.fopdt_output) > 0:
                ax1.plot(self.time_data, self.fopdt_output, 'g-.', linewidth=2, label='FOPDT Model')
            
            # Add reference lines
            final_value = self.rpm_data[-1] if self.rpm_data else 0
            if final_value > 0:
                ax1.axhline(y=final_value, color='gray', linestyle=':', alpha=0.7)
                ax1.axhline(y=final_value * 0.632, color='green', linestyle=':', alpha=0.5)
                
                # Add annotations for final value
                ax1.text(max(self.time_data) * 0.1, final_value + final_value * 0.05, 
                        f"Final: {final_value:.1f} RPM", fontsize=9,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.8))
            
            ax1.grid(True, alpha=0.3)
            ax1.set_title("Motor Step Response Analysis", fontsize=14, fontweight='bold')
            ax1.set_xlabel("Time (ms)", fontsize=12)
            ax1.set_ylabel("Speed (RPM)", fontsize=12)
            ax1.legend()
            
            # Right panel - Analysis Text (same style as your training history)
            ax2.axis('off')
            
            # Get current analysis values from UI
            rise_time_text = self.Tr.text().replace(" ms", "") if self.Tr.text() != "--" else "N/A"
            t28_text = self.t28.text().replace(" ms", "") if self.t28.text() != "--" else "N/A"
            t63_text = self.t63.text().replace(" ms", "") if self.t63.text() != "--" else "N/A"
            settling_time_text = self.Ts.text().replace(" ms", "") if self.Ts.text() != "--" else "N/A"
            fv_text = self.fv.text().replace(" RPM", "") if self.fv.text() != "--" else "N/A"
            tau_text = self.tau.text().replace(" ms", "") if self.tau.text() != "--" else "N/A"
            
            # Get FOPDT parameters from input fields
            try:
                K_fopdt_text = self.k_fopdt.text() if self.k_fopdt.text().strip() else "N/A"
                tau_fopdt_text = self.tau_fopdt.text() if self.tau_fopdt.text().strip() else "N/A"
                l_fopdt_text = self.l_fopdt.text() if self.l_fopdt.text().strip() else "N/A"
            except:
                K_fopdt_text = "N/A"
                tau_fopdt_text = "N/A"
                l_fopdt_text = "N/A"
            
            # Get target RPM
            target_rpm = self.targetRPM.text() if self.targetRPM.text().strip() else "N/A"
            
            # Create formatted analysis text using the same style
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
                f"{'K (RPM/PWM)'.ljust(20)}{str(K_fopdt_text).rjust(15)}\n"
                f"{'τ (seconds)'.ljust(20)}{str(tau_fopdt_text).rjust(15)}\n"
                f"{'L (seconds)'.ljust(20)}{str(l_fopdt_text).rjust(15)}\n"
                f"\n"
            )
            
            # Add text to right panel with same formatting as your example
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

    def analyzeClicked(self):
        if not hasattr(self, 'time_data') or not hasattr(self, 'rpm_data'):
            return
            
        target = self.target_data[-1] if self.target_data else 0
        max_speed = max(self.rpm_data)
        
        # Find rise time (10% to 90% of target)
        for i, target in enumerate(self.target_data):
            if target != 0:
                start_time = self.time_data[i]
                break
        else:
            start_time = 0

        #Calculate final value
        fv = self.rpm_data[-1]

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

        #Try calculating for dead time
        #Try calculating for dead time
        gradient_at_tau = None
        dead_time = None
        if t_63_2:
            # Find index closest to t_63_2 in time_data
            t_63_2_index = None
            for i, t in enumerate(self.time_data):
                if t >= t_63_2 + start_time:
                    t_63_2_index = i
                    break
            
            if t_63_2_index is not None and t_63_2_index > 0 and t_63_2_index < len(self.time_data) - 1:
                # Use centered finite difference to calculate gradient
                dt_before = self.time_data[t_63_2_index] - self.time_data[t_63_2_index - 1]
                dt_after = self.time_data[t_63_2_index + 1] - self.time_data[t_63_2_index]
                
                drpm_before = self.rpm_data[t_63_2_index] - self.rpm_data[t_63_2_index - 1]
                drpm_after = self.rpm_data[t_63_2_index + 1] - self.rpm_data[t_63_2_index]
                
                # Average the before and after gradients
                gradient_at_tau = ((drpm_before / dt_before) + (drpm_after / dt_after)) / 2.0
                
                # Calculate dead time using the tangent method
                if gradient_at_tau > 0:
                    # Calculate the y-intercept of the tangent line
                    y_intercept = self.rpm_data[t_63_2_index] - gradient_at_tau * self.time_data[t_63_2_index]
                    
                    # Calculate time when tangent line crosses x-axis (y = 0)
                    dead_time = -y_intercept / gradient_at_tau - 1000
                    #print(f"Calculated dead time: {dead_time} ms")
                    # Update the dead time estimate
                    sampling_time_olc = 10  # ms

        #Find settling time 2% oscillation band
        settling_time = 0
        if rise_end:
            upper_bound = fv * 1.05
            lower_bound = fv * 0.95
            for i in range(len(self.rpm_data)-1, -1, -1):
                if not (lower_bound <= self.rpm_data[i] <= upper_bound):
                    settling_time = self.time_data[i+1] - start_time if (i+1) < len(self.time_data) else 0
                    break

        #Display values
        self.Tr.setText(f"{rise_time} ms" if rise_time else "--")
        self.t28.setText(f"{t_28_3} ms" if t_28_3 else "--")
        self.t63.setText(f"{t_63_2} ms" if t_63_2 else "--")
        self.Ts.setText(f"{settling_time} ms" if settling_time else "--")
        self.fv.setText(f"{fv:.2f} RPM" if fv else "--")
        self.tau.setText(f"{t_63_2:.2f} ms" if t_63_2 else "--")

        #Find FOPDT Parameters
        try:
            #sampling_time_olc = 10  # ms
            self.main_window.true_fopdt_K = fv / self.controller_data[-1] if self.controller_data and self.controller_data[-1] != 0 else 0
            self.main_window.true_fopdt_tau = 1.5 * (t_63_2 - t_28_3) / 1000.0  # convert to seconds
            self.main_window.true_fopdt_L = 0  # convert to seconds
            L_test = dead_time / 1000.0 if dead_time else self.main_window.true_fopdt_L
            #print(f"Calculated FOPDT Parameters: K={self.main_window.true_fopdt_K}, Tau={self.main_window.true_fopdt_tau}, L={self.main_window.true_fopdt_L}, L_test={L_test}, gradient_at_tau={gradient_at_tau}")
        except Exception as e:
            print(f"Error calculating FOPDT parameters: {e}")
            QtWidgets.QMessageBox.warning(self, "Calculation Error", f"Error calculating FOPDT parameters: {e}")
            return

        #Calculate Control Parameters
        #try:
            #Kp_PID = (1.2 * self.main_window.true_fopdt_tau) / (self.main_window.true_fopdt_K * self.main_window.true_fopdt_L) if self.main_window.true_fopdt_K != 0 and self.main_window.true_fopdt_L != 0 else 0
            #Ti_PID = 2 * self.main_window.true_fopdt_L if self.main_window.true_fopdt_L != 0 else 0
            #Td_PID = 0.5 * self.main_window.true_fopdt_L if self.main_window.true_fopdt_L != 0 else 0
            #Kp_PI = (0.9 * self.main_window.true_fopdt_tau) / (self.main_window.true_fopdt_K * self.main_window.true_fopdt_L) if self.main_window.true_fopdt_K != 0 and self.main_window.true_fopdt_L != 0 else 0
            #Ti_PI = self.main_window.true_fopdt_L / 0.3 if self.main_window.true_fopdt_L != 0 else 0
            #Kp_P = (self.main_window.true_fopdt_tau) / (self.main_window.true_fopdt_K * self.main_window.true_fopdt_L) if self.main_window.true_fopdt_K != 0 and self.main_window.true_fopdt_L != 0 else 0
        
            #print(f"Calculated Control Parameters: Kp_PID={Kp_PID}, Ti_PID={Ti_PID}, Td_PID={Td_PID}, Kp_PI={Kp_PI}, Ti_PI={Ti_PI}, Kp_P={Kp_P}")
        #except Exception as e:
            #print(f"Error calculating control parameters with {e} ")
            #QtWidgets.QMessageBox.warning(self, "Calculation Error", f"Error calculating control parameters: {e}")
            #return
        
        #try:
            #sampling_rate = 0.01  # s   
            #k1_PID = Kp_PID * (1 + sampling_rate / (2 * Ti_PID) + 2 * Td_PID / sampling_rate) if Ti_PID != 0 and Kp_PID != 0 else 0
            #k2_PID = Kp_PID * (-1 + sampling_rate / (2 * Ti_PID) - 4 * Td_PID / sampling_rate) if Ti_PID != 0 and Kp_PID != 0 else 0
            #k3_PID = Kp_PID * (2 * Td_PID / sampling_rate) if Td_PID != 0 and Kp_PID != 0 else 0
            #k1_PI = Kp_PI * (1 + sampling_rate / (2 * Ti_PI)) if Ti_PI != 0 and Kp_PI != 0 else 0
            #k2_PI = Kp_PI * (-1 + sampling_rate / (2 * Ti_PI)) if Ti_PI != 0 and Kp_PI != 0 else 0
            #k3_PI = 0
            #k1_P = Kp_P if Kp_P != 0 else 0
            #k2_P = 0
            #k3_P = 0
            #print(f"Discrete Control Gains: k1_PID={k1_PID}, k2_PID={k2_PID}, k3_PID={k3_PID}, k1_PI={k1_PI}, k2_PI={k2_PI}, k3_PI={k3_PI}, k1_P={k1_P}")
        #except Exception as e:
            #print(f"Error calculating discrete control gains: {e}")
            #QtWidgets.QMessageBox.warning(self, "Calculation Error", f"Error calculating discrete control gains: {e}")
            #return


    def closeEvent(self, event):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(b"4")
                self.serial_conn.flush()
                self.clear_serial_buffers()

        except Exception:
            pass
        event.accept()

    def clear_serial_buffers(self):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()
        except Exception as e:
            print("Serial buffer clear error:", e)

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

class clc(QtWidgets.QMainWindow):
    def __init__(self, serial_conn, main_window=None):
        super().__init__(main_window)
        uic.loadUi(resource_path("ui_910/clc.ui"), self)
        self.setWindowTitle("DC Motor Closed Loop Control")
        self.setWindowIcon(QtGui.QIcon("asset/Logo Control.png"))

        self.serial_conn = serial_conn
        self.main_window = main_window  # Store reference to main window

        # Connect buttons
        self.start.clicked.connect(self.startClicked)
        self.analyze.clicked.connect(self.analyzeClicked)
        self.popup.clicked.connect(self.popupClicked)
        self.popup_2.clicked.connect(self.popup2Clicked)

        # Create real-time chart for transient response
        self.chart = QtChart.QChart()
        self.speedSeries = QtChart.QLineSeries()  # Actual speed
        self.targetSeries = QtChart.QLineSeries()  # Target speed
        
        self.speedSeries.setPointsVisible(True)  # Show actual data points

        # Add series to chart
        self.chart.addSeries(self.speedSeries)
        self.chart.addSeries(self.targetSeries)
        self.speedSeries.setColor(QtGui.QColor("blue"))
        self.targetSeries.setColor(QtGui.QColor("red"))

        #self.speedSeries.setUseOpenGL(True)  # Enable OpenGL for better performance
        #self.targetSeries.setUseOpenGL(True)  # Enable OpenGL for better performance
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(QtCore.Qt.AlignTop)
        self.chart.legend().setFont(QtGui.QFont("Arial", 10))
        self.speedSeries.setName("Speed (RPM)")
        self.targetSeries.setName("Target (RPM)")
        
        # Create axes
        self.chart.createDefaultAxes()
        self.chart.axisX().setTitleText("Time (ms)")
        self.chart.axisY().setTitleText("Speed (RPM)")
        self.chart.setTitle("Motor Transient Response")

        # Setup chart view
        self.chartView = QtChart.QChartView(self.chart)
        self.chartView.setRenderHint(QtGui.QPainter.Antialiasing)

        # Add chartView into clcgraph
        layout = self.clcgraph.layout()
        if not layout:
            layout = QtWidgets.QGridLayout(self.clcgraph)
        layout.addWidget(self.chartView, 0, 0, 2, 1)  # row=0, col=0, rowspan=2, colspan=1

        # Enable hover events for tooltips
        self.speedSeries.hovered.connect(self.on_hover)
        self.targetSeries.hovered.connect(self.on_hover)

        # Tooltip label
        self.tooltip = QtWidgets.QLabel(self.chartView)
        self.tooltip.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip.hide()

        #Add a second graph
        self.chart2 = QtChart.QChart()
        self.controllerSeries = QtChart.QLineSeries()  # Controller output series
        self.rawControlSeries = QtChart.QLineSeries()  # Raw control output series
        self.errorSeries = QtChart.QLineSeries()  # Error series
        self.controllerSeries.setPointsVisible(True)  # Show actual data points
        self.rawControlSeries.setPointsVisible(True)  # Show actual data points
        self.errorSeries.setPointsVisible(True)  # Show actual data points
        self.chart2.addSeries(self.controllerSeries)
        self.chart2.addSeries(self.rawControlSeries)
        self.chart2.addSeries(self.errorSeries)
        self.controllerSeries.setColor(QtGui.QColor("green"))
        self.rawControlSeries.setColor(QtGui.QColor("orange"))
        self.errorSeries.setColor(QtGui.QColor("red"))
        self.chart2.legend().setVisible(True)
        self.chart2.legend().setAlignment(QtCore.Qt.AlignTop)
        self.chart2.legend().setFont(QtGui.QFont("Arial", 10))
        self.controllerSeries.setName("Controller Output (PWM)")
        self.rawControlSeries.setName("Raw Control Output (PWM)")
        self.errorSeries.setName("Error (RPM)")

        # Create axes
        self.chart2.createDefaultAxes()
        self.chart2.axisX().setTitleText("Time (ms)")
        self.chart2.axisY().setTitleText("Controller Output (PWM)")
        self.chart2.setTitle("Controller Output Over Time")
        # Setup chart view
        self.chartView2 = QtChart.QChartView(self.chart2)
        self.chartView2.setRenderHint(QtGui.QPainter.Antialiasing)
        # Add chartView2 into controllergraph
        layout2 = self.controlgraph.layout()
        if not layout2:
            layout2 = QtWidgets.QGridLayout(self.controlgraph)
        layout2.addWidget(self.chartView2, 0, 0, 2, 1)  # row=0, col=0, rowspan=2, colspan=1
        # Enable hover events for tooltips
        self.controllerSeries.hovered.connect(self.on_hover2)
        # Tooltip label for second chart
        self.tooltip2 = QtWidgets.QLabel(self.chartView2)
        self.tooltip2.setStyleSheet("background-color: white; border: 1px solid black; padding: 2px;")
        self.tooltip2.hide()

        # Add Ctrl+S shortcut (add this after the tooltip2 setup)
        self.save_action = QtWidgets.QAction("Save Data", self)
        self.save_action.setShortcut(QtGui.QKeySequence.Save)  # Ctrl+S
        self.save_action.triggered.connect(self.saveDataToCSV)
        self.addAction(self.save_action)

    def saveDataToCSV(self):
        """Save collected data to CSV file - only if all data series are available"""
        # Check if we have ALL required data series for CLC
        required_data = ['time_data', 'rpm_data', 'target_data', 'error_data', 'controller_data', 'rawController_data']
        missing_data = []
        
        for data_name in required_data:
            if not hasattr(self, data_name) or not getattr(self, data_name):
                missing_data.append(data_name)
        
        if missing_data:
            QtWidgets.QMessageBox.information(
                self, 
                "Incomplete Data", 
                f"Cannot save data. Missing or empty data series:\n" + 
                "\n".join([f"• {data.replace('_', ' ').title()}" for data in missing_data]) +
                "\n\nPlease run a complete closed-loop test first to collect all data."
            )
            return
        
        # Verify all data series have the same length
        data_lengths = {
            'Time': len(self.time_data),
            'Speed': len(self.rpm_data),
            'Target': len(self.target_data),
            'Error': len(self.error_data),
            'Controller': len(self.controller_data),
            'Raw Controller': len(self.rawController_data)
        }
        
        if len(set(data_lengths.values())) > 1:
            QtWidgets.QMessageBox.warning(
                self, 
                "Data Length Mismatch", 
                f"Data series have different lengths:\n" + 
                "\n".join([f"• {name}: {length} points" for name, length in data_lengths.items()]) +
                "\n\nCannot save inconsistent data."
            )
            return
        
        # Open file save dialog
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save CLC Data",
            f"clc_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Create DataFrame with all required data
            data_dict = {
                'Time_ms': self.time_data,
                'Target_Speed_RPM': self.target_data,
                'Actual_Speed_RPM': self.rpm_data,
                'Error_RPM': self.error_data,
                'Controller_Output_PWM': self.controller_data,
                'Raw_Control_Output_PWM': self.rawController_data
            }
            
            # Create DataFrame
            df = pd.DataFrame(data_dict)
            
            # Get controller parameters for metadata
            k1 = float(self.k1.text()) if self.k1.text() else 0
            k2 = float(self.k2.text()) if self.k2.text() else 0
            k3 = float(self.k3.text()) if self.k3.text() else 0
            controller_type = "PID" if k3 != 0 else ("PI" if k2 != 0 else "P")
            
            # Add metadata as comments
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                # Write metadata header
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
                f.write("#\n")  # Separator line
                
                # Write the actual CSV data
                df.to_csv(f, index=False)
            
            # Show success message with detailed statistics
            overshoot = max(self.rpm_data) - self.rpm_data[-1] if self.rpm_data else 0
            
            QtWidgets.QMessageBox.information(
                self, 
                "Save Successful", 
                f"Data saved successfully to:\n{file_path}\n\n"
                f"Summary:\n"
                f"• Records saved: {len(self.time_data)}\n"
                f"• Controller: {controller_type} (K1={k1:.2f}, K2={k2:.2f}, K3={k3:.2f})\n"
                f"• Target RPM: {self.target_data[-1]:.1f}\n"
                f"• Final Speed: {self.rpm_data[-1]:.1f} RPM\n"
                f"• Peak Overshoot: {overshoot:.1f} RPM\n"
                f"• Test Duration: {max(self.time_data) - min(self.time_data):.0f} ms"
            )
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                "Save Error", 
                f"Error saving data to CSV:\n{str(e)}"
            )

    def startClicked(self):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                targetRPM = float(self.targetRPM.text())
                k1 = float(self.k1.text())
                k2 = float(self.k2.text())
                k3 = float(self.k3.text())
            except ValueError:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for Target RPM, K1, K2, and K3.")
                return
            
            # Get sampling rate from radio buttons
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
            
            #QtWidgets.QMessageBox.warning(self, "Starting Test", f"{self.sampling_rate}")

            #Check if all parameters are there
            if not self.sampling_rate:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please select a sampling rate.")
                return
            elif targetRPM <= 0.0:
                QtWidgets.QMessageBox.warning(self, "Invalid Input", "Target RPM must be positive.")
                return
            elif targetRPM > float(self.main_window.maxRPM.text()):
                QtWidgets.QMessageBox.warning(self, "Invalid Input", f"Target RPM cannot exceed maximum RPM ({self.main_window.maxRPM.text()}).")
                return
            
            # If we get here, targetRPM is valid, send it to ESP32
            self.readTransientResponse(targetRPM, self.sampling_rate, k1, k2, k3)
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No serial port is open.")

    def on_hover(self, point, state):
        """Show tooltip when hovering points"""
        if state:
            # Find the closest data point in our dataset
            if hasattr(self, 'time_data') and hasattr(self, 'rpm_data'):
                # Get the x-coordinate from the hovered point
                hover_time = point.x()
                
                # Find the closest time in our actual data
                closest_index = 0
                min_distance = float('inf')
                
                for i, time_val in enumerate(self.time_data):
                    distance = abs(time_val - hover_time)
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
                
                # Get the actual values from our dataset
                actual_time = self.time_data[closest_index]
                actual_speed = self.rpm_data[closest_index]
                
                # Use actual data values in tooltip
                self.tooltip.setText(f"Time: {actual_time} ms\nSpeed: {actual_speed:.1f} RPM")
            else:
                # Fallback to chart coordinates if data not available
                self.tooltip.setText(f"Time: {point.x():.1f} ms\nSpeed: {point.y():.1f} RPM")

            self.tooltip.adjustSize()

            # Position tooltip near mouse (top left instead of top right)
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView.mapFromGlobal(cursor_pos)
            self.tooltip.move(widget_pos.x() - self.tooltip.width() - 10, widget_pos.y() - 20)
            self.tooltip.show()
        else:
            self.tooltip.hide()

    def on_hover2(self, point, state):
        """Show tooltip when hovering points in second chart"""
        if state:
            # Find the closest data point in our dataset
            if hasattr(self, 'time_data') and hasattr(self, 'controller_data'):
                # Get the x-coordinate from the hovered point
                hover_time = point.x()
                
                # Find the closest time in our actual data
                closest_index = 0
                min_distance = float('inf')
                
                for i, time_val in enumerate(self.time_data):
                    distance = abs(time_val - hover_time)
                    if distance < min_distance:
                        min_distance = distance
                        closest_index = i
                
                # Get the actual values from our dataset
                actual_time = self.time_data[closest_index]
                actual_pwm = self.controller_data[closest_index]
                actual_control = self.rawController_data[closest_index]
                actual_error = self.error_data[closest_index]

                # Use actual data values in tooltip
                self.tooltip2.setText(f"Time: {actual_time:.1f} ms\nPWM: {actual_pwm:.1f}\nRaw Control: {actual_control:.1f}\nError: {actual_error:.1f} RPM")
            else:
                # Fallback to chart coordinates if data not available
                self.tooltip2.setText(f"Time: {point.x():.1f} ms\nPWM: {point.y():.1f}")
            
            self.tooltip2.adjustSize()

            # Position tooltip near mouse (top left instead of top right)
            cursor_pos = QtGui.QCursor.pos()
            widget_pos = self.chartView2.mapFromGlobal(cursor_pos)
            self.tooltip2.move(widget_pos.x() - self.tooltip2.width() - 10, widget_pos.y() - 20)
            self.tooltip2.show()
        else:
            self.tooltip2.hide()

    def safe_write(self, data):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(data)
            else:
                QtWidgets.QMessageBox.critical(self, "Serial Error", "Serial connection lost.")
                self.close()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Serial Error", f"Serial error: {e}")
            self.close()

    def readTransientResponse(self, targetRPM, sampling_rate, k1, k2, k3):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.reset_input_buffer()

            #Prepare arrays
            self.time_data = []
            self.rpm_data = []
            self.target_data = []
            self.controller_data = []
            self.rawController_data = []
            self.error_data = []

            self.speedSeries.clear()
            self.targetSeries.clear()
            self.controllerSeries.clear()
            self.rawControlSeries.clear()
            self.errorSeries.clear()

            self.safe_write(f"1 {targetRPM} {sampling_rate} {k1} {k2} {k3}".encode())
            self.serial_conn.flush()

            # Start timer to poll for data
            self.responseTimer = QtCore.QTimer(self)
            self.responseTimer.timeout.connect(self.updateTransientPlot)
            self.responseTimer.start(sampling_rate)  # Poll every X ms for fast updates

    def updateTransientPlot(self):
        try:
            if not self.serial_conn or not self.serial_conn.is_open:
                self.responseTimer.stop()
                return
                
            if self.serial_conn.in_waiting > 0:
                line = self.serial_conn.readline().decode("utf-8").strip()
                
                # Check if data collection is complete
                if line == "DONE":
                    self.responseTimer.stop()
                    return

                 # Skip the header line
                if line == "time_ms,rpm,targetrpm,pwm,control,error":
                    print("Received header, starting data collection...")
                    return
                    
                try:
                    # Parse the CSV format: timestamp,actual_speed,target_speed
                    parts = line.split(',')
                    if len(parts) == 6:
                        timestamp = int(parts[0])  # milliseconds
                        actual_speed = float(parts[1])
                        target_speed = float(parts[2])
                        controller_output = float(parts[3])
                        raw_control_output = float(parts[4])  # Raw control output (before saturation)
                        error = float(parts[5])
                        
                        # Store data
                        self.time_data.append(timestamp)
                        self.rpm_data.append(actual_speed)
                        self.target_data.append(target_speed)
                        self.controller_data.append(controller_output)
                        self.rawController_data.append(raw_control_output)
                        self.error_data.append(error)

                        # Add to chart series
                        self.speedSeries.append(timestamp, actual_speed)
                        self.targetSeries.append(timestamp, target_speed)
                        self.controllerSeries.append(timestamp, controller_output)
                        self.rawControlSeries.append(timestamp, raw_control_output)
                        self.errorSeries.append(timestamp, error)

                        # Update chart axes to fit data
                        self.chart.axisX().setRange(0, max(self.time_data) + 100)
                        self.chart2.axisX().setRange(0, max(self.time_data) + 100)
                        
                        # Calculate y-axis range to fit data with some margin
                        max_y = max(max(self.rpm_data, default=0), target_speed) * 1.1
                        min_y = min(min(self.rpm_data, default=-1), -1) * 1.1
                        self.chart.axisY().setRange(min_y, max_y)

                        max_y2 = max(max(max(self.controller_data, default=0), max(self.rawController_data, default=0)), max(self.error_data, default=0)) * 1.1
                        min_y2 = min(min(min(self.controller_data, default=-1), min(self.rawController_data, default=-1)), min(self.error_data, default=-1)) * 1.1
                        self.chart2.axisY().setRange(min_y2, max_y2)

                except (ValueError, IndexError) as e:
                    print(f"Error parsing data: {e}")
                    # Skip invalid lines
                    pass
                    
        except Exception as e:
            print(f"Error in updateTransientPlot: {e}")
            self.responseTimer.stop()

    def popupClicked(self):
        if hasattr(self, 'time_data') and hasattr(self, 'rpm_data') and hasattr(self, 'target_data') and self.time_data and self.rpm_data and self.target_data:
            # Create figure with side-by-side layout
            fig = plt.figure(figsize=(15, 6))
            gs = fig.add_gridspec(1, 2, width_ratios=[2.5, 1])  # Plot gets 2.5x more space than text
            
            ax1 = fig.add_subplot(gs[0])  # Plot area
            ax2 = fig.add_subplot(gs[1])  # Text area
            ax2.axis('off')
            
            # Left plot - Speed Response
            ax1.plot(self.time_data, self.rpm_data, '-', color='blue', linewidth=2, label='Actual Speed')
            ax1.plot(self.time_data, self.target_data, 'r--', linewidth=2, label='Target Speed')
            
            # Add reference lines
            final_value = self.rpm_data[-1] if self.rpm_data else 0
            final_speed = final_value
            max_speed = max(self.rpm_data) if self.rpm_data else 0
            
            if final_value > 0:
                ax1.axhline(y=final_value, color='gray', linestyle=':', alpha=0.7)
                ax1.axhline(y=max_speed, color='orange', linestyle=':', alpha=0.5)
                
                # Add annotations for key values
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
            
            # Right panel - Analysis Text
            ax2.axis('off')
            
            # Get current analysis values from UI
            rise_time_text = self.Tr.text().replace(" ms", "") if hasattr(self, 'Tr') and self.Tr.text() != "--" else "N/A"
            peak_time_text = self.Tp.text().replace(" ms", "") if hasattr(self, 'Tp') and self.Tp.text() != "--" else "N/A"
            settling_time_text = self.Ts.text().replace(" ms", "") if hasattr(self, 'Ts') and self.Ts.text() != "--" else "N/A"
            overshoot_text = self.os.text().replace(" %", "") if hasattr(self, 'os') and self.os.text() != "--" else "N/A"
            
            # Get controller parameters
            k1 = float(self.k1.text()) if self.k1.text() else 0
            k2 = float(self.k2.text()) if self.k2.text() else 0
            k3 = float(self.k3.text()) if self.k3.text() else 0
            target_rpm = float(self.targetRPM.text()) if self.targetRPM.text() else 0
            
            # Determine controller type
            controller_type = "PID" if k3 != 0 else ("PI" if k2 != 0 else "P")
            
            # Create formatted analysis text
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
            
            # Add text to right panel
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
            plt.plot(self.time_data, self.rawController_data, '--', color='orange', label='Raw Control Output (PWM)')
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
        if not self.time_data or not self.rpm_data:
            return
        
        #Analyze transient response
        target = self.target_data[0] if self.target_data else 0
        fv = self.rpm_data[-1] if self.rpm_data else 0
        
        # Find rise time (10% to 90% of target)
        for i, target in enumerate(self.target_data):
            if target != 0:
                start_time = self.time_data[i]
                break
        else:
            start_time = 0

        #Is there an overshoot?
        overshoot = max(self.rpm_data) - fv if self.rpm_data else 0
        if overshoot > 0:
            print(f"Overshoot detected: {overshoot} RPM")

        #When it happened? (Peak Time)
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

        #Find settling time 2% oscillation band
        settling_time = 0
        if rise_end:
            upper_bound = fv * 1.05
            lower_bound = fv * 0.95
            for i in range(len(self.rpm_data)-1, -1, -1):
                if not (lower_bound <= self.rpm_data[i] <= upper_bound):
                    settling_time = self.time_data[i+1] - start_time if (i+1) < len(self.time_data) else 0
                    break

        #Display values
        self.Tr.setText(f"{rise_time} ms" if rise_time else "--")
        self.Tp.setText(f"{overshoot_time} ms" if overshoot_time else "--")
        self.Ts.setText(f"{settling_time} ms" if settling_time else "--")
        self.os.setText(f"{overshoot/fv*100:.2f} %" if overshoot else "--")

        #Calculate control parameters based on FOPDT
        L = 0.5 * self.sampling_rate / 1000.0  # Delay time in seconds (half the sampling rate)
        try:
            Kp_PID = (1.2 * self.main_window.true_fopdt_tau) / (self.main_window.true_fopdt_K * L) if self.main_window.true_fopdt_K != 0 and L != 0 else 0
            Ti_PID = 2 * L if L != 0 else 0
            Td_PID = 0.5 * L if L != 0 else 0
            Kp_PI = (0.9 * self.main_window.true_fopdt_tau) / (self.main_window.true_fopdt_K * L) if self.main_window.true_fopdt_K != 0 and L != 0 else 0
            Ti_PI = L / 0.3 if L != 0 else 0
            Kp_P = (self.main_window.true_fopdt_tau) / (self.main_window.true_fopdt_K * L) if self.main_window.true_fopdt_K != 0 and L != 0 else 0
        
            #print(f"Calculated Control Parameters: Kp_PID={Kp_PID}, Ti_PID={Ti_PID}, Td_PID={Td_PID}, Kp_PI={Kp_PI}, Ti_PI={Ti_PI}, Kp_P={Kp_P}")
        except Exception as e:
            print(f"Error calculating control parameters with {e} ")
            QtWidgets.QMessageBox.warning(self, "Calculation Error", f"Error calculating control parameters: {e}")
            return

        #Calculate true k1, k2, k3 values
        try:
            self.main_window.k1_PID = Kp_PID * (1 + (self.sampling_rate / 1000.0) / (2 * Ti_PID) + 2 * Td_PID / (self.sampling_rate / 1000.0)) if Ti_PID != 0 and Kp_PID != 0 else 0
            self.main_window.k2_PID = Kp_PID * (-1 + (self.sampling_rate / 1000.0) / (2 * Ti_PID) - 4 * Td_PID / (self.sampling_rate / 1000.0)) if Ti_PID != 0 and Kp_PID != 0 else 0
            self.main_window.k3_PID = Kp_PID * (2 * Td_PID / (self.sampling_rate / 1000.0)) if Td_PID != 0 and Kp_PID != 0 else 0
            self.main_window.k1_PI = Kp_PI * (1 + (self.sampling_rate / 1000.0) / (2 * Ti_PI)) if Ti_PI != 0 and Kp_PI != 0 else 0
            self.main_window.k2_PI = Kp_PI * (-1 + (self.sampling_rate / 1000.0) / (2 * Ti_PI)) if Ti_PI != 0 and Kp_PI != 0 else 0
            self.main_window.k3_PI = 0
            self.main_window.k1_P = Kp_P if Kp_P != 0 else 0
            self.main_window.k2_P = 0
            self.main_window.k3_P = 0
            #print(f"Discrete Control Gains: k1_PID={self.main_window.k1_PID}, k2_PID={self.main_window.k2_PID}, k3_PID={self.main_window.k3_PID}, k1_PI={self.main_window.k1_PI}, k2_PI={self.main_window.k2_PI}, k3_PI={self.main_window.k3_PI}, k1_P={self.main_window.k1_P}")
        except Exception as e:
            #print(f"Error calculating k1, k2, k3 parameters: {e}")
            QtWidgets.QMessageBox.warning(self, "Calculation Error", f"Error calculating k1, k2, k3 parameters: {e}")
            return

    def closeEvent(self, event):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.write(b"4")
                self.serial_conn.flush()
                self.clear_serial_buffers()
        except Exception:
            pass
        event.accept()

    def clear_serial_buffers(self):
        try:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()
        except Exception as e:
            print("Serial buffer clear error:", e)
              
class sa(QtWidgets.QMainWindow):
    def __init__(self, serial_conn, main_window=None):
        super().__init__(main_window)
        uic.loadUi(resource_path("ui_910/sa.ui"), self)
        self.setWindowTitle("Submit Answers")
        self.setWindowIcon(QtGui.QIcon(resource_path("../../public/Logo Merah.png")))

        self.serial_conn = serial_conn
        self.main_window = main_window  # Store reference to main window

        self.submit.clicked.connect(self.submitClicked)

    def submitClicked(self):
        try:
            submit_K_fopdt = float(self.K_fopdt.text())
            submit_tau_fopdt = float(self.tau_fopdt.text())
            submit_L_fopdt = float(self.L_fopdt.text())
            submit_K1 = float(self.K1.text())
            submit_K2 = float(self.K2.text())
            submit_K3 = float(self.K3.text())

            print(f"Submitted Parameters: FOPDT K={submit_K_fopdt}, Tau={submit_tau_fopdt}, L={submit_L_fopdt}; Control K1={submit_K1}, K2={submit_K2}, K3={submit_K3}")
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for all fields.")
            return
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"An error occurred: {e}")
            return
    
        #Calculate score
        if (hasattr(self.main_window, 'true_fopdt_K') and hasattr(self.main_window, 'true_fopdt_tau') and 
            hasattr(self.main_window, 'true_fopdt_L')):

            # Calculate K error
            if self.main_window.true_fopdt_K != 0:
                K_fopdt_error = abs(submit_K_fopdt - self.main_window.true_fopdt_K) / abs(self.main_window.true_fopdt_K)
            else:
                # If true value is 0, use absolute error scaled to percentage (0.1 difference = 10% error)
                K_fopdt_error = abs(submit_K_fopdt - self.main_window.true_fopdt_K)
            
            # Calculate Tau error
            if self.main_window.true_fopdt_tau != 0:
                tau_fopdt_error = abs(submit_tau_fopdt - self.main_window.true_fopdt_tau) / abs(self.main_window.true_fopdt_tau)
            else:
                # If true value is 0, use absolute error scaled to percentage
                tau_fopdt_error = abs(submit_tau_fopdt - self.main_window.true_fopdt_tau)
            
            # Calculate L error
            if self.main_window.true_fopdt_L != 0:
                L_fopdt_error = abs(submit_L_fopdt - self.main_window.true_fopdt_L) / abs(self.main_window.true_fopdt_L)
            else:
                # If true value is 0, use absolute error scaled to percentage
                L_fopdt_error = abs(submit_L_fopdt - self.main_window.true_fopdt_L)

            #print(f"FOPDT Errors: K Error={K_fopdt_error*100:.2f}%, Tau Error={tau_fopdt_error*100:.2f}%, L Error={L_fopdt_error*100:.2f}%")

            model_score = (self.error_to_score(K_fopdt_error) + self.error_to_score(tau_fopdt_error) + self.error_to_score(L_fopdt_error)) / 3.0

        else:
            QtWidgets.QMessageBox.warning(self, "Error", "True FOPDT parameters not available. Run analysis first.")
            return
        
        if (hasattr(self.main_window, 'k1_PID') and hasattr(self.main_window, 'k2_PID') and 
            hasattr(self.main_window, 'k3_PID') and hasattr(self.main_window, 'k1_PI') and 
            hasattr(self.main_window, 'k2_PI') and hasattr(self.main_window, 'k3_PI') and 
            hasattr(self.main_window, 'k1_P')):

            if submit_K3 == 0:
                #PI or P controller
                if submit_K2 == 0:
                    #P controller
                    true_k1 = getattr(self.main_window, 'k1_P', None)
                    true_k2 = 0
                    true_k3 = 0
                    k1_error = abs(submit_K1 - self.main_window.k1_P) / abs(self.main_window.k1_P) if self.main_window.k1_P != 0 else float('inf')
                    k2_error = 0
                    k3_error = 0
                    control_score = self.error_to_score(k1_error)

                    #print(f"P Controller K1 Error: {k1_error*100:.2f}%")
                else:
                    #PI controller
                    true_k1 = getattr(self.main_window, 'k1_PI', None)
                    true_k2 = getattr(self.main_window, 'k2_PI', None)
                    true_k3 = 0
                    k1_error = abs(submit_K1 - self.main_window.k1_PI) / abs(self.main_window.k1_PI) if self.main_window.k1_PI != 0 else float('inf')
                    k2_error = abs(submit_K2 - self.main_window.k2_PI) / abs(self.main_window.k2_PI) if self.main_window.k2_PI != 0 else float('inf')
                    k3_error = 0
                    control_score = (self.error_to_score(k1_error) + self.error_to_score(k2_error)) / 2.0

                    #print(f"PI Controller K1 Error: {k1_error*100:.2f}%, K2 Error: {k2_error*100:.2f}%")
            else:
                #PID controller
                true_k1 = getattr(self.main_window, 'k1_PID', None)
                true_k2 = getattr(self.main_window, 'k2_PID', None)
                true_k3 = getattr(self.main_window, 'k3_PID', None)
                k1_error = abs(submit_K1 - self.main_window.k1_PID) / abs(self.main_window.k1_PID) if self.main_window.k1_PID != 0 else float('inf')
                k2_error = abs(submit_K2 - self.main_window.k2_PID) / abs(self.main_window.k2_PID) if self.main_window.k2_PID != 0 else float('inf')
                k3_error = abs(submit_K3 - self.main_window.k3_PID) / abs(self.main_window.k3_PID) if self.main_window.k3_PID != 0 else float('inf')
                control_score = (self.error_to_score(k1_error) + self.error_to_score(k2_error) + self.error_to_score(k3_error)) / 3.0

                #print(f"PID Controller K1 Error: {k1_error*100:.2f}%, K2 Error: {k2_error*100:.2f}%, K3 Error: {k3_error*100:.2f}%")

            final_score = (model_score + control_score) / 2.0 * 10.0  # Scale to 0-100
            #print(f"Model Score: {model_score*10:.2f}/100")
            #print(f"Control Score: {control_score*10:.2f}/100")
            #print(f"Final Score: {final_score:.2f}/100")

            # Upload submission to Firebase
            if self.main_window and self.main_window.firebase_manager:
                submission_data = {
                    'K_fopdt': submit_K_fopdt,
                    'tau_fopdt': submit_tau_fopdt,
                    'L_fopdt': submit_L_fopdt,
                    'K1': submit_K1,
                    'K2': submit_K2,
                    'K3': submit_K3,
                    'true_K_fopdt': self.main_window.true_fopdt_K,
                    'true_tau_fopdt': self.main_window.true_fopdt_tau,
                    'true_L_fopdt': self.main_window.true_fopdt_L,
                    'true_k1': true_k1,
                    'true_k2': true_k2,
                    'true_k3': true_k3,
                    'model_score': model_score,
                    'control_score': control_score,
                    'final_score': final_score,
                    'K_fopdt_error_percent': K_fopdt_error * 100,
                    'tau_fopdt_error_percent': tau_fopdt_error * 100,
                    'L_fopdt_error_percent': L_fopdt_error * 100,
                    'k1_error_percent': k1_error * 100,
                    'k2_error_percent': k2_error * 100,
                    'k3_error_percent': k3_error * 100,
                    'controller_type': 'PID' if submit_K3 != 0 else ('PI' if submit_K2 != 0 else 'P')
                }
                
                for student_info in self.main_window.current_students:
                    student_npm = student_info['NPM']
                    student_name = student_info['Name']
                    self.main_window.firebase_manager.upload_student_submission(student_npm, student_name, submission_data)

            # Upload score to Firebase
            #if self.main_window and self.main_window.firebase_manager:
            #    for student_info in self.main_window.current_students:
            #        student_npm = student_info['NPM']
            #        self.main_window.firebase_manager.upload_student_score(student_npm, final_score)
                
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "True control parameters not available. Run analysis first.")
            return

        
    
    def error_to_score(self, error):
        if error == float('inf'):
            return 0
        elif error < 0.01: # 1% error
            return 10
        elif error < 0.05: # 5% error
            return 8
        elif error < 0.1: # 10% error
            return 6
        elif error < 0.2: # 20% error
            return 4
        elif error < 0.5: # 50% error
            return 2
        else:
            return 0

def exec_DMMCD(nama, npm, kelompok):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow(kelompok)
    window.show()
    
    return window
