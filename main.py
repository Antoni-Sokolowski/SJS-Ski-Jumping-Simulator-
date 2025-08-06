"""Główny plik uruchamiający aplikację symulatora skoków narciarskich."""

import sys
import os
import json
import copy
import random
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QSpinBox,
    QPushButton,
    QTextEdit,
    QLabel,
    QStackedWidget,
    QSlider,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFormLayout,
    QScrollArea,
    QDoubleSpinBox,
    QLineEdit,
    QTabWidget,
    QFileDialog,
    QProxyStyle,
    QStyle,
    QGroupBox,
    QCheckBox,
)
from PySide6.QtCore import (
    Qt,
    QUrl,
    QTimer,
    QSize,
    QPoint,
    QThread,
    Signal as pyqtSignal,
)
from PySide6.QtGui import QIcon, QPixmap, QImage, QPainter, QPolygon, QColor, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.animation as animation
import numpy as np
import math
from PIL import Image, ImageDraw
from src.simulation import load_data_from_json, inrun_simulation, fly_simulation
from src.hill import Hill
from src.jumper import Jumper
from utils.constants import GRAVITY, AIR_DENSITY
from utils.helpers import gravity_force_parallel, friction_force, drag_force


def calculate_jump_points(distance: float, k_point: float) -> float:
    """
    Oblicza punkty za skok na podstawie odległości i punktu K.

    Args:
        distance: Odległość skoku w metrach
        k_point: Punkt K skoczni w metrach

    Returns:
        Punkty za skok (60 punktów za skok na K-point, +/- za każdy metr)
    """
    # Oblicz różnicę od K-point
    difference = distance - k_point

    # Określ meter value na podstawie K-point
    meter_value = get_meter_value(k_point)

    # Oblicz punkty: 60 + (różnica * meter_value)
    points = 60.0 + (difference * meter_value)

    return points


def get_meter_value(k_point: float) -> float:
    """Returns the meter value based on the K-point, as per FIS table."""
    if k_point <= 24:
        return 4.8
    elif k_point <= 29:
        return 4.4
    elif k_point <= 34:
        return 4.0
    elif k_point <= 39:
        return 3.6
    elif k_point <= 49:
        return 3.2
    elif k_point <= 59:
        return 2.8
    elif k_point <= 69:
        return 2.4
    elif k_point <= 79:
        return 2.2
    elif k_point <= 99:
        return 2.0
    elif k_point <= 169:
        return 1.8
    else:
        return 1.2


def round_distance_to_half_meter(distance: float) -> float:
    """Rounds distance to the nearest 0.5m precision."""
    return round(distance * 2) / 2


def get_qualification_limit(k_point: float) -> int:
    """
    Określa liczbę zawodników awansujących z kwalifikacji na podstawie typu skoczni.

    Args:
        k_point: Punkt K skoczni w metrach

    Returns:
        int: Liczba zawodników awansujących (40 dla mamucich, 50 dla pozostałych)
    """
    # Skocznie mamucie (K >= 170) mają przelicznik 1.2 i limit 40 zawodników
    if k_point >= 170:
        return 40
    else:
        return 50


def slider_to_drag_coefficient(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na współczynnik oporu aerodynamicznego (0.5-0.38).
    """
    # Mapowanie: 0 -> 0.5, 100 -> 0.38
    return 0.5 - (slider_value / 100.0) * (0.5 - 0.38)


def drag_coefficient_to_slider(drag_coefficient: float) -> int:
    """
    Konwertuje współczynnik oporu aerodynamicznego (0.5-0.38) na wartość slidera (0-100).
    """
    # Mapowanie: 0.5 -> 0, 0.38 -> 100
    if drag_coefficient >= 0.5:
        return 0
    elif drag_coefficient <= 0.38:
        return 100
    else:
        return int(((0.5 - drag_coefficient) / (0.5 - 0.38)) * 100)


def slider_to_jump_force(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na siłę wybicia (1000N-2000N).
    """
    # Mapowanie: 0 -> 1000N, 100 -> 2000N
    return 1000.0 + (slider_value / 100.0) * (2000.0 - 1000.0)


def jump_force_to_slider(jump_force: float) -> int:
    """
    Konwertuje siłę wybicia (1000N-2000N) na wartość slidera (0-100).
    """
    # Mapowanie: 1000N -> 0, 2000N -> 100
    if jump_force <= 1000.0:
        return 0
    elif jump_force >= 2000.0:
        return 100
    else:
        return int(((jump_force - 1000.0) / (2000.0 - 1000.0)) * 100)


def slider_to_lift_coefficient(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na współczynnik siły nośnej (0.5-1.0).
    """
    # Mapowanie: 0 -> 0.5, 100 -> 1.0
    return 0.5 + (slider_value / 100.0) * (1.0 - 0.5)


def lift_coefficient_to_slider(lift_coefficient: float) -> int:
    """
    Konwertuje współczynnik siły nośnej (0.5-1.0) na wartość slidera (0-100).
    """
    # Mapowanie: 0.5 -> 0, 1.0 -> 100
    if lift_coefficient <= 0.5:
        return 0
    elif lift_coefficient >= 1.0:
        return 100
    else:
        return int(((lift_coefficient - 0.5) / (1.0 - 0.5)) * 100)


def slider_to_drag_coefficient_flight(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na współczynnik oporu aerodynamicznego w locie (0.5-0.4).
    """
    # Mapowanie: 0 -> 0.5, 100 -> 0.4
    result = 0.5 - (slider_value / 100.0) * (0.5 - 0.4)
    return result


def drag_coefficient_flight_to_slider(drag_coefficient: float) -> int:
    """
    Konwertuje współczynnik oporu aerodynamicznego w locie (0.5-0.4) na wartość slidera (0-100).
    """
    # Mapowanie: 0.5 -> 0, 0.4 -> 100
    if drag_coefficient >= 0.5:
        return 0
    elif drag_coefficient <= 0.4:
        return 100
    else:
        result = round(((0.5 - drag_coefficient) / (0.5 - 0.4)) * 100)
        return result


def style_to_frontal_area(style: str) -> float:
    """
    Konwertuje styl lotu na powierzchnię czołową.
    """
    style_mapping = {"Normalny": 0.52, "Agresywny": 0.5175, "Pasywny": 0.5225}
    return style_mapping.get(style, 0.52)  # Default to Normalny


def frontal_area_to_style(frontal_area: float) -> str:
    """
    Konwertuje powierzchnię czołową na styl lotu.
    """
    if abs(frontal_area - 0.5175) < 0.002:
        return "Agresywny"
    elif abs(frontal_area - 0.5225) < 0.002:
        return "Pasywny"
    else:
        return "Normalny"


def apply_style_physics(jumper, style: str):
    """
    Aplikuje styl lotu z zrównoważonymi efektami fizycznymi.
    Każdy styl ma małe zmiany (±0.5%) w różnych parametrach.
    """
    if style == "Agresywny":
        # Mniejsza powierzchnia = lepsze wykorzystanie siły nośnej i mniejszy opór
        jumper.flight_frontal_area = 0.5175
        jumper.flight_lift_coefficient *= 1.005  # +0.5% siły nośnej
        jumper.flight_drag_coefficient *= 0.995  # -0.5% oporu

    elif style == "Pasywny":
        # Większa powierzchnia = gorsze wykorzystanie siły nośnej i większy opór
        jumper.flight_frontal_area = 0.5225
        jumper.flight_lift_coefficient *= 0.995  # -0.5% siły nośnej
        jumper.flight_drag_coefficient *= 1.005  # +0.5% oporu

    else:  # Normalny
        # Neutralny styl - bez zmian w innych parametrach
        jumper.flight_frontal_area = 0.52
        # Bez zmian w flight_lift_coefficient i flight_drag_coefficient


class RecommendedGateWorker(QThread):
    """
    Worker thread do obliczania rekomendowanej belki w tle.
    """

    calculation_finished = pyqtSignal(int, float)  # recommended_gate, max_distance

    def __init__(self, hill, jumpers):
        super().__init__()
        self.hill = hill
        self.jumpers = jumpers

    def run(self):
        """
        Wykonuje obliczenia rekomendowanej belki w osobnym wątku.
        """
        if not self.jumpers or not self.hill:
            self.calculation_finished.emit(1, 0.0)
            return

        # Sprawdź każdą belkę od najwyższej do najniższej
        for gate in range(self.hill.gates, 0, -1):
            max_distance = 0
            safe_gate = True

            # Sprawdź wszystkich zawodników na tej belce
            for jumper in self.jumpers:
                try:
                    distance = fly_simulation(self.hill, jumper, gate_number=gate)
                    max_distance = max(max_distance, distance)

                    # Jeśli którykolwiek skoczek przekracza HS, ta belka nie jest bezpieczna
                    if distance > self.hill.L:
                        safe_gate = False
                        break

                except Exception:
                    # W przypadku błędu symulacji, uznaj belkę za niebezpieczną
                    safe_gate = False
                    break

            # Jeśli wszystkie skoki są bezpieczne, to jest rekomendowana belka
            if safe_gate:
                self.calculation_finished.emit(gate, max_distance)
                return

        # Jeśli żadna belka nie jest bezpieczna, zwróć najniższą
        self.calculation_finished.emit(1, 0.0)


def calculate_recommended_gate(hill, jumpers):
    """
    Oblicza rekomendowaną belkę na podstawie skoczni i listy zawodników.
    Rekomendowana belka to najwyższa belka, z której żaden skoczek nie skacze powyżej HS.

    Args:
        hill: Obiekt skoczni
        jumpers: Lista zawodników do sprawdzenia

    Returns:
        int: Numer rekomendowanej belki (1-based)
    """
    if not jumpers or not hill:
        return 1

    # Sprawdź każdą belkę od najwyższej do najniższej
    for gate in range(hill.gates, 0, -1):
        max_distance = 0
        safe_gate = True

        # Sprawdź wszystkich zawodników na tej belce
        for jumper in jumpers:
            try:
                distance = fly_simulation(hill, jumper, gate_number=gate)
                max_distance = max(max_distance, distance)

                # Jeśli którykolwiek skoczek przekracza HS, ta belka nie jest bezpieczna
                if distance > hill.L:
                    safe_gate = False
                    break

            except Exception:
                # W przypadku błędu symulacji, uznaj belkę za niebezpieczną
                safe_gate = False
                break

        # Jeśli wszystkie skoki są bezpieczne, to jest rekomendowana belka
        if safe_gate:
            return gate

    # Jeśli żadna belka nie jest bezpieczna, zwróć najniższą
    return 1


def format_distance_with_unit(distance: float) -> str:
    """Formatuje odległość z jednostką, zaokrąglając do 0.5m."""
    rounded_distance = round_distance_to_half_meter(distance)
    return f"{rounded_distance:.1f} m"


def create_arrow_pixmap(direction, color):
    """Tworzy pixmapę ze strzałką (trójkątem) o danym kolorze."""
    pixmap = QPixmap(10, 10)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    if direction == "up":
        points = [QPoint(5, 2), QPoint(2, 7), QPoint(8, 7)]
    else:  # down
        points = [QPoint(5, 8), QPoint(2, 3), QPoint(8, 3)]
    painter.drawPolygon(QPolygon(points))
    painter.end()
    return pixmap


class CustomSpinBox(QSpinBox):
    """
    Niestandardowy SpinBox z własnymi przyciskami, gwarantujący
    poprawny wygląd i blokadę scrolla.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)

        self.up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.up_button.clicked.connect(self.stepUp)
        self.down_button.clicked.connect(self.stepDown)

    def set_button_icons(self, up_icon, down_icon):
        self.up_button.setIcon(up_icon)
        self.down_button.setIcon(down_icon)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        button_width = 25
        self.up_button.setGeometry(
            self.width() - button_width, 0, button_width, self.height() // 2
        )
        self.down_button.setGeometry(
            self.width() - button_width,
            self.height() // 2,
            button_width,
            self.height() // 2,
        )

    def wheelEvent(self, event):
        event.ignore()


class CustomDoubleSpinBox(QDoubleSpinBox):
    """
    Niestandardowy DoubleSpinBox z własnymi przyciskami, gwarantujący
    poprawny wygląd i blokadę scrolla.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)

        self.up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.up_button.clicked.connect(self.stepUp)
        self.down_button.clicked.connect(self.stepDown)

    def set_button_icons(self, up_icon, down_icon):
        self.up_button.setIcon(up_icon)
        self.down_button.setIcon(down_icon)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        button_width = 25
        self.up_button.setGeometry(
            self.width() - button_width, 0, button_width, self.height() // 2
        )
        self.down_button.setGeometry(
            self.width() - button_width,
            self.height() // 2,
            button_width,
            self.height() // 2,
        )

    def wheelEvent(self, event):
        event.ignore()


class CustomSlider(QWidget):
    """
    Niestandardowy widget slider z edytowalnym wyświetlaniem wartości.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #2b2b2b;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                border: 2px solid #0078d4;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #106ebe;
                border-color: #106ebe;
            }
            QSlider::sub-page:horizontal {
                background: #0078d4;
                border-radius: 4px;
            }
        """)

        # Custom value spinbox with custom arrow buttons
        self.value_spinbox = CustomDoubleSpinBox()
        self.value_spinbox.setRange(0.0, 100.0)
        self.value_spinbox.setDecimals(2)
        self.value_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                min-width: 60px;
                background: #2b2b2b;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px;
            }
        """)

        self.layout.addWidget(self.slider, 1)
        self.layout.addWidget(self.value_spinbox)

        # Connect signals
        self.slider.valueChanged.connect(self._update_spinbox)
        self.value_spinbox.valueChanged.connect(self._update_slider)

    def set_button_icons(self, up_icon, down_icon):
        """Ustawia ikony przycisków dla spinboxa."""
        self.value_spinbox.set_button_icons(up_icon, down_icon)

    def _update_spinbox(self, value):
        # Prevent recursive calls
        self.value_spinbox.blockSignals(True)
        self.value_spinbox.setValue(float(value))
        self.value_spinbox.blockSignals(False)

    def _update_slider(self, value):
        # Prevent recursive calls
        self.slider.blockSignals(True)
        self.slider.setValue(int(value))
        self.slider.blockSignals(False)

    def value(self):
        return self.value_spinbox.value()

    def setValue(self, value):
        self.slider.setValue(int(value))
        self.value_spinbox.setValue(float(value))

    def setRange(self, min_val, max_val):
        self.slider.setRange(min_val, max_val)
        self.value_spinbox.setRange(float(min_val), float(max_val))


class CustomProxyStyle(QProxyStyle):
    """
    Niestandardowy styl, który nadpisuje domyślny czas wyświetlania podpowiedzi.
    """

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return 100
        try:
            return super().styleHint(hint, option, widget, returnData)
        except TypeError:
            # Fallback dla przypadków gdy argumenty są nieprawidłowych typów
            try:
                return super().styleHint(hint)
            except:
                return 0


def resource_path(relative_path):
    """
    Zwraca bezwzględną ścieżkę do zasobu. Niezbędne do poprawnego działania
    zapakowanej aplikacji (.exe), która przechowuje zasoby w tymczasowym folderze.
    """
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji symulatora skoków narciarskich.
    Zarządza wszystkimi elementami UI, logiką przełączania stron i stanem aplikacji.
    """

    def __init__(self):
        """
        Konstruktor klasy MainWindow. Inicjalizuje całe UI, wczytuje dane
        i ustawia początkowy stan aplikacji.
        """
        super().__init__()
        self.setWindowTitle("Ski Jumping Simulator")

        icon_path = resource_path(os.path.join("assets", "SJS.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        (
            self.MAIN_MENU_IDX,
            self.SIM_TYPE_MENU_IDX,
            self.SINGLE_JUMP_IDX,
            self.COMPETITION_IDX,
            self.DATA_EDITOR_IDX,
            self.DESCRIPTION_IDX,
            self.SETTINGS_IDX,
            self.JUMP_REPLAY_IDX,
            self.POINTS_BREAKDOWN_IDX,
        ) = range(9)

        self.current_theme = "dark"
        self.contrast_level = 1.0
        self.volume_level = 0.3

        self.up_arrow_icon_dark = QIcon(create_arrow_pixmap("up", "#b0b0b0"))
        self.down_arrow_icon_dark = QIcon(create_arrow_pixmap("down", "#b0b0b0"))
        self.up_arrow_icon_light = QIcon(create_arrow_pixmap("up", "#404040"))
        self.down_arrow_icon_light = QIcon(create_arrow_pixmap("down", "#404040"))

        self.themes = {
            "dark": lambda contrast: f"""
                QMainWindow, QWidget {{ background-color: #{self.adjust_brightness("1a1a1a", contrast)}; }}
                QLabel {{ color: #{self.adjust_brightness("ffffff", contrast)}; font-size: 16px; font-family: 'Roboto', 'Segoe UI', Arial, sans-serif; }}
                QLabel.headerLabel {{ font-size: 32px; font-weight: bold; color: #0078d4; }}
                QLabel#replayTitleLabel {{ font-size: 24px; font-weight: bold; color: #{self.adjust_brightness("ffffff", contrast)}; }}
                QLabel#replayStatsLabel {{ font-size: 18px; color: #{self.adjust_brightness("b0b0b0", contrast)}; }}
                QComboBox, QSpinBox, QTextEdit, QListWidget, QTableWidget, QLineEdit, QDoubleSpinBox, QTabWidget::pane {{
                    background-color: #{self.adjust_brightness("2a2a2a", contrast)};
                    color: #{self.adjust_brightness("ffffff", contrast)};
                    border: 1px solid #{self.adjust_brightness("4a4a4a", contrast)};
                    padding: 12px; border-radius: 5px; font-size: 16px;
                }}
                QToolTip {{
                    background-color: #{self.adjust_brightness("111111", contrast)};
                    color: #{self.adjust_brightness("dddddd", contrast)};
                    border: 1px solid #{self.adjust_brightness("4a4a4a", contrast)};
                    padding: 8px;
                    border-radius: 5px;
                    font-size: 14px;
                }}
                QGroupBox {{
                    font-size: 16px;
                    font-weight: bold;
                    color: #{self.adjust_brightness("b0b0b0", contrast)};
                    border: 1px solid #{self.adjust_brightness("4a4a4a", contrast)};
                    border-radius: 8px;
                    margin-top: 10px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 10px;
                }}
                QDoubleSpinBox, QSpinBox {{ padding-right: 25px; }}
                QDoubleSpinBox::up-button, QSpinBox::up-button, QDoubleSpinBox::down-button, QSpinBox::down-button {{
                    width: 0px; border: none;
                }}
                CustomSpinBox > QPushButton, CustomDoubleSpinBox > QPushButton {{
                    background-color: transparent; border: none;
                }}
                CustomSpinBox > QPushButton:hover, CustomDoubleSpinBox > QPushButton:hover {{
                    background-color: #{self.adjust_brightness("3f3f3f", contrast)};
                }}

                QTabWidget::tab-bar {{ alignment: center; }}
                QTabBar::tab {{
                    background: #{self.adjust_brightness("2a2a2a", contrast)};
                    color: #{self.adjust_brightness("b0b0b0", contrast)};
                    border: 1px solid #{self.adjust_brightness("4a4a4a", contrast)};
                    border-bottom: none;
                    padding: 10px 25px;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                }}
                QTabBar::tab:selected {{
                    background: #{self.adjust_brightness("3a3a3a", contrast)};
                    color: #{self.adjust_brightness("ffffff", contrast)};
                }}
                QComboBox QAbstractItemView {{
                    background-color: #{self.adjust_brightness("2a2a2a", contrast)};
                    color: #{self.adjust_brightness("ffffff", contrast)};
                    border: 1px solid #{self.adjust_brightness("4a4a4a", contrast)};
                    selection-background-color: #{self.adjust_brightness("005ea6", contrast)};
                }}
                QListWidget::item {{ padding: 5px; }}
                QListWidget::item:hover {{ background-color: #{self.adjust_brightness("3a3a3a", contrast)}; }}
                QListWidget::item:selected {{ background-color: #{self.adjust_brightness("005ea6", contrast)}; }}
                QListWidget::indicator {{ width: 18px; height: 18px; border-radius: 4px; }}
                QListWidget::indicator:unchecked {{ border: 1px solid #777777; background-color: #2a2a2a; }}
                QListWidget::indicator:checked {{ border: 1px solid #0078d4; background-color: #0078d4; image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iI2ZmZmZmZiIgZD0iTTkgMTYuMTdMNC44MyAxMmwtMS40MSAxLjQxTDkgMTkgMjEgN2wtMS40MS0xLjQxeiIvPjwvc3ZnPg==); }}
                QTableWidget {{ 
                    border: 2px solid #{self.adjust_brightness("4a4a4a", contrast)}; 
                    border-radius: 8px; 
                    background-color: #{self.adjust_brightness("2a2a2a", contrast)}; 
                    gridline-color: #{self.adjust_brightness("4a4a4a", contrast)}; 
                    alternate-background-color: #{self.adjust_brightness("3a3a3a", contrast)}; 
                }}
                QTableWidget::item {{ 
                    padding: 8px; 
                    border: none; 
                    background-color: #{self.adjust_brightness("2a2a2a", contrast)}; 
                    color: #{self.adjust_brightness("ffffff", contrast)}; 
                }}
                QTableWidget::item:hover {{ background-color: #{self.adjust_brightness("0078d4", contrast)}; color: white; }}
                QTableWidget::item:selected {{ background-color: #{self.adjust_brightness("005ea6", contrast)}; color: white; }}
                QHeaderView::section {{ 
                    background-color: #{self.adjust_brightness("3a3a3a", contrast)}; 
                    color: #{self.adjust_brightness("ffffff", contrast)}; 
                    padding: 10px; 
                    border: 1px solid #{self.adjust_brightness("4a4a4a", contrast)}; 
                    font-weight: bold; 
                }}
                QHeaderView::section:hover {{ background-color: #{self.adjust_brightness("4a4a4a", contrast)}; }}
                QPushButton {{ background-color: #{self.adjust_brightness("0078d4", contrast)}; color: #{self.adjust_brightness("ffffff", contrast)}; border: none; padding: 15px; border-radius: 5px; font-size: 20px; font-family: 'Roboto', 'Segoe UI', Arial, sans-serif; }}
                QPushButton:hover {{ background-color: #{self.adjust_brightness("005ea6", contrast)}; }}
                QLabel#authorLabel {{ color: #{self.adjust_brightness("b0b0b0", contrast)}; padding: 0 10px 5px 0; }}
                QPushButton#backArrowButton {{ font-size: 28px; font-weight: bold; color: #{self.adjust_brightness("b0b0b0", contrast)}; background-color: transparent; border: none; padding: 0px; border-radius: 20px; }}
                QPushButton#backArrowButton:hover {{ background-color: #{self.adjust_brightness("2f2f2f", contrast)}; }}
                QSlider::groove:horizontal {{ border: 1px solid #{self.adjust_brightness("4a4a4a", contrast)}; height: 8px; background: #{self.adjust_brightness("2a2a2a", contrast)}; margin: 2px 0; border-radius: 4px; }}
                QSlider::handle:horizontal {{ background: #0078d4; border: 1px solid #0078d4; width: 18px; height: 18px; margin: -5px 0; border-radius: 9px; }}
                QSlider::sub-page:horizontal {{ background: #{self.adjust_brightness("005ea6", contrast)}; border: 1px solid #{self.adjust_brightness("4a4a4a", contrast)}; height: 8px; border-radius: 4px; }}
                QScrollBar:vertical {{ border: none; background: #{self.adjust_brightness("2a2a2a", contrast)}; width: 10px; margin: 0; }}
                QScrollBar::handle:vertical {{ background: #{self.adjust_brightness("555555", contrast)}; min-height: 20px; border-radius: 5px; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
                QScrollBar:horizontal {{ border: none; background: #{self.adjust_brightness("2a2a2a", contrast)}; height: 10px; margin: 0; }}
                QScrollBar::handle:horizontal {{ background: #{self.adjust_brightness("555555", contrast)}; min-width: 20px; border-radius: 5px; }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
            """,
            "light": lambda contrast: f"""
                QMainWindow, QWidget {{ background-color: #{self.adjust_brightness("f0f0f0", contrast)}; }}
                QLabel {{ color: #{self.adjust_brightness("1a1a1a", contrast)}; font-size: 16px; }}
                QLabel.headerLabel {{ font-size: 32px; font-weight: bold; color: #0078d4; }}
                QLabel#replayTitleLabel {{ font-size: 24px; font-weight: bold; color: #{self.adjust_brightness("1a1a1a", contrast)}; }}
                QLabel#replayStatsLabel {{ font-size: 18px; color: #{self.adjust_brightness("404040", contrast)}; }}
                QComboBox, QSpinBox, QTextEdit, QListWidget, QTableWidget, QLineEdit, QDoubleSpinBox, QTabWidget::pane {{ background-color: #{self.adjust_brightness("ffffff", contrast)}; color: #{self.adjust_brightness("1a1a1a", contrast)}; border: 1px solid #{self.adjust_brightness("d0d0d0", contrast)}; padding: 12px; border-radius: 5px; font-size: 16px; }}
                QToolTip {{
                    background-color: #{self.adjust_brightness("ffffff", contrast)};
                    color: #{self.adjust_brightness("1a1a1a", contrast)};
                    border: 1px solid #{self.adjust_brightness("c0c0c0", contrast)};
                    padding: 8px;
                    border-radius: 5px;
                    font-size: 14px;
                }}
                QGroupBox {{
                    font-size: 16px;
                    font-weight: bold;
                    color: #{self.adjust_brightness("404040", contrast)};
                    border: 1px solid #{self.adjust_brightness("d0d0d0", contrast)};
                    border-radius: 8px;
                    margin-top: 10px;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top center;
                    padding: 0 10px;
                }}
                QDoubleSpinBox, QSpinBox {{ padding-right: 25px; }}
                QDoubleSpinBox::up-button, QSpinBox::up-button, QDoubleSpinBox::down-button, QSpinBox::down-button {{
                    width: 0px; border: none;
                }}
                CustomSpinBox > QPushButton, CustomDoubleSpinBox > QPushButton {{
                    background-color: transparent; border: none;
                }}
                CustomSpinBox > QPushButton:hover, CustomDoubleSpinBox > QPushButton:hover {{
                    background-color: #{self.adjust_brightness("e0e0e0", contrast)};
                }}
                QTabWidget::tab-bar {{ alignment: center; }}
                QTabBar::tab {{
                    background: #{self.adjust_brightness("f0f0f0", contrast)};
                    color: #{self.adjust_brightness("505050", contrast)};
                    border: 1px solid #{self.adjust_brightness("d0d0d0", contrast)};
                    border-bottom: none;
                    padding: 10px 25px;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                }}
                QTabBar::tab:selected {{
                    background: #{self.adjust_brightness("ffffff", contrast)};
                    color: #{self.adjust_brightness("1a1a1a", contrast)};
                }}
                QComboBox QAbstractItemView {{
                    border: 1px solid #{self.adjust_brightness("d0d0d0", contrast)};
                    selection-background-color: #{self.adjust_brightness("0078d4", contrast)};
                }}
                QListWidget::item {{ padding: 5px; }}
                QListWidget::item:hover {{ background-color: #{self.adjust_brightness("e0e0e0", contrast)}; }}
                QListWidget::item:selected {{ background-color: #{self.adjust_brightness("0078d4", contrast)}; color: white; }}
                QListWidget::indicator {{ width: 18px; height: 18px; border-radius: 4px; }}
                QListWidget::indicator:unchecked {{ border: 1px solid #999999; background-color: #ffffff; }}
                QListWidget::indicator:checked {{ border: 1px solid #0078d4; background-color: #0078d4; image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iI2ZmZmZmZiIgZD0iTTkgMTYuMTdMNC44MyAxMmwtMS40MSAxLjQxTDkgMTkgMjEgN2wtMS40MS0xLjQxeiIvPjwvc3ZnPg==); }}
                QTableWidget {{ 
                    border: 2px solid #{self.adjust_brightness("d0d0d0", contrast)}; 
                    border-radius: 8px; 
                    background-color: #{self.adjust_brightness("ffffff", contrast)}; 
                    gridline-color: #{self.adjust_brightness("d0d0d0", contrast)}; 
                    alternate-background-color: #{self.adjust_brightness("f8f8f8", contrast)}; 
                }}
                QTableWidget::item {{ 
                    padding: 8px; 
                    border: none; 
                    background-color: #{self.adjust_brightness("ffffff", contrast)}; 
                    color: #{self.adjust_brightness("1a1a1a", contrast)}; 
                }}
                QTableWidget::item:hover {{ background-color: #{self.adjust_brightness("d0eaff", contrast)}; color: #{self.adjust_brightness("1a1a1a", contrast)}; }}
                QTableWidget::item:selected {{ background-color: #{self.adjust_brightness("0078d4", contrast)}; color: white; }}
                QHeaderView::section {{ 
                    background-color: #{self.adjust_brightness("e9e9e9", contrast)}; 
                    color: #{self.adjust_brightness("1a1a1a", contrast)}; 
                    padding: 10px; 
                    border: 1px solid #{self.adjust_brightness("d0d0d0", contrast)}; 
                    font-weight: bold; 
                }}
                QHeaderView::section:hover {{ background-color: #{self.adjust_brightness("d0d0d0", contrast)}; }}
                QPushButton {{ background-color: #{self.adjust_brightness("0078d4", contrast)}; color: #{self.adjust_brightness("ffffff", contrast)}; border: none; padding: 15px; border-radius: 5px; font-size: 20px; }}
                QPushButton:hover {{ background-color: #{self.adjust_brightness("005ea6", contrast)}; }}
                QLabel#authorLabel {{ color: #{self.adjust_brightness("404040", contrast)}; padding: 0 10px 5px 0; }}
                QPushButton#backArrowButton {{ font-size: 28px; font-weight: bold; color: #{self.adjust_brightness("404040", contrast)}; background-color: transparent; border: none; padding: 0px; border-radius: 20px; }}
                QPushButton#backArrowButton:hover {{ background-color: #{self.adjust_brightness("e0e0e0", contrast)}; }}
                QSlider::groove:horizontal {{ border: 1px solid #{self.adjust_brightness("d0d0d0", contrast)}; height: 8px; background: #{self.adjust_brightness("e9e9e9", contrast)}; margin: 2px 0; border-radius: 4px; }}
                QSlider::handle:horizontal {{ background: #0078d4; border: 1px solid #0078d4; width: 18px; height: 18px; margin: -5px 0; border-radius: 9px; }}
                QSlider::sub-page:horizontal {{ background: #{self.adjust_brightness("005ea6", contrast)}; border: 1px solid #{self.adjust_brightness("d0d0d0", contrast)}; height: 8px; border-radius: 4px; }}
                QScrollBar:vertical {{ border: none; background: #{self.adjust_brightness("e9e9e9", contrast)}; width: 10px; margin: 0; }}
                QScrollBar::handle:vertical {{ background: #{self.adjust_brightness("c0c0c0", contrast)}; min-height: 20px; border-radius: 5px; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
                QScrollBar:horizontal {{ border: none; background: #{self.adjust_brightness("e9e9e9", contrast)}; height: 10px; margin: 0; }}
                QScrollBar::handle:horizontal {{ background: #{self.adjust_brightness("c0c0c0", contrast)}; min-width: 20px; border-radius: 5px; }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
            """,
        }
        self.setStyleSheet(self.themes[self.current_theme](self.contrast_level))

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        sound_file = resource_path(os.path.join("assets", "click.wav"))
        self.sound_loaded = os.path.exists(sound_file)
        if self.sound_loaded:
            self.player.setSource(QUrl.fromLocalFile(sound_file))
            self.audio_output.setVolume(self.volume_level)

        try:
            self.all_hills, self.all_jumpers = load_data_from_json()
        except Exception as e:
            title = "Błąd Krytyczny - Nie można wczytać danych"
            message = (
                f"Nie udało się wczytać lub przetworzyć pliku 'data.json'!\n\n"
                f"Błąd: {type(e).__name__}: {e}\n\n"
                f"Upewnij się, że folder 'data' z plikiem 'data.json' istnieje."
            )
            QMessageBox.critical(None, title, message)
            self.all_hills, self.all_jumpers = [], []

        if self.all_jumpers:
            self.all_jumpers.sort(key=lambda jumper: str(jumper))
        if self.all_hills:
            self.all_hills.sort(key=lambda hill: str(hill))

        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.central_widget = QStackedWidget()
        main_layout.addWidget(self.central_widget, 1)

        self.author_label = QLabel("Antoni Sokołowski")
        self.author_label.setObjectName("authorLabel")
        main_layout.addWidget(self.author_label, 0, Qt.AlignRight | Qt.AlignBottom)
        self.setCentralWidget(main_container)

        self.selection_order = []
        self.competition_results = []
        self.current_jumper_index = 0
        self.current_round = 1
        self.selected_jumper, self.selected_hill, self.ani = None, None, None
        self.points_ani = None
        self.replay_ani = None
        self.zoom_ani = None
        self.jumper_edit_widgets = {}
        self.hill_edit_widgets = {}

        # Panel sędziowski
        self.judge_panel = JudgePanel()

        self._create_main_menu()
        self._create_sim_type_menu()
        self._create_single_jump_page()
        self._create_competition_page()
        self._create_data_editor_page()
        self._create_description_page()
        self._create_settings_page()
        self._create_jump_replay_page()
        self._create_points_breakdown_page()

    def _create_main_menu(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(50)
        title = QLabel("Ski Jumping Simulator")
        title.setProperty("class", "headerLabel")
        layout.addWidget(title)
        btn_sim = QPushButton("Symulacja")
        btn_sim.clicked.connect(
            lambda: [
                self.play_sound(),
                self.central_widget.setCurrentIndex(self.SIM_TYPE_MENU_IDX),
            ]
        )
        layout.addWidget(btn_sim)
        btn_editor = QPushButton("Edytor Danych")
        btn_editor.clicked.connect(
            lambda: [
                self.play_sound(),
                self.central_widget.setCurrentIndex(self.DATA_EDITOR_IDX),
            ]
        )
        layout.addWidget(btn_editor)
        btn_desc = QPushButton("Opis Projektu")
        btn_desc.clicked.connect(
            lambda: [
                self.play_sound(),
                self.central_widget.setCurrentIndex(self.DESCRIPTION_IDX),
            ]
        )
        layout.addWidget(btn_desc)
        btn_settings = QPushButton("Ustawienia")
        btn_settings.clicked.connect(
            lambda: [
                self.play_sound(),
                self.central_widget.setCurrentIndex(self.SETTINGS_IDX),
            ]
        )
        layout.addWidget(btn_settings)
        btn_exit = QPushButton("Wyjdź")
        btn_exit.clicked.connect(lambda: [self.play_sound(), self.close()])
        layout.addWidget(btn_exit)
        layout.addStretch()
        self.central_widget.addWidget(widget)

    def _create_sim_type_menu(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.setSpacing(40)
        layout.addLayout(
            self._create_top_bar("Wybierz Tryb Symulacji", self.MAIN_MENU_IDX)
        )
        layout.addStretch(1)
        btn_single = QPushButton("Pojedynczy skok")
        btn_single.clicked.connect(
            lambda: [
                self.play_sound(),
                self.central_widget.setCurrentIndex(self.SINGLE_JUMP_IDX),
            ]
        )
        layout.addWidget(btn_single)
        btn_comp = QPushButton("Zawody")
        btn_comp.clicked.connect(
            lambda: [
                self.play_sound(),
                self.central_widget.setCurrentIndex(self.COMPETITION_IDX),
            ]
        )
        layout.addWidget(btn_comp)
        layout.addStretch(1)
        self.central_widget.addWidget(widget)

    def _create_single_jump_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(
            self._create_top_bar("Symulacja skoku", self.SIM_TYPE_MENU_IDX)
        )

        # Główny layout z podziałem na sekcje
        main_hbox = QHBoxLayout()

        # Lewa sekcja - Konfiguracja skoku
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        # Sekcja wyboru parametrów
        config_group = QGroupBox("Konfiguracja skoku")
        config_group_layout = QVBoxLayout(config_group)
        config_group_layout.setSpacing(10)

        # Wybór zawodnika
        self.jumper_combo = QComboBox()
        self.jumper_combo.addItem("Wybierz zawodnika")
        for jumper in self.all_jumpers:
            self.jumper_combo.addItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )
        self.jumper_combo.currentIndexChanged.connect(self.update_jumper)
        config_group_layout.addLayout(
            self._create_form_row("Zawodnik:", self.jumper_combo)
        )

        # Wybór skoczni
        self.hill_combo = QComboBox()
        self.hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.hill_combo.addItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )
        self.hill_combo.currentIndexChanged.connect(self.update_hill)
        config_group_layout.addLayout(
            self._create_form_row("Skocznia:", self.hill_combo)
        )

        # Wybór belki
        self.gate_spin = QSpinBox()
        self.gate_spin.setMinimum(1)
        self.gate_spin.setMaximum(1)
        config_group_layout.addLayout(self._create_form_row("Belka:", self.gate_spin))

        # Przyciski akcji
        btn_layout = QHBoxLayout()
        self.simulate_button = QPushButton("Uruchom symulację")
        self.simulate_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #005ea6;
            }
            QPushButton:pressed {
                background-color: #004578;
            }
        """)
        self.simulate_button.clicked.connect(self.run_simulation)

        self.clear_button = QPushButton("Wyczyść")
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #495057;
            }
        """)
        self.clear_button.clicked.connect(self.clear_results)

        btn_layout.addWidget(self.simulate_button)
        btn_layout.addWidget(self.clear_button)
        config_group_layout.addLayout(btn_layout)

        left_panel.addWidget(config_group)

        # Sekcja statystyk
        stats_group = QGroupBox("Statystyki skoku")
        stats_group_layout = QVBoxLayout(stats_group)
        stats_group_layout.setSpacing(10)

        # Label na statystyki (zamiast QTextEdit)
        self.single_jump_stats_label = QLabel(
            "Wybierz zawodnika i skocznię, aby rozpocząć symulację"
        )
        self.single_jump_stats_label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-size: 14px;
                padding: 15px;
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 8px;
                border: 2px solid rgba(0, 120, 212, 0.3);
            }
        """)
        self.single_jump_stats_label.setWordWrap(True)
        self.single_jump_stats_label.setAlignment(Qt.AlignCenter)
        stats_group_layout.addWidget(self.single_jump_stats_label)

        left_panel.addWidget(stats_group)
        left_panel.addStretch()

        main_hbox.addLayout(left_panel, 1)

        # Prawa sekcja - Animacja
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        animation_group = QGroupBox("Animacja trajektorii")
        animation_group_layout = QVBoxLayout(animation_group)

        self.figure = Figure(
            facecolor=f"#{self.adjust_brightness('1a1a1a', self.contrast_level)}"
        )
        self.canvas = FigureCanvas(self.figure)
        animation_group_layout.addWidget(self.canvas)

        right_panel.addWidget(animation_group)
        right_panel.addStretch()

        main_hbox.addLayout(right_panel, 2)

        layout.addLayout(main_hbox)
        self.central_widget.addWidget(widget)

    def _create_competition_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Zawody", self.SIM_TYPE_MENU_IDX))

        # Główny layout z podziałem na sekcje
        main_hbox = QHBoxLayout()

        # Lewa sekcja - Konfiguracja zawodów
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        # Sekcja wyboru zawodników
        jumper_group = QGroupBox("Wybór zawodników")
        jumper_group_layout = QVBoxLayout(jumper_group)
        jumper_group_layout.setSpacing(10)

        # Kontrolki wyboru zawodników
        jumper_controls_layout = QHBoxLayout()
        self.toggle_all_button = QPushButton("Zaznacz wszystkich")
        self.toggle_all_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005ea6;
            }
        """)
        self.toggle_all_button.clicked.connect(self._toggle_all_jumpers)
        jumper_controls_layout.addWidget(self.toggle_all_button)

        # Licznik wybranych zawodników
        self.selected_count_label = QLabel("Wybrano: 0 zawodników")
        self.selected_count_label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-weight: bold;
                padding: 8px;
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 4px;
            }
        """)
        jumper_controls_layout.addWidget(self.selected_count_label)
        jumper_group_layout.addLayout(jumper_controls_layout)

        # Sortowanie zawodników
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sortuj:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Wg Nazwiska (A-Z)", "Wg Kraju"])
        self.sort_combo.currentTextChanged.connect(self._sort_jumper_list)
        sort_layout.addWidget(self.sort_combo)
        jumper_group_layout.addLayout(sort_layout)

        # Lista zawodników z lepszym stylem
        self.jumper_list_widget = QListWidget()
        self.jumper_list_widget.setStyleSheet("""
            QListWidget {
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                background-color: #2a2a2a;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
                background-color: transparent;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        self.jumper_list_widget.setMaximumHeight(300)

        for jumper in self.all_jumpers:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, jumper)
            self.jumper_list_widget.addItem(item)
        self.jumper_list_widget.itemChanged.connect(self._on_jumper_item_changed)
        jumper_group_layout.addWidget(self.jumper_list_widget)

        left_panel.addWidget(jumper_group)

        # Sekcja konfiguracji zawodów
        competition_group = QGroupBox("Konfiguracja zawodów")
        competition_group_layout = QVBoxLayout(competition_group)
        competition_group_layout.setSpacing(15)

        # Kontener dla skoczni i belki w jednym wierszu
        hill_gate_container = QHBoxLayout()
        hill_gate_container.setSpacing(20)

        # Wybór skoczni z ikoną
        hill_layout = QVBoxLayout()
        hill_layout.setSpacing(5)
        hill_label = QLabel("Skocznia:")
        hill_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        hill_layout.addWidget(hill_label)

        self.comp_hill_combo = QComboBox()
        self.comp_hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.comp_hill_combo.addItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )
        self.comp_hill_combo.currentIndexChanged.connect(self.update_competition_hill)
        hill_layout.addWidget(self.comp_hill_combo)
        hill_gate_container.addLayout(hill_layout)

        # Wybór belki z rekomendacją
        gate_layout = QVBoxLayout()
        gate_layout.setSpacing(5)
        gate_label = QLabel("Belka:")
        gate_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        gate_layout.addWidget(gate_label)

        # Kontener dla belki i rekomendacji
        gate_input_layout = QHBoxLayout()
        gate_input_layout.setSpacing(10)

        self.comp_gate_spin = QSpinBox()
        self.comp_gate_spin.setMinimum(1)
        self.comp_gate_spin.setMaximum(1)
        gate_input_layout.addWidget(self.comp_gate_spin)

        # Label z rekomendowaną belką
        self.recommended_gate_label = QLabel("")
        self.recommended_gate_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: bold;
                font-size: 12px;
                padding: 4px 8px;
                background-color: rgba(40, 167, 69, 0.1);
                border-radius: 4px;
                border: 1px solid #28a745;
            }
        """)
        self.recommended_gate_label.setVisible(False)
        gate_input_layout.addWidget(self.recommended_gate_label)
        gate_input_layout.addStretch()

        gate_layout.addLayout(gate_input_layout)

        # Dolny wiersz z informacją o rekomendacji
        self.gate_info_label = QLabel("")
        self.gate_info_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-size: 11px;
                font-style: italic;
                padding: 2px 0px;
            }
        """)
        self.gate_info_label.setVisible(False)
        gate_layout.addWidget(self.gate_info_label)

        hill_gate_container.addLayout(gate_layout)
        competition_group_layout.addLayout(hill_gate_container)

        # Opcje kwalifikacji
        qualification_layout = QHBoxLayout()
        qualification_layout.setSpacing(10)

        self.qualification_checkbox = QCheckBox("Kwalifikacje")
        self.qualification_checkbox.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a4a4a;
                border-radius: 3px;
                background-color: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
        """)
        self.qualification_checkbox.setChecked(True)  # Domyślnie włączone
        qualification_layout.addWidget(self.qualification_checkbox)
        qualification_layout.addStretch()

        competition_group_layout.addLayout(qualification_layout)

        # Przycisk rozpoczęcia zawodów z lepszym stylem
        self.run_comp_btn = QPushButton("Rozpocznij zawody")
        self.run_comp_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.run_comp_btn.clicked.connect(self._on_competition_button_clicked)
        competition_group_layout.addWidget(self.run_comp_btn)

        left_panel.addWidget(competition_group)
        left_panel.addStretch()
        main_hbox.addLayout(left_panel, 1)

        # Prawa sekcja - Wyniki zawodów
        results_panel = QVBoxLayout()
        results_panel.setSpacing(15)

        # Status zawodów z lepszym stylem
        self.competition_status_label = QLabel(
            "Tabela wyników (kliknij odległość, aby zobaczyć powtórkę):"
        )

        # Dodajemy informację o aktualnej serii
        self.round_info_label = QLabel("Seria: 1/2")
        self.round_info_label.setStyleSheet("""
            QLabel {
                color: #ffc107;
                font-weight: bold;
                font-size: 12px;
                padding: 5px 10px;
                background-color: rgba(255, 193, 7, 0.1);
                border-radius: 4px;
                border: 1px solid #ffc107;
            }
        """)
        self.round_info_label.setAlignment(Qt.AlignCenter)

        # Layout dla statusu i informacji o serii
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.competition_status_label, 3)
        status_layout.addWidget(self.round_info_label, 1)
        results_panel.addLayout(status_layout)

        # Dodajemy pasek postępu
        self.progress_label = QLabel("Postęp: 0%")
        self.progress_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: bold;
                font-size: 12px;
                padding: 5px 10px;
                background-color: rgba(40, 167, 69, 0.1);
                border-radius: 4px;
                border: 1px solid #28a745;
            }
        """)
        self.progress_label.setAlignment(Qt.AlignCenter)
        results_panel.addWidget(self.progress_label)

        # Tabela wyników z ulepszonym stylem
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(
            8
        )  # Miejsce, Flaga, Zawodnik, I seria (dystans), I seria (punkty), II seria (dystans), II seria (punkty), Suma (pkt)
        self.results_table.setHorizontalHeaderLabels(
            [
                "",
                "",
                "Zawodnik",
                "I seria",
                "I seria (pkt)",
                "II seria",
                "II seria (pkt)",
                "Suma (pkt)",
            ]
        )
        self.results_table.verticalHeader().setDefaultSectionSize(45)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.cellClicked.connect(self._on_result_cell_clicked)

        # Styl tabeli wyników - będzie aktualizowany w update_styles()
        self.results_table.setStyleSheet("")

        # Tabela kwalifikacji - osobna tabela z inną strukturą
        self.qualification_table = QTableWidget()
        self.qualification_table.setColumnCount(
            5
        )  # Miejsce, Flaga, Zawodnik, Dystans, Punkty
        self.qualification_table.setHorizontalHeaderLabels(
            [
                "",
                "",
                "Zawodnik",
                "Dystans",
                "Punkty",
            ]
        )
        self.qualification_table.verticalHeader().setDefaultSectionSize(45)
        self.qualification_table.verticalHeader().setVisible(False)
        self.qualification_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.qualification_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.qualification_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.qualification_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.qualification_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.qualification_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.qualification_table.cellClicked.connect(
            self._on_qualification_cell_clicked
        )
        self.qualification_table.setVisible(False)  # Domyślnie ukryta

        # Styl tabeli kwalifikacji - będzie aktualizowany w update_styles()
        self.qualification_table.setStyleSheet("")

        results_panel.addWidget(self.results_table)
        results_panel.addWidget(self.qualification_table)
        main_hbox.addLayout(results_panel, 2)

        layout.addLayout(main_hbox)
        self.competition_page = widget
        self.central_widget.addWidget(widget)

    def _create_data_editor_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Edytor Danych", self.MAIN_MENU_IDX))

        main_hbox = QHBoxLayout()
        layout.addLayout(main_hbox, 1)

        # Left panel (Selection)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        editor_sort_layout = QHBoxLayout()
        editor_sort_layout.addWidget(QLabel("Sortuj:"))
        self.editor_sort_combo = QComboBox()
        self.editor_sort_combo.addItems(["Alfabetycznie (A-Z)", "Wg Kraju (A-Z)"])
        editor_sort_layout.addWidget(self.editor_sort_combo)
        left_panel.addLayout(editor_sort_layout)

        self.editor_search_bar = QLineEdit()
        self.editor_search_bar.setPlaceholderText("🔍 Szukaj...")
        left_panel.addWidget(self.editor_search_bar)

        self.editor_tab_widget = QTabWidget()

        jumper_tab = QWidget()
        jumper_tab_layout = QVBoxLayout(jumper_tab)
        jumper_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.editor_jumper_list = QListWidget()
        jumper_tab_layout.addWidget(self.editor_jumper_list)
        self.editor_tab_widget.addTab(jumper_tab, "Skoczkowie")

        hill_tab = QWidget()
        hill_tab_layout = QVBoxLayout(hill_tab)
        hill_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.editor_hill_list = QListWidget()
        hill_tab_layout.addWidget(self.editor_hill_list)
        self.editor_tab_widget.addTab(hill_tab, "Skocznie")

        self._repopulate_editor_lists()

        self.editor_jumper_list.currentItemChanged.connect(self._populate_editor_form)
        self.editor_hill_list.currentItemChanged.connect(self._populate_editor_form)

        self.editor_sort_combo.currentTextChanged.connect(self._sort_editor_lists)
        self.editor_tab_widget.currentChanged.connect(self._filter_editor_lists)
        self.editor_search_bar.textChanged.connect(self._filter_editor_lists)

        left_panel.addWidget(self.editor_tab_widget)

        editor_button_layout = QHBoxLayout()
        self.clone_button = QPushButton("Klonuj")
        self.add_new_button = QPushButton("+ Dodaj")
        self.delete_button = QPushButton("- Usuń zaznaczone")
        editor_button_layout.addWidget(self.clone_button)
        editor_button_layout.addWidget(self.add_new_button)
        editor_button_layout.addWidget(self.delete_button)
        left_panel.addLayout(editor_button_layout)

        self.clone_button.clicked.connect(self._clone_selected_item)
        self.add_new_button.clicked.connect(self._add_new_item)
        self.delete_button.clicked.connect(self._delete_selected_item)

        main_hbox.addLayout(left_panel, 1)

        # Right panel (Form)
        right_panel = QVBoxLayout()

        self.editor_placeholder_label = QLabel(
            "Wybierz obiekt z listy po lewej, aby edytować jego właściwości."
        )
        self.editor_placeholder_label.setAlignment(Qt.AlignCenter)
        self.editor_placeholder_label.setWordWrap(True)

        jumper_form_scroll = QScrollArea()
        jumper_form_scroll.setWidgetResizable(True)
        self.jumper_form_widget = QWidget()
        self.jumper_edit_widgets = self._create_editor_form_content(
            self.jumper_form_widget, Jumper
        )
        jumper_form_scroll.setWidget(self.jumper_form_widget)

        hill_form_scroll = QScrollArea()
        hill_form_scroll.setWidgetResizable(True)
        self.hill_form_widget = QWidget()
        self.hill_edit_widgets = self._create_editor_form_content(
            self.hill_form_widget, Hill
        )
        hill_form_scroll.setWidget(self.hill_form_widget)

        self.editor_form_stack = QStackedWidget()
        self.editor_form_stack.addWidget(self.editor_placeholder_label)
        self.editor_form_stack.addWidget(jumper_form_scroll)
        self.editor_form_stack.addWidget(hill_form_scroll)

        right_panel.addWidget(self.editor_form_stack, 1)

        form_button_layout = QHBoxLayout()
        apply_button = QPushButton("Zastosuj zmiany")
        apply_button.clicked.connect(self._save_current_edit)
        save_to_file_button = QPushButton("Zapisz wszystko do pliku...")
        save_to_file_button.clicked.connect(self._save_data_to_json)

        form_button_layout.addWidget(apply_button)
        form_button_layout.addWidget(save_to_file_button)
        right_panel.addLayout(form_button_layout)

        main_hbox.addLayout(right_panel, 2)

        self.central_widget.addWidget(widget)

    def _create_editor_form_content(self, parent_widget, data_class):
        jumper_groups = {
            "Dane Podstawowe": ["name", "last_name", "nationality"],
            "Najazd": [
                "inrun_position",
            ],
            "Wybicie": [
                "takeoff_force",
            ],
            "Lot": [
                "flight_technique",
                "flight_style",
                "flight_resistance",
            ],
            "Lądowanie": [
                "telemark",
            ],
        }
        hill_groups = {
            "Dane Podstawowe": ["name", "country", "K", "L", "gates"],
            "Geometria Najazdu": ["e1", "e2", "t", "gamma_deg", "alpha_deg", "r1"],
            "Profil Zeskoku": [
                "h",
                "n",
                "s",
                "P",
                "l1",
                "l2",
                "a_finish",
                "beta_deg",
                "betaP_deg",
                "betaL_deg",
                "Zu",
            ],
            "Parametry Fizyczne": ["inrun_friction_coefficient"],
        }

        groups = jumper_groups if data_class == Jumper else hill_groups
        jumper_tooltips = {
            "name": "Imię zawodnika.",
            "last_name": "Nazwisko zawodnika.",
            "nationality": "Kod kraju (np. POL, GER, NOR). Wpływa na wyświetlaną flagę.",
            "inrun_position": "Pozycja najazdowa skoczka. Wyższe wartości = lepsza aerodynamika = wyższa prędkość na progu.",
            "takeoff_force": "Siła wybicia skoczka. Wyższe wartości = większa siła odbicia = dłuższe skoki. Kluczowy parametr wpływający na parabolę lotu.",
            "flight_technique": "Technika lotu skoczka. Wyższe wartości = lepsze wykorzystanie siły nośnej = dłuższe skoki.",
            "flight_style": "Styl lotu skoczka. Normalny = zrównoważony styl. Agresywny = mniejsza powierzchnia czołowa. Pasywny = większa powierzchnia czołowa.",
            "flight_resistance": "Opór powietrza w locie. Wyższe wartości = mniejszy opór aerodynamiczny = dłuższe skoki.",
            "telemark": "Umiejętność lądowania telemarkiem. Wyższe wartości = częstsze i ładniejsze lądowania telemarkiem.",
            "landing_drag_coefficient": "Opór aerodynamiczny podczas lądowania (bardzo wysoki).",
            "landing_frontal_area": "Powierzchnia czołowa podczas lądowania (największa).",
            "landing_lift_coefficient": "Siła nośna podczas lądowania (zazwyczaj 0).",
        }
        hill_tooltips = {
            "name": "Oficjalna nazwa skoczni.",
            "country": "Kod kraju (np. POL, GER, NOR). Wpływa na wyświetlaną flagę.",
            "gates": "Całkowita liczba belek startowych dostępnych na skoczni.",
            "e1": "Długość najazdu od najwyższej belki do progu (w metrach).",
            "e2": "Długość najazdu od najniższej belki do progu (w metrach).",
            "t": "Długość drugiej prostej najadzu (w metrach).",
            "inrun_friction_coefficient": "Współczynnik tarcia nart o tory. Wyższe wartości = niższa prędkość na progu. Typowo: 0.02.",
            "P": "Początek strefy lądowania (w metrach).",
            "K": "Punkt konstrukcyjny skoczni w metrach (np. 90, 120, 200).",
            "l1": "Odległość po zeskoku między punktem P a K (w metrach).",
            "l2": "Odległosć po zeskoku między punktem K a L (w metrach).",
            "a_finish": "Długość całego wypłaszczenia zeskoku (w metrach).",
            "L": "Rozmiar skoczni (HS) w metrach. Określa granicę bezpiecznego skoku.",
            "alpha_deg": "Kąt nachylenia progu w stopniach. Kluczowy dla kąta wybicia. Zwykle 10-11 stopni.",
            "gamma_deg": "Kąt nachylenia górnej, stromej części najazdu w stopniach.",
            "r1": "Promień krzywej przejściowej na najeździe (w metrach).",
            "h": "Różnica wysokości między progiem a punktem K.",
            "n": "Odległość w poziomie między progiem a punktem K.",
            "betaP_deg": "Kąt nachylenia zeskoku w punkcie P w stopniach.",
            "beta_deg": "Kąt nachylenia zeskoku w punkcie K w stopniach.",
            "betaL_deg": "Kąt nachylenia zeskoku w punkcie L w stopniach.",
            "Zu": "Wysokość progu nad pełnym wypłaszczeniem zeskoku (w metrach).",
            "s": "Wysokość progu nad zeskokiem.",
        }

        tooltips = jumper_tooltips if data_class == Jumper else hill_tooltips
        widgets = {}
        main_layout = QVBoxLayout(parent_widget)

        for group_title, attributes in groups.items():
            group_box = QGroupBox(group_title)
            form_layout = QFormLayout(group_box)

            for attr in attributes:
                widget = None
                if attr in ["K", "L", "gates"]:
                    widget = CustomSpinBox()
                    widget.setRange(0, 500)
                elif (
                    "coefficient" in attr
                    or "area" in attr
                    or attr
                    in [
                        "e1",
                        "e2",
                        "t",
                        "r1",
                        "h",
                        "n",
                        "s",
                        "l1",
                        "l2",
                        "a_finish",
                        "P",
                        "Zu",
                    ]
                ):
                    widget = CustomDoubleSpinBox()
                    widget.setRange(-10000.0, 10000.0)
                    widget.setDecimals(4)
                    widget.setSingleStep(0.01)
                elif attr in [
                    "inrun_position",
                    "takeoff_force",
                    "flight_technique",
                    "flight_resistance",
                    "telemark",
                ]:
                    widget = CustomSlider()
                    widget.setRange(0, 100)
                elif attr == "flight_style":
                    widget = QComboBox()
                    widget.addItems(["Normalny", "Agresywny", "Pasywny"])
                    # Ustawienie odpowiedniego rozmiaru dla dropdowna
                    widget.setFixedHeight(
                        35
                    )  # Większa wysokość aby tekst był w pełni widoczny
                    widget.setStyleSheet("""
                        QComboBox {
                            padding: 4px;
                            border: 1px solid #555;
                            border-radius: 4px;
                            background: #2b2b2b;
                            color: #ffffff;
                            font-size: 14px;
                        }
                        QComboBox::drop-down {
                            border: none;
                            width: 20px;
                        }
                        QComboBox::down-arrow {
                            image: none;
                            border-left: 5px solid transparent;
                            border-right: 5px solid transparent;
                            border-top: 5px solid #ffffff;
                            margin-right: 5px;
                        }
                        QComboBox QAbstractItemView {
                            background: #2b2b2b;
                            color: #ffffff;
                            border: 1px solid #555;
                            selection-background-color: #0078d4;
                        }
                    """)
                elif "deg" in attr:
                    widget = CustomDoubleSpinBox()
                    widget.setRange(-10000.0, 10000.0)
                    widget.setDecimals(2)
                else:
                    widget = QLineEdit()

                # Ustawienie ikon w zależności od motywu
                if isinstance(
                    widget, (CustomSpinBox, CustomDoubleSpinBox, CustomSlider)
                ):
                    if self.current_theme == "dark":
                        widget.set_button_icons(
                            self.up_arrow_icon_dark, self.down_arrow_icon_dark
                        )
                    else:
                        widget.set_button_icons(
                            self.up_arrow_icon_light, self.down_arrow_icon_light
                        )

                # Special case for Polish labels
                if attr == "inrun_position":
                    label_text = "Pozycja najazdowa:"
                elif attr == "takeoff_force":
                    label_text = "Siła wybicia:"
                elif attr == "flight_technique":
                    label_text = "Technika lotu:"
                elif attr == "flight_style":
                    label_text = "Styl lotu:"
                elif attr == "flight_resistance":
                    label_text = "Opór powietrza:"
                else:
                    label_text = (
                        attr.replace("_", " ").replace("deg", "(deg)").capitalize()
                        + ":"
                    )

                label_widget = QLabel(label_text)
                label_widget.setToolTip(tooltips.get(attr, ""))

                form_layout.addRow(label_widget, widget)
                widgets[attr] = widget

            main_layout.addWidget(group_box)

        main_layout.addStretch()
        return widgets

    def _filter_editor_lists(self):
        search_text = self.editor_search_bar.text().lower().strip()

        current_tab_index = self.editor_tab_widget.currentIndex()
        active_list = (
            self.editor_jumper_list if current_tab_index == 0 else self.editor_hill_list
        )

        for i in range(active_list.count()):
            item = active_list.item(i)
            item_text = item.text().lower()

            if search_text in item_text:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _repopulate_editor_lists(self):
        current_jumper = (
            self.editor_jumper_list.currentItem().data(Qt.UserRole)
            if self.editor_jumper_list.currentItem()
            else None
        )
        current_hill = (
            self.editor_hill_list.currentItem().data(Qt.UserRole)
            if self.editor_hill_list.currentItem()
            else None
        )

        self.editor_jumper_list.clear()
        for jumper in self.all_jumpers:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )
            item.setData(Qt.UserRole, jumper)
            self.editor_jumper_list.addItem(item)
            if jumper == current_jumper:
                self.editor_jumper_list.setCurrentItem(item)

        self.editor_hill_list.clear()
        for hill in self.all_hills:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )
            item.setData(Qt.UserRole, hill)
            self.editor_hill_list.addItem(item)
            if hill == current_hill:
                self.editor_hill_list.setCurrentItem(item)

        self._sort_editor_lists()

    def _sort_editor_lists(self):
        current_tab_index = self.editor_tab_widget.currentIndex()
        list_widget = (
            self.editor_jumper_list if current_tab_index == 0 else self.editor_hill_list
        )

        current_item_data = (
            list_widget.currentItem().data(Qt.UserRole)
            if list_widget.currentItem()
            else None
        )

        items_data = [
            list_widget.item(i).data(Qt.UserRole) for i in range(list_widget.count())
        ]

        sort_text = self.editor_sort_combo.currentText()
        if "Wg Kraju" in sort_text:
            items_data.sort(
                key=lambda x: (
                    getattr(x, "nationality", "") or getattr(x, "country", ""),
                    str(x),
                )
            )
        else:
            items_data.sort(key=lambda x: str(x))

        list_widget.clear()
        new_selection = None
        for data_obj in items_data:
            icon = self.create_rounded_flag_icon(
                getattr(data_obj, "nationality", None)
                or getattr(data_obj, "country", None)
            )
            item = QListWidgetItem(icon, str(data_obj))
            item.setData(Qt.UserRole, data_obj)
            list_widget.addItem(item)
            if current_item_data and data_obj == current_item_data:
                new_selection = item

        if new_selection:
            list_widget.setCurrentItem(new_selection)

        self._filter_editor_lists()

    def _add_new_item(self):
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()

        if current_tab_index == 0:  # Skoczkowie
            new_jumper = Jumper(name="Nowy", last_name="Skoczek", nationality="POL")
            self.all_jumpers.append(new_jumper)

            item = QListWidgetItem(
                self.create_rounded_flag_icon(new_jumper.nationality), str(new_jumper)
            )
            item.setData(Qt.UserRole, new_jumper)
            self.editor_jumper_list.addItem(item)
            self._sort_editor_lists()
            for i in range(self.editor_jumper_list.count()):
                if self.editor_jumper_list.item(i).data(Qt.UserRole) == new_jumper:
                    self.editor_jumper_list.setCurrentRow(i)
                    self.editor_jumper_list.scrollToItem(
                        self.editor_jumper_list.item(i),
                        QListWidget.ScrollHint.PositionAtCenter,
                    )
                    break

        elif current_tab_index == 1:  # Skocznie
            new_hill = Hill(name="Nowa Skocznia", country="POL", K=90, L=120, gates=10)
            self.all_hills.append(new_hill)

            item = QListWidgetItem(
                self.create_rounded_flag_icon(new_hill.country), str(new_hill)
            )
            item.setData(Qt.UserRole, new_hill)
            self.editor_hill_list.addItem(item)
            self._sort_editor_lists()
            for i in range(self.editor_hill_list.count()):
                if self.editor_hill_list.item(i).data(Qt.UserRole) == new_hill:
                    self.editor_hill_list.setCurrentRow(i)
                    self.editor_hill_list.scrollToItem(
                        self.editor_hill_list.item(i),
                        QListWidget.ScrollHint.PositionAtCenter,
                    )
                    break

        self._refresh_all_data_widgets()

    def _clone_selected_item(self):
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()

        if current_tab_index == 0:  # Skoczkowie
            selected_item = self.editor_jumper_list.currentItem()
            if not selected_item:
                QMessageBox.information(
                    self,
                    "Informacja",
                    "Aby sklonować skoczka, najpierw zaznacz go na liście.",
                )
                return

            jumper_to_clone = selected_item.data(Qt.UserRole)
            new_jumper = copy.deepcopy(jumper_to_clone)
            new_jumper.name = f"{jumper_to_clone.name} (kopia)"

            self.all_jumpers.append(new_jumper)

            item = QListWidgetItem(
                self.create_rounded_flag_icon(new_jumper.nationality), str(new_jumper)
            )
            item.setData(Qt.UserRole, new_jumper)
            self.editor_jumper_list.addItem(item)
            self._sort_editor_lists()
            for i in range(self.editor_jumper_list.count()):
                if self.editor_jumper_list.item(i).data(Qt.UserRole) == new_jumper:
                    self.editor_jumper_list.setCurrentRow(i)
                    self.editor_jumper_list.scrollToItem(
                        self.editor_jumper_list.item(i),
                        QListWidget.ScrollHint.PositionAtCenter,
                    )
                    break

        elif current_tab_index == 1:  # Skocznie
            selected_item = self.editor_hill_list.currentItem()
            if not selected_item:
                QMessageBox.information(
                    self,
                    "Informacja",
                    "Aby sklonować skocznię, najpierw zaznacz ją na liście.",
                )
                return

            hill_to_clone = selected_item.data(Qt.UserRole)
            new_hill = copy.deepcopy(hill_to_clone)
            new_hill.name = f"{hill_to_clone.name} (Kopia)"

            self.all_hills.append(new_hill)

            item = QListWidgetItem(
                self.create_rounded_flag_icon(new_hill.country), str(new_hill)
            )
            item.setData(Qt.UserRole, new_hill)
            self.editor_hill_list.addItem(item)
            self._sort_editor_lists()
            for i in range(self.editor_hill_list.count()):
                if self.editor_hill_list.item(i).data(Qt.UserRole) == new_hill:
                    self.editor_hill_list.setCurrentRow(i)
                    self.editor_hill_list.scrollToItem(
                        self.editor_hill_list.item(i),
                        QListWidget.ScrollHint.PositionAtCenter,
                    )
                    break

        self._refresh_all_data_widgets()

    def _delete_selected_item(self):
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()
        active_list = (
            self.editor_jumper_list if current_tab_index == 0 else self.editor_hill_list
        )

        current_item = active_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "Błąd", "Nie zaznaczono żadnego elementu do usunięcia."
            )
            return

        data_obj = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć '{str(data_obj)}'?\nTej operacji nie można cofnąć.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            row = active_list.row(current_item)
            active_list.takeItem(row)

            if isinstance(data_obj, Jumper):
                self.all_jumpers.remove(data_obj)
            elif isinstance(data_obj, Hill):
                self.all_hills.remove(data_obj)

            del data_obj
            self._refresh_all_data_widgets()
            self._populate_editor_form()
            QMessageBox.information(
                self, "Usunięto", "Wybrany element został usunięty."
            )

    def _populate_editor_form(self, current_item=None, previous_item=None):
        active_list_widget = self.editor_tab_widget.currentWidget()
        if isinstance(active_list_widget, QListWidget):
            current_item = active_list_widget.currentItem()
        else:
            current_item = (
                self.editor_jumper_list.currentItem()
                if self.editor_tab_widget.currentIndex() == 0
                else self.editor_hill_list.currentItem()
            )

        if not current_item:
            self.editor_form_stack.setCurrentIndex(0)
            return

        data_obj = current_item.data(Qt.UserRole)
        widgets = {}
        if isinstance(data_obj, Jumper):
            self.editor_form_stack.setCurrentIndex(1)
            widgets = self.jumper_edit_widgets
        elif isinstance(data_obj, Hill):
            self.editor_form_stack.setCurrentIndex(2)
            widgets = self.hill_edit_widgets
        else:
            return

        for attr, widget in widgets.items():
            if not hasattr(data_obj, attr):
                continue

            value = getattr(data_obj, attr)

            widget.blockSignals(True)
            try:
                if attr == "inrun_position":
                    # Konwertuj inrun_drag_coefficient na wartość slidera
                    drag_coeff = getattr(data_obj, "inrun_drag_coefficient", 0.46)
                    slider_value = drag_coefficient_to_slider(drag_coeff)
                    widget.setValue(slider_value)
                elif attr == "takeoff_force":
                    # Konwertuj jump_force na wartość slidera
                    jump_force = getattr(data_obj, "jump_force", 1500.0)
                    slider_value = jump_force_to_slider(jump_force)
                    widget.setValue(slider_value)
                elif attr == "flight_technique":
                    # Konwertuj flight_lift_coefficient na wartość slidera
                    lift_coeff = getattr(data_obj, "flight_lift_coefficient", 0.8)
                    slider_value = lift_coefficient_to_slider(lift_coeff)
                    widget.setValue(slider_value)
                elif attr == "flight_style":
                    # Konwertuj flight_frontal_area na styl
                    frontal_area = getattr(data_obj, "flight_frontal_area", 0.52)
                    style = frontal_area_to_style(frontal_area)
                    widget.setCurrentText(style)
                elif attr == "flight_resistance":
                    # Konwertuj flight_drag_coefficient na wartość slidera
                    drag_coeff = getattr(data_obj, "flight_drag_coefficient", 0.5)
                    slider_value = drag_coefficient_flight_to_slider(drag_coeff)
                    widget.setValue(slider_value)
                elif attr == "telemark":
                    # Ustaw wartość telemark bezpośrednio (nie fizyczna)
                    telemark_value = getattr(data_obj, "telemark", 50)
                    widget.setValue(int(telemark_value))

                elif isinstance(widget, QLineEdit):
                    widget.setText(str(value) if value is not None else "")
                elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                    if value is None:
                        widget.setValue(0)
                    else:
                        widget.setValue(float(value))
            except (ValueError, TypeError) as e:
                print(
                    f"Błąd podczas wypełniania pola dla '{attr}': {e}. Ustawiono wartość domyślną."
                )
                if isinstance(widget, QLineEdit):
                    widget.clear()
                else:
                    widget.setValue(0)
            finally:
                widget.blockSignals(False)

    def _save_current_edit(self):
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()
        active_list_widget = (
            self.editor_jumper_list if current_tab_index == 0 else self.editor_hill_list
        )

        current_item = active_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "Błąd", "Nie wybrano żadnego elementu do zapisania."
            )
            return

        data_obj = current_item.data(Qt.UserRole)
        widgets = {}
        if isinstance(data_obj, Jumper):
            widgets = self.jumper_edit_widgets

        elif isinstance(data_obj, Hill):
            widgets = self.hill_edit_widgets

        for attr, widget in widgets.items():
            if not hasattr(data_obj, attr):
                continue

            try:
                if attr == "inrun_position":
                    # Konwertuj wartość slidera na inrun_drag_coefficient
                    slider_value = widget.value()
                    drag_coefficient = slider_to_drag_coefficient(slider_value)
                    setattr(data_obj, "inrun_drag_coefficient", drag_coefficient)
                elif attr == "takeoff_force":
                    # Konwertuj wartość slidera na jump_force
                    slider_value = widget.value()
                    jump_force = slider_to_jump_force(slider_value)
                    setattr(data_obj, "jump_force", jump_force)
                elif attr == "flight_technique":
                    # Konwertuj wartość slidera na flight_lift_coefficient
                    slider_value = widget.value()
                    lift_coefficient = slider_to_lift_coefficient(slider_value)
                    setattr(data_obj, "flight_lift_coefficient", lift_coefficient)
                elif attr == "flight_style":
                    # Konwertuj styl na parametry fizyczne
                    style = widget.currentText()
                    old_style = getattr(data_obj, "flight_style", "Normalny")

                    # Sprawdź czy styl się rzeczywiście zmienił
                    if style != old_style:
                        frontal_area = style_to_frontal_area(style)
                        setattr(data_obj, "flight_frontal_area", frontal_area)
                        setattr(data_obj, "flight_style", style)

                        # Aplikuj dodatkowe efekty stylu na inne parametry
                        apply_style_physics(data_obj, style)
                    else:
                        # Jeśli styl się nie zmienił, tylko zaktualizuj flight_frontal_area
                        frontal_area = style_to_frontal_area(style)
                        setattr(data_obj, "flight_frontal_area", frontal_area)
                        setattr(data_obj, "flight_style", style)
                elif attr == "flight_resistance":
                    # Konwertuj wartość slidera na flight_drag_coefficient
                    slider_value = widget.value()
                    drag_coefficient = slider_to_drag_coefficient_flight(slider_value)
                    setattr(data_obj, "flight_drag_coefficient", drag_coefficient)
                elif attr == "telemark":
                    # Zapisz wartość telemark bezpośrednio (nie fizyczna)
                    slider_value = widget.value()
                    setattr(data_obj, "telemark", slider_value)

                elif isinstance(widget, QLineEdit):
                    new_value = widget.text()
                    setattr(data_obj, attr, new_value)
                elif isinstance(widget, QComboBox):
                    new_value = widget.currentText()
                    setattr(data_obj, attr, new_value)
                elif isinstance(widget, QDoubleSpinBox):
                    new_value = widget.value()
                    setattr(data_obj, attr, new_value)
                elif isinstance(widget, QSpinBox):
                    new_value = widget.value()
                    setattr(data_obj, attr, new_value)
            except Exception as e:
                print(f"Nie udało się zapisać atrybutu '{attr}': {e}")

        if isinstance(data_obj, Hill):
            data_obj.recalculate_derived_attributes()

        current_item.setText(str(data_obj))
        if hasattr(data_obj, "country"):
            current_item.setIcon(self.create_rounded_flag_icon(data_obj.country))
        elif hasattr(data_obj, "nationality"):
            current_item.setIcon(self.create_rounded_flag_icon(data_obj.nationality))

        self._refresh_all_data_widgets()

        QMessageBox.information(
            self,
            "Sukces",
            f"Zmiany dla '{str(data_obj)}' zostały zastosowane w aplikacji.",
        )

    def _save_data_to_json(self):
        self.play_sound()
        data_dir = resource_path("data")
        default_path = os.path.join(data_dir, "data.json")

        filePath, _ = QFileDialog.getSaveFileName(
            self, "Zapisz plik danych", default_path, "JSON Files (*.json)"
        )

        if not filePath:
            return

        try:
            data_to_save = {
                "hills": [h.to_dict() for h in self.all_hills],
                "jumpers": [j.to_dict() for j in self.all_jumpers],
            }
            with open(filePath, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)

            QMessageBox.information(
                self, "Sukces", f"Dane zostały pomyślnie zapisane do pliku:\n{filePath}"
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Błąd zapisu", f"Nie udało się zapisać pliku.\nBłąd: {e}"
            )

    def _refresh_all_data_widgets(self):
        sel_jumper_text = ""
        if self.jumper_combo.currentIndex() > -1:
            sel_jumper_text = self.jumper_combo.currentText()

        sel_hill_text = ""
        if self.hill_combo.currentIndex() > -1:
            sel_hill_text = self.hill_combo.currentText()

        sel_comp_hill_text = ""
        if self.comp_hill_combo.currentIndex() > -1:
            sel_comp_hill_text = self.comp_hill_combo.currentText()

        self.all_jumpers.sort(key=lambda jumper: str(jumper))
        self.all_hills.sort(key=lambda hill: str(hill))

        self.jumper_combo.clear()
        self.jumper_combo.addItem("Wybierz zawodnika")
        for jumper in self.all_jumpers:
            self.jumper_combo.addItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )

        self.hill_combo.clear()
        self.hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.hill_combo.addItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )

        self.comp_hill_combo.clear()
        self.comp_hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.comp_hill_combo.addItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )

        self.jumper_list_widget.clear()
        for jumper in self.all_jumpers:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, jumper)
            self.jumper_list_widget.addItem(item)
        self._sort_jumper_list(self.sort_combo.currentText())

        self.jumper_combo.setCurrentText(sel_jumper_text)
        self.hill_combo.setCurrentText(sel_hill_text)
        self.comp_hill_combo.setCurrentText(sel_comp_hill_text)

        self._repopulate_editor_lists()

    def _create_jump_replay_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 8, 15, 15)

        layout.addLayout(self._create_top_bar("Powtórka skoku", self.COMPETITION_IDX))

        self.replay_title_label = QLabel("Imię i nazwisko skoczka")
        self.replay_title_label.setObjectName("replayTitleLabel")
        self.replay_title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.replay_title_label)

        self.replay_stats_label = QLabel("Statystyki skoku")
        self.replay_stats_label.setObjectName("replayStatsLabel")
        self.replay_stats_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.replay_stats_label)

        self.replay_figure = Figure(
            facecolor=f"#{self.adjust_brightness('1a1a1a', self.contrast_level)}"
        )
        self.replay_canvas = FigureCanvas(self.replay_figure)
        layout.addWidget(self.replay_canvas)

        self.central_widget.addWidget(widget)

    def _create_points_breakdown_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 8, 15, 15)

        layout.addLayout(self._create_top_bar("Podział punktów", self.COMPETITION_IDX))

        # Hill information at the top
        self.points_hill_info_group = QGroupBox("Informacje o skoczni")
        self.points_hill_info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #ffffff;
                border: 2px solid #4a4a4a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        hill_info_layout = QVBoxLayout(self.points_hill_info_group)

        self.points_hill_name = QLabel()
        self.points_hill_name.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #ffffff;
                padding: 5px;
                font-weight: bold;
            }
        """)
        hill_info_layout.addWidget(self.points_hill_name)

        self.points_gate_info = QLabel()
        self.points_gate_info.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #cccccc;
                padding: 5px;
            }
        """)
        hill_info_layout.addWidget(self.points_gate_info)

        layout.addWidget(self.points_hill_info_group)

        # Tytuł z informacjami o zawodniku
        self.points_title_label = QLabel("Imię i nazwisko skoczka")
        self.points_title_label.setObjectName("replayTitleLabel")
        self.points_title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.points_title_label)

        self.points_info_label = QLabel("Informacje o skoku")
        self.points_info_label.setObjectName("replayStatsLabel")
        self.points_info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.points_info_label)

        # Główny layout z podziałem na dwie kolumny
        main_hbox = QHBoxLayout()

        # Lewa kolumna - Podział punktów
        points_panel = QVBoxLayout()
        points_panel.setSpacing(10)

        # Nowa wizualna tabela z kartami zamiast technicznej tabeli
        self.points_breakdown_container = QWidget()
        self.points_breakdown_layout = QVBoxLayout(self.points_breakdown_container)
        self.points_breakdown_layout.setSpacing(6)

        # Karty będą dodawane dynamicznie w _show_points_breakdown
        points_panel.addWidget(self.points_breakdown_container)

        # Usunięto starą grupę z notami sędziowskimi i starą formułę obliczeniową
        # Teraz używamy tylko kart w self.points_breakdown_layout

        points_panel.addStretch()
        main_hbox.addLayout(points_panel, 1)

        # Prawa kolumna - Animacja trajektorii w tle
        animation_panel = QVBoxLayout()

        self.points_figure = Figure(
            facecolor=f"#{self.adjust_brightness('1a1a1a', self.contrast_level)}"
        )
        self.points_canvas = FigureCanvas(self.points_figure)
        animation_panel.addWidget(self.points_canvas)

        main_hbox.addLayout(animation_panel, 2)
        layout.addLayout(main_hbox)

        self.central_widget.addWidget(widget)

    def _create_description_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(40)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Opis Projektu", self.MAIN_MENU_IDX))
        desc_text = QTextEdit()
        desc_text.setReadOnly(True)
        desc_text.setText("Tutaj pojawi się opis projektu.")
        layout.addWidget(desc_text)
        layout.addStretch()
        self.central_widget.addWidget(widget)

    def _create_settings_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(40)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Ustawienia", self.MAIN_MENU_IDX))

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(
            [
                "Ciemny",
                "Jasny",
            ]
        )
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        layout.addLayout(self._create_form_row("Motyw:", self.theme_combo))

        self.window_mode_combo = QComboBox()
        self.window_mode_combo.addItems(
            ["W oknie", "Pełny ekran w oknie", "Pełny ekran"]
        )
        self.window_mode_combo.setCurrentText("Pełny ekran w oknie")
        self.window_mode_combo.currentTextChanged.connect(self._change_window_mode)
        layout.addLayout(self._create_form_row("Tryb okna:", self.window_mode_combo))

        contrast_label = QLabel("Kontrast:")
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(50, 150)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.change_contrast)
        self.contrast_slider.sliderReleased.connect(self.update_styles)
        layout.addLayout(
            self._create_form_row(contrast_label.text(), self.contrast_slider)
        )

        volume_label = QLabel("Głośność:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.volume_level * 100))
        self.volume_slider.valueChanged.connect(self.change_volume)
        layout.addLayout(self._create_form_row(volume_label.text(), self.volume_slider))

        layout.addStretch()
        self.central_widget.addWidget(widget)

    def _change_window_mode(self, mode):
        if mode == "Pełny ekran":
            self.showFullScreen()
        elif mode == "Pełny ekran w oknie":
            self.showMaximized()
        else:  # "W oknie"
            self.showNormal()

    def _create_top_bar(self, title_text, back_index):
        top_bar = QHBoxLayout()
        btn = QPushButton("←")
        btn.clicked.connect(
            lambda: [self.play_sound(), self.central_widget.setCurrentIndex(back_index)]
        )
        btn.setFixedSize(40, 40)
        btn.setObjectName("backArrowButton")
        top_bar.addWidget(btn, 0, Qt.AlignLeft)
        lbl = QLabel(title_text)
        lbl.setProperty("class", "headerLabel")
        lbl.setAlignment(Qt.AlignCenter)
        top_bar.addWidget(lbl)
        phantom = QWidget()
        phantom.setFixedSize(40, 40)
        top_bar.addWidget(phantom, 0, Qt.AlignRight)
        return top_bar

    def _create_form_row(self, label_text, widget):
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        row.addWidget(widget)
        return row

    def _on_jumper_item_changed(self, item):
        jumper = item.data(Qt.UserRole)
        if item.checkState() == Qt.Checked:
            if jumper not in self.selection_order:
                self.selection_order.append(jumper)
        else:
            if jumper in self.selection_order:
                self.selection_order.remove(jumper)

        # Aktualizuj licznik wybranych zawodników
        if hasattr(self, "selected_count_label"):
            count = len(self.selection_order)
            self.selected_count_label.setText(f"Wybrano: {count} zawodników")
            if count > 0:
                self.selected_count_label.setStyleSheet("""
                    QLabel {
                        color: #28a745;
                        font-weight: bold;
                        padding: 8px;
                        background-color: rgba(40, 167, 69, 0.1);
                        border-radius: 4px;
                    }
                """)
            else:
                self.selected_count_label.setStyleSheet("""
                    QLabel {
                        color: #0078d4;
                        font-weight: bold;
                        padding: 8px;
                        background-color: rgba(0, 120, 212, 0.1);
                        border-radius: 4px;
                    }
                """)

        # Aktualizuj rekomendowaną belkę jeśli skocznia jest wybrana
        if hasattr(self, "comp_hill_combo") and self.comp_hill_combo.currentIndex() > 0:
            hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
            self._update_recommended_gate(hill)

    def _toggle_all_jumpers(self):
        self.play_sound()
        checked_count = sum(
            1
            for i in range(self.jumper_list_widget.count())
            if self.jumper_list_widget.item(i).checkState() == Qt.Checked
        )

        if checked_count < self.jumper_list_widget.count():
            new_state = Qt.Checked
            self.toggle_all_button.setText("☐ Odznacz wszystkich")
            self.toggle_all_button.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
        else:
            new_state = Qt.Unchecked
            self.toggle_all_button.setText("Zaznacz wszystkich")
            self.toggle_all_button.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #005ea6;
                }
            """)

        self.jumper_list_widget.itemChanged.disconnect(self._on_jumper_item_changed)
        for i in range(self.jumper_list_widget.count()):
            self.jumper_list_widget.item(i).setCheckState(new_state)
        self.jumper_list_widget.itemChanged.connect(self._on_jumper_item_changed)

        self.selection_order.clear()
        if new_state == Qt.Checked:
            self.selection_order = [
                self.jumper_list_widget.item(i).data(Qt.UserRole)
                for i in range(self.jumper_list_widget.count())
            ]

        # Aktualizuj licznik wybranych zawodników po zmianie stanu
        if hasattr(self, "selected_count_label"):
            count = len(self.selection_order)
            self.selected_count_label.setText(f"Wybrano: {count} zawodników")
            if count > 0:
                self.selected_count_label.setStyleSheet("""
                    QLabel {
                        color: #28a745;
                        font-weight: bold;
                        padding: 8px;
                        background-color: rgba(40, 167, 69, 0.1);
                        border-radius: 4px;
                    }
                """)
            else:
                self.selected_count_label.setStyleSheet("""
                    QLabel {
                        color: #0078d4;
                        font-weight: bold;
                        padding: 8px;
                        background-color: rgba(0, 120, 212, 0.1);
                        border-radius: 4px;
                    }
                """)

        # Aktualizuj rekomendowaną belkę jeśli skocznia jest wybrana
        if hasattr(self, "comp_hill_combo") and self.comp_hill_combo.currentIndex() > 0:
            hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
            self._update_recommended_gate(hill)

    def _update_recommended_gate(self, hill):
        """
        Aktualizuje wyświetlanie rekomendowanej belki na podstawie wybranej skoczni i zawodników.
        Obliczenia są wykonywane w osobnym wątku, aby nie blokować interfejsu.
        """
        if not hasattr(self, "recommended_gate_label") or not hasattr(
            self, "gate_info_label"
        ):
            return

        if not self.selection_order:
            self.recommended_gate_label.setVisible(False)
            self.gate_info_label.setVisible(False)
            return

        # Zatrzymaj poprzedni worker jeśli istnieje
        if (
            hasattr(self, "recommended_gate_worker")
            and self.recommended_gate_worker.isRunning()
        ):
            self.recommended_gate_worker.quit()
            self.recommended_gate_worker.wait()

        # Pokaż wskaźnik ładowania
        self.recommended_gate_label.setText("Obliczanie rekomendacji...")
        self.recommended_gate_label.setStyleSheet("""
            QLabel {
                color: #ffc107;
                font-weight: bold;
                font-size: 12px;
                padding: 4px 8px;
                background-color: rgba(255, 193, 7, 0.1);
                border-radius: 4px;
                border: 1px solid #ffc107;
            }
        """)
        self.recommended_gate_label.setVisible(True)
        self.gate_info_label.setVisible(False)

        # Utwórz i uruchom worker w osobnym wątku
        self.recommended_gate_worker = RecommendedGateWorker(hill, self.selection_order)
        self.recommended_gate_worker.calculation_finished.connect(
            self._on_recommended_gate_calculated
        )
        self.recommended_gate_worker.start()

    def _on_recommended_gate_calculated(self, recommended_gate, max_distance):
        """
        Callback wywoływany po zakończeniu obliczeń rekomendowanej belki.
        """
        if not hasattr(self, "recommended_gate_label") or not hasattr(
            self, "gate_info_label"
        ):
            return

        # Przywróć normalny styl (niebieski zamiast zielonego)
        self.recommended_gate_label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-weight: bold;
                font-size: 12px;
                padding: 4px 8px;
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 4px;
                border: 1px solid #0078d4;
            }
        """)

        # Aktualizuj wyświetlanie
        self.recommended_gate_label.setText(f"Rekomendowana: {recommended_gate}")
        self.recommended_gate_label.setVisible(True)

        # Ukryj informację o maksymalnej odległości
        self.gate_info_label.setVisible(False)

    def _sort_jumper_list(self, sort_text):
        items_data = []
        for i in range(self.jumper_list_widget.count()):
            item = self.jumper_list_widget.item(i)
            jumper = item.data(Qt.UserRole)
            check_state = item.checkState()
            items_data.append((jumper, check_state))

        if sort_text == "Wg Kraju":
            items_data.sort(key=lambda data: (data[0].nationality, str(data[0])))
        else:
            items_data.sort(key=lambda data: str(data[0]))

        self.jumper_list_widget.itemChanged.disconnect(self._on_jumper_item_changed)
        self.jumper_list_widget.clear()

        for jumper, check_state in items_data:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(check_state)
            item.setData(Qt.UserRole, jumper)
            self.jumper_list_widget.addItem(item)

        self.jumper_list_widget.itemChanged.connect(self._on_jumper_item_changed)

    def _on_result_cell_clicked(self, row, column):
        self.play_sound()

        if row >= len(self.competition_results):
            return

        result_data = self.competition_results[row]
        jumper = result_data["jumper"]

        # Kolumny z dystansami to 3 (I seria) i 5 (II seria)
        if column in [3, 5]:
            seria_num = 1 if column == 3 else 2
            distance_str = self.results_table.item(row, column).text()

            if distance_str == "-":
                return

            try:
                # Extract distance value from format like "123.5 m"
                distance = float(distance_str.replace(" m", ""))
                self._show_jump_replay(
                    jumper,
                    self.competition_hill,
                    self.competition_gate,
                    distance,
                    seria_num,
                )
            except (ValueError, TypeError):
                return

        # Kolumny z punktami to 4 (I seria) i 6 (II seria) - tutaj będą wyświetlane noty sędziów
        elif column in [4, 6]:
            seria_num = 1 if column == 4 else 2
            points_str = self.results_table.item(row, column).text()

            if points_str == "-":
                return

            try:
                points = float(points_str)
                distance = result_data[f"d{seria_num}"]
                judge_data = result_data[f"judges{seria_num}"]

                # Pokaż podział punktów z notami sędziów jeśli dostępne
                self._show_points_breakdown(
                    jumper,
                    distance,
                    points,
                    seria_num,
                    judge_data,
                )
            except (ValueError, TypeError):
                return

        # Kolumna z sumą punktów to 7
        elif column == 7:
            total_points_str = self.results_table.item(row, column).text()

            if total_points_str == "-":
                return

            try:
                total_points = float(total_points_str)
                self._show_total_points_breakdown(
                    jumper,
                    result_data,
                    total_points,
                )
            except (ValueError, TypeError):
                return

    def _on_qualification_cell_clicked(self, row, column):
        """Obsługa kliknięcia w komórkę tabeli kwalifikacji"""
        self.play_sound()

        if not self.qualification_results or row >= len(self.qualification_results):
            return

        result = self.qualification_results[row]
        jumper = result["jumper"]

        # Sprawdź czy kliknięto w kolumnę z dystansem (kolumna 3)
        if column == 3 and result.get("distance", 0) > 0:  # Dystans kwalifikacji
            self._show_jump_replay(
                jumper,
                self.competition_hill,
                self.competition_gate,
                result["distance"],
                "Q",
            )
        # Sprawdź czy kliknięto w kolumnę z punktami (kolumna 4) - tutaj będą wyświetlane noty sędziów
        elif column == 4 and result.get("points", 0) > 0:  # Punkty kwalifikacji
            judge_data = result.get("judge_scores")

            # Pokaż podział punktów z notami sędziów jeśli dostępne
            self._show_points_breakdown(
                jumper, result["distance"], result["points"], "Q", judge_data
            )

    def _show_jump_replay(self, jumper, hill, gate, distance, seria_num):
        sim_data = self._calculate_trajectory(jumper, hill, gate)

        self.replay_title_label.setText(f"{jumper} - Seria {seria_num}")
        stats_text = (
            f"Odległość: {format_distance_with_unit(distance)}  |  "
            f"Prędkość na progu: {sim_data['inrun_velocity_kmh']:.2f} km/h  |  "
            f"Kąt wybicia: {sim_data['takeoff_angle_deg']:.2f}°  |  "
            f"Max wysokość: {sim_data['max_height']:.1f} m  |  "
            f"Czas lotu: {sim_data['flight_time']:.2f} s  |  "
            f"Max prędkość: {sim_data['max_velocity_kmh']:.1f} km/h"
        )
        self.replay_stats_label.setText(stats_text)

        self.central_widget.setCurrentIndex(self.JUMP_REPLAY_IDX)
        self._run_animation_on_canvas(
            self.replay_canvas, self.replay_figure, sim_data, hill
        )

    def _create_distance_card(
        self, distance, k_point, meter_value, difference, distance_points
    ):
        """Tworzy kartę z informacjami o odległości i obliczeniach punktów."""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Tytuł karty
        title = QLabel("Punkty za odległość")
        title.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
                padding: 2px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Główna informacja o odległości
        distance_info = QLabel(f"Odległość: {format_distance_with_unit(distance)}")
        distance_info.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #28a745;
                padding: 6px;
                background-color: rgba(40, 167, 69, 0.1);
                border-radius: 4px;
            }
        """)
        distance_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(distance_info)

        # Szczegóły obliczeń
        details_layout = QHBoxLayout()

        # Lewa kolumna - wartości
        left_col = QVBoxLayout()

        k_point_label = QLabel(f"K-point: {k_point:.1f} m")
        k_point_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #cccccc;
                padding: 2px;
            }
        """)
        left_col.addWidget(k_point_label)

        difference_label = QLabel(f"Różnica: {difference:+.1f} m")
        difference_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #cccccc;
                padding: 2px;
            }
        """)
        left_col.addWidget(difference_label)

        meter_label = QLabel(f"Meter value: {meter_value:.1f} pkt/m")
        meter_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #cccccc;
                padding: 2px;
            }
        """)
        left_col.addWidget(meter_label)

        details_layout.addLayout(left_col)

        # Prawa kolumna - obliczenia
        right_col = QVBoxLayout()

        base_points_label = QLabel("60.0 pkt")
        base_points_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #28a745;
                padding: 2px;
                font-weight: bold;
            }
        """)
        right_col.addWidget(base_points_label)

        bonus_points = difference * meter_value
        bonus_label = QLabel(f"{bonus_points:+.1f} pkt")
        bonus_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #0078d4;
                padding: 2px;
                font-weight: bold;
            }
        """)
        right_col.addWidget(bonus_label)

        total_distance_label = QLabel(f"{distance_points:.1f} pkt")
        total_distance_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #ffffff;
                padding: 4px;
                background-color: #28a745;
                border-radius: 4px;
                font-weight: bold;
            }
        """)
        total_distance_label.setAlignment(Qt.AlignCenter)
        right_col.addWidget(total_distance_label)

        details_layout.addLayout(right_col)
        layout.addLayout(details_layout)

        self.points_breakdown_layout.addWidget(card)

    def _create_judge_card(self, judge_data):
        """Tworzy kartę z informacjami o notach sędziowskich."""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border: 1px solid #4a4a4a;
                border-radius: 6px;
                padding: 8px;
                margin: 2px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        # Tytuł karty
        title = QLabel("Punkty za noty")
        title.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
                padding: 2px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Noty sędziowskie w poziomie
        scores_layout = QHBoxLayout()
        scores_layout.setSpacing(6)

        all_scores = judge_data["all_scores"]

        # Zawsze pokazuj 3 środkowe noty na zielono, 2 skrajne na czerwono.
        # Niezależnie od duplikatów, zawsze dokładnie 2 noty są czerwone (najniższa i najwyższa).

        # Tworzymy listę krotek (wynik, oryginalny_indeks)
        indexed_scores = [(score, i) for i, score in enumerate(all_scores)]

        # Sortujemy po wyniku, aby znaleźć najniższy i najwyższy element
        sorted_indexed_scores = sorted(indexed_scores, key=lambda x: x[0])

        # Zbieramy oryginalne indeksy, które mają być czerwone (pierwszy i ostatni z posortowanej listy)
        red_indices = {sorted_indexed_scores[0][1], sorted_indexed_scores[-1][1]}

        for i, score in enumerate(all_scores):
            score_widget = QWidget()
            score_layout = QVBoxLayout(score_widget)
            score_layout.setSpacing(2)

            # Nazwa sędziego
            judge_name = QLabel(f"Sędzia {i + 1}")
            judge_name.setStyleSheet("""
                QLabel {
                    font-size: 9px;
                    color: #cccccc;
                    font-weight: bold;
                }
            """)
            judge_name.setAlignment(Qt.AlignCenter)
            score_layout.addWidget(judge_name)

            # Nota
            score_label = QLabel(f"{score:.1f}")
            score_label.setAlignment(Qt.AlignCenter)
            score_label.setMinimumSize(35, 25)

            # Kolorowanie not - zawsze 2 skrajne na czerwono, 3 środkowe na zielono
            if i in red_indices:
                # Czerwony dla wykluczonych not (2 skrajne)
                score_label.setStyleSheet("""
                    QLabel {
                        font-size: 13px;
                        font-weight: bold;
                        color: #ffffff;
                        background-color: #dc3545;
                        border-radius: 4px;
                        padding: 4px;
                    }
                """)
            else:
                # Zielony dla liczonych not (3 środkowe)
                score_label.setStyleSheet("""
                    QLabel {
                        font-size: 13px;
                        font-weight: bold;
                        color: #ffffff;
                        background-color: #28a745;
                        border-radius: 4px;
                        padding: 4px;
                    }
                """)

            score_layout.addWidget(score_label)
            scores_layout.addWidget(score_widget)

        layout.addLayout(scores_layout)

        # Suma not
        total_judge_points = judge_data["total_score"]
        judge_summary = QLabel(f"Suma (bez skrajnych): {total_judge_points:.1f} pkt")
        judge_summary.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #0078d4;
                padding: 6px;
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 4px;
            }
        """)
        judge_summary.setAlignment(Qt.AlignCenter)
        layout.addWidget(judge_summary)

        # Informacja o lądowaniu
        landing_info = "Lądowanie: "
        if judge_data["telemark_landing"]:
            landing_info += "Telemark ✅"
        else:
            landing_info += "Zwykłe"

        landing_label = QLabel(landing_info)
        landing_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                color: #cccccc;
                padding: 2px;
            }
        """)
        landing_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(landing_label)

        self.points_breakdown_layout.addWidget(card)

    def _create_total_card(self, distance_points, judge_data):
        """Tworzy kartę z sumą punktów."""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border: 1px solid #28a745;
                border-radius: 6px;
                padding: 8px;
                margin: 3px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        # Tytuł karty
        title = QLabel("Suma punktów")
        title.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
                padding: 2px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Minimalistyczna suma punktów
        if judge_data:
            judge_points = judge_data["total_score"]
            total_points = distance_points + judge_data["total_score"]
            calc_text = f"{total_points:.1f} pkt"
        else:
            calc_text = f"{distance_points:.1f} pkt"

        calc_label = QLabel(calc_text)
        calc_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #28a745;
                padding: 4px;
                background-color: rgba(40, 167, 69, 0.1);
                border-radius: 4px;
            }
        """)
        calc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(calc_label)

        self.points_breakdown_layout.addWidget(card)

    def _show_points_breakdown(
        self, jumper, distance, points, seria_num, judge_data=None
    ):
        """Wyświetla szczegółowy podział punktów za skok na pełnej stronie z animacją w tle."""
        k_point = self.competition_hill.K
        meter_value = get_meter_value(k_point)
        difference = distance - k_point

        # Aktualizuj tytuł i informacje
        self.points_title_label.setText(f"{jumper} - Seria {seria_num}")
        stats_text = (
            f"Odległość: {format_distance_with_unit(distance)}  |  "
            f"Punkty: {points:.1f} pkt  |  "
            f"K-point: {k_point:.1f} m"
        )
        self.points_info_label.setText(stats_text)

        # Clear existing breakdown cards
        while self.points_breakdown_layout.count() > 0:
            item = self.points_breakdown_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Calculate distance points
        distance_points = 60.0 + (difference * meter_value)

        # Create visual breakdown cards
        self._create_distance_card(
            distance, k_point, meter_value, difference, distance_points
        )

        if judge_data:
            self._create_judge_card(judge_data)

        self._create_total_card(distance_points, judge_data)

        # Calculate judge points if available
        judge_points = 0.0
        if judge_data:
            judge_points = judge_data["total_score"]

        # Calculate total points
        total_points = distance_points + judge_points

        # Usunięto referencje do starej formuły obliczeniowej

        # Aktualizuj informacje o skoczni
        self.points_hill_name.setText(f"Skocznia: {self.competition_hill}")
        self.points_gate_info.setText(f"Belka startowa: {self.competition_gate}")

        # Dodaj noty sędziowskie jeśli dostępne są dane
        # Usunięto referencje do starej grupy z notami sędziowskimi

        # Uruchom animację trajektorii w tle
        sim_data = self._calculate_trajectory(
            jumper, self.competition_hill, self.competition_gate
        )
        self._run_animation_on_canvas(
            self.points_canvas, self.points_figure, sim_data, self.competition_hill
        )

        # Przełącz na stronę podziału punktów
        self.central_widget.setCurrentIndex(self.POINTS_BREAKDOWN_IDX)

    def _show_total_points_breakdown(self, jumper, result_data, total_points):
        """Wyświetla szczegółowy podział punktów za obie serie na pełnej stronie z animacją w tle."""
        k_point = self.competition_hill.K
        meter_value = get_meter_value(k_point)

        # Aktualizuj tytuł i informacje
        self.points_title_label.setText(f"{jumper} - Podsumowanie zawodów")
        stats_text = (
            f"Suma punktów: {total_points:.1f} pkt  |  "
            f"K-point: {k_point:.1f} m  |  "
            f"Meter value: {meter_value:.1f} pkt/m"
        )
        self.points_info_label.setText(stats_text)

        # Clear existing breakdown cards
        while self.points_breakdown_layout.count() > 0:
            item = self.points_breakdown_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Prepare data for both series
        series_data = []
        if result_data.get("d1", 0) > 0 and result_data.get("p1", 0) > 0:
            d1 = result_data["d1"]
            p1 = result_data["p1"]
            diff1 = d1 - k_point
            series_data.append(("I seria", d1, p1, diff1))

        if result_data.get("d2", 0) > 0 and result_data.get("p2", 0) > 0:
            d2 = result_data["d2"]
            p2 = result_data["p2"]
            diff2 = d2 - k_point
            series_data.append(("II seria", d2, p2, diff2))

        # Create cards for each series
        for seria_name, distance, points, difference in series_data:
            self._create_series_summary_card(
                seria_name, distance, points, difference, k_point, meter_value
            )

        # Add a total card for both series
        self._create_total_card(
            total_points, None
        )  # Pass None for judge_data as it's a total sum

        # Aktualizuj informacje o skoczni
        self.points_hill_name.setText(f"Skocznia: {self.competition_hill}")
        self.points_gate_info.setText(f"Belka startowa: {self.competition_gate}")

        # Usunięto referencje do starej formuły obliczeniowej

        # Usunięto referencje do starej grupy z notami sędziowskimi

        # Uruchom animację trajektorii w tle (użyj pierwszej serii jeśli dostępna)
        if result_data.get("d1", 0) > 0:
            sim_data = self._calculate_trajectory(
                jumper, self.competition_hill, self.competition_gate
            )
            self._run_animation_on_canvas(
                self.points_canvas, self.points_figure, sim_data, self.competition_hill
            )

        # Przełącz na stronę podziału punktów
        self.central_widget.setCurrentIndex(self.POINTS_BREAKDOWN_IDX)

    def _calculate_trajectory(self, jumper, hill, gate):
        inrun_velocity = inrun_simulation(hill, jumper, gate_number=gate)

        base_cl = jumper.flight_lift_coefficient
        effective_cl = base_cl

        baseline_velocity_ms = 24.5
        max_bonus_velocity_ms = 28.5

        if inrun_velocity > baseline_velocity_ms:
            max_lift_bonus = 0.12

            velocity_factor = (inrun_velocity - baseline_velocity_ms) / (
                max_bonus_velocity_ms - baseline_velocity_ms
            )
            velocity_factor = min(1.0, max(0.0, velocity_factor))

            lift_bonus = max_lift_bonus * velocity_factor
            effective_cl = base_cl + lift_bonus

        positions = [(0, 0)]
        velocities = []
        current_position_x, current_position_y = 0, 0
        initial_total_velocity = inrun_velocity

        initial_velocity_x = initial_total_velocity * math.cos(-hill.alpha_rad)
        initial_velocity_y = initial_total_velocity * math.sin(-hill.alpha_rad)

        velocity_takeoff = (jumper.jump_force * 0.1) / jumper.mass
        velocity_takeoff_x = velocity_takeoff * math.sin(hill.alpha_rad)
        velocity_takeoff_y = velocity_takeoff * math.cos(hill.alpha_rad)

        velocity_x_final = initial_velocity_x + velocity_takeoff_x
        velocity_y_final = initial_velocity_y + velocity_takeoff_y

        takeoff_angle_rad = math.atan2(velocity_y_final, velocity_x_final)

        current_velocity_x = velocity_x_final
        current_velocity_y = velocity_y_final

        time_step = 0.01
        max_hill_length = (
            hill.n + hill.a_finish + 100
        )  # Zwiększ limit aby pokazać całą skocznię
        max_height = 0
        flight_time = 0

        while (
            current_position_y > hill.y_landing(current_position_x)
            and current_position_x < max_hill_length
        ):
            total_velocity = math.sqrt(current_velocity_x**2 + current_velocity_y**2)
            velocities.append(total_velocity)
            angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)
            force_g_y = -jumper.mass * 9.81

            c_d = jumper.flight_drag_coefficient
            c_l = effective_cl
            area = jumper.flight_frontal_area

            force_drag_magnitude = 0.5 * 1.225 * c_d * area * total_velocity**2
            force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
            force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)
            force_lift_magnitude = 0.5 * 1.225 * c_l * area * total_velocity**2
            force_lift_x = -force_lift_magnitude * math.sin(angle_of_flight_rad)
            force_lift_y = force_lift_magnitude * math.cos(angle_of_flight_rad)

            acceleration_x = (force_drag_x + force_lift_x) / jumper.mass
            acceleration_y = (force_g_y + force_drag_y + force_lift_y) / jumper.mass

            current_velocity_x += acceleration_x * time_step
            current_velocity_y += acceleration_y * time_step
            current_position_x += current_velocity_x * time_step
            current_position_y += current_velocity_y * time_step
            # Calculate height above the landing area
            height_above_landing = current_position_y - hill.y_landing(
                current_position_x
            )
            max_height = max(max_height, height_above_landing)
            flight_time += time_step
            positions.append((current_position_x, current_position_y))

        x_landing = np.linspace(
            0, hill.n + hill.a_finish + 50, 100
        )  # Zawsze pokazuj całą skocznię
        y_landing = [hill.y_landing(x_val) for x_val in x_landing]

        # Calculate additional statistics
        max_velocity = max(velocities) if velocities else 0
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0

        return {
            "positions": positions,
            "x_landing": x_landing,
            "y_landing": y_landing,
            "max_height": max_height,
            "max_hill_length": max_hill_length,
            "inrun_velocity_kmh": inrun_velocity * 3.6,
            "takeoff_angle_deg": math.degrees(takeoff_angle_rad),
            "flight_time": flight_time,
            "max_velocity_kmh": max_velocity * 3.6,
            "avg_velocity_kmh": avg_velocity * 3.6,
        }

    def _run_animation_on_canvas(self, canvas, figure, sim_data, hill):
        # Zatrzymaj poprzednią animację jeśli istnieje
        # Użyj różnych zmiennych animacji dla różnych canvasów
        if canvas == self.points_canvas:
            animation_var = "points_ani"
        elif canvas == self.replay_canvas:
            animation_var = "replay_ani"
        else:
            animation_var = "ani"  # fallback dla innych canvasów

        # Zatrzymaj wszystkie animacje dla tego canvasu
        for var in ["ani", "points_ani", "replay_ani", "zoom_ani"]:
            if hasattr(self, var) and getattr(self, var) is not None:
                try:
                    current_ani = getattr(self, var)
                    if (
                        hasattr(current_ani, "event_source")
                        and current_ani.event_source is not None
                    ):
                        current_ani.event_source.stop()
                except Exception:
                    pass  # Ignoruj błędy przy zatrzymywaniu animacji
                setattr(self, var, None)

        # Wyczyść figure przed rozpoczęciem nowej animacji
        figure.clear()
        ax = figure.add_subplot(111)
        ax.set_facecolor(
            f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}"
        )
        figure.patch.set_facecolor(
            f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}"
        )
        ax.axis("off")
        ax.set_aspect("auto")

        inrun_length_to_show = 15.0
        x_inrun = np.linspace(-inrun_length_to_show, 0, 50)
        y_inrun = np.tan(-hill.alpha_rad) * x_inrun
        ax.plot(x_inrun, y_inrun, color="#00aaff", linewidth=3)

        max_y_inrun = y_inrun[0] if len(y_inrun) > 0 else 0
        # Poprawione limity - animacja będzie wyżej i ładniej sformatowana
        ax.set_xlim(-inrun_length_to_show - 5, hill.n + hill.a_finish + 30)
        ax.set_ylim(
            min(min(sim_data["y_landing"]), 0) - 3,
            max(sim_data["max_height"] * 1.3, max_y_inrun) + 3,
        )

        (jumper_point,) = ax.plot(
            [], [], "ro", markersize=10, markeredgecolor="white", markeredgewidth=2
        )
        (trail_line,) = ax.plot([], [], color="#4da8ff", linewidth=3, alpha=0.7)
        (landing_line,) = ax.plot([], [], color="#00aaff", linewidth=4, alpha=0.8)
        plot_elements = [jumper_point, trail_line, landing_line]

        def init():
            for element in plot_elements:
                element.set_data([], [])
            return plot_elements

        def update(frame):
            positions, x_landing, y_landing = (
                sim_data["positions"],
                sim_data["x_landing"],
                sim_data["y_landing"],
            )
            if frame >= max(len(positions), len(x_landing)):
                # Zatrzymaj animację gdy się skończy
                try:
                    current_ani = getattr(self, animation_var)
                    if (
                        hasattr(current_ani, "event_source")
                        and current_ani.event_source is not None
                    ):
                        current_ani.event_source.stop()
                except Exception:
                    pass
                setattr(self, animation_var, None)
                return plot_elements
            if frame < len(positions):
                x, y = positions[frame]
                jumper_point.set_data([x], [y])
                trail_line.set_data(
                    [p[0] for p in positions[: frame + 1]],
                    [p[1] for p in positions[: frame + 1]],
                )
            if frame < len(x_landing):
                landing_line.set_data(x_landing[:frame], y_landing[:frame])
            return plot_elements

        new_ani = animation.FuncAnimation(
            figure,
            update,
            init_func=init,
            frames=max(len(sim_data["positions"]), len(sim_data["x_landing"])),
            interval=8,
            blit=False,
            repeat=False,
        )
        setattr(self, animation_var, new_ani)
        canvas.draw()

    def run_simulation(self):
        self.play_sound()
        if not self.selected_jumper or not self.selected_hill:
            self.single_jump_stats_label.setText(
                "BŁĄD: Musisz wybrać zawodnika i skocznię!"
            )
            self.single_jump_stats_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-size: 14px;
                    padding: 15px;
                    background-color: rgba(220, 53, 69, 0.1);
                    border-radius: 8px;
                    border: 2px solid rgba(220, 53, 69, 0.3);
                }
            """)
            return
        gate = self.gate_spin.value()

        try:
            sim_data = self._calculate_trajectory(
                self.selected_jumper, self.selected_hill, gate
            )
            raw_distance = fly_simulation(
                self.selected_hill, self.selected_jumper, gate
            )
            distance = round_distance_to_half_meter(raw_distance)

            # Oblicz punkty za skok
            points = calculate_jump_points(distance, self.selected_hill.K)

            # Wyświetl statystyki w tym samym stylu co w zawodach
            stats_text = (
                f"Odległość: {format_distance_with_unit(distance)}  |  "
                f"Prędkość na progu: {sim_data['inrun_velocity_kmh']:.2f} km/h  |  "
                f"Kąt wybicia: {sim_data['takeoff_angle_deg']:.2f}°  |  "
                f"Max wysokość: {sim_data['max_height']:.1f} m  |  "
                f"Czas lotu: {sim_data['flight_time']:.2f} s  |  "
                f"Max prędkość: {sim_data['max_velocity_kmh']:.1f} km/h  |  "
                f"Punkty: {points:.1f} pkt"
            )

            self.single_jump_stats_label.setText(stats_text)
            self.single_jump_stats_label.setStyleSheet("""
                QLabel {
                    color: #28a745;
                    font-size: 14px;
                    padding: 15px;
                    background-color: rgba(40, 167, 69, 0.1);
                    border-radius: 8px;
                    border: 2px solid rgba(40, 167, 69, 0.3);
                }
            """)

            self._run_animation_on_canvas(
                self.canvas, self.figure, sim_data, self.selected_hill
            )

        except ValueError as e:
            self.single_jump_stats_label.setText(f"BŁĄD: {str(e)}")
            self.single_jump_stats_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-size: 14px;
                    padding: 15px;
                    background-color: rgba(220, 53, 69, 0.1);
                    border-radius: 8px;
                    border: 2px solid rgba(220, 53, 69, 0.3);
                }
            """)

    def play_sound(self):
        if hasattr(self, "sound_loaded") and self.sound_loaded:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.setPosition(0)
            else:
                self.player.play()

    def adjust_brightness(self, hex_color, contrast):
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        rgb = [min(max(int(c * contrast), 0), 255) for c in rgb]
        return f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def update_jumper(self):
        if self.jumper_combo.currentIndex() > 0:
            self.selected_jumper = self.all_jumpers[
                self.jumper_combo.currentIndex() - 1
            ]
        else:
            self.selected_jumper = None

    def update_hill(self):
        if self.hill_combo.currentIndex() > 0:
            self.selected_hill = self.all_hills[self.hill_combo.currentIndex() - 1]
            if self.selected_hill:
                self.gate_spin.setMaximum(self.selected_hill.gates)
        else:
            self.selected_hill = None

    def update_competition_hill(self):
        if self.comp_hill_combo.currentIndex() > 0:
            hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
            if hill:
                self.comp_gate_spin.setMaximum(hill.gates)
                # Oblicz rekomendowaną belkę dla wybranych zawodników
                self._update_recommended_gate(hill)
        else:
            hill = None
            # Ukryj informację o rekomendowanej belce
            if hasattr(self, "recommended_gate_label"):
                self.recommended_gate_label.setVisible(False)

    def clear_results(self):
        self.jumper_combo.setCurrentIndex(0)
        self.hill_combo.setCurrentIndex(0)
        self.gate_spin.setValue(1)
        self.single_jump_stats_label.setText(
            "Wybierz zawodnika i skocznię, aby rozpocząć symulację"
        )
        self.single_jump_stats_label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-size: 14px;
                padding: 15px;
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 8px;
                border: 2px solid rgba(0, 120, 212, 0.3);
            }
        """)
        if hasattr(self, "figure"):
            self.figure.clear()
            self.canvas.draw()
        # Zatrzymaj wszystkie animacje
        for animation_var in ["ani", "points_ani", "replay_ani", "zoom_ani"]:
            if (
                hasattr(self, animation_var)
                and getattr(self, animation_var) is not None
            ):
                try:
                    current_ani = getattr(self, animation_var)
                    if (
                        hasattr(current_ani, "event_source")
                        and current_ani.event_source is not None
                    ):
                        current_ani.event_source.stop()
                except Exception:
                    pass  # Ignoruj błędy przy zatrzymywaniu animacji
                setattr(self, animation_var, None)

    def change_theme(self, theme):
        theme_mapping = {
            "Ciemny": "dark",
            "Jasny": "light",
        }
        self.current_theme = theme_mapping.get(theme, "dark")
        self.update_styles()

    def change_contrast(self):
        self.contrast_level = self.contrast_slider.value() / 100.0
        self.update_styles()

    def change_volume(self):
        self.volume_level = self.volume_slider.value() / 100.0
        if hasattr(self, "sound_loaded") and self.sound_loaded:
            self.audio_output.setVolume(self.volume_level)

    def update_styles(self):
        self.setStyleSheet(self.themes[self.current_theme](self.contrast_level))

        # Apply styles to both tables
        if hasattr(self, "results_table"):
            self.results_table.setStyleSheet("")
        if hasattr(self, "qualification_table"):
            self.qualification_table.setStyleSheet("")

        if hasattr(self, "figure"):
            self.figure.set_facecolor(
                f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}"
            )
            if hasattr(self, "canvas"):
                self.canvas.draw()
        if hasattr(self, "replay_figure"):
            self.replay_figure.set_facecolor(
                f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}"
            )
            if hasattr(self, "replay_canvas"):
                self.replay_canvas.draw()

    def _create_rounded_flag_pixmap(self, country_code, size=QSize(48, 33), radius=8):
        if not country_code:
            return QPixmap()
        flag_path = resource_path(
            os.path.join("assets", "flags", f"{country_code}.png")
        )
        if not os.path.exists(flag_path):
            return QPixmap()
        try:
            with Image.open(flag_path) as img:
                img_resized = img.resize(
                    (size.width(), size.height()), Image.Resampling.LANCZOS
                ).convert("RGBA")
            mask = Image.new("L", img_resized.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle(((0, 0), img_resized.size), radius=radius, fill=255)
            img_resized.putalpha(mask)
            qimage = QImage(
                img_resized.tobytes("raw", "RGBA"),
                img_resized.width,
                img_resized.height,
                QImage.Format_RGBA8888,
            )
            return QPixmap.fromImage(qimage)
        except Exception as e:
            print(f"Error creating flag pixmap for {country_code}: {e}")
            return QPixmap()

    def create_rounded_flag_icon(self, country_code, radius=6):
        pixmap = self._create_rounded_flag_pixmap(
            country_code, size=QSize(32, 22), radius=radius
        )
        if pixmap.isNull():
            return QIcon()
        return QIcon(pixmap)

    def run_competition(self):
        self.play_sound()
        hill_idx = self.comp_hill_combo.currentIndex()
        if hill_idx == 0 or not self.selection_order:
            self.competition_status_label.setText(
                "BŁĄD: Wybierz skocznię i co najmniej jednego zawodnika!"
            )
            self.competition_status_label.setStyleSheet("""
                QLabel {
                    color: #dc3545;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 10px;
                    background-color: rgba(220, 53, 69, 0.1);
                    border-radius: 6px;
                    border-left: 4px solid #dc3545;
                }
            """)
            QTimer.singleShot(3000, lambda: self._reset_status_label())
            return

        # Reset status label style
        self._reset_status_label()

        self.competition_hill = self.all_hills[hill_idx - 1]
        self.competition_gate = self.comp_gate_spin.value()
        self.competition_results = []
        self.current_jumper_index = 0
        self.current_round = 1
        self.competition_order = self.selection_order
        self.pause_after_qualification = False
        self.pause_after_first_round = False
        self.simulation_running = True  # Flaga kontrolująca symulację

        # Sprawdź czy kwalifikacje są włączone
        self.qualification_enabled = self.qualification_checkbox.isChecked()
        if self.qualification_enabled:
            self.qualification_limit = get_qualification_limit(self.competition_hill.K)
            self.qualification_phase = True  # True = kwalifikacje, False = konkurs
            self.qualification_results = []
            self.qualification_order = self.selection_order.copy()
            self.current_qualification_jumper_index = 0

            # Pokaż tabelę kwalifikacji, ukryj tabelę konkursu
            self.qualification_table.setVisible(True)
            self.results_table.setVisible(False)
        else:
            self.qualification_phase = False
            self.qualification_limit = 0

            # Pokaż tabelę konkursu, ukryj tabelę kwalifikacji
            self.results_table.setVisible(True)
            self.qualification_table.setVisible(False)

        # Aktualizuj informację o serii
        if hasattr(self, "round_info_label"):
            if self.qualification_enabled:
                self.round_info_label.setText("Kwalifikacje")
            else:
                self.round_info_label.setText("Seria: 1/2")

        # Reset postępu
        if hasattr(self, "progress_label"):
            self.progress_label.setText("Postęp: 0%")

        for jumper in self.selection_order:
            self.competition_results.append(
                {
                    "jumper": jumper,
                    "d1": 0.0,
                    "d2": 0.0,
                    "p1": 0.0,  # Punkty za pierwszą serię
                    "p2": 0.0,  # Punkty za drugą serię
                    "judges1": None,  # Noty sędziów za pierwszą serię
                    "judges2": None,  # Noty sędziów za drugą serię
                }
            )

        self.results_table.clearContents()
        self.results_table.setRowCount(len(self.competition_results))
        self._update_competition_table()

        # Lepszy komunikat rozpoczęcia
        if self.qualification_enabled:
            status_text = f"Rozpoczynanie kwalifikacji na {self.competition_hill.name}... ({len(self.selection_order)} zawodników)"
        else:
            status_text = f"Rozpoczynanie zawodów na {self.competition_hill.name}... ({len(self.selection_order)} zawodników)"

        self.competition_status_label.setText(status_text)
        self.competition_status_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: rgba(40, 167, 69, 0.1);
                border-radius: 6px;
                border-left: 4px solid #28a745;
            }
        """)

        # Zmień przycisk na 'Stop' podczas zawodów
        self._update_competition_button("Stop", "#dc3545")

        QTimer.singleShot(500, self._process_next_jumper)

    def _reset_status_label(self):
        """Resetuje status label do domyślnego wyglądu"""
        self.competition_status_label.setText(
            "Tabela wyników (kliknij odległość, aby zobaczyć powtórkę):"
        )
        self.competition_status_label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 6px;
                border-left: 4px solid #0078d4;
            }
        """)

    def _process_next_jumper(self):
        # Sprawdź czy symulacja jest zatrzymana
        if not self.simulation_running:
            return

        # Sprawdź czy jesteśmy w fazie kwalifikacji
        if self.qualification_enabled and self.qualification_phase:
            # Logika kwalifikacji
            if self.current_qualification_jumper_index >= len(self.qualification_order):
                # Koniec kwalifikacji - przejdź do konkursu
                self._finish_qualification()
                return

            jumper = self.qualification_order[self.current_qualification_jumper_index]

            # Lepszy komunikat o aktualnym skoczku w kwalifikacjach
            self.competition_status_label.setText(
                f"🎯 Kwalifikacje: {jumper} skacze..."
            )
            self.competition_status_label.setStyleSheet("""
                QLabel {
                    color: #0078d4;
                    font-weight: bold;
                    font-size: 14px;
                    padding: 10px;
                    background-color: rgba(0, 120, 212, 0.1);
                    border-radius: 6px;
                    border-left: 4px solid #0078d4;
                }
            """)

            # Symuluj skok kwalifikacyjny
            try:
                distance = fly_simulation(
                    self.competition_hill, jumper, gate_number=self.competition_gate
                )
                distance = round_distance_to_half_meter(distance)
                distance_points = calculate_jump_points(
                    distance, self.competition_hill.K
                )

                # Oceniaj skok przez sędziów
                judge_scores = self.judge_panel.score_jump(
                    jumper, distance, self.competition_hill.L, self.competition_hill
                )

                # Oblicz całkowite punkty (odległość + noty sędziowskie)
                total_points = distance_points + judge_scores["total_score"]

                # Dodaj wynik kwalifikacji
                self.qualification_results.append(
                    {
                        "jumper": jumper,
                        "distance": distance,
                        "points": total_points,
                        "judge_scores": judge_scores,
                    }
                )

                # Aktualizuj postęp
                progress = (
                    (self.current_qualification_jumper_index + 1)
                    / len(self.qualification_order)
                ) * 100
                if hasattr(self, "progress_label"):
                    self.progress_label.setText(f"Postęp kwalifikacji: {progress:.1f}%")

                self.current_qualification_jumper_index += 1

                # Aktualizuj tabelę wyników kwalifikacji
                self._update_qualification_table()

                # Następny skoczek po krótkiej przerwie
                QTimer.singleShot(150, self._process_next_jumper)

            except Exception as e:
                print(f"Błąd symulacji skoku kwalifikacyjnego: {e}")
                self.current_qualification_jumper_index += 1
                QTimer.singleShot(150, self._process_next_jumper)

            return

        # Logika konkursu (bez zmian)
        if self.current_jumper_index >= len(self.competition_order):
            if self.current_round == 1:
                # Koniec pierwszej serii
                self.competition_status_label.setText("Koniec 1. serii!")
                self.competition_status_label.setStyleSheet("""
                    QLabel {
                        color: #ffc107;
                        font-weight: bold;
                        font-size: 14px;
                        padding: 10px;
                        background-color: rgba(255, 193, 7, 0.1);
                        border-radius: 6px;
                        border-left: 4px solid #ffc107;
                    }
                """)

                self.current_round = 2
                self.competition_results.sort(key=lambda x: x["p1"], reverse=True)
                # Do drugiej serii zawsze przechodzi 30 najlepszych zawodników z pierwszej serii
                finalist_limit = 30
                finalists = self.competition_results[:finalist_limit]
                finalists.reverse()
                self.competition_order = [res["jumper"] for res in finalists]
                self.current_jumper_index = 0

                # Aktualizuj informację o serii
                if hasattr(self, "round_info_label"):
                    self.round_info_label.setText("Seria: 2/2")

                # Reset postępu dla drugiej serii
                if hasattr(self, "progress_label"):
                    self.progress_label.setText("Postęp: 0%")

                if not self.competition_order:
                    self.competition_status_label.setText(
                        "Zawody zakończone! (Brak finalistów)"
                    )
                    self.competition_status_label.setStyleSheet("""
                        QLabel {
                            color: #dc3545;
                            font-weight: bold;
                            font-size: 14px;
                            padding: 10px;
                            background-color: rgba(220, 53, 69, 0.1);
                            border-radius: 6px;
                            border-left: 4px solid #dc3545;
                        }
                    """)

                    # Przywróć przycisk do stanu początkowego gdy brak finalistów
                    self._update_competition_button("Rozpocznij zawody", "#28a745")
                    return

                # Ustaw flagę pauzy po pierwszej serii
                self.pause_after_first_round = True
                QTimer.singleShot(2000, self._pause_after_first_round)
            else:
                # Koniec zawodów
                self.competition_status_label.setText("Zawody zakończone!")
                self.competition_status_label.setStyleSheet("""
                    QLabel {
                        color: #28a745;
                        font-weight: bold;
                        font-size: 14px;
                        padding: 10px;
                        background-color: rgba(40, 167, 69, 0.1);
                        border-radius: 6px;
                        border-left: 4px solid #28a745;
                    }
                """)

                self.competition_results.sort(
                    key=lambda x: (x["p1"] + x["p2"]), reverse=True
                )
                self._update_competition_table()

                # Przywróć przycisk do stanu początkowego na końcu zawodów
                self._update_competition_button("Rozpocznij zawody", "#28a745")
            return

        jumper = self.competition_order[self.current_jumper_index]

        # Lepszy komunikat o aktualnym skoczku
        self.competition_status_label.setText(
            f"🎯 Seria {self.current_round}: {jumper} skacze..."
        )
        self.competition_status_label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 6px;
                border-left: 4px solid #0078d4;
            }
        """)

        raw_distance = fly_simulation(
            self.competition_hill, jumper, self.competition_gate
        )
        # Round distance to 0.5m precision for display and point calculation
        distance = round_distance_to_half_meter(raw_distance)
        res_item = next(
            item for item in self.competition_results if item["jumper"] == jumper
        )

        # Oblicz punkty za skok using rounded distance
        distance_points = calculate_jump_points(distance, self.competition_hill.K)

        # Oceniaj skok przez sędziów
        judge_scores = self.judge_panel.score_jump(
            jumper, distance, self.competition_hill.L, self.competition_hill
        )

        # Oblicz całkowite punkty (odległość + noty sędziowskie)
        total_points = distance_points + judge_scores["total_score"]

        if self.current_round == 1:
            res_item["d1"] = distance
            res_item["p1"] = total_points
            res_item["judges1"] = judge_scores
        else:
            res_item["d2"] = distance
            res_item["p2"] = total_points
            res_item["judges2"] = judge_scores

        self._update_competition_table()
        self.current_jumper_index += 1

        # Aktualizuj postęp
        if hasattr(self, "progress_label"):
            total_jumpers = len(self.competition_order)
            progress = (self.current_jumper_index / total_jumpers) * 100
            self.progress_label.setText(f"Postęp: {progress:.0f}%")

        QTimer.singleShot(150, self._process_next_jumper)

    def _finish_qualification(self):
        """Kończy kwalifikacje i przechodzi do konkursu"""
        # Sortuj wyniki kwalifikacji
        self.qualification_results.sort(key=lambda x: x["points"], reverse=True)

        # Wybierz zawodników awansujących
        qualified_jumpers = self.qualification_results[: self.qualification_limit]

        # Aktualizuj komunikat
        self.competition_status_label.setText(
            f"Kwalifikacje zakończone! {len(qualified_jumpers)} zawodników awansuje do konkursu."
        )
        self.competition_status_label.setStyleSheet("""
            QLabel {
                color: #ffc107;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: rgba(255, 193, 7, 0.1);
                border-radius: 6px;
                border-left: 4px solid #ffc107;
            }
        """)

        # Przygotuj dane konkursu (ale nie przełączaj tabeli jeszcze)
        self.qualification_phase = False
        self.competition_order = [result["jumper"] for result in qualified_jumpers]
        self.current_jumper_index = 0
        self.current_round = 1

        # Reset wyników konkursu
        self.competition_results = []
        for jumper in self.competition_order:
            self.competition_results.append(
                {
                    "jumper": jumper,
                    "d1": 0.0,
                    "d2": 0.0,
                    "p1": 0.0,
                    "p2": 0.0,
                    "judges1": None,  # Noty sędziów za pierwszą serię
                    "judges2": None,  # Noty sędziów za drugą serię
                }
            )

        # Aktualizuj informację o serii
        if hasattr(self, "round_info_label"):
            self.round_info_label.setText("Seria: 1/2")

        # Reset postępu
        if hasattr(self, "progress_label"):
            self.progress_label.setText("Postęp: 0%")

        # Zachowaj tabelę kwalifikacji widoczną do momentu rozpoczęcia konkursu
        # self.qualification_table.setVisible(False)
        # self.results_table.setVisible(True)

        # Aktualizuj tabelę wyników konkursu (ale nie pokazuj jej jeszcze)
        self.results_table.clearContents()
        self.results_table.setRowCount(len(self.competition_results))
        self._update_competition_table()

        # Ustaw flagę pauzy po kwalifikacjach
        self.pause_after_qualification = True
        # Rozpocznij konkurs po krótkiej przerwie
        QTimer.singleShot(2000, self._pause_after_qualification)

    def _update_qualification_table(self):
        """Aktualizuje tabelę wyników kwalifikacji"""
        # Sortuj wyniki kwalifikacji
        sorted_results = sorted(
            self.qualification_results, key=lambda x: x["points"], reverse=True
        )

        # Aktualizuj tabelę kwalifikacji
        self.qualification_table.clearContents()
        self.qualification_table.setRowCount(len(sorted_results))

        for row, result in enumerate(sorted_results):
            jumper = result["jumper"]
            distance = result["distance"]
            points = result["points"]

            # Miejsce
            place_item = QTableWidgetItem(str(row + 1))
            place_item.setTextAlignment(Qt.AlignCenter)
            self.qualification_table.setItem(row, 0, place_item)

            # Flaga
            flag_item = QTableWidgetItem()
            flag_item.setIcon(self.create_rounded_flag_icon(jumper.nationality))
            self.qualification_table.setItem(row, 1, flag_item)

            # Zawodnik
            jumper_item = QTableWidgetItem(str(jumper))
            self.qualification_table.setItem(row, 2, jumper_item)

            # Odległość kwalifikacji
            distance_item = QTableWidgetItem(format_distance_with_unit(distance))
            distance_item.setTextAlignment(Qt.AlignCenter)
            self.qualification_table.setItem(row, 3, distance_item)

            # Punkty kwalifikacji
            points_item = QTableWidgetItem(f"{points:.1f}")
            points_item.setTextAlignment(Qt.AlignCenter)
            self.qualification_table.setItem(row, 4, points_item)

            # Kolorowanie awansujących
            if row < self.qualification_limit:
                for col in range(self.qualification_table.columnCount()):
                    item = self.qualification_table.item(row, col)
                    if item:
                        item.setBackground(
                            QColor(40, 167, 69, 50)
                        )  # Zielone tło dla awansujących

    def _start_second_round(self):
        """Rozpoczyna drugą serię zawodów"""
        self.simulation_running = True  # Wznów symulację
        self.competition_status_label.setText(
            f"Rozpoczynanie 2. serii... ({len(self.competition_order)} finalistów)"
        )
        self.competition_status_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: rgba(40, 167, 69, 0.1);
                border-radius: 6px;
                border-left: 4px solid #28a745;
            }
        """)
        self._update_competition_button("Stop", "#dc3545")
        QTimer.singleShot(1000, self._process_next_jumper)

    def _pause_after_qualification(self):
        """Pauza po kwalifikacjach"""
        self.competition_status_label.setText(
            "Kwalifikacje zakończone! Kliknij przycisk aby rozpocząć konkurs."
        )
        self.competition_status_label.setStyleSheet("""
            QLabel {
                color: #ffc107;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: rgba(255, 193, 7, 0.1);
                border-radius: 6px;
                border-left: 4px solid #ffc107;
            }
        """)
        self._update_competition_button("Rozpocznij I serię", "#ffc107")

    def _pause_after_first_round(self):
        """Pauza po pierwszej serii"""
        self.competition_status_label.setText(
            "I seria zakończona! Kliknij przycisk aby rozpocząć II serię."
        )
        self.competition_status_label.setStyleSheet("""
            QLabel {
                color: #ffc107;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: rgba(255, 193, 7, 0.1);
                border-radius: 6px;
                border-left: 4px solid #ffc107;
            }
        """)
        self._update_competition_button("Rozpocznij II serię", "#ffc107")

    def _on_competition_button_clicked(self):
        """Obsługa kliknięcia głównego przycisku zawodów"""
        self.play_sound()

        # Sprawdź aktualny stan przycisku i wykonaj odpowiednią akcję
        button_text = self.run_comp_btn.text()

        if button_text == "Rozpocznij zawody":
            # Rozpocznij zawody
            self.run_competition()
        elif button_text == "Stop":
            # Zatrzymaj zawody
            self._stop_competition()
        elif button_text == "Kontynuuj":
            # Kontynuuj zawody
            self._continue_competition()
        elif button_text == "Rozpocznij I serię":
            # Rozpocznij pierwszą serię konkursu
            self._start_first_round()
        elif button_text == "Rozpocznij II serię":
            # Rozpocznij drugą serię
            self._start_second_round()

    def _update_competition_button(self, text, color="#28a745"):
        """Aktualizuje tekst i kolor głównego przycisku zawodów"""
        self.run_comp_btn.setText(text)
        self.run_comp_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._get_hover_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._get_pressed_color(color)};
            }}
        """)

    def _get_hover_color(self, base_color):
        """Zwraca kolor hover na podstawie koloru bazowego"""
        color_map = {
            "#28a745": "#218838",  # Zielony
            "#dc3545": "#c82333",  # Czerwony
            "#007bff": "#0056b3",  # Niebieski
            "#ffc107": "#e0a800",  # Żółty
        }
        return color_map.get(base_color, "#218838")

    def _get_pressed_color(self, base_color):
        """Zwraca kolor pressed na podstawie koloru bazowego"""
        color_map = {
            "#28a745": "#1e7e34",  # Zielony
            "#dc3545": "#bd2130",  # Czerwony
            "#007bff": "#004085",  # Niebieski
            "#ffc107": "#d39e00",  # Żółty
        }
        return color_map.get(base_color, "#1e7e34")

    def _stop_competition(self):
        """Zatrzymuje zawody i zmienia przycisk na 'Kontynuuj'"""
        self.simulation_running = False  # Zatrzymaj symulację
        self.competition_status_label.setText(
            "Symulacja zatrzymana. Kliknij 'Kontynuuj' aby wznowić."
        )
        self.competition_status_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                background-color: rgba(108, 117, 125, 0.1);
                border-radius: 6px;
                border-left: 4px solid #6c757d;
            }
        """)
        self._update_competition_button("Kontynuuj", "#007bff")

    def _continue_competition(self):
        """Kontynuuje zawody i przywraca przycisk 'Stop'"""
        self.simulation_running = True  # Wznów symulację
        self._reset_status_label()
        self._update_competition_button("Stop", "#dc3545")
        QTimer.singleShot(500, self._process_next_jumper)

    def _start_first_round(self):
        """Rozpoczyna pierwszą serię konkursu po kwalifikacjach"""
        self.simulation_running = True  # Wznów symulację
        self.qualification_phase = False
        self.current_jumper_index = 0
        self.current_round = 1

        # Pokaż tabelę konkursu, ukryj tabelę kwalifikacji
        self.results_table.setVisible(True)
        self.qualification_table.setVisible(False)

        # Aktualizuj informację o serii
        self.round_info_label.setText("Seria: 1/2")

        self._update_competition_button("Stop", "#dc3545")
        self._reset_status_label()

        QTimer.singleShot(500, self._process_next_jumper)

    def _update_competition_table(self):
        # Sort results before displaying
        if self.current_round == 1:
            # In round 1, sort by first round points
            self.competition_results.sort(key=lambda x: x.get("p1", 0), reverse=True)
        elif self.current_round == 2:
            # In round 2, sort by total points
            self.competition_results.sort(
                key=lambda x: (x.get("p1", 0) + x.get("p2", 0)), reverse=True
            )

        self.results_table.setRowCount(len(self.competition_results))
        for i, res in enumerate(self.competition_results):
            jumper = res["jumper"]

            # Miejsce dla top 3
            place_item = QTableWidgetItem()
            if i == 0:
                place_item.setText("1")
                place_item.setBackground(QColor("#FFD700"))
            elif i == 1:
                place_item.setText("2")
                place_item.setBackground(QColor("#C0C0C0"))
            elif i == 2:
                place_item.setText("3")
                place_item.setBackground(QColor("#CD7F32"))
            else:
                place_item.setText(str(i + 1))
            place_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 0, place_item)

            # Flaga kraju
            flag_label = QLabel()
            flag_pixmap = self._create_rounded_flag_pixmap(jumper.nationality)
            if not flag_pixmap.isNull():
                flag_label.setPixmap(flag_pixmap)
            flag_label.setScaledContents(True)
            flag_label.setAlignment(Qt.AlignCenter)
            flag_label.setStyleSheet("padding: 4px;")
            self.results_table.setCellWidget(i, 1, flag_label)

            # Nazwa zawodnika
            jumper_item = QTableWidgetItem(str(jumper))
            jumper_item.setBackground(QColor("#2a2a2a"))
            self.results_table.setItem(i, 2, jumper_item)

            # I seria - dystans
            d1_item = QTableWidgetItem()
            if res["d1"] > 0:
                d1_item.setText(format_distance_with_unit(res["d1"]))
                d1_item.setBackground(QColor("#1e3a8a"))
                d1_item.setForeground(QColor("#ffffff"))
            else:
                d1_item.setText("-")
            d1_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 3, d1_item)

            # I seria - punkty
            p1_item = QTableWidgetItem()
            if res["p1"] > 0:
                p1_item.setText(f"{res['p1']:.1f}")
                p1_item.setBackground(QColor("#059669"))
                p1_item.setForeground(QColor("#ffffff"))
            else:
                p1_item.setText("-")
            p1_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 4, p1_item)

            # II seria - dystans
            d2_item = QTableWidgetItem()
            if res["d2"] > 0:
                d2_item.setText(format_distance_with_unit(res["d2"]))
                d2_item.setBackground(QColor("#1e3a8a"))
                d2_item.setForeground(QColor("#ffffff"))
            else:
                d2_item.setText("-")
            d2_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 5, d2_item)

            # II seria - punkty
            p2_item = QTableWidgetItem()
            if res["p2"] > 0:
                p2_item.setText(f"{res['p2']:.1f}")
                p2_item.setBackground(QColor("#059669"))
                p2_item.setForeground(QColor("#ffffff"))
            else:
                p2_item.setText("-")
            p2_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 6, p2_item)

            # Suma punktów
            total_points = res.get("p1", 0) + res.get("p2", 0)
            total_item = QTableWidgetItem()
            if total_points > 0:
                total_item.setText(f"{total_points:.1f}")
                total_item.setBackground(QColor("#dc3545"))
                total_item.setForeground(QColor("#ffffff"))
                total_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            else:
                total_item.setText("-")
            total_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 7, total_item)

        QApplication.processEvents()

    def start_zoom_animation(self, ax, plot_elements):
        if not hasattr(self, "positions") or not self.positions:
            return
        final_x, final_y = self.positions[-1]
        zoom_frames = 10
        initial_xlim, initial_ylim = ax.get_xlim(), ax.get_ylim()
        final_xlim = (final_x - 10, final_x + 10)
        final_ylim = (final_y - 10, final_y + 10)

        def zoom_update(frame):
            if frame >= zoom_frames:
                ax.set_xlim(final_xlim)
                ax.set_ylim(final_ylim)
                self.canvas.draw_idle()
                if hasattr(self, "zoom_ani") and self.zoom_ani is not None:
                    try:
                        if (
                            hasattr(self.zoom_ani, "event_source")
                            and self.zoom_ani.event_source is not None
                        ):
                            self.zoom_ani.event_source.stop()
                    except Exception:
                        pass
                    self.zoom_ani = None
                return
            t = frame / zoom_frames
            new_xlim = (
                initial_xlim[0] + t * (final_xlim[0] - initial_xlim[0]),
                initial_xlim[1] + t * (final_xlim[1] - initial_xlim[1]),
            )
            new_ylim = (
                initial_ylim[0] + t * (final_ylim[0] - initial_ylim[0]),
                initial_ylim[1] + t * (final_ylim[1] - initial_ylim[1]),
            )
            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)
            self.canvas.draw_idle()
            return

        self.zoom_ani = animation.FuncAnimation(
            self.figure,
            zoom_update,
            frames=zoom_frames + 1,
            interval=50,
            blit=False,
            repeat=False,
        )
        self.canvas.draw()

    def _create_series_summary_card(
        self, seria_name, distance, points, difference, k_point, meter_value
    ):
        """Tworzy kartę z podsumowaniem dla pojedynczej serii w widoku sumy punktów."""
        card = QWidget()
        card.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border: 1px solid #4a4a4a;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(5)

        title = QLabel(f"📊 {seria_name}")
        title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                padding: 2px;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Details in a grid-like format
        details_layout = QFormLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(5)

        # Distance
        dist_label = QLabel("Odległość:")
        dist_value = QLabel(format_distance_with_unit(distance))
        dist_value.setStyleSheet("QLabel { color: #28a745; font-weight: bold; }")
        details_layout.addRow(dist_label, dist_value)

        # Difference from K-point
        diff_label = QLabel("Różnica od K-point:")
        diff_value = QLabel(f"{difference:+.1f} m")
        diff_value.setStyleSheet("QLabel { color: #0078d4; font-weight: bold; }")
        details_layout.addRow(diff_label, diff_value)

        # Points for distance
        dist_points_label = QLabel("Punkty za odległość:")
        dist_points_value = QLabel(f"{60.0 + (difference * meter_value):.1f} pkt")
        dist_points_value.setStyleSheet("QLabel { color: #28a745; font-weight: bold; }")
        details_layout.addRow(dist_points_label, dist_points_value)

        # Total points for series
        total_series_points_label = QLabel("Suma punktów serii:")
        total_series_points_value = QLabel(f"{points:.1f} pkt")
        total_series_points_value.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #ffffff;
                background-color: #059669;
                border-radius: 4px;
                padding: 3px;
            }
        """)
        total_series_points_value.setAlignment(Qt.AlignCenter)
        details_layout.addRow(total_series_points_label, total_series_points_value)

        layout.addLayout(details_layout)
        self.points_breakdown_layout.addWidget(card)


