import sys
from PyQt5.QtWidgets import QApplication
import pages.Home.resources_rc

from pages.Home.Login import Login


def main():
    app = QApplication(sys.argv)

    window = Login()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()