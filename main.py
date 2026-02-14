import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.db.database import init_db, close_db
from app.config import APP_NAME


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")

    init_db()

    from app.ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    exit_code = app.exec()
    close_db()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
