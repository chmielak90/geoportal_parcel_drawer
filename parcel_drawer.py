# Copyright © 2024 Michal Chmielewski
import os
import sys
from binascii import unhexlify
from concurrent.futures import ThreadPoolExecutor
from ctypes import WinDLL

import ezdxf
import requests
from PyQt5.QtCore import QRect, QSize, pyqtSignal, QObject
from PyQt5.QtGui import QColor, QPixmap, QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
                             QRadioButton, QHBoxLayout, QComboBox, QStyledItemDelegate, QCheckBox, QMessageBox,
                             QProgressBar)
from shapely.wkb import loads


class PathNotFoundError(Exception):
    def __init__(self, path_error, message="Path not found"):
        self.path_error = path_error
        self.message = message
        super().__init__(f"{self.message}: '{self.path_error}'")


class ParcelDrawer(QObject):
    progress_updated = pyqtSignal(int)

    def __init__(self, identifiers, full_path, draw_as_lines=False, line_color=1, polygon_color=2,
                 identifier_color=3, add_identifier_at_layer=False):
        super().__init__()
        self.identifiers = identifiers
        self.full_path = full_path
        self.draw_as_lines_flag = draw_as_lines  # Renamed attribute
        self.line_color = line_color
        self.polygon_color = polygon_color
        self.identifier_color = identifier_color
        self.add_identifier_at_layer = add_identifier_at_layer
        self.doc = None
        self.msp = None

    def fetch_wkb_data(self, identifier):
        url = f"https://uldk.gugik.gov.pl/?request=GetParcelById&id={identifier}"
        response = requests.get(url)
        hex_wkb_data = response.text.split('\n')[1]
        if 'błędny format odpowiedzi XML, usługa zwróciła odpowiedź' in hex_wkb_data:
            raise ValueError(f"Identifier: {identifier} does not exist or there was an error in the response.")
        wkb_data = unhexlify(hex_wkb_data)
        return loads(wkb_data), identifier

    def read_or_create_dxf(self):
        try:
            self.doc = ezdxf.readfile(self.full_path)
        except IOError:
            self.doc = ezdxf.new('R2010')
        self.msp = self.doc.modelspace()

    def ensure_layer(self, layer_name, color=7):
        if not self.doc.layers.has_entry(layer_name):
            self.doc.layers.new(name=layer_name, dxfattribs={'color': color})

    def draw_as_polygon(self, geometry, identifier):
        layer_name = 'plot_as_polygon'
        self.ensure_layer(layer_name, self.polygon_color)
        coords = list(geometry.exterior.coords)
        self.msp.add_lwpolyline(coords, dxfattribs={'layer': layer_name, 'color': self.polygon_color})
        if self.add_identifier_at_layer:
            short_id = identifier.split(".")[-1]
            self.add_identifier(geometry, short_id)

    def draw_lines(self, geometry, identifier):  # Renamed method
        layer_name = 'plot_as_lines'
        self.ensure_layer(layer_name, self.line_color)
        coords = list(geometry.exterior.coords)
        for i in range(len(coords) - 1):
            start_point = coords[i]
            end_point = coords[i + 1]
            self.msp.add_line(start_point, end_point, dxfattribs={'layer': layer_name, 'color': self.line_color})
        if self.add_identifier_at_layer:
            short_id = identifier.split(".")[-1]
            self.add_identifier(geometry, short_id)

    def add_identifier(self, geometry, identifier):
        identifier_layer = 'identifier_layer'
        self.ensure_layer(identifier_layer, self.identifier_color)
        centroid = geometry.centroid
        self.msp.add_text(identifier, dxfattribs={'layer': identifier_layer, 'height': 2.5, 'insert': (centroid.x, centroid.y), 'color': self.identifier_color})

    def process_parcels(self):
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.fetch_wkb_data, identifier) for identifier in self.identifiers]
            for i, future in enumerate(futures):
                geometry, identifier = future.result()
                if self.draw_as_lines_flag:
                    self.draw_lines(geometry, identifier)
                else:
                    self.draw_as_polygon(geometry, identifier)

                progress = (i + 1) / len(self.identifiers) * 100
                self.progress_updated.emit(progress)

    def save_dxf(self):
        directory, filename = os.path.split(self.full_path)
        try:
            self.doc.saveas(self.full_path)
        except FileNotFoundError:
            raise PathNotFoundError(directory)


# Helper function to get the keyboard layout
def get_keyboard_layout():
    user32 = WinDLL('user32', use_last_error=True)
    hkl = user32.GetKeyboardLayout(0) # 0 here represents the current thread
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


class ColorItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # Call the standard paint method to paint the item text, etc.
        super().paint(painter, option, index)
        # Draw the color square
        color_hex = index.data()
        color = QColor(color_hex)
        if color.isValid():
            painter.save()
            rect = QRect(option.rect.right() - 30, option.rect.top(), 20, option.rect.height())
            painter.fillRect(rect, color)
            painter.restore()

    def sizeHint(self, option, index):
        # Provide a size hint to ensure there is space for the color square
        defaultSize = super().sizeHint(option, index)
        return QSize(defaultSize.width() + 30, defaultSize.height())


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
        # Check system locale and set messages
        # Check the keyboard layout or Windows display language
        keyboard_layout = get_keyboard_layout()
        windows_display_language = get_windows_display_language()[0]
        self.language = "en-US"
        if keyboard_layout == '0x415' or windows_display_language.startswith('pl-PL'):
            self.set_polish_language()
            self.language = "pl-PL"

        # Set default file path to user's desktop
        self.default_file_path = os.path.join(os.path.expanduser("~\\Desktop"), "parcelDrawer.dxf")
        self.filepath_display.setText(self.default_file_path)

    def set_polish_language(self):
        self.identifier_label_text = "Wpisz identyfikatory działek (oddzielone przecinkami)\n" \
                                     "Przykład: 101511_1.0016.164/1,101511_2.0016.164/2"
        self.filepath_label_text = "Wybierz lub wpisz ścieżkę do pliku:"
        self.drawing_option_label_text = "Wybierz opcję rysowania:"
        self.identifier_checkbox_label_text = "Chcesz dodać identyfikator działek?"
        self.color_label_text = "Wybierz kolor warstwy dla obrysu działek:"
        self.ok_button_text = "Ok"
        self.file_dialog_title = "Wybierz plik DXF"
        self.color_label_id_text = "Wybierz kolor warstwy dla identyfikatoró:"

        # Set the texts
        self.identifier_label.setText(self.identifier_label_text)
        self.filepath_label.setText(self.filepath_label_text)
        self.drawing_option_label.setText(self.drawing_option_label_text)
        self.add_identifier_checkbox.setText(self.identifier_checkbox_label_text)
        self.color_label.setText(self.color_label_text)
        self.ok_button.setText(self.ok_button_text)
        self.color_label_id.setText(self.color_label_id_text)

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
        layout.addWidget(self.add_identifier_checkbox)

        # Color Selection
        self.color_label_id = QLabel("Select Identifier Layer Color:")
        self.color_combo_id = ColorComboBox(self)
        self.color_combo_id.currentIndexChanged.connect(self.on_color_combo_changed)  # Connect the change event
        layout.addWidget(self.color_label_id)
        layout.addWidget(self.color_combo_id)

        # OK Button
        self.ok_button = QPushButton('Ok', self)
        self.ok_button.clicked.connect(self.on_click)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)
        self.setWindowTitle('Parcel Drawer')
        self.setMinimumWidth(400)  # Adjust the width of the window

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

        color = self.color_combo.currentText()
        color_id = self.color_combo_id.currentText()
        is_polygon = self.polygon_radio.isChecked()
        add_identifier = self.add_identifier_checkbox.isChecked()
        list_of_identifiers = identifiers.split(',')

        if not is_polygon:
            draw_as_lines = True
        try:
            self.drawer = ParcelDrawer(list_of_identifiers, file_path, draw_as_lines=draw_as_lines,
                                  line_color=color_aci[color], polygon_color=color_aci[color],
                                  identifier_color=color_aci[color_id], add_identifier_at_layer=add_identifier)
            self.drawer.progress_updated.connect(self.update_progress_bar)

            self.drawer.read_or_create_dxf()
            self.drawer.process_parcels()

        except ValueError as e:
            error_message = str(e)
            if self.language == "pl-PL":
                identifier = error_message.split()[1]
                QMessageBox.critical(self, "Error", f"Identifikator: {identifier} nie istnieje,"
                                                    f" bądź wystąpił bład odpowiedzi serwera.")
            else:
                QMessageBox.critical(self, "Error", error_message)
            return

        try:
            self.drawer.save_dxf()
        except PathNotFoundError as e:
            error_message = str(e)
            if self.language == "pl-PL":
                path_error = error_message.split(": ")[1]
                QMessageBox.critical(self, "Error",
                                     f"Podana ścieżka nie istnieje: {path_error}")
            else:
                QMessageBox.critical(self, "Error", error_message)
            return

        if self.language == "pl-PL":
            success_message = "Obramowania działek zostały dodane"
        else:
            success_message = "Plot borders have been added"
        QMessageBox.information(self, "Success", success_message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ParcelDrawerGUI()
    ex.show()
    sys.exit(app.exec_())
