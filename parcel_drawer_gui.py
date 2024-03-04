# Copyright © 2024 Michal Chmielewski
import os
from ctypes import WinDLL

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor, QIcon
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
                             QRadioButton, QHBoxLayout, QCheckBox, QMessageBox,
                             QProgressBar, QSpacerItem, QSizePolicy, QComboBox, QDoubleSpinBox)

from errors import WrongZoneError, PathNotFoundError, ServerConnectionError
from parcel_drawer import ParcelDrawer


# Helper function to get the keyboard layout
def get_keyboard_layout():
    user32 = WinDLL('user32', use_last_error=True)
    hkl = user32.GetKeyboardLayout(0)
    language_id = hkl & (2**16 - 1)
    language_code = hex(language_id)
    return language_code


# Helper function to get the Windows display language
def get_windows_display_language():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Control Panel\\Desktop")
        language, _ = winreg.QueryValueEx(key, "PreferredUILanguages")
        winreg.CloseKey(key)
        return language
    except Exception as e:
        print(f"Error reading registry: {e}")
        return None


class ColorComboBox(QComboBox):
    def __init__(self, parent=None):
        super(ColorComboBox, self).__init__(parent)
        self.populate_colors()

    def populate_colors(self):
        color_names = {
            "Red": "#ff0000",
            "Green": "#00ff00",
            "Blue": "#0000ff",
            "Yellow": "#ffff00",
            "Black": "#000000",
            "White": "#ffffff",
        }
        for name, hex in color_names.items():
            # Create a pixmap and fill it with the color
            pixmap = QPixmap(20, 20)
            pixmap.fill(QColor(hex))
            # Create an icon from the pixmap
            icon = QIcon(pixmap)
            # Add the item to the combo box with the icon and the color name
            self.addItem(icon, name)


class ParcelDrawerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.stop_requested = False
        self.ignore_all_errors = False
        # Check system locale and set messages
        # Check the keyboard layout or Windows display language
        try:
            keyboard_layout = get_keyboard_layout()
        except:
            keyboard_layout = '0x409'
        try:
            windows_display_language = get_windows_display_language()[0]
        except:
            windows_display_language = 'en-US'
        self.language = "en-US"
        if keyboard_layout == '0x415' or windows_display_language.startswith('pl-PL'):
            self.set_polish_language()
            self.language = "pl-PL"

        # Set default file path to user's desktop
        self.default_file_path = os.path.join(os.path.expanduser("~\\Desktop"), "parcelDrawer.dxf")
        self.filepath_display.setText(self.default_file_path)

    def show_error_message(self, message):
        if not self.ignore_all_errors:
            info_text = "Do you want to continue or stop processing?"
            continue_button = "Continue"
            continue_all_button = "Continue for all"
            if self.language == "pl-PL":
                info_text = "Czy chcesz kontynuować czy przerwać przetwarzanie?"
                continue_button = "Kontynuuj"
                continue_all_button = "Kontynuuj dla wszystkich"

            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setWindowTitle("Warning")
            msgBox.setText(message)
            msgBox.setInformativeText(info_text)
            continueButton = msgBox.addButton(continue_button, QMessageBox.AcceptRole)
            continueAllButton = msgBox.addButton(continue_all_button, QMessageBox.YesRole)
            stopButton = msgBox.addButton("Stop", QMessageBox.RejectRole)
            msgBox.setDefaultButton(continueButton)
            msgBox.exec_()

            if msgBox.clickedButton() == stopButton:
                self.drawer.request_stop()
                self.stop_requested = True
                self.update_progress_bar(0)
            elif msgBox.clickedButton() == continueAllButton:
                self.ignore_all_errors = True

    def set_polish_language(self):
        self.identifier_label_text = "Wpisz identyfikatory działek (oddzielone przecinkami)\n" \
                                     "Przykład: 101511_1.0016.164/1,101511_2.0016.164/2"
        self.filepath_label_text = "Wybierz lub wpisz ścieżkę do pliku:"
        self.drawing_option_label_text = "Wybierz opcję rysowania:"
        self.identifier_checkbox_label_text = "Chcesz dodać identyfikator działek?"
        self.color_label_text = "Wybierz kolor warstwy dla obrysu działek:"
        self.ok_button_text = "Ok"
        self.file_dialog_title = "Wybierz plik DXF"
        self.color_label_id_text = "Wybierz kolor warstwy dla identyfikatorów:"
        self.identifier_file_button_text = "Albo wybierz Identyfikatory z pliku"
        self.identifier_file_label_text = "Nie wybrano pliku"
        self.puwg_transformation_checkbox_text = "Czy chcesz dokonać transformacji układu" \
                                                 " współrzędnych PUWG 1992 do PUWG 2000?"
        self.spin_box_label_text = "Wysokość tekstu dla Identyfikatorów"

        # Set the texts
        self.identifier_label.setText(self.identifier_label_text)
        self.filepath_label.setText(self.filepath_label_text)
        self.drawing_option_label.setText(self.drawing_option_label_text)
        self.add_identifier_checkbox.setText(self.identifier_checkbox_label_text)
        self.color_label.setText(self.color_label_text)
        self.ok_button.setText(self.ok_button_text)
        self.color_label_id.setText(self.color_label_id_text)
        self.identifier_file_button.setText(self.identifier_file_button_text)
        self.identifier_file_label.setText(self.identifier_file_label_text)
        self.puwg_transformation_checkbox.setText(self.puwg_transformation_checkbox_text)
        self.spin_box_label.setText(self.spin_box_label_text)

    def initUI(self):
        layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        # Identifier Input
        self.identifier_label = QLabel("Enter Parcel Identifiers (comma-separated):")
        self.identifier_input = QLineEdit(self)
        layout.addWidget(self.identifier_label)
        layout.addWidget(self.identifier_input)

        # Identifier File Upload
        self.identifier_file_button = QPushButton('Or upload Identifier File', self)
        self.identifier_file_button.clicked.connect(self.upload_identifier_file)
        layout.addWidget(self.identifier_file_button)

        # Label to display the file path
        self.identifier_file_label = QLabel("No file selected")
        layout.addWidget(self.identifier_file_label)

        # Transform coordinate system PUWG 1992 to PUWG 2000
        self.puwg_transformation_checkbox = QCheckBox("Do you want to transform coordinate"
                                                      " system PUWG 1992 to PUWG 2000?")
        layout.addWidget(self.puwg_transformation_checkbox)

        # File Path Selection
        self.filepath_label = QLabel("Select or Enter File Path:")
        self.filepath_display = QLineEdit(self)  # Display selected file path
        self.filepath_display.setReadOnly(False)  # Now editable
        self.filepath_button = QPushButton('Choose File', self)
        self.filepath_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.filepath_label)
        layout.addWidget(self.filepath_display)
        layout.addWidget(self.filepath_button)

        # Drawing Options
        self.drawing_option_label = QLabel("Choose Drawing Option:")
        self.polygon_radio = QRadioButton("Polygon")
        self.lines_radio = QRadioButton("Lines")
        self.polygon_radio.setChecked(True)
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.polygon_radio)
        radio_layout.addWidget(self.lines_radio)
        layout.addWidget(self.drawing_option_label)
        layout.addLayout(radio_layout)

        # Color Selection
        self.color_label = QLabel("Select Drawing Layer Color:")
        self.color_combo = ColorComboBox(self)
        self.color_combo.currentIndexChanged.connect(self.on_color_combo_changed)  # Connect the change event
        layout.addWidget(self.color_label)
        layout.addWidget(self.color_combo)

        # Add a checkbox for adding an identifier
        self.add_identifier_checkbox = QCheckBox("Do you want to add an identifier?")
        self.add_identifier_checkbox.stateChanged.connect(self.toggle_identifier_options)
        layout.addWidget(self.add_identifier_checkbox)

        # Color Selection
        self.color_label_id = QLabel("Select Identifier Layer Color:")
        self.color_combo_id = ColorComboBox(self)
        self.color_combo_id.currentIndexChanged.connect(self.on_color_combo_changed)  # Connect the change event
        layout.addWidget(self.color_label_id)
        layout.addWidget(self.color_combo_id)
        self.color_label_id.hide()  # Initially hide the label
        self.color_combo_id.hide()  # Initially hide the combo box

        # Create a label for height of text
        self.spin_box_label = QLabel("Identifier text height", self)
        layout.addWidget(self.spin_box_label)

        # Create the QDoubleSpinBox for displaying and inputting the value
        self.spin_box = QDoubleSpinBox(self)
        self.spin_box.setValue(8.0)  # Set the initial value
        self.spin_box.setSingleStep(0.5)  # Set the step value
        layout.addWidget(self.spin_box)
        self.spin_box.hide()  # Initially hide the spin box

        # OK Button
        self.ok_button = QPushButton('Ok', self)
        self.ok_button.clicked.connect(self.on_click)
        layout.addWidget(self.ok_button)

        # Copyright Label
        copyright_label = QLabel("Copyright © 2024 Michał Chmielewski")
        copyright_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)  # Align to bottom right

        # Add a spacer to push the copyright label to the bottom right corner
        spacer = QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)

        layout.addWidget(copyright_label)

        self.setLayout(layout)
        self.setWindowTitle('Parcel Drawer')
        self.setMinimumWidth(420)  # Adjust the width of the window

    def toggle_identifier_options(self, state):
        if state == Qt.Checked:
            # Show the widgets
            self.color_label_id.show()
            self.color_combo_id.show()
            self.spin_box_label.show()
            self.spin_box.show()
        else:
            # Hide the widgets
            self.color_label_id.hide()
            self.color_combo_id.hide()
            self.spin_box_label.hide()
            self.spin_box.hide()

    def open_file_dialog(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Select or Create File", self.default_file_path,
                                                   "DXF Files (*.dxf)", options=options)

        if file_path:
            # Normalize file path for Windows
            file_path = os.path.normpath(file_path)
            # Set the file path to the QLineEdit to display it
            self.filepath_display.setText(file_path)

    def on_color_combo_changed(self):
        # Remove duplicate entries if necessary
        current_color = self.color_combo.currentText()
        for i in range(self.color_combo.count()):
            if self.color_combo.itemText(i) == current_color and i != self.color_combo.currentIndex():
                self.color_combo.removeItem(i)
                break  # Break after removing the duplicate to avoid skipping items

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)

    def upload_identifier_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Identifier File", "",
                                                   "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.identifier_file_path = file_path
            self.identifier_file_label.setText(file_path)
            identifiers = self.read_identifiers_from_file(file_path)
            self.identifier_input.setText(','.join(identifiers))

    def on_click(self):
        draw_as_lines = False
        color_aci = {
            "Red": 1,
            "Yellow": 2,
            "Green": 3,
            "Blue": 5,
            "Black": 7,
            "White": 7
        }

        identifiers = self.identifier_input.text().strip()
        file_path = self.filepath_display.text().strip()

        # Check for empty inputs
        if not identifiers or not file_path:
            if self.language == "pl-PL":
                QMessageBox.warning(self, "Warning", "Proszę wprowadzić identyfikatory i ścieżkę do pliku.")
            else:
                QMessageBox.warning(self, "Warning", "Please enter both identifiers and a file path.")
            return

        directory, filename = os.path.split(file_path)
        if not os.path.isdir(directory):
            if self.language == "pl-PL":
                QMessageBox.critical(self, "Warning", f"Podana ścieżka nie istnieje: {directory}")
            else:
                QMessageBox.critical(self, "Warning", f"The path not found: {directory}")
            return

        color = self.color_combo.currentText()
        color_id = self.color_combo_id.currentText()
        is_polygon = self.polygon_radio.isChecked()
        add_identifier = self.add_identifier_checkbox.isChecked()
        list_of_identifiers = identifiers.split(',')
        list_of_identifiers = list(filter(None, list_of_identifiers))
        puwg_transformation = self.puwg_transformation_checkbox.isChecked()
        height_identifier_text = float(self.spin_box.cleanText())

        if not is_polygon:
            draw_as_lines = True
        self.drawer = ParcelDrawer(list_of_identifiers, file_path, draw_as_lines=draw_as_lines,
                                   line_color=color_aci[color], polygon_color=color_aci[color],
                                   identifier_color=color_aci[color_id], add_identifier_at_layer=add_identifier,
                                   identifier_height=height_identifier_text,
                                   make_transformation_to_puwg_2000=puwg_transformation)
        self.drawer.error_occurred.connect(self.show_error_message)
        self.drawer.progress_updated.connect(self.update_progress_bar)

        self.drawer.read_or_create_dxf()
        try:
            self.drawer.process_parcels()
        except ServerConnectionError:
            if self.language == "pl-PL":
                QMessageBox.critical(self, "Error", f"Problem z połączeniem do serwera. Spróbuj później.")
            else:
                QMessageBox.critical(self, "Error",
                                     "There is a connection issue to the server. Please try again later.")
            self.update_progress_bar(0)
            return

        except WrongZoneError:
            if self.language == "pl-PL":
                QMessageBox.critical(self, "Error", f"Twoje identyfikatory nie pochodzą z jednej strefy.")
            else:
                QMessageBox.critical(self, "Error", f"Your identifiers are from different zones.")
            self.update_progress_bar(0)
            return

        try:
            if not self.stop_requested:
                self.drawer.save_dxf()
                self.drawer.save_log_error()
        except PathNotFoundError as e:
            error_message = str(e)
            path_error = error_message.split(": ")[1]
            if self.language == "pl-PL":
                QMessageBox.critical(self, "Error", f"Podana ścieżka nie istnieje: {path_error}, spróbuj ponownie")
            else:
                QMessageBox.critical(self, "Error", f"The path not found: {path_error}, please try again")
            self.update_progress_bar(0)
            return

        if not self.stop_requested:
            if self.language == "pl-PL":
                success_message = "Obramowania działek zostały dodane"
            else:
                success_message = "Plot borders have been added"
            QMessageBox.information(self, "Success", success_message)

    @staticmethod
    def read_identifiers_from_file(file_path):
        with open(file_path, 'r') as file:
            return file.read().split(',')