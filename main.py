"""Główny plik uruchamiający aplikację symulatora skoków narciarskich."""

import sys
import os
import json
import copy
import random
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QSpinBox,
    QAbstractSpinBox,
    QPushButton,
    QLabel,
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
    QSizePolicy,
    QGridLayout,
    QProgressBar,
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

# from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtGui import (
    QIcon,
    QPixmap,
    QImage,
    QPainter,
    QPolygon,
    QColor,
    QFont,
    QFontMetrics,
    QDesktopServices,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.animation as animation
import numpy as np
import math
from PIL import Image, ImageDraw, ImageFilter
from src.simulation import load_data_from_json, inrun_simulation, fly_simulation
from src.hill import Hill
from src.jumper import Jumper

# Removed unused physics constants/helpers imports (kept in simulation modules)
from ui import AnimatedStackedWidget, NavigationSidebar, ModernComboBox, ModernSlider
from utils.history_store import (
    init_db as history_init_db,
    start_competition as history_start_competition,
    register_participants as history_register_participants,
    add_jump as history_add_jump,
    finalize_competition as history_finalize_competition,
)


class TimingIndicatorBar(QWidget):
    """Minimalistyczny pasek wizualizujący timing wybicia.

    Zakres: od -max_abs_seconds (za wcześnie) do +max_abs_seconds (za późno).
    Marker pokazuje przesunięcie czasu (εt) oraz kolor zależny od klasyfikacji.
    """

    def __init__(self, parent=None, max_abs_seconds: float = 0.12):
        super().__init__(parent)
        self._max_abs_seconds = float(max_abs_seconds)
        self._epsilon_t_s = 0.0
        self._classification = "idealny"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(44)

    def sizeHint(self):  # noqa: N802 - Qt API
        return QSize(300, 48)

    def setTiming(self, epsilon_t_s: float, classification: str):  # noqa: N802 - Qt API
        self._epsilon_t_s = float(epsilon_t_s or 0.0)
        self._classification = str(classification or "idealny")
        self.update()

    def _interpolate_color(self, c1: QColor, c2: QColor, t: float) -> QColor:
        t = max(0.0, min(1.0, t))
        r = int(c1.red() + (c2.red() - c1.red()) * t)
        g = int(c1.green() + (c2.green() - c1.green()) * t)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
        return QColor(r, g, b)

    def _color_for_magnitude(self) -> QColor:
        """Zwraca kolor wg modułu błędu czasu: zielony→żółty→czerwony.

        0% = zielony (#28a745), ~50% = żółty (#ffc107), 100% = czerwony (#dc3545)
        """
        ratio = min(1.0, abs(self._epsilon_t_s) / max(1e-6, self._max_abs_seconds))
        green = QColor("#28a745")
        yellow = QColor("#ffc107")
        red = QColor("#dc3545")
        if ratio <= 0.5:
            # 0.0..0.5 → green→yellow
            return self._interpolate_color(green, yellow, ratio / 0.5)
        # 0.5..1.0 → yellow→red
        return self._interpolate_color(yellow, red, (ratio - 0.5) / 0.5)

    def paintEvent(self, event):  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Kompaktowe marginesy zgodne z motywem (większy dolny margines na napisy)
        rect = self.rect().adjusted(8, 6, -8, -14)

        # Tło (transparentne, nie rysujemy pełnego panelu żeby było minimalistycznie)

        # Tor paska (ciemna szyna zgodna z motywem)
        track_h = 8
        track_y = rect.center().y() - track_h // 2

        # Rysuj szynę
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e2430"))
        painter.drawRoundedRect(rect.left(), track_y, rect.width(), track_h, 4, 4)

        # Znacznik środka (idealny)
        center_x = rect.left() + rect.width() // 2
        painter.setPen(QColor(76, 132, 255, 120))  # akcent motywu
        painter.drawLine(center_x, track_y - 6, center_x, track_y + track_h + 6)

        # Pozycja markera
        max_abs = max(0.001, self._max_abs_seconds)
        ratio = (self._epsilon_t_s / (2 * max_abs)) + 0.5  # map [-max, +max] -> [0,1]
        ratio = max(0.0, min(1.0, ratio))
        marker_x = rect.left() + int(ratio * rect.width())

        # Marker (kółko) w kolorze zależnym od wielkości błędu
        color = self._color_for_magnitude()
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 230))
        painter.setPen(Qt.NoPen)
        radius = 7
        painter.drawEllipse(QPoint(marker_x, rect.center().y()), radius, radius)

        # Delikatna obwódka dopasowująca do tła
        painter.setPen(QColor(15, 17, 21, 180))  # #0f1115 z lekką alfą
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(marker_x, rect.center().y()), radius, radius)

        # Podpisy krańcowe subtelne
        font = painter.font()
        small_font = QFont(font)
        small_font.setPointSizeF(max(7.5, font.pointSizeF() - 1))
        painter.setFont(small_font)
        painter.setPen(QColor(200, 208, 227, 140))
        # Ustaw podpisy w bezpiecznej strefie wewnątrz widgetu, tuż nad krawędzią
        metrics_small = QFontMetrics(small_font)
        text_y = self.rect().bottom() - 4
        painter.drawText(rect.left(), text_y, "za wcześnie")
        painter.drawText(
            rect.right() - metrics_small.horizontalAdvance("za późno"),
            text_y,
            "za późno",
        )

        painter.end()


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
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)

        # Minimal, consistent arrow buttons
        self.up_button.setObjectName("spinUpButton")
        self.down_button.setObjectName("spinDownButton")
        self.up_button.setFlat(True)
        self.down_button.setFlat(True)
        self.up_button.setText("▲")
        self.down_button.setText("▼")

        self.up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.up_button.clicked.connect(self.stepUp)
        self.down_button.clicked.connect(self.stepDown)

    def set_button_icons(self, up_icon, down_icon):
        # Keep textual arrows for crisp, minimal look across DPI settings
        self.up_button.setIcon(QIcon())
        self.down_button.setIcon(QIcon())
        self.up_button.setText("▲")
        self.down_button.setText("▼")

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
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)

        # Minimal, consistent arrow buttons
        self.up_button.setObjectName("spinUpButton")
        self.down_button.setObjectName("spinDownButton")
        self.up_button.setFlat(True)
        self.down_button.setFlat(True)
        self.up_button.setText("▲")
        self.down_button.setText("▼")

        self.up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.up_button.clicked.connect(self.stepUp)
        self.down_button.clicked.connect(self.stepDown)

    def set_button_icons(self, up_icon, down_icon):
        # Keep textual arrows for crisp, minimal look across DPI settings
        self.up_button.setIcon(QIcon())
        self.down_button.setIcon(QIcon())
        self.up_button.setText("▲")
        self.down_button.setText("▼")

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
        self.slider = ModernSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        # Apply slider styles directly
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #1e2430;
                border-radius: 4px;
                border: none;
                margin: 0;
            }
            QSlider::sub-page:horizontal {
                background: #4c84ff;
                border-radius: 4px;
                border: none;
            }
            QSlider::add-page:horizontal {
                background: #2a2f3a;
                border-radius: 4px;
                border: none;
            }
            QSlider::handle:horizontal {
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
                background: #4c84ff;
                border: 3px solid #0f1115;
            }
            QSlider::handle:horizontal:hover {
                background: #5b90ff;
                border-color: #1e2430;
            }
        """)

        # Custom value spinbox with custom arrow buttons
        self.value_spinbox = CustomDoubleSpinBox()
        self.value_spinbox.setRange(0.0, 100.0)
        self.value_spinbox.setDecimals(2)

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
            except Exception:
                return 0


def resource_path(relative_path):
    """
    Zwraca ścieżkę do zasobu, preferując zasoby obok pliku .exe w trybie
    zapakowanym (onefile). Jeśli nie ma zasobu obok .exe, używa rozpakowanych
    plików wewnątrz katalogu tymczasowego (_MEIPASS). W trybie uruchamiania ze
    źródeł zwraca ścieżkę względną do bieżącego katalogu.
    """
    if getattr(sys, "frozen", False):
        # Preferuj zasoby zewnętrzne obok .exe
        external_base = os.path.dirname(sys.executable)
        candidate_external = os.path.join(external_base, relative_path)
        if os.path.exists(candidate_external):
            return candidate_external

        # Fallback: zasoby rozpakowane do katalogu tymczasowego przez PyInstaller
        internal_base = getattr(sys, "_MEIPASS", external_base)
        return os.path.join(internal_base, relative_path)

    # Uruchamianie ze źródeł
    return os.path.join(os.path.abspath("."), relative_path)


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
            self.SUPPORT_IDX,
            self.HISTORY_IDX,
        ) = range(11)

        self.current_theme = "dark"
        self.contrast_level = 1.0
        self.volume_level = 0.3

        self.up_arrow_icon_dark = QIcon(create_arrow_pixmap("up", "#b0b0b0"))
        self.down_arrow_icon_dark = QIcon(create_arrow_pixmap("down", "#b0b0b0"))
        self.up_arrow_icon_light = QIcon(create_arrow_pixmap("up", "#404040"))
        self.down_arrow_icon_light = QIcon(create_arrow_pixmap("down", "#404040"))

        # Global QSS is loaded in __main__; remove legacy dynamic themes

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
        shell_layout = QHBoxLayout(main_container)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # Left navigation sidebar
        self.nav_sidebar = NavigationSidebar("SJS")
        shell_layout.addWidget(self.nav_sidebar, 0)

        # Right content column: header + stacked content + footer
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(12)

        # Global header title (updates on page change)
        self.header_title_label = QLabel("Ski Jumping Simulator")
        self.header_title_label.setProperty("class", "headerLabel")
        content_layout.addWidget(self.header_title_label, 0, Qt.AlignLeft)

        self.central_widget = AnimatedStackedWidget()
        content_layout.addWidget(self.central_widget, 1)

        self.author_label = QLabel("Antoni Sokołowski")
        self.author_label.setObjectName("authorLabel")
        content_layout.addWidget(self.author_label, 0, Qt.AlignRight)

        shell_layout.addWidget(content_container, 1)
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
        self._create_sim_type_menu()  # placeholder to preserve indices
        self._create_single_jump_page()
        self._create_competition_page()
        self._create_data_editor_page()
        # Zachowaj kolejność indeksów: Opis (placeholder), Ustawienia, Powtórka, Punkty
        self._create_description_page()
        self._create_settings_page()
        self._create_jump_replay_page()
        self._create_points_breakdown_page()
        self._create_support_page()
        self._create_history_page()

        # Map indices to titles
        self.index_to_title = {
            self.MAIN_MENU_IDX: "Start",
            self.SINGLE_JUMP_IDX: "Symulacja skoku",
            self.COMPETITION_IDX: "Zawody",
            self.DATA_EDITOR_IDX: "Edytor danych",
            # Opis projektu usunięty, Ustawienia odchudzone
            self.SETTINGS_IDX: "Ustawienia",
            self.JUMP_REPLAY_IDX: "Powtórka skoku",
            self.POINTS_BREAKDOWN_IDX: "Podział punktów",
            self.SUPPORT_IDX: "Wsparcie",
            self.HISTORY_IDX: "Historia",
        }

        # Build navigation buttons and wire to pages
        def go(idx: int):
            return lambda: [self.play_sound(), self.central_widget.setCurrentIndex(idx)]

        self._nav_btn_start = self.nav_sidebar.add_nav("Start", go(self.MAIN_MENU_IDX))
        self._nav_btn_single = self.nav_sidebar.add_nav(
            "Skok", go(self.SINGLE_JUMP_IDX)
        )
        self._nav_btn_comp = self.nav_sidebar.add_nav(
            "Zawody", go(self.COMPETITION_IDX)
        )
        self._nav_btn_history = self.nav_sidebar.add_nav(
            "Historia", go(self.HISTORY_IDX)
        )
        self._nav_btn_editor = self.nav_sidebar.add_nav(
            "Edytor", go(self.DATA_EDITOR_IDX)
        )
        # Ustawienia w pasku bocznym
        self._nav_btn_settings = self.nav_sidebar.add_nav(
            "Ustawienia", go(self.SETTINGS_IDX)
        )
        self._nav_btn_support = self.nav_sidebar.add_nav(
            "Wsparcie", go(self.SUPPORT_IDX)
        )
        # Usunięto skrót do punktów z paska bocznego
        self.nav_sidebar.finalize()

        # React to page changes: update title and active nav
        self.central_widget.currentChanged.connect(self._on_page_changed)
        self._on_page_changed(self.central_widget.currentIndex())

        # Discord invite for Support page live stats
        self.discord_invite_code = "D445FhKEmT"

    def _create_main_menu(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setSpacing(40)

        # Hero section with improved typography
        hero = QVBoxLayout()
        hero.setSpacing(16)

        title = QLabel("Ski Jumping Simulator")
        title.setProperty("class", "headerLabel")
        title.setAlignment(Qt.AlignCenter)
        hero.addWidget(title)

        subtitle = QLabel("Wybierz tryb")
        subtitle.setProperty("role", "subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        hero.addWidget(subtitle)

        layout.addLayout(hero)

        # Cards grid with improved spacing and responsive layout
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setSpacing(24)
        grid.setContentsMargins(0, 0, 0, 0)

        def make_card(text, sub, on_click):
            # Create a custom widget container
            container = QWidget()
            container.setProperty("class", "cardButton")
            container.setCursor(Qt.PointingHandCursor)
            container.setMinimumSize(280, 120)
            container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Create layout
            layout = QVBoxLayout(container)
            layout.setContentsMargins(24, 28, 24, 20)
            layout.setSpacing(8)

            # Add some top spacing for better symmetry
            layout.addSpacing(4)

            # Main text label (bold)
            main_label = QLabel(text)
            main_label.setProperty("class", "cardMainText")
            main_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            main_label.setWordWrap(True)

            # Subtitle label
            sub_label = QLabel(sub)
            sub_label.setProperty("class", "cardSubText")
            sub_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            sub_label.setWordWrap(True)

            # Add labels to layout
            layout.addWidget(main_label)
            layout.addWidget(sub_label)
            layout.addStretch()

            # Make the entire widget clickable
            container.mousePressEvent = lambda event: [self.play_sound(), on_click()]

            return container

        card_single = make_card(
            "Skok",
            "Pojedyncza symulacja",
            lambda: self.central_widget.setCurrentIndex(self.SINGLE_JUMP_IDX),
        )
        card_comp = make_card(
            "Zawody",
            "Konkurs i kwalifikacje",
            lambda: self.central_widget.setCurrentIndex(self.COMPETITION_IDX),
        )
        card_editor = make_card(
            "Edytor",
            "Zawodnicy i skocznie",
            lambda: self.central_widget.setCurrentIndex(self.DATA_EDITOR_IDX),
        )
        card_settings = make_card(
            "Ustawienia",
            "Grafika i dźwięk",
            lambda: self.central_widget.setCurrentIndex(self.SETTINGS_IDX),
        )
        card_history = make_card(
            "Historia",
            "Wyniki zapisane lokalnie",
            lambda: self.central_widget.setCurrentIndex(self.HISTORY_IDX),
        )
        card_support = make_card(
            "Wsparcie",
            "Kontakt i informacje",
            lambda: self.central_widget.setCurrentIndex(self.SUPPORT_IDX),
        )

        grid.addWidget(card_single, 0, 0)
        grid.addWidget(card_comp, 0, 1)
        grid.addWidget(card_editor, 1, 0)
        grid.addWidget(card_history, 1, 1)
        grid.addWidget(card_settings, 2, 0)
        grid.addWidget(card_support, 2, 1)

        layout.addWidget(grid_container)

        # Minimal – bez dodatkowych przycisków i podpowiedzi

        layout.addStretch(1)
        self.central_widget.addWidget(widget)
        self.page_main_menu = widget

    def _create_sim_type_menu(self):
        # Nie tworzymy już strony wyboru trybów – utrzymujemy indeksy, dodając pusty widget
        widget = QWidget()
        self.central_widget.addWidget(widget)

    def _create_single_jump_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(24)
        layout.setContentsMargins(50, 20, 50, 40)
        layout.addLayout(self._create_top_bar("Symulacja skoku", self.MAIN_MENU_IDX))

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
        self.jumper_combo = ModernComboBox()
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
        self.hill_combo = ModernComboBox()
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
        self.gate_spin = CustomSpinBox()
        self.gate_spin.setMinimum(1)
        self.gate_spin.setMaximum(1)
        config_group_layout.addLayout(self._create_form_row("Belka:", self.gate_spin))

        # Przyciski akcji
        btn_layout = QHBoxLayout()
        self.simulate_button = QPushButton("Uruchom symulację")
        self.simulate_button.setProperty("variant", "primary")
        self.simulate_button.clicked.connect(self.run_simulation)

        self.clear_button = QPushButton("Wyczyść")
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
        self.single_jump_stats_label.setProperty("chip", True)
        self.single_jump_stats_label.setProperty("variant", "info")
        self.single_jump_stats_label.setStyleSheet("")
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

        self.figure = Figure(facecolor="#0f1115")
        self.canvas = FigureCanvas(self.figure)
        animation_group_layout.addWidget(self.canvas)

        right_panel.addWidget(animation_group)
        right_panel.addStretch()

        main_hbox.addLayout(right_panel, 2)

        layout.addLayout(main_hbox)
        self.central_widget.addWidget(widget)
        self.page_points = widget
        self.page_single_jump = widget

    def _create_competition_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Zawody", self.MAIN_MENU_IDX))

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
        self.toggle_all_button.setProperty("variant", "primary")
        self.toggle_all_button.clicked.connect(self._toggle_all_jumpers)
        jumper_controls_layout.addWidget(self.toggle_all_button)

        # Licznik wybranych zawodników
        self.selected_count_label = QLabel("Wybrano: 0 zawodników")
        self.selected_count_label.setProperty("chip", True)
        self.selected_count_label.setProperty("variant", "info")
        jumper_controls_layout.addWidget(self.selected_count_label)
        jumper_group_layout.addLayout(jumper_controls_layout)

        # Sortowanie zawodników
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sortuj:"))
        self.sort_combo = ModernComboBox()
        self.sort_combo.addItems(["Wg Nazwiska (A-Z)", "Wg Kraju"])
        self.sort_combo.currentTextChanged.connect(self._sort_jumper_list)
        sort_layout.addWidget(self.sort_combo)
        jumper_group_layout.addLayout(sort_layout)

        # Lista zawodników z lepszym stylem
        self.jumper_list_widget = QListWidget()
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
        hill_layout.addWidget(hill_label)

        self.comp_hill_combo = ModernComboBox()
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
        gate_layout.addWidget(gate_label)

        # Kontener dla belki i rekomendacji
        gate_input_layout = QHBoxLayout()
        gate_input_layout.setSpacing(10)

        self.comp_gate_spin = CustomSpinBox()
        self.comp_gate_spin.setMinimum(1)
        self.comp_gate_spin.setMaximum(1)
        gate_input_layout.addWidget(self.comp_gate_spin)

        # Label z rekomendowaną belką
        self.recommended_gate_label = QLabel("")
        self.recommended_gate_label.setProperty("chip", True)
        self.recommended_gate_label.setProperty("variant", "primary")
        self.recommended_gate_label.setVisible(False)
        gate_input_layout.addWidget(self.recommended_gate_label)
        gate_input_layout.addStretch()

        gate_layout.addLayout(gate_input_layout)

        # Dolny wiersz z informacją o rekomendacji
        self.gate_info_label = QLabel("")
        self.gate_info_label.setProperty("chip", True)
        self.gate_info_label.setProperty("variant", "info")
        self.gate_info_label.setVisible(False)
        gate_layout.addWidget(self.gate_info_label)

        hill_gate_container.addLayout(gate_layout)
        competition_group_layout.addLayout(hill_gate_container)

        # Opcje kwalifikacji
        qualification_layout = QHBoxLayout()
        qualification_layout.setSpacing(10)

        self.qualification_checkbox = QCheckBox("Kwalifikacje")
        self.qualification_checkbox.setChecked(True)  # Domyślnie włączone
        qualification_layout.addWidget(self.qualification_checkbox)
        qualification_layout.addStretch()

        competition_group_layout.addLayout(qualification_layout)

        # Przycisk rozpoczęcia zawodów z lepszym stylem
        self.run_comp_btn = QPushButton("Rozpocznij zawody")
        self.run_comp_btn.setProperty("variant", "success")
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
        self.competition_status_label.setProperty("chip", True)
        self.competition_status_label.setProperty("variant", "info")

        # Dodajemy informację o aktualnej serii
        self.round_info_label = QLabel("Seria: 1/2")
        self.round_info_label.setProperty("chip", True)
        self.round_info_label.setProperty("variant", "primary")
        self.round_info_label.setAlignment(Qt.AlignCenter)

        # Layout dla statusu i informacji o serii
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.competition_status_label, 3)
        status_layout.addWidget(self.round_info_label, 1)
        results_panel.addLayout(status_layout)

        # Dodajemy pasek postępu
        self.progress_label = QLabel("Postęp: 0%")
        self.progress_label.setProperty("chip", True)
        self.progress_label.setProperty("variant", "primary")
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
        self.results_table.verticalHeader().setDefaultSectionSize(34)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        # Name column: fixed width to fit ~25 bold characters
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        # Numeric columns stretch to occupy remaining width nicely
        self.results_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Stretch
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.Stretch
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.Stretch
        )
        self.results_table.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.Stretch
        )
        # Allow narrow sections so compact modes can actually shrink
        self.results_table.horizontalHeader().setMinimumSectionSize(24)
        # Compute and set name column width for ~25 characters (bold font used in cells)
        name_font = self.results_table.font()
        name_font.setBold(True)
        metrics_name = QFontMetrics(name_font)
        name_col_width = metrics_name.horizontalAdvance("W" * 25) + 20
        self.results_table.setColumnWidth(2, name_col_width)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.cellClicked.connect(self._on_result_cell_clicked)

        # Styl tabeli wyników ustalany globalnie przez QSS
        self.results_table.setAlternatingRowColors(True)
        # Ustal spójny i mniejszy rozmiar ikon (flagi)
        self.results_table.setIconSize(QSize(24, 16))
        # Stała, dopasowana szerokość kolumny flagi (więcej luzu)
        self.results_table.setColumnWidth(1, 42)

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
        self.qualification_table.verticalHeader().setDefaultSectionSize(34)
        self.qualification_table.verticalHeader().setVisible(False)
        self.qualification_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.qualification_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.qualification_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Fixed
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

        # Styl tabeli kwalifikacji ustalany globalnie przez QSS
        self.qualification_table.setAlternatingRowColors(True)
        # Ustal spójny i mniejszy rozmiar ikon (flagi)
        self.qualification_table.setIconSize(QSize(24, 16))
        # Stała, dopasowana szerokość kolumny flagi (więcej luzu)
        self.qualification_table.setColumnWidth(1, 42)

        results_panel.addWidget(self.results_table)
        results_panel.addWidget(self.qualification_table)
        main_hbox.addLayout(results_panel, 2)

        layout.addLayout(main_hbox)
        self.competition_page = widget
        self.central_widget.addWidget(widget)
        self.page_competition = widget

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
        self.editor_sort_combo = ModernComboBox()
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
        self.jumper_form_widget.setObjectName("editorForm")
        self.jumper_form_widget.setObjectName("editorForm")
        self.jumper_edit_widgets = self._create_editor_form_content(
            self.jumper_form_widget, Jumper
        )
        jumper_form_scroll.setWidget(self.jumper_form_widget)

        hill_form_scroll = QScrollArea()
        hill_form_scroll.setWidgetResizable(True)
        self.hill_form_widget = QWidget()
        self.hill_form_widget.setObjectName("editorForm")
        self.hill_form_widget.setObjectName("editorForm")
        self.hill_edit_widgets = self._create_editor_form_content(
            self.hill_form_widget, Hill
        )
        hill_form_scroll.setWidget(self.hill_form_widget)

        self.editor_form_stack = AnimatedStackedWidget()
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
                "timing",
            ],
            "Lot": [
                "flight_technique",
                "flight_style",
                "flight_resistance",
            ],
            "Lądowanie": [
                "telemark",
                "stability",
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
            "timing": "Timing wybicia. Wyższe wartości = bliżej optimum, lepsze ukierunkowanie impulsu i mniejsza losowość.",
            "flight_technique": "Technika lotu skoczka. Wyższe wartości = lepsze wykorzystanie siły nośnej = dłuższe skoki.",
            "flight_style": "Styl lotu skoczka. Normalny = zrównoważony styl. Agresywny = mniejsza powierzchnia czołowa. Pasywny = większa powierzchnia czołowa.",
            "flight_resistance": "Opór powietrza w locie. Wyższe wartości = mniejszy opór aerodynamiczny = dłuższe skoki.",
            "telemark": "Umiejętność lądowania telemarkiem. Wyższe wartości = częstsze i ładniejsze lądowania telemarkiem.",
            "stability": "Stabilność lądowania. Zmniejsza ryzyko podpórki i upadku daleko za HS.",
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
                    "timing",
                    "flight_technique",
                    "flight_resistance",
                    "telemark",
                    "stability",
                ]:
                    widget = CustomSlider()
                    widget.setRange(0, 100)
                elif attr == "flight_style":
                    widget = ModernComboBox()
                    widget.addItems(["Normalny", "Agresywny", "Pasywny"])
                    # Ustawienie odpowiedniego rozmiaru dla dropdowna
                    widget.setFixedHeight(
                        35
                    )  # Większa wysokość aby tekst był w pełni widoczny
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
                elif attr == "timing":
                    label_text = "Timing wybicia:"
                elif attr == "flight_technique":
                    label_text = "Technika lotu:"
                elif attr == "flight_style":
                    label_text = "Styl lotu:"
                elif attr == "flight_resistance":
                    label_text = "Opór powietrza:"
                elif attr == "stability":
                    label_text = "Stabilność:"
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
                elif attr == "timing":
                    timing_value = getattr(data_obj, "timing", 50)
                    widget.setValue(int(timing_value))
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
                elif attr == "stability":
                    stability_value = getattr(data_obj, "stability", 50)
                    widget.setValue(int(stability_value))

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
                elif attr == "timing":
                    slider_value = widget.value()
                    setattr(data_obj, "timing", slider_value)
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
                elif attr == "stability":
                    # Zapisz wartość stabilności bezpośrednio (nie fizyczna)
                    slider_value = widget.value()
                    setattr(data_obj, "stability", slider_value)

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
        layout.setSpacing(6)
        layout.setContentsMargins(15, 8, 15, 15)

        layout.addLayout(self._create_top_bar("Powtórka skoku", self.COMPETITION_IDX))

        self.replay_title_label = QLabel("Imię i nazwisko skoczka")
        self.replay_title_label.setProperty("role", "title")
        self.replay_title_label.setObjectName("replayTitleLabel")
        self.replay_title_label.setAlignment(Qt.AlignCenter)
        # Utrzymaj stałą wysokość niezależnie od rozmiaru okna
        self.replay_title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.replay_title_label.setMaximumHeight(36)
        layout.addWidget(self.replay_title_label)

        self.replay_stats_label = QLabel("Statystyki skoku")
        self.replay_stats_label.setProperty("role", "subtitle")
        self.replay_stats_label.setObjectName("replayStatsLabel")
        self.replay_stats_label.setAlignment(Qt.AlignCenter)
        self.replay_stats_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.replay_stats_label.setMaximumHeight(26)
        layout.addWidget(self.replay_stats_label)

        self.replay_figure = Figure(facecolor="#0f1115")
        self.replay_canvas = FigureCanvas(self.replay_figure)
        self.replay_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.replay_canvas)

        # Placeholder na chip timingu (tworzony dynamicznie w _show_jump_replay)
        self.replay_timing_chip = None

        self.central_widget.addWidget(widget)

    def _create_points_breakdown_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 8, 15, 15)

        layout.addLayout(self._create_top_bar("Podział punktów", self.COMPETITION_IDX))

        # Hill information at the top
        self.points_hill_info_group = QGroupBox("Informacje o skoczni")
        hill_info_layout = QVBoxLayout(self.points_hill_info_group)

        self.points_hill_name = QLabel()
        hill_info_layout.addWidget(self.points_hill_name)

        self.points_gate_info = QLabel()
        hill_info_layout.addWidget(self.points_gate_info)

        layout.addWidget(self.points_hill_info_group)

        # Tytuł z informacjami o zawodniku
        self.points_title_label = QLabel("Imię i nazwisko skoczka")
        self.points_title_label.setProperty("role", "title")
        self.points_title_label.setObjectName("replayTitleLabel")
        self.points_title_label.setAlignment(Qt.AlignCenter)
        self.points_title_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.points_title_label.setMaximumHeight(36)
        layout.addWidget(self.points_title_label)

        self.points_info_label = QLabel("Informacje o skoku")
        self.points_info_label.setProperty("role", "subtitle")
        self.points_info_label.setObjectName("replayStatsLabel")
        self.points_info_label.setAlignment(Qt.AlignCenter)
        self.points_info_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.points_info_label.setMaximumHeight(26)
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

        self.points_figure = Figure(facecolor="#0f1115")
        self.points_canvas = FigureCanvas(self.points_figure)
        animation_panel.addWidget(self.points_canvas)

        main_hbox.addLayout(animation_panel, 2)
        layout.addLayout(main_hbox)

        self.central_widget.addWidget(widget)

    def _create_history_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 8, 15, 15)

        layout.addLayout(self._create_top_bar("Historia zawodów", self.MAIN_MENU_IDX))

        # Tabela historii zawodów
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            [
                "ID",
                "Nazwa",
                "Skocznia",
                "K",
                "Data",
                "Typ",
            ]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table = table

        refresh_btn = QPushButton("Odśwież")
        refresh_btn.setProperty("variant", "primary")
        refresh_btn.clicked.connect(self._refresh_history_table)

        layout.addWidget(refresh_btn, 0, Qt.AlignLeft)
        layout.addWidget(table, 1)

        self.central_widget.addWidget(widget)

        try:
            self._refresh_history_table()
        except Exception:
            pass

        # Single click opens detail
        self.history_table.itemClicked.connect(self._open_history_detail)

    def _refresh_history_table(self):
        try:
            from utils.history_store import list_competitions as _list

            rows = _list(limit=200, offset=0)
            self.history_table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                mode = r.get("mode", "")
                if "qualification" in mode.lower():
                    comp_type = "Kwalifikacje"
                elif "competition" in mode.lower():
                    comp_type = "Konkurs"
                else:
                    comp_type = mode or "Nieznany"
                values = [
                    str(r.get("id", "")),
                    r.get("name", ""),
                    r.get("hill_name", ""),
                    f"{float(r.get('k_point') or 0):.0f}",
                    r.get("created_at", ""),
                    comp_type,
                ]
                for col, val in enumerate(values):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.history_table.setItem(i, col, item)
        except Exception:
            pass

    def _open_history_detail(self, item: QTableWidgetItem):  # noqa: N802 - Qt slot
        row = item.row()
        comp_id_item = self.history_table.item(row, 0)
        if not comp_id_item:
            return
        try:
            comp_id = int(comp_id_item.text())
        except Exception:
            return
        try:
            from utils.history_store import get_competition_detail as _detail

            data = _detail(comp_id)
        except Exception:
            return

        if not data:
            return

        # Build a simple detail page similar to competition results
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 8, 15, 15)

        # Determine competition type
        comp_mode = data["competition"].get("mode", "")
        is_qualification = "qualification" in comp_mode.lower()
        type_label = "Kwalifikacje" if is_qualification else "Konkurs"
        title = QLabel(f"Wyniki: {type_label}")
        title.setProperty("class", "headerLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addLayout(self._create_top_bar("Historia: wyniki", self.HISTORY_IDX))
        layout.addWidget(title)

        # Determine competition type
        comp_mode = data["competition"].get("mode", "")
        is_qualification = "qualification" in comp_mode.lower()

        table = QTableWidget()
        if is_qualification:
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(
                [
                    "Miejsce",
                    "Flaga",
                    "Zawodnik",
                    "Dystans",
                    "Punkty",
                ]
            )
        else:
            table.setColumnCount(8)
            table.setHorizontalHeaderLabels(
                [
                    "Miejsce",
                    "Flaga",
                    "Zawodnik",
                    "I seria",
                    "I seria (pkt)",
                    "II seria",
                    "II seria (pkt)",
                    "Suma (pkt)",
                ]
            )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Reconstruct per-jumper aggregates
        results_map = {}
        rounds = data.get("rounds", [])

        for r in rounds:
            ri = int(r.get("round_index") or 0)
            for j in r.get("jumps", []):
                key = (
                    j.get("name", ""),
                    j.get("last_name", ""),
                    j.get("country_code", ""),
                )
                if key not in results_map:
                    results_map[key] = {
                        "name": key[0],
                        "last": key[1],
                        "country": key[2],
                        "d1": 0.0,
                        "p1": 0.0,
                        "d2": 0.0,
                        "p2": 0.0,
                        "judges1": None,
                        "judges2": None,
                    }
                entry = results_map[key]
                distance = float(j.get("distance") or 0.0)
                total_points = float(j.get("total_points") or 0.0)
                notes = j.get("notes_json")
                if ri == 1:
                    entry["d1"] = distance
                    entry["p1"] = total_points
                    entry["judges1"] = notes
                elif ri == 2:
                    entry["d2"] = distance
                    entry["p2"] = total_points
                    entry["judges2"] = notes

        results = list(results_map.values())
        # Sort like competition: by p1 in round 1; by p1+p2 in round 2 or final
        if is_qualification:
            # For qualification, sort by points (only one round)
            results.sort(key=lambda x: x.get("p1", 0), reverse=True)
        elif any(e.get("d2", 0) > 0 for e in results):
            results.sort(key=lambda x: (x.get("p1", 0) + x.get("p2", 0)), reverse=True)
        else:
            results.sort(key=lambda x: x.get("p1", 0), reverse=True)

        table.setRowCount(len(results))
        # k_point can be used for derived metrics if needed in the future
        for i, res in enumerate(results):
            place_item = QTableWidgetItem(str(i + 1))
            place_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, place_item)

            # Flag
            flag_container = QWidget()
            flag_layout = QHBoxLayout(flag_container)
            flag_layout.setContentsMargins(0, 0, 0, 0)
            flag_layout.setSpacing(0)
            flag_label = QLabel()
            pix = self._create_rounded_flag_pixmap(
                res["country"], size=QSize(24, 16), radius=4
            )
            if not pix.isNull():
                flag_label.setPixmap(pix)
            flag_label.setAlignment(Qt.AlignCenter)
            flag_layout.addStretch(1)
            flag_layout.addWidget(flag_label, 0, Qt.AlignCenter)
            flag_layout.addStretch(1)
            table.setCellWidget(i, 1, flag_container)

            # Name
            name_item = QTableWidgetItem(f"{res['name']} {res['last']}")
            f = name_item.font()
            f.setBold(True)
            name_item.setFont(f)
            table.setItem(i, 2, name_item)

            def _set_cell(col, text):
                it = QTableWidgetItem(text)
                it.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, col, it)

            if is_qualification:
                # Qualification: single round
                d1 = res.get("d1", 0.0)
                p1 = res.get("p1", 0.0)
                _set_cell(3, f"{d1:.1f} m" if d1 > 0 else "-")
                _set_cell(4, f"{p1:.1f}" if p1 > 0 else "-")
            else:
                # Competition: two rounds
                d1 = res.get("d1", 0.0)
                p1 = res.get("p1", 0.0)
                d2 = res.get("d2", 0.0)
                p2 = res.get("p2", 0.0)
                _set_cell(3, f"{d1:.1f} m" if d1 > 0 else "-")
                _set_cell(4, f"{p1:.1f}" if p1 > 0 else "-")
                _set_cell(5, f"{d2:.1f} m" if d2 > 0 else "-")
                _set_cell(6, f"{p2:.1f}" if p2 > 0 else "-")
                total = (p1 + p2) if (p1 or p2) else 0.0
                _set_cell(7, f"{total:.1f}" if total > 0 else "-")

        layout.addWidget(table)

        # Store context for click handling
        self.history_detail_table = table
        self._history_detail_is_qualification = is_qualification
        self._history_detail_results = results
        self._history_detail_hill_name = data["competition"].get("hill_name", "")
        self._history_detail_gate = getattr(self, "competition_gate", None)
        self.history_detail_table.itemClicked.connect(
            self._on_history_detail_cell_clicked
        )

        # Navigate to this detail page
        self.central_widget.addWidget(widget)
        self.central_widget.setCurrentWidget(widget)

    def _on_history_detail_cell_clicked(self, item: QTableWidgetItem):
        try:
            row = item.row()
            col = item.column()
            results = getattr(self, "_history_detail_results", [])
            if row < 0 or row >= len(results):
                return
            res = results[row]
            # Resolve hill by name
            hill_name = getattr(self, "_history_detail_hill_name", "")
            hill = next(
                (h for h in self.all_hills if getattr(h, "name", None) == hill_name),
                None,
            )
            hill = hill or getattr(self, "competition_hill", None)
            if hill is None:
                return
            gate = (
                getattr(self, "_history_detail_gate", None)
                or getattr(self, "competition_gate", None)
                or hill.gates
            )

            if getattr(self, "_history_detail_is_qualification", False):
                # distance in col 3, points in col 4
                if col == 3 and res.get("d1", 0) > 0:
                    # replay
                    # Find a representative jumper-like object: we only have name/last, so use matching from all_jumpers if possible
                    jumper = next(
                        (
                            j
                            for j in self.all_jumpers
                            if j.name == res["name"] and j.last_name == res["last"]
                        ),
                        None,
                    )
                    jumper = jumper or Jumper(
                        res["name"], res["last"], nationality=res.get("country")
                    )
                    self._show_jump_replay(jumper, hill, gate, res.get("d1", 0.0), "Q")
                elif col == 4 and res.get("p1", 0) > 0:
                    # points breakdown
                    distance = res.get("d1", 0.0)
                    points = res.get("p1", 0.0)
                    judge = res.get("judges1")
                    jumper = next(
                        (
                            j
                            for j in self.all_jumpers
                            if j.name == res["name"] and j.last_name == res["last"]
                        ),
                        None,
                    )
                    jumper = jumper or Jumper(
                        res["name"], res["last"], nationality=res.get("country")
                    )
                    self._show_points_breakdown(jumper, distance, points, "Q", judge)
                return

            # Competition: series 1 (cols 3,4), series 2 (cols 5,6)
            if col in (3, 4) and (res.get("d1", 0) > 0 or res.get("p1", 0) > 0):
                jumper = next(
                    (
                        j
                        for j in self.all_jumpers
                        if j.name == res["name"] and j.last_name == res["last"]
                    ),
                    None,
                )
                jumper = jumper or Jumper(
                    res["name"], res["last"], nationality=res.get("country")
                )
                if col == 3 and res.get("d1", 0) > 0:
                    self._show_jump_replay(jumper, hill, gate, res.get("d1", 0.0), 1)
                elif col == 4 and res.get("p1", 0) > 0:
                    self._show_points_breakdown(
                        jumper,
                        res.get("d1", 0.0),
                        res.get("p1", 0.0),
                        1,
                        res.get("judges1"),
                    )
            elif col in (5, 6) and (res.get("d2", 0) > 0 or res.get("p2", 0) > 0):
                jumper = next(
                    (
                        j
                        for j in self.all_jumpers
                        if j.name == res["name"] and j.last_name == res["last"]
                    ),
                    None,
                )
                jumper = jumper or Jumper(
                    res["name"], res["last"], nationality=res.get("country")
                )
                if col == 5 and res.get("d2", 0) > 0:
                    self._show_jump_replay(jumper, hill, gate, res.get("d2", 0.0), 2)
                elif col == 6 and res.get("p2", 0) > 0:
                    self._show_points_breakdown(
                        jumper,
                        res.get("d2", 0.0),
                        res.get("p2", 0.0),
                        2,
                        res.get("judges2"),
                    )
        except Exception:
            pass

    def _create_support_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Wsparcie", self.MAIN_MENU_IDX))

        title = QLabel("Potrzebujesz pomocy?")
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        title.setAlignment(Qt.AlignCenter)

        # Karta zaproszenia w stylu Discord
        card_btn = QPushButton()
        card_btn.setCursor(Qt.PointingHandCursor)
        card_btn.setFlat(True)
        card_btn.setStyleSheet(
            "QPushButton{background:#11151d; border:1px solid #232a36; border-radius:12px; padding:0;}"
            "QPushButton:hover{border-color:#2f3a4d;}"
        )
        card_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/D445FhKEmT"))
        )

        card = QWidget(card_btn)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 16, 16, 16)

        # Pasek z ikoną SJS (wycentrowany) z pliku assets/SJS.ico
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(12)
        icon_holder = QWidget()
        icon_holder.setFixedSize(60, 60)
        icon_holder.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1b2230, stop:1 #0f1115); border-radius: 12px;"
        )
        icon_inner = QVBoxLayout(icon_holder)
        icon_inner.setContentsMargins(8, 8, 8, 8)
        icon_inner.setSpacing(0)
        ico_label = QLabel()
        ico_pix = QPixmap(resource_path(os.path.join("assets", "SJS.ico")))
        if not ico_pix.isNull():
            ico_label.setPixmap(
                ico_pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        ico_label.setAlignment(Qt.AlignCenter)
        icon_inner.addWidget(ico_label)
        top_row.addStretch(1)
        top_row.addWidget(icon_holder, 0, Qt.AlignCenter)
        top_row.addStretch(1)
        card_layout.addLayout(top_row)

        name = QLabel("SJS (Ski Jumping Simulator)")
        name.setStyleSheet("font-size: 18px; font-weight: 600;")
        name.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(name)

        open_btn = QPushButton("Przejdź do serwera")
        open_btn.setProperty("variant", "success")
        open_btn.setStyleSheet("font-size: 16px; font-weight: 600;")
        open_btn.setFixedHeight(48)
        open_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/D445FhKEmT"))
        )
        card_layout.addWidget(open_btn)

        card_btn.setMinimumWidth(600)
        card_btn.setMinimumHeight(300)
        card_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay_btn = QVBoxLayout(card_btn)
        lay_btn.setContentsMargins(0, 0, 0, 0)
        lay_btn.addWidget(card)

        # Wycentrowanie pionowe i horyzontalne: tytuł + kafelek jako jeden blok
        layout.addStretch(1)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(16)
        center_layout.addWidget(title, 0, Qt.AlignHCenter)
        center_layout.addWidget(card_btn, 0, Qt.AlignHCenter)
        layout.addWidget(center_widget, 0, Qt.AlignCenter)
        layout.addStretch(1)

        # Usunięto automatyczne odświeżanie - kafelek bez liczb członków/online

        self.central_widget.addWidget(widget)
        self.page_support = widget

    # Usunięto metody Discord API - nie są już potrzebne

    def _create_description_page(self):
        # Placeholder to zachować kolejność indeksów (bez treści)
        widget = QWidget()
        self.central_widget.addWidget(widget)
        self.page_description = widget

    def _create_settings_page(self):
        # Ustawienia: tryb okna, głośność, kontrast
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(40)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Ustawienia", self.MAIN_MENU_IDX))

        self.window_mode_combo = ModernComboBox()
        self.window_mode_combo.addItems(
            ["W oknie", "Pełny ekran w oknie", "Pełny ekran"]
        )
        self.window_mode_combo.setCurrentText("Pełny ekran w oknie")
        self.window_mode_combo.currentTextChanged.connect(self._change_window_mode)
        layout.addLayout(self._create_form_row("Tryb okna:", self.window_mode_combo))

        volume_label = QLabel("Głośność:")
        self.volume_slider = ModernSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.volume_level * 100))
        self.volume_slider.valueChanged.connect(self.change_volume)
        # Usuń style QSS per-widget – wygląd zapewnia ModernSlider.paintEvent
        self.volume_slider.setStyleSheet("")
        layout.addLayout(self._create_form_row(volume_label.text(), self.volume_slider))

        contrast_label = QLabel("Kontrast:")
        self.contrast_slider = ModernSlider(Qt.Horizontal)
        self.contrast_slider.setRange(50, 150)  # 0.50x – 1.50x
        self.contrast_slider.setValue(int(self.contrast_level * 100))
        self.contrast_slider.valueChanged.connect(self.change_contrast)
        self.contrast_slider.setStyleSheet("")
        layout.addLayout(
            self._create_form_row(contrast_label.text(), self.contrast_slider)
        )

        layout.addStretch()
        self.central_widget.addWidget(widget)
        self.page_settings = widget

    def _change_window_mode(self, mode):
        if mode == "Pełny ekran":
            self.showFullScreen()
        elif mode == "Pełny ekran w oknie":
            self.showMaximized()
        else:  # "W oknie"
            self.showNormal()

    def _create_top_bar(self, title_text, back_index):
        # With global header + nav, top bar reduces to optional back button row
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← Wróć")
        back_btn.clicked.connect(
            lambda: [self.play_sound(), self.central_widget.setCurrentIndex(back_index)]
        )
        back_btn.setFixedHeight(36)
        back_btn.setObjectName("backArrowButton")
        top_bar.addWidget(back_btn, 0, Qt.AlignLeft)
        top_bar.addStretch(1)
        return top_bar

    def _on_page_changed(self, index: int):
        # Header title
        title = self.index_to_title.get(index, "Ski Jumping Simulator")
        self.header_title_label.setText(title)

        # Active nav button
        mapping = {
            self.MAIN_MENU_IDX: self._nav_btn_start,
            self.SINGLE_JUMP_IDX: self._nav_btn_single,
            self.COMPETITION_IDX: self._nav_btn_comp,
            self.DATA_EDITOR_IDX: self._nav_btn_editor,
            # self.DESCRIPTION_IDX: no sidebar button
            self.SETTINGS_IDX: self._nav_btn_settings,
            # self.JUMP_REPLAY_IDX: no sidebar button
        }
        btn = mapping.get(index)
        if btn is not None:
            self.nav_sidebar.set_active(btn)

    def _create_form_row(self, label_text, widget):
        row = QHBoxLayout()
        label = QLabel(label_text)
        # Stała szerokość etykiet, aby kolumna z polami wyrównywała się
        label.setFixedWidth(100)
        row.addWidget(label)
        # Pola wejściowe mają wypełniać dostępną szerokość i mieć wspólną minimalną szerokość
        try:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        except Exception:
            pass
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

        # Aktualizuj licznik wybranych zawodników (pozostaje niebieski)
        if hasattr(self, "selected_count_label"):
            count = len(self.selection_order)
            self.selected_count_label.setText(f"Wybrano: {count} zawodników")
            self.selected_count_label.setProperty("chip", True)
            self.selected_count_label.setProperty("variant", "primary")
            self.selected_count_label.setStyleSheet("")

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
            self.toggle_all_button.setText("Odznacz wszystkich")
            self.toggle_all_button.setProperty("variant", "danger")
        else:
            new_state = Qt.Unchecked
            self.toggle_all_button.setText("Zaznacz wszystkich")
            self.toggle_all_button.setProperty("variant", "primary")

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

        # Aktualizuj licznik wybranych zawodników po zmianie stanu (niebieski)
        if hasattr(self, "selected_count_label"):
            count = len(self.selection_order)
            self.selected_count_label.setText(f"Wybrano: {count} zawodników")
            self.selected_count_label.setProperty("variant", "primary")

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
        self.recommended_gate_label.setProperty("variant", "primary")
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

        # Przywróć styl chip "info"
        self.recommended_gate_label.setProperty("variant", "info")

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

        # Klik na kolumnę 2 (Zawodnik) – obecnie bez akcji
        if column == 2:
            return

        # Kolumny z dystansami to 3 (I seria) i 5 (II seria)
        if column in [3, 5]:
            seria_num = 1 if column == 3 else 2
            distance_str = self.results_table.item(row, column).text()

            if distance_str == "-":
                return

            try:
                # Extract distance value from format like "123.5 m"
                distance = float(distance_str.replace(" m", ""))
                # Użyj timingu zapisanej serii, jeśli dostępny; w innym razie fallback
                ti = result_data.get(f"timing{seria_num}") or getattr(
                    jumper, "last_timing_info", None
                )

                self._show_jump_replay(
                    jumper,
                    self.competition_hill,
                    self.competition_gate,
                    distance,
                    seria_num,
                    ti,
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

    def _show_jumper_card(self, jumper: "Jumper"):
        return

        # DEAD CODE BLOCK START (removed feature)
        card_layout = None
        card = None
        # style_meter placeholder removed
        return
        # DEAD CODE BLOCK END

        header = QLabel(str(jumper))
        header.setProperty("chip", True)
        header.setProperty("variant", "primary")
        header.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(header)

        # Flaga i kraj
        flag_row = QHBoxLayout()
        flag_row.setSpacing(10)
        flag_label = QLabel()
        flag_pix = self._create_rounded_flag_pixmap(
            jumper.nationality, QSize(48, 32), 6
        )
        if not flag_pix.isNull():
            flag_label.setPixmap(flag_pix)
        flag_row.addStretch(1)
        flag_row.addWidget(flag_label)
        country_label = QLabel(f"Kraj: {jumper.nationality.upper()}")
        flag_row.addWidget(country_label)
        flag_row.addStretch(1)
        card_layout.addLayout(flag_row)

        # Siatka statystyk (czytelnie, bez zbędnych ramek)
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(8)

        def add_stat(row_i: int, label_text: str, value_text: str):
            lbl = QLabel(label_text)
            val = QLabel(value_text)
            f = val.font()
            f.setBold(True)
            val.setFont(f)
            grid.addWidget(lbl, row_i, 0, Qt.AlignRight)
            grid.addWidget(val, row_i, 1, Qt.AlignLeft)

        add_stat(0, "Wiek:", str(getattr(jumper, "age", "-")))
        add_stat(1, "Wzrost:", f"{getattr(jumper, 'height', '-')}")
        add_stat(2, "Waga:", f"{getattr(jumper, 'weight', '-')}")
        add_stat(3, "Siła wybicia:", f"{getattr(jumper, 'takeoff_force', '-')}")
        add_stat(4, "Timing:", f"{getattr(jumper, 'timing', '-')}")
        add_stat(5, "Styl lotu:", f"{getattr(jumper, 'flight_style', '-')}")
        add_stat(
            6, "Opór w locie:", f"{getattr(jumper, 'flight_drag_coefficient', '-')}"
        )
        add_stat(
            7, "Powierzchnia czołowa:", f"{getattr(jumper, 'flight_frontal_area', '-')}"
        )
        add_stat(8, "Telemark:", f"{getattr(jumper, 'telemark', '-')}")

        card_layout.addLayout(grid)

        # Paski 0-100 jak w edytorze (minimalistyczne, w motywie)
        meters = QVBoxLayout()
        meters.setSpacing(10)

        def meter_row(name: str, value_0_100: int) -> QWidget:
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(10)
            h.addWidget(QLabel(name))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(max(0, min(100, int(value_0_100))))
            bar.setTextVisible(False)
            bar.setFixedHeight(12)
            bar.setStyleSheet(
                "QProgressBar{background:#151923;border:1px solid #2a2f3a;border-radius:6px;}"
                "QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #4c84ff, stop:1 #5b90ff);border-radius:6px;}"
            )
            h.addWidget(bar, 1)
            return w

        # Pozycja najazdowa (z inrun_drag_coefficient)
        inrun_drag = getattr(jumper, "inrun_drag_coefficient", None) or 0.46
        inrun_pos = drag_coefficient_to_slider(float(inrun_drag))

        takeoff_force_val = getattr(jumper, "takeoff_force", None) or 1500.0
        takeoff_slider = jump_force_to_slider(float(takeoff_force_val))

        timing_val = int((getattr(jumper, "timing", None) or 50))

        drag_coeff_val = getattr(jumper, "flight_drag_coefficient", None) or 0.5
        drag_slider = drag_coefficient_flight_to_slider(float(drag_coeff_val))

        lift_coeff_val = getattr(jumper, "flight_lift_coefficient", None) or 0.8
        technique_slider = lift_coefficient_to_slider(float(lift_coeff_val))

        telemark_val = int((getattr(jumper, "telemark", None) or 50))

        # frontal_area used for style chip only in removed UI

        meters.addWidget(meter_row("Pozycja najazdowa", inrun_pos))
        meters.addWidget(meter_row("Siła wybicia", takeoff_slider))
        meters.addWidget(meter_row("Timing wybicia", timing_val))
        meters.addWidget(meter_row("Technika lotu", technique_slider))
        meters.addWidget(meter_row("Opór powietrza", drag_slider))
        meters.addWidget(meter_row("Telemark", telemark_val))

        # Styl lotu – bez paska, elegancki chip
        style_chip = QLabel(f"Styl lotu: {getattr(jumper, 'flight_style', 'Normalny')}")
        style_chip.setProperty("chip", True)
        style_chip.setProperty("variant", "primary")
        style_chip.setAlignment(Qt.AlignCenter)
        meters.addWidget(style_chip)

        # OVR – średnia z metryk 0-100
        ovr = round(
            (
                inrun_pos
                + takeoff_slider
                + timing_val
                + technique_slider
                + drag_slider
                + telemark_val
            )
            / 6
        )
        ovr_chip = QLabel(f"OVR {ovr}")
        ovr_chip.setProperty("chip", True)
        ovr_chip.setProperty(
            "variant",
            "success" if ovr >= 70 else ("warning" if ovr >= 50 else "danger"),
        )
        ovr_chip.setAlignment(Qt.AlignCenter)
        meters.addWidget(ovr_chip)

        card_layout.addLayout(meters)

        # Przycisk powrotu do tabeli (na dole też)
        back_btn = QPushButton("Wróć do tabeli")
        back_btn.setProperty("variant", "primary")
        back_btn.clicked.connect(
            lambda: self.central_widget.setCurrentIndex(self.COMPETITION_IDX)
        )
        card_layout.addWidget(back_btn, 0, Qt.AlignCenter)

        # Dodaj i pokaż stronę
        self.central_widget.addWidget(card)
        self.central_widget.setCurrentWidget(card)

    def _on_qualification_cell_clicked(self, row, column):
        """Obsługa kliknięcia w komórkę tabeli kwalifikacji"""
        self.play_sound()

        # Pobierz obiekt wyniku przypisany do wiersza (po sortowaniu)
        result_item = self.qualification_table.item(row, 0)
        result = result_item.data(Qt.UserRole) if result_item is not None else None
        # Fallback (gdyby nie było danych na elemencie)
        if result is None:
            if not self.qualification_results or row >= len(self.qualification_results):
                return
            result = self.qualification_results[row]
        jumper = result["jumper"]

        # Klik na kolumnę 2 (Zawodnik) – obecnie bez akcji
        if column == 2:
            return

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

    def _show_jump_replay(
        self, jumper, hill, gate, distance, seria_num, timing_info=None
    ):
        # Użyj przekazanego timingu (konkretnej serii), a jeśli nie ma – ostatniego dostępnego
        ti = timing_info or getattr(jumper, "last_timing_info", None)
        sim_data = self._calculate_trajectory(jumper, hill, gate, ti)

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

        # Minimalistyczny pasek timingu pod statystykami
        try:
            parent_layout = self.central_widget.widget(self.JUMP_REPLAY_IDX).layout()

            # Usuń poprzednie wskaźniki (chip lub pasek), jeśli istnieją
            for attr_name in (
                "replay_timing_label",
                "replay_timing_bar",
                "replay_timing_chip",
            ):
                old_widget = getattr(self, attr_name, None)
                if old_widget is not None:
                    try:
                        parent_layout.removeWidget(old_widget)
                        old_widget.deleteLater()
                    except Exception:
                        pass
                    setattr(self, attr_name, None)

            ti_bar = timing_info or (getattr(jumper, "last_timing_info", None) or {})
            epsilon_t_s = float(ti_bar.get("epsilon_t_s", 0.0))
            classification = ti_bar.get("classification", "idealny")

            # Tytuł nad paskiem
            title_label = QLabel("Timing wybicia")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet(
                """
                QLabel {
                    color: #cccccc;
                    font-size: 11px;
                    padding: 0px;
                    margin: 2px 0 0 0;
                }
                """
            )

            bar = TimingIndicatorBar(max_abs_seconds=0.12)
            bar.setTiming(epsilon_t_s, classification)
            # Wstaw pod stats_label: najpierw label (idx 3), potem pasek (idx 4)
            parent_layout.insertWidget(3, title_label, 0, Qt.AlignCenter)
            parent_layout.insertWidget(4, bar, 0, Qt.AlignCenter)
            self.replay_timing_label = title_label
            self.replay_timing_bar = bar
        except Exception:
            pass

    def _create_distance_card(
        self, distance, k_point, meter_value, difference, distance_points
    ):
        """Tworzy kartę z informacjami o odległości i obliczeniach punktów."""
        card = QWidget()
        # Neutralna karta bez lokalnych kolorów; wygląd po stronie QSS
        card.setProperty("class", "card")

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Tytuł karty
        title = QLabel("Punkty za odległość")
        title.setProperty("chip", True)
        title.setProperty("variant", "primary")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Główna informacja o odległości
        distance_info = QLabel(f"Odległość: {format_distance_with_unit(distance)}")
        distance_info.setProperty("chip", True)
        distance_info.setProperty("variant", "success")
        distance_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(distance_info)

        # Szczegóły obliczeń
        details_layout = QHBoxLayout()

        # Lewa kolumna - wartości
        left_col = QVBoxLayout()

        k_point_label = QLabel(f"K-point: {k_point:.1f} m")
        left_col.addWidget(k_point_label)

        difference_label = QLabel(f"Różnica: {difference:+.1f} m")
        left_col.addWidget(difference_label)

        meter_label = QLabel(f"Meter value: {meter_value:.1f} pkt/m")
        left_col.addWidget(meter_label)

        details_layout.addLayout(left_col)

        # Prawa kolumna - obliczenia
        right_col = QVBoxLayout()

        base_points_label = QLabel("60.0 pkt")
        base_points_label.setProperty("role", "meta")
        right_col.addWidget(base_points_label)

        bonus_points = difference * meter_value
        bonus_label = QLabel(f"{bonus_points:+.1f} pkt")
        bonus_label.setProperty("role", "meta")
        right_col.addWidget(bonus_label)

        total_distance_label = QLabel(f"{distance_points:.1f} pkt")
        total_distance_label.setProperty("chip", True)
        total_distance_label.setProperty("variant", "success")
        total_distance_label.setAlignment(Qt.AlignCenter)
        right_col.addWidget(total_distance_label)

        details_layout.addLayout(right_col)
        layout.addLayout(details_layout)

        self.points_breakdown_layout.addWidget(card)

    def _create_judge_card(self, judge_data, title_text: str = "Punkty za noty"):
        """Tworzy kartę z informacjami o notach sędziowskich.

        title_text: nagłówek karty (np. "Noty sędziów - I seria").
        """
        card = QWidget()
        card.setProperty("class", "card")

        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        # Tytuł karty
        title = QLabel(title_text)
        title.setProperty("chip", True)
        title.setProperty("variant", "primary")
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
            judge_name.setAlignment(Qt.AlignCenter)
            score_layout.addWidget(judge_name)

            # Nota
            score_label = QLabel(f"{score:.1f}")
            score_label.setAlignment(Qt.AlignCenter)
            score_label.setMinimumSize(35, 25)

            # Kolorowanie not - zawsze 2 skrajne na czerwono, 3 środkowe na zielono
            if i in red_indices:
                score_label.setProperty("chip", True)
                score_label.setProperty("variant", "danger")
            else:
                score_label.setProperty("chip", True)
                score_label.setProperty("variant", "success")

            score_layout.addWidget(score_label)
            scores_layout.addWidget(score_widget)

        layout.addLayout(scores_layout)

        # Suma not
        total_judge_points = judge_data["total_score"]
        judge_summary = QLabel(f"Suma (bez skrajnych): {total_judge_points:.1f} pkt")
        judge_summary.setProperty("chip", True)
        judge_summary.setProperty("variant", "primary")
        judge_summary.setAlignment(Qt.AlignCenter)
        layout.addWidget(judge_summary)

        # Informacja o lądowaniu (uwzględnia upadek/podpórkę)
        landing_label = QLabel()
        landing_label.setAlignment(Qt.AlignCenter)
        landing_label.setProperty("chip", True)
        event = judge_data.get("event")
        if event == "fall":
            landing_label.setText("Lądowanie: Upadek ❌")
            landing_label.setProperty("variant", "danger")
        elif event == "hand":
            landing_label.setText("Lądowanie: Podpórka ❗")
            landing_label.setProperty("variant", "warning")
        else:
            # SAFE – rozróżnij telemark vs zwykłe
            if judge_data.get("telemark_landing", False):
                landing_label.setText("Lądowanie: Telemark ✅")
                landing_label.setProperty("variant", "success")
            else:
                landing_label.setText("Lądowanie: Zwykłe")
                landing_label.setProperty("variant", "primary")
        layout.addWidget(landing_label)

        self.points_breakdown_layout.addWidget(card)

    def _create_total_card(self, distance_points, judge_data):
        """Tworzy kartę z sumą punktów."""
        card = QWidget()
        card.setProperty("class", "card")

        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        # Tytuł karty
        title = QLabel("Suma punktów")
        title.setProperty("role", "subtitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Minimalistyczna suma punktów
        if judge_data:
            calc_text = (
                f"{(distance_points + float(judge_data['total_score'])):.1f} pkt"
            )
        else:
            calc_text = f"{distance_points:.1f} pkt"

        calc_label = QLabel(calc_text)
        calc_label.setProperty("chip", True)
        calc_label.setProperty("variant", "primary")
        calc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(calc_label)

        self.points_breakdown_layout.addWidget(card)

    def _create_series_points_table(
        self,
        title_text: str,
        distance_points: float,
        judge_points: float,
        total_points: float,
    ):
        """Tworzy zwięzłą tabelę 3-kolumnową dla jednej serii: za odległość, noty sędziowskie, suma."""
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setSpacing(6)
        vbox.setContentsMargins(0, 0, 0, 0)

        title = QLabel(title_text)
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("role", "subtitle")
        vbox.addWidget(title)

        table = QTableWidget(1, 3)
        table.setHorizontalHeaderLabels(["Odległość", "Noty", "Suma"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setShowGrid(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setRowHeight(0, 32)
        # Użyj globalnego QSS dla tabel

        def mk_item(text: str):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignCenter)
            f = item.font()
            f.setBold(True)
            item.setFont(f)
            return item

        # Ustal wysokość tabeli dynamicznie tak, aby treść zawsze była widoczna
        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        header_h = table.horizontalHeader().height()
        row_h = table.rowHeight(0)
        frame = table.frameWidth() * 2
        extra = 28  # margines bezpieczeństwa na padding/styl
        table.setFixedHeight(header_h + row_h + frame + extra)

        table.setItem(0, 0, mk_item(f"{distance_points:.1f} pkt"))
        table.setItem(0, 1, mk_item(f"{judge_points:.1f} pkt"))
        table.setItem(0, 2, mk_item(f"{total_points:.1f} pkt"))

        vbox.addWidget(table)
        self.points_breakdown_layout.addWidget(container)

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

        # Usunięto zbędne lokalne obliczenia sumy – karta sumy jest tworzona powyżej

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
        """Wyświetla dwie spójne tabele z punktami za I i II serię: za odległość, noty, suma."""
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

        # I seria – prosty, logiczny widok z trzema wartościami
        if result_data.get("d1", 0) > 0 and result_data.get("p1", 0) > 0:
            d1 = float(result_data["d1"])
            p1 = float(result_data["p1"])  # suma serii (odległość + noty)
            distance_points_1 = calculate_jump_points(d1, k_point)
            judges1 = result_data.get("judges1")
            judge_points_1 = (
                float(judges1["total_score"])
                if judges1
                else max(0.0, p1 - distance_points_1)
            )
            self._create_series_points_table(
                "I seria", distance_points_1, judge_points_1, p1
            )

        # II seria – analogicznie
        if result_data.get("d2", 0) > 0 and result_data.get("p2", 0) > 0:
            d2 = float(result_data["d2"])
            p2 = float(result_data["p2"])  # suma serii
            distance_points_2 = calculate_jump_points(d2, k_point)
            judges2 = result_data.get("judges2")
            judge_points_2 = (
                float(judges2["total_score"])
                if judges2
                else max(0.0, p2 - distance_points_2)
            )
            self._create_series_points_table(
                "II seria", distance_points_2, judge_points_2, p2
            )

        # Zwięzła karta sumy punktów pozostaje bez zmian, ale mogę ją też
        # zamienić na trzecią mini-tabelę "Razem" jeśli zechcesz.
        self._create_total_card(total_points, None)

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

    def _calculate_trajectory(self, jumper, hill, gate, timing_info=None):
        """Oblicza trajektorię do wyświetlenia.

        Jeśli podasz `timing_info` (słownik jak w `Jumper.last_timing_info`),
        zostaną zastosowane te same korekty co w symulacji: wcześniejsze wejście
        w większe opory (εs) oraz skala impulsu i efektywność pionowa.
        """
        early_shift = 0.0
        magnitude_scale = 1.0
        vertical_efficiency = 1.0
        if isinstance(timing_info, dict) and timing_info:
            try:
                eps_s = float(timing_info.get("epsilon_s_m", 0.0))
                early_shift = min(max(0.0, -eps_s), 1.0)
                magnitude_scale = float(timing_info.get("magnitude_scale", 1.0))
                vertical_efficiency = float(timing_info.get("vertical_efficiency", 1.0))
            except Exception:
                pass

        inrun_velocity = inrun_simulation(
            hill, jumper, gate_number=gate, early_takeoff_aero_shift_m=early_shift
        )

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

        base_delta_v = (jumper.jump_force * 0.1) / jumper.mass
        velocity_takeoff = base_delta_v * magnitude_scale
        velocity_takeoff_x = velocity_takeoff * math.sin(hill.alpha_rad)
        velocity_takeoff_y = (
            velocity_takeoff * math.cos(hill.alpha_rad) * vertical_efficiency
        )

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

    def _create_timing_card(self, timing_info):
        card = QWidget()
        card.setStyleSheet(
            """
            QWidget {
                background-color: #1f1f1f;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 10px;
                margin: 3px;
            }
            """
        )
        layout = QVBoxLayout(card)
        title = QLabel("Timing wybicia")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            """
            QLabel {
                font-size: 13px;
                font-weight: bold;
                color: #ffffff;
            }
            """
        )
        layout.addWidget(title)

        status = (timing_info or {}).get("classification", "idealny")
        color = {
            "za wcześnie": "#ffc107",
            "idealny": "#28a745",
            "za późno": "#dc3545",
        }.get(status, "#28a745")

        bar = QWidget()
        bar.setFixedHeight(12)
        bar.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        layout.addWidget(bar)

        if timing_info:
            details = QLabel(
                f"Δt: {timing_info['epsilon_t_s'] * 1000:.0f} ms  |  Δs: {timing_info['epsilon_s_m']:.2f} m"
            )
            details.setAlignment(Qt.AlignCenter)
            details.setStyleSheet(
                """
                QLabel {
                    font-size: 11px;
                    color: #cccccc;
                }
                """
            )
            layout.addWidget(details)

        self.points_breakdown_layout.addWidget(card)

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
        # Ciemne tło zgodne z motywem
        ax.set_facecolor("#0f1115")
        figure.patch.set_facecolor("#0f1115")
        ax.axis("off")
        ax.set_aspect("auto")

        inrun_length_to_show = 15.0
        x_inrun = np.linspace(-inrun_length_to_show, 0, 50)
        y_inrun = np.tan(-hill.alpha_rad) * x_inrun
        ax.plot(x_inrun, y_inrun, color="#4c84ff", linewidth=2.5)

        max_y_inrun = y_inrun[0] if len(y_inrun) > 0 else 0
        # Poprawione limity - animacja będzie wyżej i ładniej sformatowana
        ax.set_xlim(-inrun_length_to_show - 5, hill.n + hill.a_finish + 30)
        ax.set_ylim(
            min(min(sim_data["y_landing"]), 0) - 3,
            max(sim_data["max_height"] * 1.3, max_y_inrun) + 3,
        )

        (jumper_point,) = ax.plot(
            [],
            [],
            "o",
            color="#e8eaf1",
            markersize=7,
            markeredgecolor="#4c84ff",
            markeredgewidth=1.5,
        )
        (trail_line,) = ax.plot([], [], color="#5b90ff", linewidth=2.5, alpha=0.7)
        (landing_line,) = ax.plot([], [], color="#4c84ff", linewidth=3, alpha=0.8)
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
            self.single_jump_stats_label.setProperty("chip", True)
            self.single_jump_stats_label.setProperty("variant", "danger")
            self.single_jump_stats_label.setStyleSheet("")
            return
        gate = self.gate_spin.value()

        try:
            sim_data = self._calculate_trajectory(
                self.selected_jumper, self.selected_hill, gate
            )
            raw_distance = fly_simulation(
                self.selected_hill, self.selected_jumper, gate, perfect_timing=True
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
            self.single_jump_stats_label.setProperty("chip", True)
            self.single_jump_stats_label.setProperty("variant", "success")
            self.single_jump_stats_label.setStyleSheet("")

            self._run_animation_on_canvas(
                self.canvas, self.figure, sim_data, self.selected_hill
            )

        except ValueError as e:
            self.single_jump_stats_label.setText(f"BŁĄD: {str(e)}")
            self.single_jump_stats_label.setProperty("chip", True)
            self.single_jump_stats_label.setProperty("variant", "danger")
            self.single_jump_stats_label.setStyleSheet("")

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
        self.single_jump_stats_label.setProperty("chip", True)
        self.single_jump_stats_label.setProperty("variant", "info")
        self.single_jump_stats_label.setStyleSheet("")
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
        # Respect global QSS. Only refresh figure backgrounds to match theme if needed.

        # Apply styles to both tables
        if hasattr(self, "results_table"):
            self.results_table.setStyleSheet("")
        if hasattr(self, "qualification_table"):
            self.qualification_table.setStyleSheet("")

        # Nie nadpisuj globalnego QSS lokalnym styleSheet na oknie, bo kasuje to reguły
        # dla QComboBox/QSlider. Tło zostawiamy po stronie QSS motywu.

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
            # Wysokiej jakości antyaliasing: rysuj maskę w skali i przeskaluj LANCZOS
            scale = 4
            target_w, target_h = size.width(), size.height()
            hi_w, hi_h = target_w * scale, target_h * scale
            with Image.open(flag_path) as img:
                img = img.convert("RGBA")
                img_resized = img.resize((hi_w, hi_h), Image.Resampling.LANCZOS)
            mask_hi = Image.new("L", (hi_w, hi_h), 0)
            draw = ImageDraw.Draw(mask_hi)
            draw.rounded_rectangle(
                ((0, 0), (hi_w, hi_h)), radius=radius * scale, fill=255
            )
            # Minimalne rozmycie krawędzi maski, by usunąć pikselowe rogi
            mask_hi = mask_hi.filter(ImageFilter.GaussianBlur(radius=scale * 0.35))
            img_resized.putalpha(mask_hi)
            # Downscale do docelowego rozmiaru z zachowaniem antyaliasingu
            final_img = img_resized.resize(
                (target_w, target_h), Image.Resampling.LANCZOS
            )
            qimage = QImage(
                final_img.tobytes("raw", "RGBA"),
                final_img.width,
                final_img.height,
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
            self.competition_status_label.setProperty("chip", True)
            self.competition_status_label.setProperty("variant", "danger")
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

        # INIT history DB and create history records
        try:
            history_init_db()
            hill_name = getattr(self.competition_hill, "name", "")
            # If qualifications enabled, create a dedicated qualification record now
            if self.qualification_enabled:
                qual_name = f"Kwalifikacje {hill_name} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                self._history_qualification_id = history_start_competition(
                    name=qual_name,
                    hill_id=str(hill_name),
                    hill_name=hill_name,
                    k_point=float(getattr(self.competition_hill, "K", 0.0)),
                    hs_point=float(getattr(self.competition_hill, "L", 0.0)),
                    mode="qualification",
                    app_version=None,
                )
                participants = [
                    (
                        getattr(j, "name", ""),
                        getattr(j, "last_name", ""),
                        getattr(j, "nationality", None),
                    )
                    for j in self.selection_order
                ]
                history_register_participants(
                    self._history_qualification_id, participants
                )
                # Delay competition record creation until first round actually starts
                self._history_competition_id = None
            else:
                comp_name = (
                    f"Zawody {hill_name} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                self._history_competition_id = history_start_competition(
                    name=comp_name,
                    hill_id=str(hill_name),
                    hill_name=hill_name,
                    k_point=float(getattr(self.competition_hill, "K", 0.0)),
                    hs_point=float(getattr(self.competition_hill, "L", 0.0)),
                    mode="competition",
                    app_version=None,
                )
                participants = [
                    (
                        getattr(j, "name", ""),
                        getattr(j, "last_name", ""),
                        getattr(j, "nationality", None),
                    )
                    for j in self.selection_order
                ]
                history_register_participants(
                    self._history_competition_id, participants
                )
        except Exception:
            # Silent fail to avoid disturbing UI; history is optional
            self._history_competition_id = None
            self._history_qualification_id = None

        # Lepszy komunikat rozpoczęcia
        if self.qualification_enabled:
            status_text = f"Rozpoczynanie kwalifikacji na {self.competition_hill.name}... ({len(self.selection_order)} zawodników)"
        else:
            status_text = f"Rozpoczynanie zawodów na {self.competition_hill.name}... ({len(self.selection_order)} zawodników)"

        self.competition_status_label.setText(status_text)
        self.competition_status_label.setProperty("chip", True)
        # Zawody startują → zielony
        self.competition_status_label.setProperty("variant", "success")

        # Zmień przycisk na 'Stop' podczas zawodów
        self._update_competition_button("Stop", variant="danger")

        QTimer.singleShot(500, self._process_next_jumper)

    def _reset_status_label(self):
        """Resetuje status label do domyślnego wyglądu"""
        self.competition_status_label.setText(
            "Tabela wyników (kliknij odległość, aby zobaczyć powtórkę):"
        )
        self.competition_status_label.setProperty("chip", True)
        # Don't override the variant - let it match the button color
        # The variant will be set by _update_competition_button

    def _process_next_jumper(self):
        # Sprawdź czy symulacja jest zatrzymana
        if not self.simulation_running:
            return

        # Sprawdź czy jesteśmy w fazie kwalifikacji
        if self.qualification_enabled and self.qualification_phase:
            # Logika kwalifikacji
            if self.current_qualification_jumper_index >= len(self.qualification_order):
                # Koniec kwalifikacji - przejdź do konkursu
                try:
                    if getattr(self, "_history_qualification_id", None):
                        history_finalize_competition(self._history_qualification_id)
                except Exception:
                    pass
                self._finish_qualification()
                return

            jumper = self.qualification_order[self.current_qualification_jumper_index]

            # Lepszy komunikat o aktualnym skoczku w kwalifikacjach
            self.competition_status_label.setText(
                f"🎯 Kwalifikacje: {jumper} skacze..."
            )
            self.competition_status_label.setProperty("chip", True)
            # Kwalifikacje w toku → zielony
            self.competition_status_label.setProperty("variant", "success")

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

                # Save to history (qualification record)
                try:
                    if getattr(self, "_history_qualification_id", None):
                        history_add_jump(
                            competition_id=self._history_qualification_id,
                            round_index=1,
                            jumper=jumper,
                            order_index=int(
                                self.current_qualification_jumper_index + 1
                            ),
                            distance=float(distance),
                            total_points=float(total_points),
                            judge_data=judge_scores,
                            wind_points=None,
                            gate_points=None,
                            timing_info=getattr(jumper, "last_timing_info", None),
                        )
                except Exception:
                    pass

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
                self.competition_status_label.setProperty("chip", True)
                # Koniec serii → żółty
                self.competition_status_label.setProperty("variant", "warning")

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
                    self.competition_status_label.setProperty("chip", True)
                    # Brak finalistów traktujemy jako zakończone → zielony
                    self.competition_status_label.setProperty("variant", "success")

                    # Przywróć przycisk do stanu początkowego gdy brak finalistów
                    self._update_competition_button(
                        "Rozpocznij zawody", variant="success"
                    )
                    return

                # Ustaw flagę pauzy po pierwszej serii
                self.pause_after_first_round = True
                QTimer.singleShot(2000, self._pause_after_first_round)
            else:
                # Koniec zawodów
                self.competition_status_label.setText("Zawody zakończone!")
                self.competition_status_label.setProperty("chip", True)
                self.competition_status_label.setProperty("variant", "success")

                self.competition_results.sort(
                    key=lambda x: (x["p1"] + x["p2"]), reverse=True
                )
                self._update_competition_table()

                # finalize competition in history
                try:
                    if getattr(self, "_history_competition_id", None):
                        history_finalize_competition(self._history_competition_id)
                except Exception:
                    pass

                # Przywróć przycisk do stanu początkowego na końcu zawodów
                self._update_competition_button("Rozpocznij zawody", variant="success")
            return

        jumper = self.competition_order[self.current_jumper_index]

        # Lepszy komunikat o aktualnym skoczku
        self.competition_status_label.setText(
            f"🎯 Seria {self.current_round}: {jumper} skacze..."
        )
        self.competition_status_label.setProperty("chip", True)
        # Seria w toku → zielony
        self.competition_status_label.setProperty("variant", "success")

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
            # Zapisz timing użyty w tej próbie
            res_item["timing1"] = getattr(jumper, "last_timing_info", None)
        else:
            res_item["d2"] = distance
            res_item["p2"] = total_points
            res_item["judges2"] = judge_scores
            res_item["timing2"] = getattr(jumper, "last_timing_info", None)

        self._update_competition_table()
        self.current_jumper_index += 1

        # Aktualizuj postęp
        if hasattr(self, "progress_label"):
            total_jumpers = len(self.competition_order)
            progress = (self.current_jumper_index / total_jumpers) * 100
            self.progress_label.setText(f"Postęp: {progress:.0f}%")

        # Save jump to history
        try:
            if getattr(self, "_history_competition_id", None):
                history_add_jump(
                    competition_id=self._history_competition_id,
                    round_index=int(self.current_round),
                    jumper=jumper,
                    order_index=int(self.current_jumper_index),
                    distance=float(distance),
                    total_points=float(total_points),
                    judge_data=judge_scores,
                    wind_points=None,
                    gate_points=None,
                    timing_info=getattr(jumper, "last_timing_info", None),
                )
        except Exception:
            pass

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
        self.competition_status_label.setProperty("chip", True)
        self.competition_status_label.setProperty("variant", "warning")
        self.competition_status_label.setStyleSheet("")

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
            # Zapamiętaj pełny wynik w wierszu, by klik działał niezależnie od sortowania
            place_item.setData(Qt.UserRole, result)
            self.qualification_table.setItem(row, 0, place_item)

            # Flaga — mniejsza, idealnie wycentrowana w kontenerze (tak jak w konkursie)
            q_flag_pix = self._create_rounded_flag_pixmap(
                jumper.nationality, size=QSize(24, 16), radius=4
            )
            q_flag_container = QWidget()
            q_flag_layout = QHBoxLayout(q_flag_container)
            q_flag_layout.setContentsMargins(0, 0, 0, 0)
            q_flag_layout.setSpacing(0)
            q_flag_layout.setAlignment(Qt.AlignCenter)
            q_flag_label = QLabel()
            if not q_flag_pix.isNull():
                q_flag_label.setPixmap(q_flag_pix)
            q_flag_layout.addWidget(q_flag_label, 0, Qt.AlignCenter)
            self.qualification_table.setCellWidget(row, 1, q_flag_container)

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
                # Nie nadpisujemy koloru tłem — użyjemy pogrubienia, by trzymać się motywu
                for col in range(self.qualification_table.columnCount()):
                    item = self.qualification_table.item(row, col)
                    if item:
                        f = item.font()
                        f.setBold(True)
                        item.setFont(f)

    def _start_second_round(self):
        """Rozpoczyna drugą serię zawodów"""
        self.simulation_running = True  # Wznów symulację
        self.competition_status_label.setText(
            f"Rozpoczynanie 2. serii... ({len(self.competition_order)} finalistów)"
        )
        self.competition_status_label.setProperty("chip", True)
        self.competition_status_label.setProperty("variant", "success")
        self._update_competition_button("Stop", variant="danger")
        QTimer.singleShot(1000, self._process_next_jumper)

    def _pause_after_qualification(self):
        """Pauza po kwalifikacjach"""
        self.competition_status_label.setText(
            "Kwalifikacje zakończone! Kliknij przycisk aby rozpocząć konkurs."
        )
        self.competition_status_label.setProperty("chip", True)
        self.competition_status_label.setProperty("variant", "warning")
        self._update_competition_button("Rozpocznij I serię", variant="warning")

    def _pause_after_first_round(self):
        """Pauza po pierwszej serii"""
        self.competition_status_label.setText(
            "I seria zakończona! Kliknij przycisk aby rozpocząć II serię."
        )
        self.competition_status_label.setProperty("chip", True)
        self.competition_status_label.setProperty("variant", "warning")
        self._update_competition_button("Rozpocznij II serię", variant="warning")

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

    def _update_competition_button(self, text, color="#28a745", variant=None):
        """Aktualizuje tekst i wariant głównego przycisku zawodów (spójny z motywem)."""
        self.run_comp_btn.setText(text)
        # Ustal kolor wg treści przycisku, aby zawsze był spójny
        normalized = text.strip().lower()
        if "stop" in normalized:
            variant = "danger"
        elif (
            "rozpocznij i seri" in normalized
            or "rozpocznij ii seri" in normalized
            or "rozpocznij 1" in normalized
            or "rozpocznij 2" in normalized
        ):
            variant = "warning"
        elif "rozpocznij zawody" in normalized:
            variant = "success"
        elif "kontynuuj" in normalized:
            variant = "primary"
        # Zastosuj wariant QSS tylko dla przycisku — status label sterowany osobno
        if variant:
            self.run_comp_btn.setProperty("variant", variant)
            self.run_comp_btn.setStyleSheet("")
            # Force button style update
            self.run_comp_btn.style().unpolish(self.run_comp_btn)
            self.run_comp_btn.style().polish(self.run_comp_btn)

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
        self.competition_status_label.setProperty("chip", True)
        self.competition_status_label.setProperty("variant", "danger")
        self.competition_status_label.setStyleSheet("")
        self._update_competition_button("Kontynuuj", variant="primary")

    def _continue_competition(self):
        """Kontynuuje zawody i przywraca przycisk 'Stop'"""
        self.simulation_running = True  # Wznów symulację
        self.competition_status_label.setText("Zawody w toku...")
        self.competition_status_label.setProperty("chip", True)
        # W trakcie → zielony
        self.competition_status_label.setProperty("variant", "success")
        self.competition_status_label.setStyleSheet("")
        self._update_competition_button("Stop", variant="danger")
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

        # Ensure competition history record is created now (finalists as participants)
        try:
            if getattr(self, "_history_competition_id", None) is None:
                hill_name = getattr(self.competition_hill, "name", "")
                comp_name = (
                    f"Zawody {hill_name} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                self._history_competition_id = history_start_competition(
                    name=comp_name,
                    hill_id=str(hill_name),
                    hill_name=hill_name,
                    k_point=float(getattr(self.competition_hill, "K", 0.0)),
                    hs_point=float(getattr(self.competition_hill, "L", 0.0)),
                    mode="competition",
                    app_version=None,
                )
                # Register only finalists/current competition order
                participants = [
                    (
                        getattr(j, "name", ""),
                        getattr(j, "last_name", ""),
                        getattr(j, "nationality", None),
                    )
                    for j in self.competition_order
                ]
                history_register_participants(
                    self._history_competition_id, participants
                )
        except Exception:
            pass

        self._update_competition_button("Stop", variant="danger")
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
            # Bez kolorów tła, tylko tekst i wyrównanie — minimalistycznie
            place_item.setText(str(i + 1))
            place_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 0, place_item)

            # Flaga kraju – opakowana w bezmarginesowy kontener dla idealnego centrowania
            flag_pix = self._create_rounded_flag_pixmap(
                jumper.nationality, size=QSize(24, 16), radius=4
            )
            flag_container = QWidget()
            flag_layout = QHBoxLayout(flag_container)
            flag_layout.setContentsMargins(0, 0, 0, 0)
            flag_layout.setSpacing(0)
            flag_label = QLabel()
            if not flag_pix.isNull():
                flag_label.setPixmap(flag_pix)
            flag_label.setAlignment(Qt.AlignCenter)
            flag_layout.addStretch(1)
            flag_layout.addWidget(flag_label, 0, Qt.AlignCenter)
            flag_layout.addStretch(1)
            self.results_table.setCellWidget(i, 1, flag_container)

            # Nazwa zawodnika (pogrubiona)
            jumper_item = QTableWidgetItem(str(jumper))
            f = jumper_item.font()
            f.setBold(True)
            jumper_item.setFont(f)
            self.results_table.setItem(i, 2, jumper_item)

            # I seria - dystans
            d1_item = QTableWidgetItem()
            d1_item.setText(format_distance_with_unit(res["d1"])) if res[
                "d1"
            ] > 0 else d1_item.setText("-")
            d1_item.setTextAlignment(Qt.AlignCenter)
            f = d1_item.font()
            f.setBold(True)
            d1_item.setFont(f)
            self.results_table.setItem(i, 3, d1_item)

            # I seria - punkty
            p1_item = QTableWidgetItem()
            p1_item.setText(f"{res['p1']:.1f}") if res["p1"] > 0 else p1_item.setText(
                "-"
            )
            p1_item.setTextAlignment(Qt.AlignCenter)
            f = p1_item.font()
            f.setBold(True)
            p1_item.setFont(f)
            self.results_table.setItem(i, 4, p1_item)

            # II seria - dystans
            d2_item = QTableWidgetItem()
            d2_item.setText(format_distance_with_unit(res["d2"])) if res[
                "d2"
            ] > 0 else d2_item.setText("-")
            d2_item.setTextAlignment(Qt.AlignCenter)
            f = d2_item.font()
            f.setBold(True)
            d2_item.setFont(f)
            self.results_table.setItem(i, 5, d2_item)

            # II seria - punkty
            p2_item = QTableWidgetItem()
            p2_item.setText(f"{res['p2']:.1f}") if res["p2"] > 0 else p2_item.setText(
                "-"
            )
            p2_item.setTextAlignment(Qt.AlignCenter)
            f = p2_item.font()
            f.setBold(True)
            p2_item.setFont(f)
            self.results_table.setItem(i, 6, p2_item)

            # Suma punktów (pogrubiona)
            total_points = res.get("p1", 0) + res.get("p2", 0)
            total_item = QTableWidgetItem()
            total_item.setText(
                f"{total_points:.1f}"
            ) if total_points > 0 else total_item.setText("-")
            # Pogrubiony font bez tła
            f_total = total_item.font()
            f_total.setBold(True)
            total_item.setFont(f_total)
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
        card.setProperty("class", "card")

        layout = QVBoxLayout(card)
        layout.setSpacing(5)

        title = QLabel(f"📊 {seria_name}")
        title.setProperty("chip", True)
        title.setProperty("variant", "primary")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Details in a grid-like format
        details_layout = QFormLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(5)

        # Distance
        dist_label = QLabel("Odległość:")
        dist_value = QLabel(format_distance_with_unit(distance))
        dist_value.setProperty("class", "metric")
        details_layout.addRow(dist_label, dist_value)

        # Difference from K-point
        diff_label = QLabel("Różnica od K-point:")
        diff_value = QLabel(f"{difference:+.1f} m")
        diff_value.setProperty("class", "metric")
        details_layout.addRow(diff_label, diff_value)

        # Points for distance
        dist_points_label = QLabel("Punkty za odległość:")
        dist_points_value = QLabel(f"{60.0 + (difference * meter_value):.1f} pkt")
        dist_points_value.setProperty("chip", True)
        dist_points_value.setProperty("variant", "success")
        details_layout.addRow(dist_points_label, dist_points_value)

        # Total points for series
        total_series_points_label = QLabel("Suma punktów serii:")
        total_series_points_value = QLabel(f"{points:.1f} pkt")
        total_series_points_value.setProperty("chip", True)
        total_series_points_value.setProperty("variant", "success")
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
        # Nowa logika: losowanie zdarzenia lądowania (upadek / podpórka / ustanie)
        # Bazowe szanse (do HS): upadek 0.6%, podpórka 0.4%
        p_fall_base = 0.006
        p_hand_base = 0.004

        # Skala ryzyka za HS zależna od Stabilności: f(s) = 1.5 - 0.004*s (0→1.5, 50→1.3, 100→1.1)
        steps_05m = 0
        if distance > hill_size:
            steps_05m = int(math.floor(2 * (distance - hill_size)))
        stability_val = getattr(jumper, "stability", 50.0) or 50.0
        factor_per_step = max(1.0, 1.5 - 0.004 * float(stability_val))

        # Odds scaling, by nie przekroczyć 100%
        r_safe = 1.0
        r_fall = (p_fall_base / (1.0 - p_fall_base)) * (factor_per_step**steps_05m)
        r_hand = (p_hand_base / (1.0 - p_hand_base)) * (factor_per_step**steps_05m)
        Z = r_safe + r_fall + r_hand
        p_fall = r_fall / Z
        p_hand = r_hand / Z
        p_safe = r_safe / Z

        # Wybór zdarzenia
        rnd = random.random()
        if rnd < p_fall:
            event = "fall"
        elif rnd < p_fall + p_hand:
            event = "hand"
        else:
            event = "safe"

        judge_scores = []
        if event == "fall":
            # 5 not: 8–12, zaokrąglenie do 0.5
            for _ in range(5):
                val = random.uniform(8.0, 12.0)
                val = round(val * 2) / 2
                judge_scores.append(val)
        elif event == "hand":
            # 5 not: 11–14, zaokrąglenie do 0.5
            for _ in range(5):
                val = random.uniform(11.0, 14.0)
                val = round(val * 2) / 2
                judge_scores.append(val)
        else:
            # SAFE → wyznacz telemark wg dotychczasowej logiki (nie zmieniamy)
            telemark_chance = self._calculate_telemark_chance(
                jumper, distance, hill_size
            )
            telemark_landing = random.random() < telemark_chance
            for judge in self.judges:
                score = judge.score_jump(
                    jumper, distance, hill_size, telemark_landing, hill
                )
                judge_scores.append(score)

        # Usuń najwyższą i najniższą notę
        judge_scores.sort()
        final_scores = judge_scores[1:-1]

        # Suma not (bez najwyższej i najniższej)
        total_judge_score = sum(final_scores)

        return {
            "all_scores": judge_scores,
            "final_scores": final_scores,
            "total_score": total_judge_score,
            "event": event,
            # Jeśli SAFE, dołącz kontekst telemarku (dla spójności UI)
            "telemark_landing": (event == "safe" and telemark_landing)
            if "telemark_landing" in locals()
            else False,
            "telemark_chance": telemark_chance
            if "telemark_chance" in locals()
            else 0.0,
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
        # Interpolacja szansy na podstawie telemarku (50%→100%)
        telemark_factor = jumper.telemark / 100.0
        base_chance = 0.50 + (telemark_factor * 0.50)

        # Spadek 2.5 p.p. za każdy pełny 1 m za HS (zgodnie z ustaleniami)
        if distance > hill_size:
            meters_over_hs = max(0.0, distance - hill_size)
            distance_penalty = meters_over_hs * 0.025
            base_chance = max(0.0, base_chance - distance_penalty)

        return base_chance


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle("Fusion")
    app.setStyle(CustomProxyStyle())

    # Load minimalist modern QSS theme
    try:
        qss_path = resource_path(os.path.join("ui", "styles.qss"))
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
    except Exception:
        # Silent fallback to default style if QSS fails to load
        pass

    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec())