class Judge:
    """Reprezentuje pojedynczego sędziego"""

    def __init__(self, judge_id: int):
        self.judge_id = judge_id
        self.name = f"Sędzia {judge_id}"

    def score_jump(
        self,
        jumper: Jumper,
        distance: float,
        hill_size: float,
        telemark_landing: bool = False,
        hill=None,
    ) -> float:
        """
        Ocenia skok w skali 14-20 punktów.

        Args:
            jumper: Zawodnik
            distance: Odległość skoku
            hill_size: Rozmiar skoczni (HS)
            telemark_landing: Czy lądowanie telemarkiem

        Returns:
            Nota sędziego (14.0-20.0)
        """
        # Potrzebujemy dostępu do punktu K skoczni
        if hill is not None:
            k_point = hill.K
        else:
            # Fallback - przybliżenie punktu K jako 90% HS
            k_point = hill_size * 0.9

        # Określ położenie względem punktów K i HS
        is_before_k = distance < k_point
        is_at_or_after_k = distance >= k_point
        is_before_hs = distance < hill_size
        is_at_or_after_hs = distance >= hill_size

        if telemark_landing:
            # Z telemarkiem - interpolacja na podstawie statystyki Telemark
            telemark_factor = jumper.telemark / 100.0

            # Bazowa ocena zależna od statystyki Telemark
            # Telemark 0 → 16, Telemark 100 → 17
            base_score = 16.0 + (telemark_factor * 1.0)

            # Bonus za odległość
            if is_before_k:
                # Przed K - bez bonusu
                final_base = base_score
            elif is_at_or_after_k and is_before_hs:
                # Na lub za K, ale przed HS - bonus +1
                final_base = base_score + 1.0
            elif is_at_or_after_hs:
                # Na lub za HS - bonus +2
                final_base = base_score + 2.0
            else:
                final_base = base_score

            # Odchylenie ±1
            score = random.uniform(final_base - 1.0, final_base + 1.0)
        else:
            # Bez telemarku - nie zależy od statystyki Telemark
            if is_before_k:
                # Przed K - bazowa ocena 14
                base_score = 14.0
            elif is_at_or_after_k and is_before_hs:
                # Na lub za K, ale przed HS - bonus +1
                base_score = 15.0
            elif is_at_or_after_hs:
                # Na lub za HS - bonus +2
                base_score = 16.0
            else:
                base_score = 14.0

            # Odchylenie ±1
            score = random.uniform(base_score - 1.0, base_score + 1.0)

        # Ogranicz do zakresu 14-20
        score = max(14.0, min(20.0, score))

        # Zaokrąglij do 0.5
        return round(score * 2) / 2


