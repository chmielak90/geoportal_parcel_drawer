import sys

from PyQt5.QtWidgets import QApplication

from parcel_drawer_gui import ParcelDrawerGUI


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ParcelDrawerGUI()
    ex.show()
    sys.exit(app.exec_())
