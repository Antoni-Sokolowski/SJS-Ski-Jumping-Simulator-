"""Główny plik uruchamiający aplikację symulatora skoków narciarskich."""

import sys
import os
import json
import copy
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
)
from PySide6.QtCore import Qt, QUrl, QTimer, QSize, QPoint
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


class CustomProxyStyle(QProxyStyle):
    """
    Niestandardowy styl, który nadpisuje domyślny czas wyświetlania podpowiedzi.
    """

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return 100
        return super().styleHint(hint, option, widget, returnData)


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
        self.jumper_edit_widgets = {}
        self.hill_edit_widgets = {}

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

        # Wybór skoczni z ikoną
        hill_layout = QHBoxLayout()
        hill_layout.addWidget(QLabel("Skocznia:"))
        self.comp_hill_combo = QComboBox()
        self.comp_hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.comp_hill_combo.addItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )
        self.comp_hill_combo.currentIndexChanged.connect(self.update_competition_hill)
        hill_layout.addWidget(self.comp_hill_combo)
        competition_group_layout.addLayout(hill_layout)

        # Wybór belki z ikoną
        gate_layout = QHBoxLayout()
        gate_layout.addWidget(QLabel("Belka:"))
        self.comp_gate_spin = QSpinBox()
        self.comp_gate_spin.setMinimum(1)
        self.comp_gate_spin.setMaximum(1)
        gate_layout.addWidget(self.comp_gate_spin)
        competition_group_layout.addLayout(gate_layout)

        # Przycisk rozpoczęcia zawodów z lepszym stylem
        run_comp_btn = QPushButton("Rozpocznij zawody")
        run_comp_btn.setStyleSheet("""
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
        run_comp_btn.clicked.connect(self.run_competition)
        competition_group_layout.addWidget(run_comp_btn)

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

        results_panel.addWidget(self.results_table)
        main_hbox.addLayout(results_panel, 2)

        layout.addLayout(main_hbox)
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
        self.add_button = QPushButton("+ Dodaj / Klonuj")
        self.delete_button = QPushButton("- Usuń zaznaczone")
        editor_button_layout.addWidget(self.add_button)
        editor_button_layout.addWidget(self.delete_button)
        left_panel.addLayout(editor_button_layout)

        self.add_button.clicked.connect(self._add_new_item)
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
            "Dane Podstawowe": ["name", "last_name", "nationality", "mass", "height"],
            "Fizyka Najazdu": [
                "inrun_drag_coefficient",
                "inrun_frontal_area",
                "inrun_lift_coefficient",
            ],
            "Fizyka Odbicia": [
                "takeoff_drag_coefficient",
                "takeoff_frontal_area",
                "takeoff_lift_coefficient",
                "jump_force",
            ],
            "Fizyka Lotu": [
                "flight_drag_coefficient",
                "flight_frontal_area",
                "flight_lift_coefficient",
            ],
            "Fizyka Lądowania": [
                "landing_drag_coefficient",
                "landing_frontal_area",
                "landing_lift_coefficient",
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
            "mass": "Masa skoczka w kilogramach. Wpływa na bezwładność i przyspieszenie.",
            "height": "Wzrost skoczka w metrach (np. 1.75).",
            "inrun_drag_coefficient": "Współczynnik oporu aerodynamicznego na najeździe. Wyższe wartości = niższa prędkość na progu.",
            "inrun_frontal_area": "Powierzchnia czołowa na najeździe. Większa powierzchnia = niższa prędkość na progu.",
            "inrun_lift_coefficient": "Siła nośna na najeździe (zazwyczaj 0 lub bliska zera).",
            "takeoff_drag_coefficient": "Opór aerodynamiczny w fazie odbicia (gdy skoczek się prostuje).",
            "takeoff_frontal_area": "Powierzchnia czołowa w fazie odbicia.",
            "takeoff_lift_coefficient": "Siła nośna w fazie odbicia (zazwyczaj 0).",
            "jump_force": "Moc odbicia skoczka. Kluczowy parametr wpływający na parabolę lotu. Typowe wartości: 1400-1800.",
            "flight_drag_coefficient": "Współczynnik oporu aerodynamicznego w locie. Wyższe wartości = krótsze skoki.",
            "flight_frontal_area": "Powierzchnia czołowa w locie.",
            "flight_lift_coefficient": "Współczynnik siły nośnej w locie. Wyższe wartości = dłuższy, bardziej płaski lot. Typowe wartości: 0.6-0.8.",
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
                if attr in ["K", "L", "gates", "jump_force"]:
                    widget = CustomSpinBox()
                    if attr == "jump_force":
                        widget.setRange(0, 3000)
                    else:
                        widget.setRange(0, 500)
                elif (
                    "coefficient" in attr
                    or "area" in attr
                    or "mass" in attr
                    or "height" in attr
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
                elif "deg" in attr:
                    widget = CustomDoubleSpinBox()
                    widget.setRange(-10000.0, 10000.0)
                    widget.setDecimals(2)
                else:
                    widget = QLineEdit()

                # Ustawienie ikon w zależności od motywu
                if isinstance(widget, (CustomSpinBox, CustomDoubleSpinBox)):
                    if self.current_theme == "dark":
                        widget.set_button_icons(
                            self.up_arrow_icon_dark, self.down_arrow_icon_dark
                        )
                    else:
                        widget.set_button_icons(
                            self.up_arrow_icon_light, self.down_arrow_icon_light
                        )

                label_text = (
                    attr.replace("_", " ").replace("deg", "(deg)").capitalize() + ":"
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
                if isinstance(widget, QLineEdit):
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
                if isinstance(widget, QLineEdit):
                    new_value = widget.text()
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
        layout.setSpacing(15)
        layout.setContentsMargins(50, 20, 50, 50)

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
        layout.setSpacing(15)
        layout.setContentsMargins(50, 20, 50, 50)

        layout.addLayout(self._create_top_bar("Podział punktów", self.COMPETITION_IDX))

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
        points_panel.setSpacing(15)

        # Tabela z podziałem punktów
        self.points_breakdown_table = QTableWidget()
        self.points_breakdown_table.setColumnCount(3)
        self.points_breakdown_table.setRowCount(4)
        self.points_breakdown_table.setHorizontalHeaderLabels(
            ["Element", "Wartość", "Punkty"]
        )
        self.points_breakdown_table.verticalHeader().setVisible(False)
        self.points_breakdown_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.points_breakdown_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Styl tabeli breakdown - będzie aktualizowany w update_styles()
        self.points_breakdown_table.setStyleSheet("")
        points_panel.addWidget(self.points_breakdown_table)

        # Formuła obliczeniowa
        self.points_formula_group = QGroupBox("Formuła obliczeniowa")
        self.points_formula_group.setStyleSheet("""
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
        formula_layout = QVBoxLayout(self.points_formula_group)

        self.points_formula_text = QLabel(
            "Punkty = 60.0 + (różnica od K-point × meter value)"
        )
        self.points_formula_text.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #ffffff;
                padding: 10px;
                background-color: #3a3a3a;
                border-radius: 6px;
            }
        """)
        self.points_formula_text.setAlignment(Qt.AlignCenter)
        formula_layout.addWidget(self.points_formula_text)

        # Konkretne obliczenia
        self.points_calculation_text = QLabel()
        self.points_calculation_text.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #059669;
                padding: 10px;
                background-color: rgba(5, 150, 105, 0.1);
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        self.points_calculation_text.setAlignment(Qt.AlignCenter)
        formula_layout.addWidget(self.points_calculation_text)

        points_panel.addWidget(self.points_formula_group)

        # Informacje o skoczni
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
                font-size: 12px;
                color: #ffffff;
                padding: 5px;
            }
        """)
        hill_info_layout.addWidget(self.points_hill_name)

        self.points_gate_info = QLabel()
        self.points_gate_info.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #ffffff;
                padding: 5px;
            }
        """)
        hill_info_layout.addWidget(self.points_gate_info)

        points_panel.addWidget(self.points_hill_info_group)
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

        # Kolumny z punktami to 4 (I seria) i 6 (II seria)
        elif column in [4, 6]:
            seria_num = 1 if column == 4 else 2
            points_str = self.results_table.item(row, column).text()

            if points_str == "-":
                return

            try:
                points = float(points_str)
                distance = result_data[f"d{seria_num}"]
                self._show_points_breakdown(
                    jumper,
                    distance,
                    points,
                    seria_num,
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

    def _show_points_breakdown(self, jumper, distance, points, seria_num):
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

        # Wypełnij tabelę danymi
        data = [
            ("Odległość skoku", format_distance_with_unit(distance), ""),
            ("Punkt K skoczni", f"{k_point:.1f} m", ""),
            ("Różnica od K-point", f"{difference:+.1f} m", ""),
            ("Meter value", f"{meter_value:.1f} pkt/m", ""),
        ]

        # Oblicz punkty dla każdego elementu
        base_points = 60.0
        distance_points = base_points
        k_point_points = 0  # K-point to punkt odniesienia
        difference_points = difference * meter_value
        meter_value_points = 0  # Meter value to współczynnik

        points_data = [
            (
                "Odległość skoku",
                format_distance_with_unit(distance),
                f"{distance_points:.1f}",
            ),
            ("Punkt K skoczni", f"{k_point:.1f} m", f"{k_point_points:.1f}"),
            ("Różnica od K-point", f"{difference:+.1f} m", f"{difference_points:+.1f}"),
            ("Meter value", f"{meter_value:.1f} pkt/m", f"{meter_value_points:.1f}"),
        ]

        for row, (element, value, points_val) in enumerate(points_data):
            element_item = QTableWidgetItem(element)
            element_item.setBackground(QColor("#3a3a3a"))
            element_item.setForeground(QColor("#ffffff"))
            self.points_breakdown_table.setItem(row, 0, element_item)

            value_item = QTableWidgetItem(value)
            value_item.setBackground(QColor("#2a2a2a"))
            value_item.setForeground(QColor("#ffffff"))
            value_item.setTextAlignment(Qt.AlignCenter)
            self.points_breakdown_table.setItem(row, 1, value_item)

            points_item = QTableWidgetItem(points_val)
            points_item.setBackground(QColor("#2a2a2a"))
            points_item.setForeground(QColor("#ffffff"))
            points_item.setTextAlignment(Qt.AlignCenter)
            self.points_breakdown_table.setItem(row, 2, points_item)

        # Aktualizuj konkretne obliczenia
        self.points_calculation_text.setText(
            f"Punkty = 60.0 + ({difference:+.1f} × {meter_value:.1f}) = {points:.1f}"
        )

        # Aktualizuj informacje o skoczni
        self.points_hill_name.setText(f"Skocznia: {self.competition_hill}")
        self.points_gate_info.setText(f"Belka startowa: {self.competition_gate}")

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

        # Przygotuj dane dla obu serii
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

        # Wypełnij tabelę danymi
        points_data = []

        # Dodaj wiersze dla każdej serii
        for seria_name, distance, points, difference in series_data:
            points_data.append(
                (
                    f"{seria_name} - Odległość",
                    format_distance_with_unit(distance),
                    f"{points:.1f}",
                )
            )
            points_data.append(
                (
                    f"{seria_name} - Różnica od K-point",
                    f"{difference:+.1f} m",
                    f"{difference * meter_value:+.1f}",
                )
            )
            points_data.append(
                (f"{seria_name} - Punkty", f"{points:.1f} pkt", f"{points:.1f}")
            )
            # Dodaj pusty wiersz jako separator
            points_data.append(("", "", ""))

        # Dodaj wiersz z sumą
        if len(series_data) > 0:
            points_data.append(
                ("SUMA PUNKTÓW", f"{total_points:.1f} pkt", f"{total_points:.1f}")
            )

        # Wyczyść tabelę i ustaw odpowiednią liczbę wierszy
        self.points_breakdown_table.setRowCount(len(points_data))

        for row, (element, value, points_val) in enumerate(points_data):
            element_item = QTableWidgetItem(element)
            if element == "SUMA PUNKTÓW":
                element_item.setBackground(QColor("#dc3545"))
                element_item.setForeground(QColor("#ffffff"))
                element_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            elif element == "":
                element_item.setBackground(QColor("#1a1a1a"))
                element_item.setForeground(QColor("#1a1a1a"))
            else:
                element_item.setBackground(QColor("#3a3a3a"))
                element_item.setForeground(QColor("#ffffff"))
            self.points_breakdown_table.setItem(row, 0, element_item)

            value_item = QTableWidgetItem(value)
            if element == "SUMA PUNKTÓW":
                value_item.setBackground(QColor("#dc3545"))
                value_item.setForeground(QColor("#ffffff"))
                value_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            elif element == "":
                value_item.setBackground(QColor("#1a1a1a"))
                value_item.setForeground(QColor("#1a1a1a"))
            else:
                value_item.setBackground(QColor("#2a2a2a"))
                value_item.setForeground(QColor("#ffffff"))
            value_item.setTextAlignment(Qt.AlignCenter)
            self.points_breakdown_table.setItem(row, 1, value_item)

            points_item = QTableWidgetItem(points_val)
            if element == "SUMA PUNKTÓW":
                points_item.setBackground(QColor("#dc3545"))
                points_item.setForeground(QColor("#ffffff"))
                points_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            elif element == "":
                points_item.setBackground(QColor("#1a1a1a"))
                points_item.setForeground(QColor("#1a1a1a"))
            else:
                points_item.setBackground(QColor("#2a2a2a"))
                points_item.setForeground(QColor("#ffffff"))
            points_item.setTextAlignment(Qt.AlignCenter)
            self.points_breakdown_table.setItem(row, 2, points_item)

        # Aktualizuj informacje o skoczni
        self.points_hill_name.setText(f"Skocznia: {self.competition_hill}")
        self.points_gate_info.setText(f"Belka startowa: {self.competition_gate}")

        # Aktualizuj formułę obliczeniową
        calculation_text = "Formuła obliczeniowa:\n"
        if len(series_data) == 2:
            calculation_text += f"Suma punktów = {series_data[0][2]:.1f} pkt (I seria) + {series_data[1][2]:.1f} pkt (II seria) = {total_points:.1f} pkt"
        elif len(series_data) == 1:
            calculation_text += f"Suma punktów = {series_data[0][2]:.1f} pkt ({series_data[0][0]}) = {total_points:.1f} pkt"
        else:
            calculation_text += f"Suma punktów = {total_points:.1f} pkt"

        self.points_calculation_text.setText(calculation_text)

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
        # Zawsze pokazuj całą skocznię - ustaw stałe limity
        ax.set_xlim(-inrun_length_to_show - 5, hill.n + hill.a_finish + 50)
        ax.set_ylim(
            min(min(sim_data["y_landing"]), 0) - 5,
            max(sim_data["max_height"] * 1.5, max_y_inrun) + 5,
        )

        (jumper_point,) = ax.plot([], [], "ro", markersize=8)
        (trail_line,) = ax.plot([], [], color="#4da8ff", linewidth=2, alpha=0.5)
        (landing_line,) = ax.plot([], [], color="#00aaff", linewidth=3)
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
                if hasattr(self, "ani") and self.ani:
                    self.ani.event_source.stop()
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

        self.ani = animation.FuncAnimation(
            figure,
            update,
            init_func=init,
            frames=max(len(sim_data["positions"]), len(sim_data["x_landing"])),
            interval=5,
            blit=False,
            repeat=False,
        )
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
        else:
            hill = None

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
        if self.ani:
            self.ani.event_source.stop()
            self.ani = None

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

        # Aktualizuj informację o serii
        if hasattr(self, "round_info_label"):
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
                }
            )

        self.results_table.clearContents()
        self.results_table.setRowCount(len(self.competition_results))
        self._update_competition_table()

        # Lepszy komunikat rozpoczęcia
        self.competition_status_label.setText(
            f"Rozpoczynanie zawodów na {self.competition_hill.name}... "
            f"({len(self.selection_order)} zawodników)"
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
                finalists = self.competition_results[:30]
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
                    return

                QTimer.singleShot(2000, self._start_second_round)
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
        points = calculate_jump_points(distance, self.competition_hill.K)

        if self.current_round == 1:
            res_item["d1"] = distance
            res_item["p1"] = points
        else:
            res_item["d2"] = distance
            res_item["p2"] = points

        self._update_competition_table()
        self.current_jumper_index += 1

        # Aktualizuj postęp
        if hasattr(self, "progress_label"):
            total_jumpers = len(self.competition_order)
            progress = (self.current_jumper_index / total_jumpers) * 100
            self.progress_label.setText(f"Postęp: {progress:.0f}%")

        QTimer.singleShot(150, self._process_next_jumper)

    def _start_second_round(self):
        """Rozpoczyna drugą serię zawodów"""
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
        QTimer.singleShot(1000, self._process_next_jumper)

    def _update_competition_table(self):
        # Sort results before displaying
        if self.current_round == 1 and self.current_jumper_index > 0:
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
                if hasattr(self, "zoom_ani"):
                    self.zoom_ani.event_source.stop()
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


if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle(CustomProxyStyle())

    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec())
