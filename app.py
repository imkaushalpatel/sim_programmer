import sys
from PyQt6.QtWidgets import QApplication
from simprog.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SIM Provisioning Studio")
    app.setOrganizationName("Local Lab")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
