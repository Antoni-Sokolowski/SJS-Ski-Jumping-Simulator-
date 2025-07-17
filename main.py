'''Główny plik uruchamiający aplikację symulatora skoków narciarskich.'''

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QComboBox, QSpinBox, QPushButton, QTextEdit, QLabel,
                               QStackedWidget, QSlider, QListWidget, QListWidgetItem,
                               QTableWidget, QTableWidgetItem, QHeaderView)
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


def resource_path(relative_path):
    """
    Zwraca bezwzględną ścieżkę do zasobu. Niezbędne do poprawnego działania
    zapakowanej aplikacji (.exe), która przechowuje zasoby w tymczasowym folderze.
    """
    if getattr(sys, 'frozen', False):  # Sprawdza, czy aplikacja jest "zamrożona" przez PyInstaller
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

        # --- Indeksy stron dla QStackedWidget ---
        self.MAIN_MENU_IDX, self.SIM_TYPE_MENU_IDX, self.SINGLE_JUMP_IDX, self.COMPETITION_IDX, self.DESCRIPTION_IDX, self.SETTINGS_IDX = range(
            6)

        # --- Zmienne stanu aplikacji ---
        self.current_theme = "dark"
        self.contrast_level = 1.0
        self.volume_level = 0.3

        # --- Definicje motywów (Arkusz Stylów QSS) ---
        self.themes = {
            "dark": lambda contrast: f"""
                QMainWindow, QWidget {{ background-color: #{self.adjust_brightness('1a1a1a', contrast)}; }}
                QLabel {{ color: #{self.adjust_brightness('ffffff', contrast)}; font-size: 16px; font-family: 'Roboto', 'Segoe UI', Arial, sans-serif; }}
                QLabel.headerLabel {{ font-size: 32px; font-weight: bold; color: #0078d4; }}
                QComboBox, QSpinBox, QTextEdit, QListWidget, QTableWidget {{
                    background-color: #{self.adjust_brightness('2a2a2a', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                    border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)};
                    padding: 12px; border-radius: 5px; font-size: 16px;
                }}
                QListWidget::item {{ padding: 5px; }}
                QListWidget::indicator {{
                    width: 18px; height: 18px; border-radius: 4px;
                }}
                QListWidget::indicator:unchecked {{
                    border: 1px solid #777777; background-color: #2a2a2a;
                }}
                QListWidget::indicator:checked {{
                    border: 1px solid #0078d4; background-color: #0078d4;
                    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iI2ZmZmZmZiIgZD0iTTkgMTYuMTdMNC44MyAxMmwtMS40MSAxLjQxTDkgMTkgMjEgN2wtMS40MS0xLjQxeiIvPjwvc3ZnPg==);
                }}
                QTableWidget::item {{ padding-left: 5px; }}
                QHeaderView::section {{ background-color: #{self.adjust_brightness('3a3a3a', contrast)}; color: #{self.adjust_brightness('ffffff', contrast)}; padding: 8px; border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)}; }}
                QComboBox QAbstractItemView::item {{ color: #{self.adjust_brightness('ffffff', contrast)}; background-color: #{self.adjust_brightness('2a2a2a', contrast)}; }}
                QComboBox QAbstractItemView::item:selected {{ background-color: #{self.adjust_brightness('005ea6', contrast)}; color: #{self.adjust_brightness('ffffff', contrast)}; }}
                QPushButton {{ background-color: #{self.adjust_brightness('0078d4', contrast)}; color: #{self.adjust_brightness('ffffff', contrast)}; border: none; padding: 15px; border-radius: 5px; font-size: 20px; font-family: 'Roboto', 'Segoe UI', Arial, sans-serif; }}
                QPushButton:hover {{ background-color: #{self.adjust_brightness('005ea6', contrast)}; }}
                QLabel#authorLabel {{ color: #{self.adjust_brightness('b0b0b0', contrast)}; padding: 0 10px 5px 0; }}
                QPushButton#backArrowButton {{ font-size: 28px; font-weight: bold; color: #{self.adjust_brightness('b0b0b0', contrast)}; background-color: transparent; border: none; padding: 0px; border-radius: 20px; }}
                QPushButton#backArrowButton:hover {{ background-color: #{self.adjust_brightness('2f2f2f', contrast)}; }}
                QSlider::groove:horizontal {{ border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)}; height: 8px; background: #{self.adjust_brightness('2a2a2a', contrast)}; margin: 2px 0; border-radius: 4px; }}
                QSlider::handle:horizontal {{ background: #0078d4; border: 1px solid #0078d4; width: 18px; height: 18px; margin: -5px 0; border-radius: 9px; }}
                QSlider::sub-page:horizontal {{ background: #{self.adjust_brightness('005ea6', contrast)}; border: 1px solid #{self.adjust_brightness('4a4a4a', contrast)}; height: 8px; border-radius: 4px; }}
            """,
            "light": lambda contrast: f"""
                QMainWindow, QWidget {{ background-color: #{self.adjust_brightness('f0f0f0', contrast)}; }}
                QLabel {{ color: #{self.adjust_brightness('1a1a1a', contrast)}; font-size: 16px; }}
                QLabel.headerLabel {{ font-size: 32px; font-weight: bold; color: #0078d4; }}
                QComboBox, QSpinBox, QTextEdit, QListWidget, QTableWidget {{ background-color: #{self.adjust_brightness('ffffff', contrast)}; color: #{self.adjust_brightness('1a1a1a', contrast)}; border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)}; padding: 12px; border-radius: 5px; font-size: 16px; }}
                QListWidget::item {{ padding: 5px; }}
                QListWidget::indicator {{
                    width: 18px; height: 18px; border-radius: 4px;
                }}
                QListWidget::indicator:unchecked {{
                    border: 1px solid #999999; background-color: #ffffff;
                }}
                QListWidget::indicator:checked {{
                    border: 1px solid #0078d4; background-color: #0078d4;
                    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iI2ZmZmZmZiIgZD0iTTkgMTYuMTdMNC44MyAxMmwtMS40MSAxLjQxTDkgMTkgMjEgN2wtMS40MS0xLjQxeiIvPjwvc3ZnPg==);
                }}
                QTableWidget::item {{ padding-left: 5px; }}
                QHeaderView::section {{ background-color: #{self.adjust_brightness('e9e9e9', contrast)}; color: #{self.adjust_brightness('1a1a1a', contrast)}; padding: 8px; border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)}; }}
                QPushButton {{ background-color: #{self.adjust_brightness('0078d4', contrast)}; color: #{self.adjust_brightness('ffffff', contrast)}; border: none; padding: 15px; border-radius: 5px; font-size: 20px; }}
                QPushButton:hover {{ background-color: #{self.adjust_brightness('005ea6', contrast)}; }}
                QLabel#authorLabel {{ color: #{self.adjust_brightness('404040', contrast)}; padding: 0 10px 5px 0; }}
                QPushButton#backArrowButton {{ font-size: 28px; font-weight: bold; color: #{self.adjust_brightness('404040', contrast)}; background-color: transparent; border: none; padding: 0px; border-radius: 20px; }}
                QPushButton#backArrowButton:hover {{ background-color: #{self.adjust_brightness('e0e0e0', contrast)}; }}
                QSlider::groove:horizontal {{ border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)}; height: 8px; background: #{self.adjust_brightness('e9e9e9', contrast)}; margin: 2px 0; border-radius: 4px; }}
                QSlider::handle:horizontal {{ background: #0078d4; border: 1px solid #0078d4; width: 18px; height: 18px; margin: -5px 0; border-radius: 9px; }}
                QSlider::sub-page:horizontal {{ background: #{self.adjust_brightness('005ea6', contrast)}; border: 1px solid #{self.adjust_brightness('d0d0d0', contrast)}; height: 8px; border-radius: 4px; }}
            """
        }
        self.setStyleSheet(self.themes[self.current_theme](self.contrast_level))

        # --- Konfiguracja odtwarzacza dźwięku ---
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        sound_file = resource_path(os.path.join("assets", "click.wav"))
        self.sound_loaded = os.path.exists(sound_file)
        if self.sound_loaded:
            self.player.setSource(QUrl.fromLocalFile(sound_file))
            self.audio_output.setVolume(self.volume_level)

        # --- Wczytywanie i sortowanie danych ---
        self.all_hills, self.all_jumpers = load_data_from_json()
        self.all_jumpers.sort(key=lambda jumper: str(jumper))
        self.all_hills.sort(key=lambda hill: str(hill))

        # --- Główna struktura layoutu ---
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

        # --- Inicjalizacja zmiennych stanu symulacji ---
        self.selection_order = []
        self.competition_results = []
        self.current_jumper_index = 0
        self.current_round = 1
        self.selected_jumper, self.selected_hill, self.ani = None, None, None

        # --- Tworzenie wszystkich stron interfejsu ---
        self._create_main_menu()
        self._create_sim_type_menu()
        self._create_single_jump_page()
        self._create_competition_page()
        self._create_description_page()
        self._create_settings_page()

    def _create_main_menu(self):
        """Tworzy i konfiguruje stronę menu głównego."""
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
        """Tworzy stronę wyboru trybu symulacji (pojedynczy skok / zawody)."""
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
        """Tworzy stronę symulacji pojedynczego skoku."""
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
        """Tworzy stronę symulacji zawodów."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 20, 50, 50)
        layout.addLayout(self._create_top_bar("Zawody", self.SIM_TYPE_MENU_IDX))
        main_hbox = QHBoxLayout()
        options_vbox = QVBoxLayout()

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
        self.competition_status_label = QLabel("Tabela wyników:")
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
        results_vbox.addWidget(self.results_table)
        main_hbox.addLayout(results_vbox, 2)

        layout.addLayout(main_hbox)
        self.central_widget.addWidget(widget)

    def _create_description_page(self):
        """Tworzy stronę z opisem projektu."""
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
        """Tworzy stronę ustawień aplikacji (motyw, kontrast, głośność)."""
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
        """Tworzy reużywalny górny pasek z przyciskiem powrotu i tytułem strony."""
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
        """Tworzy reużywalny wiersz formularza (etykieta + widget)."""
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        row.addWidget(widget)
        return row

    def _on_jumper_item_changed(self, item):
        """Obsługuje zmianę zaznaczenia na liście zawodników do zawodów."""
        jumper = item.data(Qt.UserRole)
        if item.checkState() == Qt.Checked:
            if jumper not in self.selection_order:
                self.selection_order.append(jumper)
        else:
            if jumper in self.selection_order:
                self.selection_order.remove(jumper)

    def _sort_jumper_list(self, sort_text):
        """Sortuje listę zawodników w trybie zawodów wg wybranego kryterium."""
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

    def play_sound(self):
        """Odtwarza dźwięk kliknięcia, jeśli plik jest załadowany."""
        if hasattr(self, 'sound_loaded') and self.sound_loaded:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.setPosition(0)
            else:
                self.player.play()

    def adjust_brightness(self, hex_color, contrast):
        """Pomocnicza funkcja do zmiany jasności koloru w motywach."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        rgb = [min(max(int(c * contrast), 0), 255) for c in rgb]
        return f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def update_jumper(self):
        """Aktualizuje wybranego zawodnika w trybie pojedynczego skoku."""
        self.selected_jumper = self.all_jumpers[
            self.jumper_combo.currentIndex() - 1] if self.jumper_combo.currentIndex() > 0 else None

    def update_hill(self):
        """Aktualizuje wybraną skocznię w trybie pojedynczego skoku."""
        self.selected_hill = self.all_hills[
            self.hill_combo.currentIndex() - 1] if self.hill_combo.currentIndex() > 0 else None
        if self.selected_hill: self.gate_spin.setMaximum(self.selected_hill.gates)

    def update_competition_hill(self):
        """Aktualizuje wybraną skocznię w trybie zawodów."""
        hill = self.all_hills[
            self.comp_hill_combo.currentIndex() - 1] if self.comp_hill_combo.currentIndex() > 0 else None
        if hill: self.comp_gate_spin.setMaximum(hill.gates)

    def clear_results(self):
        """Czyści wyniki i resetuje pola w trybie pojedynczego skoku."""
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
        """Aktualizuje motyw aplikacji."""
        self.current_theme = "dark" if theme == "Ciemny" else "light"
        self.update_styles()

    def change_contrast(self):
        """Aktualizuje kontrast aplikacji."""
        self.contrast_level = self.contrast_slider.value() / 100.0
        self.update_styles()

    def change_volume(self):
        """Aktualizuje poziom głośności."""
        self.volume_level = self.volume_slider.value() / 100.0
        if hasattr(self, 'sound_loaded') and self.sound_loaded: self.audio_output.setVolume(self.volume_level)

    def update_styles(self):
        """Aplikuje zmiany stylów (motyw/kontrast) do całej aplikacji."""
        self.setStyleSheet(self.themes[self.current_theme](self.contrast_level))
        if hasattr(self, 'figure'):
            self.figure.set_facecolor(
                f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
            if hasattr(self, 'canvas'): self.canvas.draw()

    def _create_rounded_flag_pixmap(self, country_code, size=QSize(48, 33), radius=8):
        """Tworzy obrazek QPixmap flagi z zaokrąglonymi rogami."""
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
        """Tworzy ikonę QIcon flagi z zaokrąglonymi rogami."""
        pixmap = self._create_rounded_flag_pixmap(country_code, size=QSize(32, 22), radius=radius)
        if pixmap.isNull():
            return QIcon()
        return QIcon(pixmap)

    def run_competition(self):
        """Uruchamia logikę symulacji zawodów."""
        self.play_sound()
        hill_idx = self.comp_hill_combo.currentIndex()
        if hill_idx == 0 or not self.selection_order:
            self.competition_status_label.setText(
                "<font color='red'>BŁĄD: Wybierz skocznię i co najmniej jednego zawodnika!</font>")
            QTimer.singleShot(3000, lambda: self.competition_status_label.setText("Tabela wyników:"))
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
        """Przetwarza skok pojedynczego zawodnika w pętli QTimer."""
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
        """Odświeża tabelę wyników na podstawie aktualnych danych."""
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

    def run_simulation(self):
        """Uruchamia symulację i animację dla pojedynczego skoku."""
        self.play_sound()
        if not self.selected_jumper or not self.selected_hill:
            self.result_text.setText("BŁĄD: Musisz wybrać zawodnika i skocznię!")
            return
        gate = self.gate_spin.value()
        try:
            inrun_velocity = inrun_simulation(self.selected_hill, self.selected_jumper, gate_number=gate)
            distance = fly_simulation(self.selected_hill, self.selected_jumper, gate)
            self.result_text.setText(
                f"Prędkość na progu: {round(3.6 * inrun_velocity, 2)} km/h\nOdległość: {distance:.2f} m")

            self.positions = [(0, 0)]
            current_position_x, current_position_y = 0, 0
            initial_total_velocity = inrun_simulation(self.selected_hill, self.selected_jumper, gate_number=gate)
            initial_velocity_x = initial_total_velocity * math.cos(-self.selected_hill.alpha_rad)
            initial_velocity_y = initial_total_velocity * math.sin(-self.selected_hill.alpha_rad)
            velocity_takeoff = (self.selected_jumper.jump_force * 0.1) / self.selected_jumper.mass
            velocity_takeoff_x = velocity_takeoff * math.sin(self.selected_hill.alpha_rad)
            velocity_takeoff_y = velocity_takeoff * math.cos(self.selected_hill.alpha_rad)
            velocity_x_final = initial_velocity_x + velocity_takeoff_x
            velocity_y_final = initial_velocity_y + velocity_takeoff_y
            takeoff_angle_rad = math.atan2(velocity_y_final, velocity_x_final)
            v_perpendicular = (self.selected_jumper.jump_force * 0.1) / self.selected_jumper.mass
            current_velocity_x = initial_total_velocity * math.cos(takeoff_angle_rad)
            current_velocity_y = initial_total_velocity * math.sin(takeoff_angle_rad) + v_perpendicular
            time_step = 0.01
            max_hill_length = self.selected_hill.n + self.selected_hill.a_finish + 50
            max_height = 0
            while current_position_y > self.selected_hill.y_landing(
                    current_position_x) and current_position_x < max_hill_length:
                total_velocity = math.sqrt(current_velocity_x ** 2 + current_velocity_y ** 2)
                angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)
                force_g_y = -self.selected_jumper.mass * 9.81
                force_drag_magnitude = 0.5 * 1.225 * self.selected_jumper.flight_drag_coefficient * self.selected_jumper.flight_frontal_area * total_velocity ** 2
                force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
                force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)
                force_lift_magnitude = 0.5 * 1.225 * self.selected_jumper.flight_lift_coefficient * self.selected_jumper.flight_frontal_area * total_velocity ** 2
                force_lift_x = -force_lift_magnitude * math.sin(angle_of_flight_rad)
                force_lift_y = force_lift_magnitude * math.cos(angle_of_flight_rad)
                acceleration_x = (force_drag_x + force_lift_x) / self.selected_jumper.mass
                acceleration_y = (force_g_y + force_drag_y + force_lift_y) / self.selected_jumper.mass
                current_velocity_x += acceleration_x * time_step
                current_velocity_y += acceleration_y * time_step
                current_position_x += current_velocity_x * time_step
                current_position_y += current_velocity_y * time_step
                max_height = max(max_height, current_position_y)
                if current_position_x >= max_hill_length:
                    current_position_x = max_hill_length
                    current_position_y = self.selected_hill.y_landing(current_position_x)
                    self.positions.append((current_position_x, current_position_y))
                    self.result_text.append("\nUWAGA: Skok przekroczył maksymalną długość skoczni!")
                    break
                self.positions.append((current_position_x, current_position_y))
            self.x_landing = np.linspace(0, min(current_position_x + 50, max_hill_length), 100)
            self.y_landing = [self.selected_hill.y_landing(x_val) for x_val in self.x_landing]

            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_facecolor(
                f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
            self.figure.patch.set_facecolor(
                f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
            ax.axis('off')
            ax.set_aspect('auto')
            inrun_length_to_show = 15.0
            x_inrun = np.linspace(-inrun_length_to_show, 0, 50)
            y_inrun = np.tan(-self.selected_hill.alpha_rad) * x_inrun
            ax.plot(x_inrun, y_inrun, color='#00aaff', linewidth=3)
            max_y_inrun = y_inrun[0] if len(y_inrun) > 0 else 0
            ax.set_xlim(-inrun_length_to_show - 5, max_hill_length + 10)
            ax.set_ylim(min(min(self.y_landing), 0) - 5, max(max_height * 1.5, max_y_inrun) + 5)

            jumper_point, = ax.plot([], [], 'ro', markersize=8)
            trail_line, = ax.plot([], [], color='#4da8ff', linewidth=2, alpha=0.5)
            landing_line, = ax.plot([], [], color='#00aaff', linewidth=3)
            plot_elements = [jumper_point, trail_line, landing_line]

            def init():
                for element in plot_elements:
                    if hasattr(element, 'set_data'):
                        element.set_data([], [])
                return plot_elements

            def update(frame):
                if frame >= max(len(self.positions), len(self.x_landing)):
                    if self.ani: self.ani.event_source.stop()
                    self.start_zoom_animation(ax, plot_elements)
                    return plot_elements
                if frame < len(self.positions):
                    x, y = self.positions[frame]
                    jumper_point.set_data([x], [y])
                    trail_line.set_data([p[0] for p in self.positions[:frame + 1]],
                                        [p[1] for p in self.positions[:frame + 1]])
                if frame < len(self.x_landing):
                    landing_line.set_data(self.x_landing[:frame], self.y_landing[:frame])
                return plot_elements

            self.ani = animation.FuncAnimation(self.figure, update, init_func=init,
                                               frames=max(len(self.positions), len(self.x_landing)), interval=5,
                                               blit=False, repeat=False)
            self.canvas.draw()
        except ValueError as e:
            self.result_text.setText(f"BŁĄD: {str(e)}")

    def start_zoom_animation(self, ax, plot_elements):
        """Uruchamia animację przybliżenia na miejsce lądowania."""
        if not self.positions: return
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