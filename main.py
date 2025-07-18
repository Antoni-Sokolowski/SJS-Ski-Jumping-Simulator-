'''Główny plik uruchamiający aplikację symulatora skoków narciarskich.'''

import sys
import os
import json
import copy
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QComboBox, QSpinBox, QPushButton, QTextEdit, QLabel,
                               QStackedWidget, QSlider, QListWidget, QListWidgetItem,
                               QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                               QFormLayout, QScrollArea, QDoubleSpinBox, QLineEdit, QTabWidget,
                               QFileDialog)
from PySide6.QtCore import Qt, QUrl, QTimer, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage
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


# --- NOWE KLASY WIDGETÓW BLOKUJĄCE PRZYPADKOWE SCROLLOWANIE ---
class NonScrollableDoubleSpinBox(QDoubleSpinBox):
    """
    Niestandardowy DoubleSpinBox, który ignoruje kółko myszy,
    chyba że pole jest aktywne (ma focus).
    """

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NonScrollableSpinBox(QSpinBox):
    """
    Niestandardowy SpinBox, który ignoruje kółko myszy,
    chyba że pole jest aktywne (ma focus).
    """

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


# --- KONIEC NOWYCH KLAS ---

def resource_path(relative_path):
    """
    Zwraca bezwzględną ścieżkę do zasobu. Niezbędne do poprawnego działania
    zapakowanej aplikacji (.exe), która przechowuje zasoby w tymczasowym folderze.
    """
    if getattr(sys, 'frozen', False):
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

        self.MAIN_MENU_IDX, self.SIM_TYPE_MENU_IDX, self.SINGLE_JUMP_IDX, self.COMPETITION_IDX, self.DATA_EDITOR_IDX, self.DESCRIPTION_IDX, self.SETTINGS_IDX, self.JUMP_REPLAY_IDX = range(
            8)

        self.current_theme = "dark"
        self.contrast_level = 1.0
        self.volume_level = 0.3

        self.themes = {
            "dark": lambda contrast: f"""
                QMainWindow, QWidget {{ background-color: #{self.adjust_brightness('1a1a1a', contrast)}; }}
                QLabel {{ color: #{self.adjust_brightness('ffffff', contrast)}; font-size: 16px; font-family: 'Roboto', 'Segoe UI', Arial, sans-serif; }}
                QLabel.headerLabel {{ font-size: 32px; font-weight: bold; color: #0078d4; }}
                QLabel#replayTitleLabel {{ font-size: 24px; font-weight: bold; color: #{self.adjust_brightness('ffffff', contrast)}; }}
                QLabel#replayStatsLabel {{ font-size: 18px; color: #{self.adjust_brightness('b0b0b0', contrast)}; }}
                QComboBox, QSpinBox, QTextEdit, QListWidget, QTableWidget, QLineEdit, QDoubleSpinBox, QTabWidget::pane {{
                    background-color: #{self.adjust_brightness('2a2a2a', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                    border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)};
                    padding: 12px; border-radius: 5px; font-size: 16px;
                }}
                QTabWidget::tab-bar {{ alignment: center; }}
                QTabBar::tab {{
                    background: #{self.adjust_brightness('2a2a2a', contrast)};
                    color: #{self.adjust_brightness('b0b0b0', contrast)};
                    border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)};
                    border-bottom: none;
                    padding: 10px 25px;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                }}
                QTabBar::tab:selected {{
                    background: #{self.adjust_brightness('3a3a3a', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                }}
                QComboBox QAbstractItemView {{
                    background-color: #{self.adjust_brightness('2a2a2a', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                    border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)};
                    selection-background-color: #{self.adjust_brightness('005ea6', contrast)};
                }}
                QListWidget::item {{ padding: 5px; }}
                QListWidget::item:hover {{ background-color: #{self.adjust_brightness('3a3a3a', contrast)}; }}
                QListWidget::item:selected {{ background-color: #{self.adjust_brightness('005ea6', contrast)}; }}
                QListWidget::indicator {{ width: 18px; height: 18px; border-radius: 4px; }}
                QListWidget::indicator:unchecked {{ border: 1px solid #777777; background-color: #2a2a2a; }}
                QListWidget::indicator:checked {{ border: 1px solid #0078d4; background-color: #0078d4; image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iI2ZmZmZmZiIgZD0iTTkgMTYuMTdMNC44MyAxMmwtMS40MSAxLjQxTDkgMTkgMjEgN2wtMS40MS0xLjQxeiIvPjwvc3ZnPg==); }}
                QTableWidget::item {{ padding-left: 5px; }}
                QTableWidget::item:hover {{ background-color: #{self.adjust_brightness('005ea6', contrast)}; }}
                QHeaderView::section {{ background-color: #{self.adjust_brightness('3a3a3a', contrast)}; color: #{self.adjust_brightness('ffffff', contrast)}; padding: 8px; border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)}; }}
                QPushButton {{ background-color: #{self.adjust_brightness('0078d4', contrast)}; color: #{self.adjust_brightness('ffffff', contrast)}; border: none; padding: 15px; border-radius: 5px; font-size: 20px; font-family: 'Roboto', 'Segoe UI', Arial, sans-serif; }}
                QPushButton:hover {{ background-color: #{self.adjust_brightness('005ea6', contrast)}; }}
                QLabel#authorLabel {{ color: #{self.adjust_brightness('b0b0b0', contrast)}; padding: 0 10px 5px 0; }}
                QPushButton#backArrowButton {{ font-size: 28px; font-weight: bold; color: #{self.adjust_brightness('b0b0b0', contrast)}; background-color: transparent; border: none; padding: 0px; border-radius: 20px; }}
                QPushButton#backArrowButton:hover {{ background-color: #{self.adjust_brightness('2f2f2f', contrast)}; }}
                QSlider::groove:horizontal {{ border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)}; height: 8px; background: #{self.adjust_brightness('2a2a2a', contrast)}; margin: 2px 0; border-radius: 4px; }}
                QSlider::handle:horizontal {{ background: #0078d4; border: 1px solid #0078d4; width: 18px; height: 18px; margin: -5px 0; border-radius: 9px; }}
                QSlider::sub-page:horizontal {{ background: #{self.adjust_brightness('005ea6', contrast)}; border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)}; height: 8px; border-radius: 4px; }}
                QScrollBar:vertical {{ border: none; background: #{self.adjust_brightness('2a2a2a', contrast)}; width: 10px; margin: 0; }}
                QScrollBar::handle:vertical {{ background: #{self.adjust_brightness('555555', contrast)}; min-height: 20px; border-radius: 5px; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
                QScrollBar:horizontal {{ border: none; background: #{self.adjust_brightness('2a2a2a', contrast)}; height: 10px; margin: 0; }}
                QScrollBar::handle:horizontal {{ background: #{self.adjust_brightness('555555', contrast)}; min-width: 20px; border-radius: 5px; }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
            """,
            "light": lambda contrast: f"""
                QMainWindow, QWidget {{ background-color: #{self.adjust_brightness('f0f0f0', contrast)}; }}
                QLabel {{ color: #{self.adjust_brightness('1a1a1a', contrast)}; font-size: 16px; }}
                QLabel.headerLabel {{ font-size: 32px; font-weight: bold; color: #0078d4; }}
                QLabel#replayTitleLabel {{ font-size: 24px; font-weight: bold; color: #{self.adjust_brightness('1a1a1a', contrast)}; }}
                QLabel#replayStatsLabel {{ font-size: 18px; color: #{self.adjust_brightness('404040', contrast)}; }}
                QComboBox, QSpinBox, QTextEdit, QListWidget, QTableWidget, QLineEdit, QDoubleSpinBox, QTabWidget::pane {{ background-color: #{self.adjust_brightness('ffffff', contrast)}; color: #{self.adjust_brightness('1a1a1a', contrast)}; border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)}; padding: 12px; border-radius: 5px; font-size: 16px; }}
                QTabWidget::tab-bar {{ alignment: center; }}
                QTabBar::tab {{
                    background: #{self.adjust_brightness('f0f0f0', contrast)};
                    color: #{self.adjust_brightness('505050', contrast)};
                    border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)};
                    border-bottom: none;
                    padding: 10px 25px;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                }}
                QTabBar::tab:selected {{
                    background: #{self.adjust_brightness('ffffff', contrast)};
                    color: #{self.adjust_brightness('1a1a1a', contrast)};
                }}
                QComboBox QAbstractItemView {{
                    border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)};
                    selection-background-color: #{self.adjust_brightness('0078d4', contrast)};
                }}
                QListWidget::item {{ padding: 5px; }}
                QListWidget::item:hover {{ background-color: #{self.adjust_brightness('e0e0e0', contrast)}; }}
                QListWidget::item:selected {{ background-color: #{self.adjust_brightness('0078d4', contrast)}; color: white; }}
                QListWidget::indicator {{ width: 18px; height: 18px; border-radius: 4px; }}
                QListWidget::indicator:unchecked {{ border: 1px solid #999999; background-color: #ffffff; }}
                QListWidget::indicator:checked {{ border: 1px solid #0078d4; background-color: #0078d4; image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iI2ZmZmZmZiIgZD0iTTkgMTYuMTdMNC44MyAxMmwtMS40MSAxLjQxTDkgMTkgMjEgN2wtMS40MS0xLjQxeiIvPjwvc3ZnPg==); }}
                QTableWidget::item {{ padding-left: 5px; }}
                QTableWidget::item:hover {{ background-color: #{self.adjust_brightness('d0eaff', contrast)}; }}
                QHeaderView::section {{ background-color: #{self.adjust_brightness('e9e9e9', contrast)}; color: #{self.adjust_brightness('1a1a1a', contrast)}; padding: 8px; border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)}; }}
                QPushButton {{ background-color: #{self.adjust_brightness('0078d4', contrast)}; color: #{self.adjust_brightness('ffffff', contrast)}; border: none; padding: 15px; border-radius: 5px; font-size: 20px; }}
                QPushButton:hover {{ background-color: #{self.adjust_brightness('005ea6', contrast)}; }}
                QLabel#authorLabel {{ color: #{self.adjust_brightness('404040', contrast)}; padding: 0 10px 5px 0; }}
                QPushButton#backArrowButton {{ font-size: 28px; font-weight: bold; color: #{self.adjust_brightness('404040', contrast)}; background-color: transparent; border: none; padding: 0px; border-radius: 20px; }}
                QPushButton#backArrowButton:hover {{ background-color: #{self.adjust_brightness('e0e0e0', contrast)}; }}
                QSlider::groove:horizontal {{ border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)}; height: 8px; background: #{self.adjust_brightness('e9e9e9', contrast)}; margin: 2px 0; border-radius: 4px; }}
                QSlider::handle:horizontal {{ background: #0078d4; border: 1px solid #0078d4; width: 18px; height: 18px; margin: -5px 0; border-radius: 9px; }}
                QSlider::sub-page:horizontal {{ background: #{self.adjust_brightness('005ea6', contrast)}; border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)}; height: 8px; border-radius: 4px; }}
                QScrollBar:vertical {{ border: none; background: #{self.adjust_brightness('e9e9e9', contrast)}; width: 10px; margin: 0; }}
                QScrollBar::handle:vertical {{ background: #{self.adjust_brightness('c0c0c0', contrast)}; min-height: 20px; border-radius: 5px; }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
                QScrollBar:horizontal {{ border: none; background: #{self.adjust_brightness('e9e9e9', contrast)}; height: 10px; margin: 0; }}
                QScrollBar::handle:horizontal {{ background: #{self.adjust_brightness('c0c0c0', contrast)}; min-width: 20px; border-radius: 5px; }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
            """
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
            message = (f"Nie udało się wczytać lub przetworzyć pliku 'data.json'!\n\n"
                       f"Błąd: {type(e).__name__}: {e}\n\n"
                       f"Upewnij się, że folder 'data' z plikiem 'data.json' istnieje.")
            QMessageBox.critical(None, title, message)
            self.all_hills, self.all_jumpers = [], []

        if self.all_jumpers: self.all_jumpers.sort(key=lambda jumper: str(jumper))
        if self.all_hills: self.all_hills.sort(key=lambda hill: str(hill))

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
            lambda: [self.play_sound(), self.central_widget.setCurrentIndex(self.SIM_TYPE_MENU_IDX)])
        layout.addWidget(btn_sim)
        btn_editor = QPushButton("Edytor Danych")
        btn_editor.clicked.connect(
            lambda: [self.play_sound(), self.central_widget.setCurrentIndex(self.DATA_EDITOR_IDX)])
        layout.addWidget(btn_editor)
        btn_desc = QPushButton("Opis Projektu")
        btn_desc.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(self.DESCRIPTION_IDX)])
        layout.addWidget(btn_desc)
        btn_settings = QPushButton("Ustawienia")
        btn_settings.clicked.connect(
            lambda: [self.play_sound(), self.central_widget.setCurrentIndex(self.SETTINGS_IDX)])
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
        layout.addLayout(self._create_top_bar("Wybierz Tryb Symulacji", self.MAIN_MENU_IDX))
        layout.addStretch(1)
        btn_single = QPushButton("Pojedynczy skok")
        btn_single.clicked.connect(
            lambda: [self.play_sound(), self.central_widget.setCurrentIndex(self.SINGLE_JUMP_IDX)])
        layout.addWidget(btn_single)
        btn_comp = QPushButton("Zawody")
        btn_comp.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(self.COMPETITION_IDX)])
        layout.addWidget(btn_comp)
        layout.addStretch(1)
        self.central_widget.addWidget(widget)

    def _create_single_jump_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Symulacja skoku", self.SIM_TYPE_MENU_IDX))
        self.jumper_combo = QComboBox()
        self.jumper_combo.addItem("Wybierz zawodnika")
        for jumper in self.all_jumpers:
            self.jumper_combo.addItem(self.create_rounded_flag_icon(jumper.nationality), str(jumper))
        self.jumper_combo.currentIndexChanged.connect(self.update_jumper)
        layout.addLayout(self._create_form_row("Zawodnik:", self.jumper_combo))
        self.hill_combo = QComboBox()
        self.hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.hill_combo.addItem(self.create_rounded_flag_icon(hill.country), str(hill))
        self.hill_combo.currentIndexChanged.connect(self.update_hill)
        layout.addLayout(self._create_form_row("Skocznia:", self.hill_combo))
        self.gate_spin = QSpinBox()
        self.gate_spin.setMinimum(1)
        self.gate_spin.setMaximum(1)
        layout.addLayout(self._create_form_row("Belka:", self.gate_spin))
        btn_layout = QHBoxLayout()
        self.simulate_button = QPushButton("Uruchom symulację")
        self.simulate_button.clicked.connect(self.run_simulation)
        self.clear_button = QPushButton("Wyczyść")
        self.clear_button.clicked.connect(self.clear_results)
        btn_layout.addWidget(self.simulate_button)
        btn_layout.addWidget(self.clear_button)
        layout.addLayout(btn_layout)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFixedHeight(80)
        layout.addWidget(self.result_text)
        self.figure = Figure(facecolor=f"#{self.adjust_brightness('1a1a1a', self.contrast_level)}")
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        self.central_widget.addWidget(widget)

    def _create_competition_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Zawody", self.SIM_TYPE_MENU_IDX))
        main_hbox = QHBoxLayout()
        options_vbox = QVBoxLayout()
        select_all_layout = QHBoxLayout()
        self.toggle_all_button = QPushButton("Zaznacz wszystkich")
        self.toggle_all_button.clicked.connect(self._toggle_all_jumpers)
        select_all_layout.addWidget(self.toggle_all_button)
        options_vbox.addLayout(select_all_layout)
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sortuj:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Wg Nazwiska (A-Z)", "Wg Kraju"])
        self.sort_combo.currentTextChanged.connect(self._sort_jumper_list)
        sort_layout.addWidget(self.sort_combo)
        options_vbox.addLayout(sort_layout)
        self.jumper_list_widget = QListWidget()
        for jumper in self.all_jumpers:
            item = QListWidgetItem(self.create_rounded_flag_icon(jumper.nationality), str(jumper))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, jumper)
            self.jumper_list_widget.addItem(item)
        self.jumper_list_widget.itemChanged.connect(self._on_jumper_item_changed)
        options_vbox.addWidget(self.jumper_list_widget)
        self.comp_hill_combo = QComboBox()
        self.comp_hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.comp_hill_combo.addItem(self.create_rounded_flag_icon(hill.country), str(hill))
        self.comp_hill_combo.currentIndexChanged.connect(self.update_competition_hill)
        options_vbox.addLayout(self._create_form_row("2. Skocznia:", self.comp_hill_combo))
        self.comp_gate_spin = QSpinBox()
        self.comp_gate_spin.setMinimum(1)
        self.comp_gate_spin.setMaximum(1)
        options_vbox.addLayout(self._create_form_row("3. Belka:", self.comp_gate_spin))
        run_comp_btn = QPushButton("Rozpocznij zawody")
        run_comp_btn.clicked.connect(self.run_competition)
        options_vbox.addWidget(run_comp_btn)
        options_vbox.addStretch()
        main_hbox.addLayout(options_vbox, 1)
        results_vbox = QVBoxLayout()
        self.competition_status_label = QLabel("Tabela wyników (kliknij odległość, aby zobaczyć powtórkę):")
        results_vbox.addWidget(self.competition_status_label)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Miejsce", "Kraj", "Zawodnik", "I seria", "II seria"])
        self.results_table.verticalHeader().setDefaultSectionSize(40)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.cellClicked.connect(self._on_result_cell_clicked)
        results_vbox.addWidget(self.results_table)
        main_hbox.addLayout(results_vbox, 2)
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

        self.editor_tab_widget = QTabWidget()

        # Jumper list
        jumper_tab = QWidget()
        jumper_tab_layout = QVBoxLayout(jumper_tab)
        jumper_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.editor_jumper_list = QListWidget()
        jumper_tab_layout.addWidget(self.editor_jumper_list)
        self.editor_tab_widget.addTab(jumper_tab, "Skoczkowie")

        # Hill list
        hill_tab = QWidget()
        hill_tab_layout = QVBoxLayout(hill_tab)
        hill_tab_layout.setContentsMargins(0, 0, 0, 0)
        self.editor_hill_list = QListWidget()
        hill_tab_layout.addWidget(self.editor_hill_list)
        self.editor_tab_widget.addTab(hill_tab, "Skocznie")

        # Populate lists
        for jumper in self.all_jumpers:
            item = QListWidgetItem(self.create_rounded_flag_icon(jumper.nationality), str(jumper))
            item.setData(Qt.UserRole, jumper)
            self.editor_jumper_list.addItem(item)
        self.editor_jumper_list.currentItemChanged.connect(self._populate_editor_form)

        for hill in self.all_hills:
            item = QListWidgetItem(self.create_rounded_flag_icon(hill.country), str(hill))
            item.setData(Qt.UserRole, hill)
            self.editor_hill_list.addItem(item)
        self.editor_hill_list.currentItemChanged.connect(self._populate_editor_form)

        left_panel.addWidget(self.editor_tab_widget)

        # Add/Delete buttons
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

        self.editor_placeholder_label = QLabel("Wybierz obiekt z listy po lewej, aby edytować jego właściwości.")
        self.editor_placeholder_label.setAlignment(Qt.AlignCenter)
        self.editor_placeholder_label.setWordWrap(True)

        jumper_form_scroll = QScrollArea()
        jumper_form_scroll.setWidgetResizable(True)
        jumper_form_widget = QWidget()
        jumper_form_layout = QFormLayout(jumper_form_widget)
        jumper_form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.jumper_edit_widgets = self._create_editor_fields(Jumper, jumper_form_layout)
        jumper_form_scroll.setWidget(jumper_form_widget)

        hill_form_scroll = QScrollArea()
        hill_form_scroll.setWidgetResizable(True)
        hill_form_widget = QWidget()
        hill_form_layout = QFormLayout(hill_form_widget)
        hill_form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.hill_edit_widgets = self._create_editor_fields(Hill, hill_form_layout)
        hill_form_scroll.setWidget(hill_form_widget)

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

    def _create_editor_fields(self, data_class, form_layout):
        widgets = {}
        attributes = data_class.__init__.__code__.co_varnames[1:]

        hill_numeric_attrs = ['e1', 'e2', 't', 'r1', 'h', 'n', 's', 'l1', 'l2', 'a_finish', 'P', 'K', 'L', 'Zu']

        for attr in attributes:
            if attr.startswith('_'):
                continue

            widget = None
            if 'coefficient' in attr or 'area' in attr or 'mass' in attr or 'height' in attr or attr in hill_numeric_attrs:
                widget = NonScrollableDoubleSpinBox()
                widget.setRange(-10000.0, 10000.0)
                widget.setDecimals(4)
                widget.setSingleStep(0.01)
            elif 'deg' in attr or 'force' in attr:
                widget = NonScrollableDoubleSpinBox()
                widget.setRange(-10000.0, 10000.0)
                widget.setDecimals(2)
            elif 'gates' in attr:
                widget = NonScrollableSpinBox()
                widget.setRange(1, 100)
            else:
                widget = QLineEdit()

            label_text = attr.replace('_', ' ').replace('deg', '(deg)').capitalize() + ':'
            form_layout.addRow(label_text, widget)
            widgets[attr] = widget
        return widgets

    def _add_new_item(self):
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()

        if current_tab_index == 0:  # Skoczkowie
            new_jumper = Jumper(name="Nowy", last_name="Skoczek", nationality="POL")
            self.all_jumpers.append(new_jumper)

            item = QListWidgetItem(self.create_rounded_flag_icon(new_jumper.nationality), str(new_jumper))
            item.setData(Qt.UserRole, new_jumper)
            self.editor_jumper_list.addItem(item)
            self.editor_jumper_list.setCurrentItem(item)
            self.editor_jumper_list.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)

        elif current_tab_index == 1:  # Skocznie
            selected_item = self.editor_hill_list.currentItem()
            if not selected_item:
                QMessageBox.information(self, "Informacja", "Aby sklonować skocznię, najpierw zaznacz ją na liście.")
                return

            hill_to_clone = selected_item.data(Qt.UserRole)
            new_hill = copy.deepcopy(hill_to_clone)
            new_hill.name = f"{hill_to_clone.name} (Kopia)"

            self.all_hills.append(new_hill)

            item = QListWidgetItem(self.create_rounded_flag_icon(new_hill.country), str(new_hill))
            item.setData(Qt.UserRole, new_hill)
            self.editor_hill_list.addItem(item)
            self.editor_hill_list.setCurrentItem(item)
            self.editor_hill_list.scrollToItem(item, QListWidget.ScrollHint.PositionAtCenter)

        self._refresh_all_data_widgets()

    def _delete_selected_item(self):
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()
        active_list = self.editor_jumper_list if current_tab_index == 0 else self.editor_hill_list

        current_item = active_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Błąd", "Nie zaznaczono żadnego elementu do usunięcia.")
            return

        data_obj = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(self, "Potwierdzenie usunięcia",
                                     f"Czy na pewno chcesz usunąć '{str(data_obj)}'?\nTej operacji nie można cofnąć.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

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
            QMessageBox.information(self, "Usunięto", "Wybrany element został usunięty.")

    def _populate_editor_form(self, current_item=None, previous_item=None):
        active_list_widget = self.editor_tab_widget.currentWidget()
        if isinstance(active_list_widget, QListWidget):
            current_item = active_list_widget.currentItem()
        else:
            current_item = self.editor_jumper_list.currentItem() if self.editor_tab_widget.currentIndex() == 0 else self.editor_hill_list.currentItem()

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

            try:
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value) if value is not None else "")
                elif isinstance(widget, (QDoubleSpinBox, QSpinBox)):
                    if value is None:
                        widget.setValue(0)
                    else:
                        widget.setValue(float(value))
            except (ValueError, TypeError) as e:
                print(f"Błąd podczas wypełniania pola dla '{attr}': {e}. Ustawiono wartość domyślną.")
                if isinstance(widget, QLineEdit):
                    widget.clear()
                else:
                    widget.setValue(0)

    def _save_current_edit(self):
        self.play_sound()
        active_list_widget = self.editor_tab_widget.currentWidget()
        if not isinstance(active_list_widget, QListWidget):
            active_list_widget = self.editor_jumper_list if self.editor_tab_widget.currentIndex() == 0 else self.editor_hill_list

        current_item = active_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Błąd", "Nie wybrano żadnego elementu do zapisania.")
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

        # Update item text in the list
        current_item.setText(str(data_obj))
        if hasattr(data_obj, 'country'):
            current_item.setIcon(self.create_rounded_flag_icon(data_obj.country))
        elif hasattr(data_obj, 'nationality'):
            current_item.setIcon(self.create_rounded_flag_icon(data_obj.nationality))

        self._refresh_all_data_widgets()

        QMessageBox.information(self, "Sukces", f"Zmiany dla '{str(data_obj)}' zostały zastosowane w aplikacji.")

    def _save_data_to_json(self):
        self.play_sound()
        data_dir = resource_path("data")
        default_path = os.path.join(data_dir, "data.json")

        filePath, _ = QFileDialog.getSaveFileName(self, "Zapisz plik danych", default_path, "JSON Files (*.json)")

        if not filePath:
            return

        try:
            data_to_save = {
                "hills": [h.to_dict() for h in self.all_hills],
                "jumpers": [j.to_dict() for j in self.all_jumpers]
            }
            with open(filePath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)

            QMessageBox.information(self, "Sukces", f"Dane zostały pomyślnie zapisane do pliku:\n{filePath}")

        except Exception as e:
            QMessageBox.critical(self, "Błąd zapisu", f"Nie udało się zapisać pliku.\nBłąd: {e}")

    def _refresh_all_data_widgets(self):
        # Store selections
        sel_jumper_text = ""
        if self.jumper_combo.currentIndex() > -1: sel_jumper_text = self.jumper_combo.currentText()

        sel_hill_text = ""
        if self.hill_combo.currentIndex() > -1: sel_hill_text = self.hill_combo.currentText()

        sel_comp_hill_text = ""
        if self.comp_hill_combo.currentIndex() > -1: sel_comp_hill_text = self.comp_hill_combo.currentText()

        # Re-sort lists
        self.all_jumpers.sort(key=lambda jumper: str(jumper))
        self.all_hills.sort(key=lambda hill: str(hill))

        # Clear and repopulate all widgets
        # Single Jump
        self.jumper_combo.clear()
        self.jumper_combo.addItem("Wybierz zawodnika")
        for jumper in self.all_jumpers:
            self.jumper_combo.addItem(self.create_rounded_flag_icon(jumper.nationality), str(jumper))

        self.hill_combo.clear()
        self.hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.hill_combo.addItem(self.create_rounded_flag_icon(hill.country), str(hill))

        # Competition
        self.comp_hill_combo.clear()
        self.comp_hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.comp_hill_combo.addItem(self.create_rounded_flag_icon(hill.country), str(hill))

        self.jumper_list_widget.clear()
        for jumper in self.all_jumpers:
            item = QListWidgetItem(self.create_rounded_flag_icon(jumper.nationality), str(jumper))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, jumper)
            self.jumper_list_widget.addItem(item)
        self._sort_jumper_list(self.sort_combo.currentText())

        # Restore selections if possible
        self.jumper_combo.setCurrentText(sel_jumper_text)
        self.hill_combo.setCurrentText(sel_hill_text)
        self.comp_hill_combo.setCurrentText(sel_comp_hill_text)

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

        self.replay_figure = Figure(facecolor=f"#{self.adjust_brightness('1a1a1a', self.contrast_level)}")
        self.replay_canvas = FigureCanvas(self.replay_figure)
        layout.addWidget(self.replay_canvas)

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
        self.theme_combo.addItems(["Ciemny", "Jasny"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        layout.addLayout(self._create_form_row("Motyw:", self.theme_combo))
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setRange(50, 150)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.change_contrast)
        layout.addLayout(self._create_form_row("Kontrast:", self.contrast_slider))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.volume_level * 100))
        self.volume_slider.valueChanged.connect(self.change_volume)
        layout.addLayout(self._create_form_row("Głośność:", self.volume_slider))
        layout.addStretch()
        self.central_widget.addWidget(widget)

    def _create_top_bar(self, title_text, back_index):
        top_bar = QHBoxLayout()
        btn = QPushButton("←")
        btn.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(back_index)])
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

    def _toggle_all_jumpers(self):
        self.play_sound()
        checked_count = sum(1 for i in range(self.jumper_list_widget.count()) if
                            self.jumper_list_widget.item(i).checkState() == Qt.Checked)

        if checked_count < self.jumper_list_widget.count():
            new_state = Qt.Checked
            self.toggle_all_button.setText("Odznacz wszystkich")
        else:
            new_state = Qt.Unchecked
            self.toggle_all_button.setText("Zaznacz wszystkich")

        self.jumper_list_widget.itemChanged.disconnect(self._on_jumper_item_changed)
        for i in range(self.jumper_list_widget.count()):
            self.jumper_list_widget.item(i).setCheckState(new_state)
        self.jumper_list_widget.itemChanged.connect(self._on_jumper_item_changed)

        self.selection_order.clear()
        if new_state == Qt.Checked:
            self.selection_order = [self.jumper_list_widget.item(i).data(Qt.UserRole) for i in
                                    range(self.jumper_list_widget.count())]

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
            item = QListWidgetItem(self.create_rounded_flag_icon(jumper.nationality), str(jumper))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(check_state)
            item.setData(Qt.UserRole, jumper)
            self.jumper_list_widget.addItem(item)

        self.jumper_list_widget.itemChanged.connect(self._on_jumper_item_changed)

    def _on_result_cell_clicked(self, row, column):
        self.play_sound()
        if column not in [3, 4]:
            return
        if row >= len(self.competition_results):
            return

        result_data = self.competition_results[row]
        jumper = result_data["jumper"]

        seria_num = 1 if column == 3 else 2
        distance_str = self.results_table.item(row, column).text()

        if distance_str == "-":
            return

        try:
            distance = float(distance_str)
            self._show_jump_replay(jumper, self.competition_hill, self.competition_gate, distance, seria_num)
        except (ValueError, TypeError):
            return

    def _show_jump_replay(self, jumper, hill, gate, distance, seria_num):
        sim_data = self._calculate_trajectory(jumper, hill, gate)

        self.replay_title_label.setText(f"{jumper} - Seria {seria_num}")
        stats_text = (f"Odległość: {distance:.2f} m  |  "
                      f"Prędkość na progu: {sim_data['inrun_velocity_kmh']:.2f} km/h  |  "
                      f"Kąt wybicia: {sim_data['takeoff_angle_deg']:.2f}°")
        self.replay_stats_label.setText(stats_text)

        self.central_widget.setCurrentIndex(self.JUMP_REPLAY_IDX)
        self._run_animation_on_canvas(self.replay_canvas, self.replay_figure, sim_data, hill)

    def _calculate_trajectory(self, jumper, hill, gate):
        inrun_velocity = inrun_simulation(hill, jumper, gate_number=gate)

        positions = [(0, 0)]
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
        max_hill_length = hill.L + 50
        max_height = 0

        while current_position_y > hill.y_landing(current_position_x) and current_position_x < max_hill_length:
            total_velocity = math.sqrt(current_velocity_x ** 2 + current_velocity_y ** 2)
            angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)
            force_g_y = -jumper.mass * 9.81

            c_d = jumper.flight_drag_coefficient
            c_l = jumper.flight_lift_coefficient
            area = jumper.flight_frontal_area

            force_drag_magnitude = 0.5 * 1.225 * c_d * area * total_velocity ** 2
            force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
            force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)
            force_lift_magnitude = 0.5 * 1.225 * c_l * area * total_velocity ** 2
            force_lift_x = -force_lift_magnitude * math.sin(angle_of_flight_rad)
            force_lift_y = force_lift_magnitude * math.cos(angle_of_flight_rad)

            acceleration_x = (force_drag_x + force_lift_x) / jumper.mass
            acceleration_y = (force_g_y + force_drag_y + force_lift_y) / jumper.mass

            current_velocity_x += acceleration_x * time_step
            current_velocity_y += acceleration_y * time_step
            current_position_x += current_velocity_x * time_step
            current_position_y += current_velocity_y * time_step
            max_height = max(max_height, current_position_y)
            positions.append((current_position_x, current_position_y))

        x_landing = np.linspace(0, current_position_x + 50, 100)
        y_landing = [hill.y_landing(x_val) for x_val in x_landing]

        return {
            "positions": positions, "x_landing": x_landing, "y_landing": y_landing,
            "max_height": max_height, "max_hill_length": max_hill_length,
            "inrun_velocity_kmh": inrun_velocity * 3.6,
            "takeoff_angle_deg": math.degrees(takeoff_angle_rad)
        }

    def _run_animation_on_canvas(self, canvas, figure, sim_data, hill):
        figure.clear()
        ax = figure.add_subplot(111)
        ax.set_facecolor(
            f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
        figure.patch.set_facecolor(
            f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
        ax.axis('off')
        ax.set_aspect('auto')

        inrun_length_to_show = 15.0
        x_inrun = np.linspace(-inrun_length_to_show, 0, 50)
        y_inrun = np.tan(-hill.alpha_rad) * x_inrun
        ax.plot(x_inrun, y_inrun, color='#00aaff', linewidth=3)

        max_y_inrun = y_inrun[0] if len(y_inrun) > 0 else 0
        ax.set_xlim(-inrun_length_to_show - 5, sim_data['max_hill_length'] + 10)
        ax.set_ylim(min(min(sim_data['y_landing']), 0) - 5, max(sim_data['max_height'] * 1.5, max_y_inrun) + 5)

        jumper_point, = ax.plot([], [], 'ro', markersize=8)
        trail_line, = ax.plot([], [], color='#4da8ff', linewidth=2, alpha=0.5)
        landing_line, = ax.plot([], [], color='#00aaff', linewidth=3)
        plot_elements = [jumper_point, trail_line, landing_line]

        def init():
            for element in plot_elements: element.set_data([], [])
            return plot_elements

        def update(frame):
            positions, x_landing, y_landing = sim_data["positions"], sim_data["x_landing"], sim_data["y_landing"]
            if frame >= max(len(positions), len(x_landing)):
                if hasattr(self, 'ani') and self.ani: self.ani.event_source.stop()
                return plot_elements
            if frame < len(positions):
                x, y = positions[frame]
                jumper_point.set_data([x], [y])
                trail_line.set_data([p[0] for p in positions[:frame + 1]], [p[1] for p in positions[:frame + 1]])
            if frame < len(x_landing):
                landing_line.set_data(x_landing[:frame], y_landing[:frame])
            return plot_elements

        self.ani = animation.FuncAnimation(figure, update, init_func=init,
                                           frames=max(len(sim_data["positions"]), len(sim_data["x_landing"])),
                                           interval=5, blit=False, repeat=False)
        canvas.draw()

    def run_simulation(self):
        self.play_sound()
        if not self.selected_jumper or not self.selected_hill:
            self.result_text.setText("BŁĄD: Musisz wybrać zawodnika i skocznię!")
            return
        gate = self.gate_spin.value()

        try:
            sim_data = self._calculate_trajectory(self.selected_jumper, self.selected_hill, gate)
            distance = fly_simulation(self.selected_hill, self.selected_jumper, gate)

            self.result_text.setText(
                f"Prędkość na progu: {sim_data['inrun_velocity_kmh']:.2f} km/h\n"
                f"Odległość: {distance:.2f} m")

            self._run_animation_on_canvas(self.canvas, self.figure, sim_data, self.selected_hill)

        except ValueError as e:
            self.result_text.setText(f"BŁĄD: {str(e)}")

    def play_sound(self):
        if hasattr(self, 'sound_loaded') and self.sound_loaded:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.setPosition(0)
            else:
                self.player.play()

    def adjust_brightness(self, hex_color, contrast):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        rgb = [min(max(int(c * contrast), 0), 255) for c in rgb]
        return f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def update_jumper(self):
        if self.jumper_combo.currentIndex() > 0:
            self.selected_jumper = self.all_jumpers[self.jumper_combo.currentIndex() - 1]
        else:
            self.selected_jumper = None

    def update_hill(self):
        if self.hill_combo.currentIndex() > 0:
            self.selected_hill = self.all_hills[self.hill_combo.currentIndex() - 1]
            if self.selected_hill: self.gate_spin.setMaximum(self.selected_hill.gates)
        else:
            self.selected_hill = None

    def update_competition_hill(self):
        if self.comp_hill_combo.currentIndex() > 0:
            hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
            if hill: self.comp_gate_spin.setMaximum(hill.gates)
        else:
            hill = None

    def clear_results(self):
        self.jumper_combo.setCurrentIndex(0)
        self.hill_combo.setCurrentIndex(0)
        self.gate_spin.setValue(1)
        self.result_text.clear()
        if hasattr(self, 'figure'):
            self.figure.clear()
            self.canvas.draw()
        if self.ani:
            self.ani.event_source.stop()
            self.ani = None

    def change_theme(self, theme):
        self.current_theme = "dark" if theme == "Ciemny" else "light"
        self.update_styles()

    def change_contrast(self):
        self.contrast_level = self.contrast_slider.value() / 100.0
        self.update_styles()

    def change_volume(self):
        self.volume_level = self.volume_slider.value() / 100.0
        if hasattr(self, 'sound_loaded') and self.sound_loaded: self.audio_output.setVolume(self.volume_level)

    def update_styles(self):
        self.setStyleSheet(self.themes[self.current_theme](self.contrast_level))
        if hasattr(self, 'figure'):
            self.figure.set_facecolor(
                f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
            if hasattr(self, 'canvas'): self.canvas.draw()
        if hasattr(self, 'replay_figure'):
            self.replay_figure.set_facecolor(
                f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
            if hasattr(self, 'replay_canvas'): self.replay_canvas.draw()

    def _create_rounded_flag_pixmap(self, country_code, size=QSize(48, 33), radius=8):
        if not country_code: return QPixmap()
        flag_path = resource_path(os.path.join("assets", "flags", f"{country_code}.png"))
        if not os.path.exists(flag_path): return QPixmap()
        try:
            with Image.open(flag_path) as img:
                img_resized = img.resize((size.width(), size.height()), Image.Resampling.LANCZOS).convert("RGBA")
            mask = Image.new('L', img_resized.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle(((0, 0), img_resized.size), radius=radius, fill=255)
            img_resized.putalpha(mask)
            qimage = QImage(img_resized.tobytes("raw", "RGBA"), img_resized.width, img_resized.height,
                            QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimage)
        except Exception as e:
            print(f"Error creating flag pixmap for {country_code}: {e}")
            return QPixmap()

    def create_rounded_flag_icon(self, country_code, radius=6):
        pixmap = self._create_rounded_flag_pixmap(country_code, size=QSize(32, 22), radius=radius)
        if pixmap.isNull():
            return QIcon()
        return QIcon(pixmap)

    def run_competition(self):
        self.play_sound()
        hill_idx = self.comp_hill_combo.currentIndex()
        if hill_idx == 0 or not self.selection_order:
            self.competition_status_label.setText(
                "<font color='red'>BŁĄD: Wybierz skocznię i co najmniej jednego zawodnika!</font>")
            QTimer.singleShot(3000, lambda: self.competition_status_label.setText(
                "Tabela wyników (kliknij odległość, aby zobaczyć powtórkę):"))
            return
        self.competition_hill = self.all_hills[hill_idx - 1]
        self.competition_gate = self.comp_gate_spin.value()
        self.competition_results = []
        self.current_jumper_index = 0
        self.current_round = 1
        self.competition_order = self.selection_order
        for jumper in self.selection_order:
            self.competition_results.append({"jumper": jumper, "d1": 0.0, "d2": 0.0})
        self.results_table.clearContents()
        self.results_table.setRowCount(len(self.competition_results))
        self._update_competition_table()
        self.competition_status_label.setText("Rozpoczynanie 1. serii...")
        QTimer.singleShot(500, self._process_next_jumper)

    def _process_next_jumper(self):
        if self.current_jumper_index >= len(self.competition_order):
            if self.current_round == 1:
                self.competition_status_label.setText("Koniec 1. serii. Rozpoczynanie 2. serii...")
                self.current_round = 2
                self.competition_results.sort(key=lambda x: x["d1"], reverse=True)
                finalists = self.competition_results[:30]
                finalists.reverse()
                self.competition_order = [res["jumper"] for res in finalists]
                self.current_jumper_index = 0
                if not self.competition_order:
                    self.competition_status_label.setText("Zawody zakończone! (Brak finalistów)")
                    return
                QTimer.singleShot(1500, self._process_next_jumper)
            else:
                self.competition_status_label.setText("Zawody zakończone!")
                self.competition_results.sort(key=lambda x: (x["d1"] + x["d2"]), reverse=True)
                self._update_competition_table()
            return
        jumper = self.competition_order[self.current_jumper_index]
        self.competition_status_label.setText(f"Seria {self.current_round}: skacze {jumper}...")
        distance = fly_simulation(self.competition_hill, jumper, self.competition_gate)
        res_item = next(item for item in self.competition_results if item["jumper"] == jumper)
        if self.current_round == 1:
            res_item["d1"] = distance
        else:
            res_item["d2"] = distance
        self._update_competition_table()
        self.current_jumper_index += 1
        QTimer.singleShot(150, self._process_next_jumper)

    def _update_competition_table(self):
        # Sort results before displaying
        if self.current_round == 1 and self.current_jumper_index > 0:
            # In round 1, sort by first distance
            self.competition_results.sort(key=lambda x: x.get('d1', 0), reverse=True)
        elif self.current_round == 2:
            # In round 2, sort by total distance
            self.competition_results.sort(key=lambda x: (x.get('d1', 0) + x.get('d2', 0)), reverse=True)

        self.results_table.setRowCount(len(self.competition_results))
        for i, res in enumerate(self.competition_results):
            jumper = res["jumper"]
            flag_label = QLabel()
            flag_pixmap = self._create_rounded_flag_pixmap(jumper.nationality)
            if not flag_pixmap.isNull():
                flag_label.setPixmap(flag_pixmap)
            flag_label.setScaledContents(True)
            flag_label.setAlignment(Qt.AlignCenter)
            flag_label.setStyleSheet("padding: 4px;")
            self.results_table.setCellWidget(i, 1, flag_label)
            self.results_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.results_table.setItem(i, 2, QTableWidgetItem(str(jumper)))
            self.results_table.setItem(i, 3, QTableWidgetItem(f"{res['d1']:.2f}" if res['d1'] > 0 else "-"))
            self.results_table.setItem(i, 4, QTableWidgetItem(f"{res['d2']:.2f}" if res['d2'] > 0 else "-"))
        QApplication.processEvents()

    def start_zoom_animation(self, ax, plot_elements):
        if not hasattr(self, 'positions') or not self.positions: return
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
                if hasattr(self, 'zoom_ani'): self.zoom_ani.event_source.stop()
                return
            t = frame / zoom_frames
            new_xlim = (initial_xlim[0] + t * (final_xlim[0] - initial_xlim[0]),
                        initial_xlim[1] + t * (final_xlim[1] - initial_xlim[1]))
            new_ylim = (initial_ylim[0] + t * (final_ylim[0] - initial_ylim[0]),
                        initial_ylim[1] + t * (final_ylim[1] - initial_ylim[1]))
            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)
            self.canvas.draw_idle()
            return

        self.zoom_ani = animation.FuncAnimation(self.figure, zoom_update, frames=zoom_frames + 1, interval=50,
                                                blit=False, repeat=False)
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec())