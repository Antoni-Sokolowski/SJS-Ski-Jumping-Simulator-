import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox, QPushButton, QTextEdit, QLabel, QStackedWidget, QSlider
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
import math
from PIL import Image
import scipy.io.wavfile as wavfile
from src.simulation import load_data_from_json, inrun_simulation, fly_simulation
from src.hill import Hill

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ski Jumping Simulator")
        self.showMaximized()  # Open in full screen

        # Theme, contrast, and volume state
        self.current_theme = "dark"
        self.contrast_level = 1.0  # Default contrast
        self.volume_level = 0.3  # Default volume (30%)
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
            """
        }
        self.setStyleSheet(self.themes[self.current_theme](self.contrast_level))

        # Sound effect with QMediaPlayer
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        sound_file = os.path.abspath("assets/click.wav")
        if not os.path.exists(sound_file):
            print(f"BŁĄD: Plik '{sound_file}' nie znaleziony!")
            self.result_text = QTextEdit()
            self.result_text.setText("BŁĄD: Plik 'click.wav' nie znaleziony! Umieść poprawny plik WAV w folderze projektu.")
            self.sound_loaded = False
        else:
            try:
                sample_rate, _ = wavfile.read(sound_file)
                if sample_rate not in [44100, 48000]:
                    print(f"BŁĄD: Plik '{sound_file}' ma nieodpowiednią częstotliwość próbkowania ({sample_rate} Hz). Wymagane: 44100 lub 48000 Hz.")
                    self.result_text = QTextEdit()
                    self.result_text.setText("BŁĄD: Plik 'click.wav' ma nieodpowiedni format. Użyj WAV 44100/48000 Hz, 16-bit PCM.")
                    self.sound_loaded = False
                else:
                    self.player.setSource(QUrl.fromLocalFile(sound_file))
                    self.audio_output.setVolume(self.volume_level)
                    self.sound_loaded = True
                    print(f"Dźwięk załadowany: {self.sound_loaded}")
            except Exception as e:
                print(f"BŁĄD: Nie można odczytać pliku '{sound_file}': {str(e)}")
                self.result_text = QTextEdit()
                self.result_text.setText(f"BŁĄD: Nie można odczytać 'click.wav': {str(e)}. Umieść poprawny plik WAV w folderze projektu.")
                self.sound_loaded = False

        # Central widget with stacked layout
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        # Main menu
        main_menu_widget = QWidget()
        main_menu_layout = QVBoxLayout(main_menu_widget)
        main_menu_layout.setAlignment(Qt.AlignCenter)
        main_menu_layout.setSpacing(50)
        main_menu_layout.setContentsMargins(50, 50, 50, 50)

        title_label = QLabel("Ski Jumping Simulator")
        title_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {'#0078d4'};")
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

        # Simulation screen
        simulation_widget = QWidget()
        simulation_layout = QVBoxLayout(simulation_widget)
        simulation_layout.setSpacing(40)
        simulation_layout.setContentsMargins(50, 50, 50, 50)

        sim_header_label = QLabel("Symulacja skoku")
        sim_header_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {'#0078d4'};")
        sim_header_label.setAlignment(Qt.AlignCenter)
        simulation_layout.addWidget(sim_header_label)

        # Jumper selection
        jumper_layout = QHBoxLayout()
        jumper_label = QLabel("Zawodnik:")
        self.jumper_combo = QComboBox()
        self.jumper_combo.addItem("Wybierz zawodnika")
        self.all_hills, self.all_jumpers = load_data_from_json()
        for jumper in self.all_jumpers:
            self.jumper_combo.addItem(str(jumper))
        self.jumper_combo.currentIndexChanged.connect(self.update_jumper)
        jumper_layout.addWidget(jumper_label)
        jumper_layout.addWidget(self.jumper_combo)
        simulation_layout.addLayout(jumper_layout)

        # Hill selection
        hill_layout = QHBoxLayout()
        hill_label = QLabel("Skocznia:")
        self.hill_combo = QComboBox()
        self.hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.hill_combo.addItem(str(hill))
        self.hill_combo.currentIndexChanged.connect(self.update_hill)
        hill_layout.addWidget(hill_label)
        hill_layout.addWidget(self.hill_combo)
        simulation_layout.addLayout(hill_layout)

        # Gate selection
        gate_layout = QHBoxLayout()
        gate_label = QLabel("Belka startowa:")
        self.gate_spin = QSpinBox()
        self.gate_spin.setMinimum(1)
        self.gate_spin.setMaximum(1)
        gate_layout.addWidget(gate_label)
        gate_layout.addWidget(self.gate_spin)
        simulation_layout.addLayout(gate_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.simulate_button = QPushButton("Uruchom symulację")
        self.simulate_button.clicked.connect(lambda: [self.play_sound(), self.run_simulation()])
        self.clear_button = QPushButton("Wyczyść")
        self.clear_button.clicked.connect(lambda: [self.play_sound(), self.clear_results()])
        button_layout.addWidget(self.simulate_button)
        button_layout.addWidget(self.clear_button)
        simulation_layout.addLayout(button_layout)

        back_button = QPushButton("Powrót")
        back_button.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(0)])
        simulation_layout.addWidget(back_button)

        # Result display
        self.result_text = QTextEdit() if not hasattr(self, 'result_text') else self.result_text
        self.result_text.setReadOnly(True)
        self.result_text.setFixedHeight(80)
        simulation_layout.addWidget(self.result_text)

        # Matplotlib canvas
        self.figure = Figure(facecolor=f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
        self.canvas = FigureCanvas(self.figure)
        simulation_layout.addWidget(self.canvas)

        sim_author_label = QLabel("Antoni Sokołowski")
        sim_author_label.setObjectName("authorLabel")
        sim_author_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        simulation_layout.addWidget(sim_author_label)
        simulation_layout.addStretch()

        # Description screen
        description_widget = QWidget()
        description_layout = QVBoxLayout(description_widget)
        description_layout.setSpacing(40)
        description_layout.setContentsMargins(50, 50, 50, 50)

        desc_header_label = QLabel("Opis Projektu")
        desc_header_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {'#0078d4'};")
        desc_header_label.setAlignment(Qt.AlignCenter)
        description_layout.addWidget(desc_header_label)

        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setText("Tutaj pojawi się opis projektu.")
        description_layout.addWidget(self.description_text)

        desc_back_button = QPushButton("Powrót")
        desc_back_button.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(0)])
        description_layout.addWidget(desc_back_button)

        desc_author_label = QLabel("Antoni Sokołowski")
        desc_author_label.setObjectName("authorLabel")
        desc_author_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        description_layout.addWidget(desc_author_label)
        description_layout.addStretch()

        # Settings screen
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setAlignment(Qt.AlignCenter)
        settings_layout.setSpacing(40)
        settings_layout.setContentsMargins(50, 50, 50, 50)

        settings_header = QLabel("Ustawienia")
        settings_header.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {'#0078d4'};")
        settings_layout.addWidget(settings_header)

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
        self.contrast_slider.setMinimum(50)  # 0.5x brightness
        self.contrast_slider.setMaximum(150)  # 1.5x brightness
        self.contrast_slider.setValue(100)  # Default 1.0
        self.contrast_slider.valueChanged.connect(self.change_contrast)
        contrast_layout.addWidget(contrast_label)
        contrast_layout.addWidget(self.contrast_slider)
        settings_layout.addLayout(contrast_layout)

        volume_layout = QHBoxLayout()
        volume_label = QLabel("Głośność:")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)  # 0% volume
        self.volume_slider.setMaximum(100)  # 100% volume
        self.volume_slider.setValue(int(self.volume_level * 100))  # Default 30%
        self.volume_slider.valueChanged.connect(self.change_volume)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        settings_layout.addLayout(volume_layout)

        settings_back_button = QPushButton("Powrót")
        settings_back_button.clicked.connect(lambda: [self.play_sound(), self.central_widget.setCurrentIndex(0)])
        settings_layout.addWidget(settings_back_button)

        settings_author_label = QLabel("Antoni Sokołowski")
        settings_author_label.setObjectName("authorLabel")
        settings_author_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        settings_layout.addWidget(settings_author_label)
        settings_layout.addStretch()

        # Add widgets to stacked layout
        self.central_widget.addWidget(main_menu_widget)
        self.central_widget.addWidget(simulation_widget)
        self.central_widget.addWidget(description_widget)
        self.central_widget.addWidget(settings_widget)

        # Animation data
        self.positions = []
        self.x_landing = []
        self.y_landing = []
        self.selected_jumper = None
        self.selected_hill = None
        self.ani = None  # Store animation to prevent garbage collection

    def play_sound(self):
        if hasattr(self, 'sound_loaded') and self.sound_loaded:
            self.player.play()

    def adjust_brightness(self, hex_color, contrast):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
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
            self.result_text.setText("BŁĄD: Plik 'click.wav' nie znaleziony lub nieprawidłowy. Użyj WAV 44100/48000 Hz, 16-bit PCM.")

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
        title_color = "#0078d4"
        for i in range(self.central_widget.count()):
            widget = self.central_widget.widget(i)
            for label in widget.findChildren(QLabel):
                if "Ski Jumping Simulator" in label.text() or "Symulacja skoku" in label.text() or "Ustawienia" in label.text() or "Opis Projektu" in label.text():
                    label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {title_color};")
        self.figure.set_facecolor(f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
        self.canvas.draw()

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

            # Calculate trajectory for animation
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
            while current_position_y > self.selected_hill.y_landing(current_position_x) and current_position_x < max_hill_length:
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

            # Animate minimalist ski jump with fixed view and adjusted scale
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.set_facecolor(f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
            self.figure.patch.set_facecolor(f"#{self.adjust_brightness('1a1a1a' if self.current_theme == 'dark' else 'f0f0f0', self.contrast_level)}")
            ax.axis('off')
            ax.set_xlim(0, max_hill_length + 10)
            ax.set_ylim(min(min(self.y_landing), 0) - 5, max_height * 1.5 + 5)
            ax.set_aspect('auto')

            # Load skier icon
            skier_icon = None
            if os.path.exists("skier.png"):
                try:
                    skier_img = Image.open("skier.png")
                    skier_img = skier_img.resize((20, 20))
                    skier_icon = OffsetImage(skier_img, zoom=1)
                except Exception as e:
                    self.result_text.append(f"\nBŁĄD: Nie udało się załadować 'skier.png': {str(e)}. Używam kropki.")
            else:
                self.result_text.append("\nBŁĄD: Plik 'skier.png' nie znaleziony! Używam kropki.")

            # Initialize plot elements
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
                    trail_x = [p[0] for p in self.positions[:frame+1]]
                    trail_y = [p[1] for p in self.positions[:frame+1]]
                    trail_line.set_data(trail_x, trail_y)
                if frame < len(self.x_landing):
                    landing_line.set_data(self.x_landing[:frame], self.y_landing[:frame])
                return plot_elements

            try:
                self.ani = animation.FuncAnimation(self.figure, update, init_func=init, frames=max(len(self.positions), len(self.x_landing)), interval=5, blit=False, repeat=False)
                self.canvas.draw()
            except Exception as e:
                self.result_text.setText(f"BŁĄD: Problem z animacją: {str(e)}")
                print(f"BŁĄD: Problem z animacją: {str(e)}")

        except ValueError as e:
            self.result_text.setText(f"BŁĄD: {str(e)}")

    def start_zoom_animation(self, ax, plot_elements):
        final_x, final_y = self.positions[-1]
        zoom_frames = 10
        initial_xlim = (0, self.selected_hill.n + self.selected_hill.a_finish + 10)
        initial_ylim = (min(min(self.y_landing), 0) - 5, Hill.Zu * 1.5 + 5)
        final_xlim = (final_x - 10, final_x + 10)
        final_ylim = (final_y - 10, final_y + 10)

        def zoom_update(frame):
            if frame >= zoom_frames:
                ax.set_xlim(final_xlim)
                ax.set_ylim(final_ylim)
                return plot_elements
            t = frame / zoom_frames
            new_xlim = (initial_xlim[0] + t * (final_xlim[0] - initial_xlim[0]), initial_xlim[1] + t * (final_xlim[1] - initial_xlim[1]))
            new_ylim = (initial_ylim[0] + t * (final_ylim[0] - initial_ylim[0]), initial_ylim[1] + t * (final_ylim[1] - initial_ylim[1]))
            ax.set_xlim(new_xlim)
            ax.set_ylim(new_ylim)
            return plot_elements

        zoom_ani = animation.FuncAnimation(self.figure, zoom_update, frames=zoom_frames + 1, interval=50, blit=False, repeat=False)
        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())