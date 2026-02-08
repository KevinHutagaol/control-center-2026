import time

from PyQt5.QtWidgets import QDialog, QLabel, QProgressBar, QTextEdit, QPushButton, QHBoxLayout, QVBoxLayout, \
    QApplication

from pages.Home.main import DownloadWorker


class UpdaterDialog(QDialog):
    def __init__(self, parent, asset):
        super().__init__(parent)
        self.setWindowTitle("Downloading Update...")
        self.setModal(True)
        self.resize(520, 320)

        self.label = QLabel(f"Target: {asset['name']}")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.btnCancel = QPushButton("Cancel")
        self.btnClose  = QPushButton("Close")
        self.btnClose.setEnabled(False)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(self.btnCancel)
        btns.addWidget(self.btnClose)

        lay = QVBoxLayout(self)
        lay.addWidget(self.label)
        lay.addWidget(self.bar)
        lay.addWidget(self.log, 1)
        lay.addLayout(btns)

        self.worker = DownloadWorker(asset)
        self.worker.progress.connect(self.bar.setValue)
        self.worker.status.connect(self._append)
        self.worker.done.connect(self._done)
        self.worker.failed.connect(self._failed)

        self.btnCancel.clicked.connect(self._cancel)
        self.btnClose.clicked.connect(self.accept)

        self.worker.start()

    def _append(self, text: str):
        self.log.append(text)

    def _done(self, filename: str):
        self.bar.setValue(100)
        self.btnCancel.setEnabled(False)
        self.btnClose.setEnabled(True)
        self.setWindowTitle("Update installed")

    def _failed(self, err: str):
        self._append(f"Failed: {err}")
        self.btnCancel.setEnabled(False)
        self.btnClose.setEnabled(True)
        self.setWindowTitle("Failed install update")

    def _cancel(self):
        self.btnCancel.setEnabled(False)
        self._append("Cancelling update...")
        self.worker.cancel()
        time.sleep(2)
        QApplication.quit()
