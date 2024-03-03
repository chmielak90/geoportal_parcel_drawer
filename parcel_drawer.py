# Copyright © 2024 Michal Chmielewski
import os
import sys
from binascii import unhexlify
from concurrent.futures import ThreadPoolExecutor
from ctypes import WinDLL

import ezdxf
import requests
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtGui import QColor, QPixmap, QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
                             QRadioButton, QHBoxLayout, QComboBox, QStyledItemDelegate, QCheckBox, QMessageBox,
                             QProgressBar, QSpacerItem, QSizePolicy)
from shapely.wkb import loads
from shapely.ops import transform
from pyproj import Transformer

zone_5_teryts = ['3263', '3207', '3205', '3208', '3209', '3261', '3211', '3204', '3218', '3216', '3201', '3262',
                 '3214', '3203', '3206', '3212', '3202', '3217', '3210', '0806', '3002', '0801', '0861', '0805',
                 '0807', '0803', '3014', '3024', '0808', '3015', '0802', '0809', '0862', '3029', '3005', '0811',
                 '0810', '0804', '0812', '0203', '0225', '0201', '0216', '0211', '0210', '0212', '0226', '0209',
                 '0262', '0205', '0206', '0261', '0207', '0221', '0265', '0219']
zone_6_teryts = ['3213', '2212', '2263', '2208', '2215', '2211', '2201', '2205', '2262', '2264', '2261', '2210',
                 '3215', '2203', '2202', '2206', '2204', '2213', '2214', '2209', '2216', '3031', '0413', '0416',
                 '0414', '2207', '0406', '0462', '3019', '0410', '0403', '0461', '0404', '0417', '0402', '3001',
                 '3028', '0419', '0407', '0415', '0463', '0405', '0412', '0408', '0464', '0401', '0411', '0418',
                 '3016', '3021', '3064', '3003', '0409', '3025', '3030', '3023', '3010', '3062', '3009', '1002',
                 '3011', '3026', '3006', '3020', '3007', '3027', '1004', '1011', '1020', '3013', '3063', '3004',
                 '3012', '3017', '3061', '1014', '1019', '1003', '1008', '1061', '0204', '3022', '0213', '0222',
                 '0220', '0214', '3018', '3008', '1018', '1017', '1001', '1009', '0218', '0264', '0223', '0215',
                 '1606', '1604', '1608', '2406', '2404', '2464', '0202', '0217', '1601', '1609', '1661', '1611',
                 '2407', '2409', '0208', '0224', '1607', '1610', '1605', '1603', '1602', '2411', '2415', '2405',
                 '2466', '2413', '2478', '2462', '2471', '2401', '2465', '2475', '2468', '2470', '1203', '2472',
                 '2476', '2463', '2474', '2469', '2408', '2477', '2414', '1213', '2402', '2410', '2461', '2403',
                 '2417', '2467', '2412', '2479', '2473']
zone_7_teryts = ['2802', '2801', '2808', '2819', '2818', '2804', '2861', '2809', '2806', '2813', '2807', '2815',
                 '2814', '2862', '2810', '2816', '2805', '2812', '2803', '2811', '2817', '2006', '2004', '1437',
                 '1413', '1422', '1415', '1461', '2007', '2062', '1427', '1402', '1411', '2014', '1419', '1462',
                 '1420', '1424', '1435', '1416', '1433', '1429', '1404', '1428', '1414', '1432', '1408', '1465',
                 '1434', '1412', '1426', '1464', '1005', '1438', '1405', '1421', '1418', '1417', '1021', '1015',
                 '1063', '1013', '1406', '1403', '0611', '1006', '1016', '1401', '1407', '0616', '1010', '1062',
                 '1007', '1423', '1425', '1463', '1436', '0614', '1012', '2605', '1430', '2610', '2611', '1409',
                 '0612', '2613', '2604', '2661', '2607', '2606', '0607', '2416', '2602', '2608', '2601', '2612',
                 '2609', '1864', '1820', '1818', '0605', '1812', '1212', '1208', '2603', '1204', '1811', '1806',
                 '1808', '1206', '1214', '1261', '1219', '1201', '1202', '1216', '1263', '1803', '1815', '1816',
                 '1863', '1810', '1218', '1209', '1207', '1210', '1262', '1205', '1805', '1819', '1807', '1861',
                 '1802', '1817', '1821', '1215', '1211', '1217']
zone_8_teryts = ['2012', '2063', '2009', '2001', '2008', '2011', '2002', '2061', '2013', '2003', '2005', '2010',
                 '1410', '0601', '0661', '0615', '0613', '0619', '0608', '0609', '0663', '0610', '0603', '0662',
                 '0617', '0606', '0602', '0620', '0664', '0604', '0618', '1809', '1814', '1804', '1813', '1862',
                 '1801']


class PathNotFoundError(Exception):
    def __init__(self, path_error, message="Path not found"):
        self.path_error = path_error
        self.message = message
        super().__init__(f"{self.message}: '{self.path_error}'")


