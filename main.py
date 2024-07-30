from PySide6.QtWidgets import QApplication

import sys

from mainWindow import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.launch_game()

    sys.exit(app.exec())