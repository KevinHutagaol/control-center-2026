import os
import zipfile
from typing import TypedDict

from PyQt5.QtCore import QStandardPaths
from PyQt5.QtWidgets import QFileDialog, QMessageBox


class FileToSave(TypedDict):
    file_name: str
    file_data: str 


def saveToZip(self, zip_file_name, files: list[FileToSave]):
    downloads_path = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
    default_file = os.path.join(downloads_path, zip_file_name)

    file_path, _ = QFileDialog.getSaveFileName(
        self,
        "Save Zip File",
        default_file,
        "ZIP Files (*.zip)"
    )

    if not file_path:
        return

    try:
        with zipfile.ZipFile(file_path, 'w') as zf:
            for file in files:
                zf.writestr(file['file_name'], file['file_data'])

            QMessageBox.information(self, "Success",
                                    f"File successfully saved to:\n{file_path}")

    except Exception as e:
        QMessageBox.critical(self, "Error Saving", f"An error occurred during save:\n{str(e)}")