class WrongZoneError(Exception):
    def __init__(self, identifier, message="Wrong zone"):
        self.path_error = identifier
        self.message = message
        super().__init__(f"Identifier: ${identifier} are from different zone then others.")


class ParcelDrawer(QObject):
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, identifiers, full_path, draw_as_lines=False, line_color=1, polygon_color=2,
                 identifier_color=3, add_identifier_at_layer=False, make_transformation_to_puwg_2000=False):
        super().__init__()
        self.identifiers = identifiers
        self.full_path = full_path
        self.draw_as_lines_flag = draw_as_lines  # Renamed attribute
        self.line_color = line_color
        self.polygon_color = polygon_color
        self.identifier_color = identifier_color
        self.add_identifier_at_layer = add_identifier_at_layer
        self.stop_requested = False
        self.failed_identifiers = []
        self.make_transformation_to_puwg_2000 = make_transformation_to_puwg_2000
        if make_transformation_to_puwg_2000:
            self.identifier_height = 10
        else:
            self.identifier_height = 2.5
        self.set_zone = None
        self.doc = None
        self.msp = None

    def save_log_error(self):
        if self.failed_identifiers:
            with open('failed_identifiers.txt', 'w') as file:
                file.write(','.join(self.failed_identifiers))

    def request_stop(self):
        self.stop_requested = True

    def fetch_wkb_data(self, identifier):
        url = f"https://uldk.gugik.gov.pl/?request=GetParcelById&id={identifier}"
        response = requests.get(url)
        hex_wkb_data = response.text.split('\n')[1]
        if 'błędny format odpowiedzi XML, usługa zwróciła odpowiedź' in hex_wkb_data:
            self.failed_identifiers.append(identifier)
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

    def draw_lines(self, geometry, identifier):
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
        self.msp.add_text(identifier, dxfattribs={'layer': identifier_layer, 'height': self.identifier_height,
                                                  'insert': (centroid.x, centroid.y), 'color': self.identifier_color})

    def process_parcels(self):
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.fetch_wkb_data, identifier) for identifier in self.identifiers]
            for i, future in enumerate(futures):
                if self.stop_requested:
                    break
                try:
                    geometry, identifier = future.result()
                    target_crs = self.determine_zone(identifier)

                    # exterior_coords = list(geometry.exterior.coords)
                    # first_point = exterior_coords[0]  # This is a tuple (x, y)
                    #
                    # x, y = first_point
                    # print(f"First point's X: {x}, Y: {y}")
                except ValueError as e:
                    self.error_occurred.emit(str(e))
                    continue

                # Check if zone are same for each identifier
                if self.set_zone:
                    if target_crs == self.set_zone:
                        if self.make_transformation_to_puwg_2000:
                            geometry = self.transform_to_puwg_2000(geometry, target_crs)

                        if self.draw_as_lines_flag:
                            self.draw_lines(geometry, identifier)
                        else:
                            self.draw_as_polygon(geometry, identifier)

                        progress = (i + 1) / len(self.identifiers) * 100
                        self.progress_updated.emit(progress)
                    else:
                        raise WrongZoneError(identifier)
                else:
                    self.set_zone = target_crs

    def save_dxf(self):
        directory, filename = os.path.split(self.full_path)
        try:
            self.doc.saveas(self.full_path)
        except FileNotFoundError:
            raise PathNotFoundError(directory)

    @staticmethod
    def determine_zone(identifier):
        starting_sequence = identifier[:4]
        if starting_sequence in zone_5_teryts:
            return 'EPSG:2176'
        elif starting_sequence in zone_6_teryts:
            return 'EPSG:2177'
        elif starting_sequence in zone_7_teryts:
            return 'EPSG:2178'
        elif starting_sequence in zone_8_teryts:
            return 'EPSG:2179'

    @staticmethod
    def transform_to_puwg_2000(geometry, target_crs):
        # Define source CRS
        source_crs = 'EPSG:2180'  # PUWG 1992

        # Create a transformer object for the CRS transformation
        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

        # Perform the transformation and return
        return transform(transformer.transform, geometry)


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

        # Copyright Label
        copyright_label = QLabel("Copyright © 2024 Michał Chmielewski")
        copyright_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)  # Align to bottom right

        # Add a spacer to push the copyright label to the bottom right corner
        spacer = QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)

        layout.addWidget(copyright_label)

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

    def read_identifiers_from_file(self, file_path):
        with open(file_path, 'r') as file:
            return file.read().split(',')

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

        if not is_polygon:
            draw_as_lines = True
        self.drawer = ParcelDrawer(list_of_identifiers, file_path, draw_as_lines=draw_as_lines,
                                   line_color=color_aci[color], polygon_color=color_aci[color],
                                   identifier_color=color_aci[color_id], add_identifier_at_layer=add_identifier,
                                   make_transformation_to_puwg_2000=puwg_transformation)
        self.drawer.error_occurred.connect(self.show_error_message)
        self.drawer.progress_updated.connect(self.update_progress_bar)

        self.drawer.read_or_create_dxf()
        try:
            self.drawer.process_parcels()
        except ConnectionError:
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ParcelDrawerGUI()
    ex.show()
    sys.exit(app.exec_())
