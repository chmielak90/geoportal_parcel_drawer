# Parcel Drawer Application

## Overview
The Parcel Drawer application is a PyQt5-based tool for processing and visualizing parcel data. It fetches parcel data using the ULDK API and generates DXF files with parcel outlines.

## Features
- Fetch parcel data using identifiers from the ULDK API.
- Generate DXF files with parcel outlines, either as polygons or lines.
- Option to include parcel identifiers in the DXF file.
- Customizable color settings for lines and polygons.
- Progress bar indicating the process completion status.
- Supports English and Polish languages based on system settings.
- Option to convert coordinate system from PUWG 1992 to PUWG 2000 with auto-detection of zone

## Usage
1. Enter parcel identifiers separated by commas in the input field or load from file.
2. (Optional) convert coordinate system from PUWG 1992 to PUWG 2000
3. Choose the file path to save the DXF file.
4. Select the drawing option: Polygon or Lines.
5. Choose whether to add identifiers to the parcels.
6. Select the color for the layer.
7. Click 'Ok' to start processing and generating the DXF file.

## Requirements
- Python 3
- PyQt5
- ezdxf
- shapely
- requests

## Note
This application is designed to work with the ULDK API for processing parcel data and requires an active internet connection for fetching data.

------------------------------------------------------------------------------------------------------

# Aplikacja Parcel Drawer - Pobieranie Obrysu Działek z GeoPortal

## Przegląd
Aplikacja Parcel Drawer to narzędzie oparte na PyQt5 do przetwarzania i wizualizacji danych działek. Pobiera dane działek za pomocą API ULDK i generuje pliki DXF z zarysami działek.

## Funkcje
- Pobieranie danych działek za pomocą identyfikatorów z API ULDK.
- Generowanie plików DXF z zarysami działek, jako poligony lub linie.
- Opcja dołączania identyfikatorów działek do pliku DXF.
- Możliwość dostosowania ustawień kolorów dla linii i poligonów.
- Pasek postępu wskazujący status ukończenia procesu.
- Wsparcie języków angielskiego i polskiego w zależności od ustawień systemowych.
- Opcjonalnie, możliwość konwersji układu PUWG 1992 do PUWG 2000 z automatyczną detekcją odpowiedniej strefy

## Użycie
1. Wprowadź identyfikatory działek oddzielone przecinkami w polu wejściowym.
2. (Opcjonalnie) Zaznacz konwersję do układu PUWG 2000
3. Wybierz ścieżkę do zapisania pliku DXF.
4. Wybierz opcję rysowania: Poligon lub Linie.
5. Wybierz, czy dodać identyfikatory do działek.
6. Wybierz kolor warstwy.
7. Kliknij 'Ok', aby rozpocząć przetwarzanie i generowanie pliku DXF.

## Wymagania
- Python 3
- PyQt5
- ezdxf
- shapely
- requests

## Uwaga
Aplikacja jest zaprojektowana do pracy z API ULDK do przetwarzania danych działek i wymaga aktywnego połączenia z internetem do pobierania danych.