class JudgePanel:
    """Panel 5 sędziów"""

    def __init__(self):
        self.judges = [Judge(i) for i in range(1, 6)]

    def score_jump(
        self, jumper: Jumper, distance: float, hill_size: float, hill=None
    ) -> dict:
        """
        Ocenia skok przez wszystkich sędziów.

        Returns:
            Dict z notami sędziów i podsumowaniem
        """
        # Określ czy lądowanie telemarkiem
        telemark_chance = self._calculate_telemark_chance(jumper, distance, hill_size)
        telemark_landing = random.random() < telemark_chance

        # Noty wszystkich sędziów
        judge_scores = []
        for judge in self.judges:
            score = judge.score_jump(
                jumper, distance, hill_size, telemark_landing, hill
            )
            judge_scores.append(score)

        # Usuń najwyższą i najniższą notę
        judge_scores.sort()
        final_scores = judge_scores[1:-1]  # Usuń pierwszy i ostatni

        # Suma not (bez najwyższej i najniższej)
        total_judge_score = sum(final_scores)

        return {
            "all_scores": judge_scores,
            "final_scores": final_scores,
            "total_score": total_judge_score,
            "telemark_landing": telemark_landing,
            "telemark_chance": telemark_chance,
        }

    def _calculate_telemark_chance(
        self, jumper: Jumper, distance: float, hill_size: float
    ) -> float:
        """
        Oblicza szansę na lądowanie telemarkiem.

        Args:
            jumper: Zawodnik
            distance: Odległość skoku
            hill_size: Rozmiar skoczni (HS)

        Returns:
            Szansa na telemark (0.0-1.0)
        """
        # Interpolacja szansy na podstawie telemarku
        # Telemark 0 → 50% szansy, Telemark 50 → 75% szansy, Telemark 100 → 100% szansy
        telemark_factor = jumper.telemark / 100.0
        base_chance = 0.50 + (telemark_factor * 0.50)  # 50% → 100%

        # Jeśli lądowanie za HS, szansa spada z każdym 0.5 metra o 2.5%
        if distance > hill_size:
            meters_over_hs = distance - hill_size
            # Każde 0.5 metra za HS zmniejsza szansę o 2.5%
            distance_penalty = (meters_over_hs / 0.5) * 0.025
            base_chance = max(0.0, base_chance - distance_penalty)

        return base_chance


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle(CustomProxyStyle())

    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec())
