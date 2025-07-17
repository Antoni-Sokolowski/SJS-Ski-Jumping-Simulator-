import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox, \
    QPushButton, QTextEdit, QLabel, QStackedWidget, QSlider
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
import math
from PIL import Image, ImageDraw
import scipy.io.wavfile as wavfile
from src.simulation import load_data_from_json, inrun_simulation, fly_simulation
from src.hill import Hill


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ski Jumping Simulator")
        self.showMaximized()

        # Stan motywu, kontrastu i głośności
        self.current_theme = "dark"
        self.contrast_level = 1.0
        self.volume_level = 0.3
        self.themes = {
            "dark": lambda contrast: f"""
                QMainWindow, QWidget {{
                    background-color: #{self.adjust_brightness('1a1a1a', contrast)};
                }}
                QLabel {{
                    color: #{self.adjust_brightness('ffffff', contrast)};
                    font-size: 16px;
                    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
                }}
                QLabel.headerLabel {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #0078d4;
                }}
                QComboBox, QSpinBox, QTextEdit, QSlider::groove {{
                    background-color: #{self.adjust_brightness('2a2a2a', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                    border: none;
                    padding: 12px;
                    border-radius: 5px;
                    font-size: 16px;
                }}
                QComboBox QAbstractItemView::item {{
                    color: #{self.adjust_brightness('ffffff', contrast)};
                    background-color: #{self.adjust_brightness('2a2a2a', contrast)};
                }}
                QComboBox QAbstractItemView::item:selected {{
                    background-color: #{self.adjust_brightness('005ea6', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                }}
                QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {{
                    border: none;
                }}
                QSlider::handle {{
                    background: #{self.adjust_brightness('0078d4', contrast)};
                    border: none;
                    width: 18px;
                    margin: -4px 0;
                    border-radius: 9px;
                }}
                QPushButton {{
                    background-color: #{self.adjust_brightness('0078d4', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                    border: none;
                    padding: 15px;
                    border-radius: 5px;
                    font-size: 20px;
                    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
                }}
                QPushButton:hover {{
                    background-color: #{self.adjust_brightness('005ea6', contrast)};
                }}
                QPushButton:pressed {{
                    background-color: #{self.adjust_brightness('004d87', contrast)};
                }}
                QLabel#authorLabel {{
                    color: #{self.adjust_brightness('b0b0b0', contrast)};
                    font-size: 14px;
                    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
                }}
                QPushButton#backArrowButton {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #{self.adjust_brightness('b0b0b0', contrast)};
                    background-color: transparent;
                    border: none;
                    padding: 0px;
                    border-radius: 20px;
                }}
                QPushButton#backArrowButton:hover {{
                    background-color: #{self.adjust_brightness('2f2f2f', contrast)};
                }}
                QPushButton#backArrowButton:pressed {{
                    background-color: #{self.adjust_brightness('3a3a3a', contrast)};
                }}
            """,
            "light": lambda contrast: f"""
                QMainWindow, QWidget {{
                    background-color: #{self.adjust_brightness('f0f0f0', contrast)};
                }}
                QLabel {{
                    color: #{self.adjust_brightness('1a1a1a', contrast)};
                    font-size: 16px;
                    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
                }}
                 QLabel.headerLabel {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #0078d4;
                }}
                QComboBox, QSpinBox, QTextEdit, QSlider::groove {{
                    background-color: #{self.adjust_brightness('ffffff', contrast)};
                    color: #{self.adjust_brightness('1a1a1a', contrast)};
                    border: none;
                    padding: 12px;
                    border-radius: 5px;
                    font-size: 16px;
                }}
                QComboBox QAbstractItemView::item {{
                    color: #{self.adjust_brightness('1a1a1a', contrast)};
                    background-color: #{self.adjust_brightness('ffffff', contrast)};
                }}
                QComboBox QAbstractItemView::item:selected {{
                    background-color: #{self.adjust_brightness('005ea6', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                }}
                QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {{
                    border: none;
                }}
                QSlider::handle {{
                    background: #{self.adjust_brightness('0078d4', contrast)};
                    border: none;
                    width: 18px;
                    margin: -4px 0;
                    border-radius: 9px;
                }}
                QPushButton {{
                    background-color: #{self.adjust_brightness('0078d4', contrast)};
                    color: #{self.adjust_brightness('ffffff', contrast)};
                    border: none;
                    padding: 15px;
                    border-radius: 5px;
                    font-size: 20px;
                    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
                }}
                QPushButton:hover {{
                    background-color: #{self.adjust_brightness('005ea6', contrast)};
                }}
                QPushButton:pressed {{
                    background-color: #{self.adjust_brightness('004d87', contrast)};
                }}
                QLabel#authorLabel {{
                    color: #{self.adjust_brightness('404040', contrast)};
                    font-size: 14px;
                    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
                }}
                QPushButton#backArrowButton {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #{self.adjust_brightness('404040', contrast)};
                    background-color: transparent;
                    border: none;
                    padding: 0px;
                    border-radius: 20px;
                }}
                QPushButton#backArrowButton:hover {{
                    background-color: #{self.adjust_brightness('e0e0e0', contrast)};
                }}
                QPushButton#backArrowButton:pressed {{
                    background-color: #{self.adjust_brightness('d0d0d0', contrast)};
                }}
            """
        }
        self.setStyleSheet(self.themes[self.current_theme](self.contrast_level))

        # Efekt dźwiękowy
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        sound_file = os.path.abspath("assets/click.wav")
        if not os.path.exists(sound_file):
            print(f"BŁĄD: Plik '{sound_file}' nie znaleziony!")
            self.result_text = QTextEdit()
            self.result_text.setText(
                "BŁĄD: Plik 'click.wav' nie znaleziony! Umieść poprawny plik WAV w folderze projektu.")
            self.sound_loaded = False
        else:
            try:
                sample_rate, _ = wavfile.read(sound_file)
                if sample_rate not in [44100, 48000]:
                    print(f"BŁĄD: Plik '{sound_file}' ma nieodpowiednią częstotliwość próbkowania ({sample_rate} Hz).")
                    self.result_text = QTextEdit()
                    self.result_text.setText(
                        "BŁĄD: Plik 'click.wav' ma nieodpowiedni format. Użyj WAV 44100/48000 Hz, 16-bit PCM.")
                    self.sound_loaded = False
                else:
                    self.player.setSource(QUrl.fromLocalFile(sound_file))
                    self.audio_output.setVolume(self.volume_level)
                    self.sound_loaded = True
            except Exception as e:
                print(f"BŁĄD: Nie można odczytać pliku '{sound_file}': {str(e)}")
                self.result_text = QTextEdit()
                self.result_text.setText(f"BŁĄD: Nie można odczytać 'click.wav': {str(e)}.")
                self.sound_loaded = False

        # Główny widżet
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        # === Menu główne ===
        main_menu_widget = QWidget()
        main_menu_layout = QVBoxLayout(main_menu_widget)
        main_menu_layout.setAlignment(Qt.AlignCenter)
        main_menu_layout.setSpacing(50)
        main_menu_layout.setContentsMargins(50, 50, 50, 50)

        title_label = QLabel("Ski Jumping Simulator")
        title_label.setProperty("class", "headerLabel")
        main_menu_layout.addWidget(title_label)

        simulation_button = QPushButton("Symulacja")
        simulation_button.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(1)])
        main_menu_layout.addWidget(simulation_button)

        description_button = QPushButton("Opis Projektu")
        description_button.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(2)])
        main_menu_layout.addWidget(description_button)

        settings_button = QPushButton("Ustawienia")
        settings_button.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(3)])
        main_menu_layout.addWidget(settings_button)

        exit_button = QPushButton("Wyjdź")
        exit_button.clicked.connect(lambda: [self.play_sound(), self.close()])
        main_menu_layout.addWidget(exit_button)

        author_label = QLabel("Antoni Sokołowski")
        author_label.setObjectName("authorLabel")
        author_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        main_menu_layout.addWidget(author_label)
        main_menu_layout.addStretch()

        # === Ekran symulacji ===
        simulation_widget = QWidget()
        simulation_layout = QVBoxLayout(simulation_widget)
        simulation_layout.setSpacing(20)
        simulation_layout.setContentsMargins(50, 20, 50, 50)

        simulation_layout.addLayout(self._create_top_bar("Symulacja skoku"))

        jumper_layout = QHBoxLayout()
        jumper_label = QLabel("Zawodnik:")
        self.jumper_combo = QComboBox()
        self.jumper_combo.addItem("Wybierz zawodnika")
        self.all_hills, self.all_jumpers = load_data_from_json()
        for jumper in self.all_jumpers:
            flag_icon = self.create_rounded_flag_icon(jumper.nationality)
            self.jumper_combo.addItem(flag_icon, str(jumper))
        self.jumper_combo.currentIndexChanged.connect(self.update_jumper)
        jumper_layout.addWidget(jumper_label)
        jumper_layout.addWidget(self.jumper_combo)
        simulation_layout.addLayout(jumper_layout)

        hill_layout = QHBoxLayout()
        hill_label = QLabel("Skocznia:")
        self.hill_combo = QComboBox()
        self.hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            flag_icon = self.create_rounded_flag_icon(hill.country)
            self.hill_combo.addItem(flag_icon, str(hill))
        self.hill_combo.currentIndexChanged.connect(self.update_hill)
        hill_layout.addWidget(hill_label)
        hill_layout.addWidget(self.hill_combo)
        simulation_layout.addLayout(hill_layout)

        gate_layout = QHBoxLayout()
        gate_label = QLabel("Belka startowa:")
        self.gate_spin = QSpinBox()
        self.gate_spin.setMinimum(1)
        self.gate_spin.setMaximum(1)
        gate_layout.addWidget(gate_label)
        gate_layout.addWidget(self.gate_spin)
        simulation_layout.addLayout(gate_layout)

        button_layout = QHBoxLayout()
        self.simulate_button = QPushButton("Uruchom symulację")
        self.simulate_button.clicked.connect(lambda: [self.play_sound(), self.run_simulation()])
        self.clear_button = QPushButton("Wyczyść")
        self.clear_button.clicked.connect(lambda: [self.play_sound(), self.clear_results()])
        button_layout.addWidget(self.simulate_button)
        button_layout.addWidget(self.clear_button)
        simulation_layout.addLayout(button_layout)

        self.result_text = QTextEdit() if not hasattr(self, 'result_text') else self.result_text
        self.result_text.setReadOnly(True)
        self.result_text.setFixedHeight(80)
        simulation_layout.addWidget(self.result_text)

        self.figure = Figure(
            facecolor=f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
        self.canvas = FigureCanvas(self.figure)
        simulation_layout.addWidget(self.canvas)

        sim_author_label = QLabel("Antoni Sokołowski")
        sim_author_label.setObjectName("authorLabel")
        sim_author_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        simulation_layout.addWidget(sim_author_label)

        # === Ekran opisu ===
        description_widget = QWidget()
        description_layout = QVBoxLayout(description_widget)
        description_layout.setSpacing(40)
        description_layout.setContentsMargins(50, 20, 50, 50)

        description_layout.addLayout(self._create_top_bar("Opis Projektu"))

        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setText("Tutaj pojawi się opis projektu.")
        description_layout.addWidget(self.description_text)
        description_layout.addStretch()

        desc_author_label = QLabel("Antoni Sokołowski")
        desc_author_label.setObjectName("authorLabel")
        desc_author_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        description_layout.addWidget(desc_author_label)

        # === Ekran ustawień ===
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setSpacing(40)
        settings_layout.setContentsMargins(50, 20, 50, 50)

        settings_layout.addLayout(self._create_top_bar("Ustawienia"))

        theme_layout = QHBoxLayout()
        theme_label = QLabel("Motyw:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Ciemny", "Jasny"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        settings_layout.addLayout(theme_layout)

        contrast_layout = QHBoxLayout()
        contrast_label = QLabel("Kontrast:")
        self.contrast_slider = QSlider(Qt.Horizontal)
        self.contrast_slider.setMinimum(50)
        self.contrast_slider.setMaximum(150)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.change_contrast)
        contrast_layout.addWidget(contrast_label)
        contrast_layout.addWidget(self.contrast_slider)
        settings_layout.addLayout(contrast_layout)

        volume_layout = QHBoxLayout()
        volume_label = QLabel("Głośność:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(int(self.volume_level * 100))
        self.volume_slider.valueChanged.connect(self.change_volume)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        settings_layout.addLayout(volume_layout)
        settings_layout.addStretch()

        settings_author_label = QLabel("Antoni Sokołowski")
        settings_author_label.setObjectName("authorLabel")
        settings_author_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        settings_layout.addWidget(settings_author_label)

        # Dodawanie widżetów do układu warstwowego
        self.central_widget.addWidget(main_menu_widget)
        self.central_widget.addWidget(simulation_widget)
        self.central_widget.addWidget(description_widget)
        self.central_widget.addWidget(settings_widget)

        # Dane animacji
        self.positions = []
        self.x_landing = []
        self.y_landing = []
        self.selected_jumper = None
        self.selected_hill = None
        self.ani = None

    def _create_top_bar(self, title_text):
        """Tworzy górny pasek nawigacyjny z przyciskiem powrotu i tytułem."""
        top_bar_layout = QHBoxLayout()

        back_arrow_button = QPushButton("←")
        back_arrow_button.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(0)])
        back_arrow_button.setFixedSize(40, 40)
        back_arrow_button.setObjectName("backArrowButton")
        top_bar_layout.addWidget(back_arrow_button, 0, Qt.AlignLeft)

        header_label = QLabel(title_text)
        header_label.setProperty("class", "headerLabel")
        header_label.setAlignment(Qt.AlignCenter)
        top_bar_layout.addWidget(header_label)

        phantom_widget = QWidget()
        phantom_widget.setFixedSize(40, 40)
        top_bar_layout.addWidget(phantom_widget, 0, Qt.AlignRight)

        return top_bar_layout

    def play_sound(self):
        if hasattr(self, 'sound_loaded') and self.sound_loaded:
            self.player.play()

    def adjust_brightness(self, hex_color, contrast):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        rgb = [min(max(int(c * contrast), 0), 255) for c in rgb]
        return f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def update_jumper(self):
        index = self.jumper_combo.currentIndex()
        self.selected_jumper = self.all_jumpers[index - 1] if index > 0 else None

    def update_hill(self):
        index = self.hill_combo.currentIndex()
        self.selected_hill = self.all_hills[index - 1] if index > 0 else None
        if self.selected_hill:
            self.gate_spin.setMaximum(self.selected_hill.gates)
        else:
            self.gate_spin.setMaximum(1)

    def clear_results(self):
        self.jumper_combo.setCurrentIndex(0)
        self.hill_combo.setCurrentIndex(0)
        self.gate_spin.setValue(1)
        self.result_text.clear()
        self.figure.clear()
        self.canvas.draw()
        self.positions = []
        self.x_landing = []
        self.y_landing = []
        if self.ani:
            self.ani.event_source.stop()
            self.ani = None
        if not hasattr(self, 'sound_loaded') or not self.sound_loaded:
            self.result_text.setText("BŁĄD: Plik 'click.wav' nie znaleziony lub nieprawidłowy.")

    def change_theme(self, theme):
        self.current_theme = "dark" if theme == "Ciemny" else "light"
        self.update_styles()

    def change_contrast(self):
        self.contrast_level = self.contrast_slider.value() / 100.0
        self.update_styles()

    def change_volume(self):
        self.volume_level = self.volume_slider.value() / 100.0
        if hasattr(self, 'sound_loaded') and self.sound_loaded:
            self.audio_output.setVolume(self.volume_level)

    def update_styles(self):
        self.setStyleSheet(self.themes[self.current_theme](self.contrast_level))
        self.figure.set_facecolor(
            f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
        self.canvas.draw()

    def create_rounded_flag_icon(self, country_code, radius=6):
        if not country_code:
            return QIcon()
        flag_path = os.path.join("assets", "flags", f"{country_code}.png")
        if not os.path.exists(flag_path):
            return QIcon()
        try:
            final_size = (32, 22)
            with Image.open(flag_path) as img:
                img_resized = img.resize(final_size, Image.Resampling.LANCZOS).convert("RGBA")
            mask = Image.new('L', img_resized.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle(((0, 0), img_resized.size), radius=radius, fill=255)
            img_resized.putalpha(mask)
            data = img_resized.tobytes("raw", "RGBA")
            qimage = QImage(data, img_resized.size[0], img_resized.size[1], QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimage)
            return QIcon(pixmap)
        except Exception as e:
            print(f"Error creating flag icon for {country_code}: {e}")
            return QIcon()

    def run_simulation(self):
        if not self.selected_jumper or not self.selected_hill:
            self.result_text.setText("BŁĄD: Musisz wybrać zawodnika i skocznię!")
            return
        gate = self.gate_spin.value()
        try:
            inrun_velocity = inrun_simulation(self.selected_hill, self.selected_jumper, gate_number=gate)
            distance = fly_simulation(self.selected_hill, self.selected_jumper, gate)
            self.result_text.setText(
                f"Prędkość na progu: {round(3.6 * inrun_velocity, 2)} km/h\n"
                f"Odległość: {distance:.2f} m"
            )
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
            y_inrun = np.tan(self.selected_hill.alpha_rad) * x_inrun
            ax.plot(x_inrun, y_inrun, color='#00aaff', linewidth=3)
            max_y_inrun = y_inrun[0] if len(y_inrun) > 0 else 0
            ax.set_xlim(-inrun_length_to_show - 5, max_hill_length + 10)
            ax.set_ylim(min(min(self.y_landing), 0) - 5, max(max_height * 1.5, max_y_inrun) + 5)
            skier_icon = None
            if os.path.exists("skier.png"):
                try:
                    skier_img = Image.open("skier.png")
                    skier_img = skier_img.resize((20, 20))
                    skier_icon = OffsetImage(skier_img, zoom=1)
                except Exception as e:
                    self.result_text.append(f"\nBŁĄD: Nie udało się załadować 'skier.png': {str(e)}.")
            else:
                self.result_text.append("\nBŁĄD: Plik 'skier.png' nie znaleziony! Używam kropki.")
            if skier_icon:
                ab = AnnotationBbox(skier_icon, (0, 0), frameon=False)
                ax.add_artist(ab)
                plot_elements = [ab]
            else:
                jumper_point, = ax.plot([], [], 'ro', markersize=8)
                plot_elements = [jumper_point]
            trail_line, = ax.plot([], [], color='#4da8ff', linewidth=2, alpha=0.5)
            landing_line, = ax.plot([], [], color='#00aaff', linewidth=3)
            plot_elements.extend([trail_line, landing_line])

            def init():
                return plot_elements

            def update(frame):
                if frame >= max(len(self.positions), len(self.x_landing)):
                    self.ani.event_source.stop()
                    self.start_zoom_animation(ax, plot_elements)
                    return plot_elements
                if frame < len(self.positions):
                    x, y = self.positions[frame]
                    if skier_icon:
                        ab.xy = (x, y)
                    else:
                        jumper_point.set_data([x], [y])
                    trail_x = [p[0] for p in self.positions[:frame + 1]]
                    trail_y = [p[1] for p in self.positions[:frame + 1]]
                    trail_line.set_data(trail_x, trail_y)
                if frame < len(self.x_landing):
                    landing_line.set_data(self.x_landing[:frame], self.y_landing[:frame])
                return plot_elements

            try:
                self.ani = animation.FuncAnimation(self.figure, update, init_func=init,
                                                   frames=max(len(self.positions), len(self.x_landing)), interval=5,
                                                   blit=False, repeat=False)
                self.canvas.draw()
            except Exception as e:
                self.result_text.setText(f"BŁĄD: Problem z animacją: {str(e)}")
        except ValueError as e:
            self.result_text.setText(f"BŁĄD: {str(e)}")

    def start_zoom_animation(self, ax, plot_elements):
        if not self.positions: return
        final_x, final_y = self.positions[-1]
        zoom_frames = 10
        initial_xlim = ax.get_xlim()
        initial_ylim = ax.get_ylim()
        final_xlim = (final_x - 10, final_x + 10)
        final_ylim = (final_y - 10, final_y + 10)

        def zoom_update(frame):
            if frame >= zoom_frames:
                ax.set_xlim(final_xlim)
                ax.set_ylim(final_ylim)
                self.canvas.draw_idle()
                if hasattr(self, 'zoom_ani'):
                    self.zoom_ani.event_source.stop()
                return plot_elements
            t = frame / zoom_frames
            new_xlim = (initial_xlim[0] + t * (final_xlim[0] - initial_xlim[0]),
                        initial_xlim[1] + t * (final_xlim[1] - initial_xlim[1]))
            new_ylim = (initial_ylim[0] + t * (final_ylim[0] - initial_ylim[0]),
                        initial_ylim[1] + t * (final_ylim[1] - initial_ylim[1]))
            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)
            self.canvas.draw_idle()
            return plot_elements

        self.zoom_ani = animation.FuncAnimation(self.figure, zoom_update, frames=zoom_frames + 1, interval=50,
                                                blit=False, repeat=False)
        self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())