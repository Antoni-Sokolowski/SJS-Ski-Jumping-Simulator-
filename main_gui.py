import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox, QPushButton, QTextEdit, QLabel, QStackedWidget
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import math
from physics.simulation import load_data_from_json, inrun_simulation, fly_simulation

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ski Jumping Simulator")
        self.setGeometry(100, 100, 1000, 750)

        # Theme state
        self.current_theme = "dark"
        self.themes = {
            "dark": """
                QMainWindow, QWidget {
                    background-color: #1e1e2e;
                }
                QLabel {
                    color: #cdd6f4;
                    font-size: 16px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QComboBox, QSpinBox, QTextEdit {
                    background-color: #313244;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    padding: 8px;
                    border-radius: 8px;
                    font-size: 14px;
                }
                QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {
                    border: none;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f38ba8, stop:1 #f9e2af);
                    color: #1e1e2e;
                    border: none;
                    padding: 12px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f9e2af, stop:1 #f38ba8);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #cdd6f4, stop:1 #89b4fa);
                }
            """,
            "light": """
                QMainWindow, QWidget {
                    background-color: #f5f5f5;
                }
                QLabel {
                    color: #1c2526;
                    font-size: 16px;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QComboBox, QSpinBox, QTextEdit {
                    background-color: #ffffff;
                    color: #1c2526;
                    border: 1px solid #d1d5db;
                    padding: 8px;
                    border-radius: 8px;
                    font-size: 14px;
                }
                QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {
                    border: none;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #60a5fa, stop:1 #a5b4fc);
                    color: #1c2526;
                    border: none;
                    padding: 12px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a5b4fc, stop:1 #60a5fa);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #bfdbfe, stop:1 #dbeafe);
                }
            """
        }
        self.setStyleSheet(self.themes[self.current_theme])

        # Central widget with stacked layout
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        # Main menu
        main_menu_widget = QWidget()
        main_menu_layout = QVBoxLayout(main_menu_widget)
        main_menu_layout.setAlignment(Qt.AlignCenter)
        main_menu_layout.setSpacing(20)

        title_label = QLabel("Ski Jumping Simulator")
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #f38ba8;" if self.current_theme == "dark" else "font-size: 32px; font-weight: bold; color: #2563eb;")
        main_menu_layout.addWidget(title_label)

        simulation_button = QPushButton("Symulacja")
        simulation_button.clicked.connect(lambda: self.central_widget.setCurrentIndex(1))
        main_menu_layout.addWidget(simulation_button)

        settings_button = QPushButton("Ustawienia")
        settings_button.clicked.connect(lambda: self.central_widget.setCurrentIndex(2))
        main_menu_layout.addWidget(settings_button)

        exit_button = QPushButton("Wyjdź")
        exit_button.clicked.connect(self.close)
        main_menu_layout.addWidget(exit_button)

        # Simulation screen
        simulation_widget = QWidget()
        simulation_layout = QVBoxLayout(simulation_widget)
        simulation_layout.setSpacing(15)
        simulation_layout.setContentsMargins(20, 20, 20, 20)

        # Load data
        self.all_hills, self.all_jumpers = load_data_from_json()
        self.selected_jumper = None
        self.selected_hill = None

        # Header
        sim_header_label = QLabel("Symulacja skoku")
        sim_header_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #f38ba8;" if self.current_theme == "dark" else "font-size: 24px; font-weight: bold; color: #2563eb;")
        sim_header_label.setAlignment(Qt.AlignCenter)
        simulation_layout.addWidget(sim_header_label)

        # Jumper selection
        jumper_layout = QHBoxLayout()
        jumper_label = QLabel("Zawodnik:")
        self.jumper_combo = QComboBox()
        self.jumper_combo.addItem("Wybierz zawodnika")
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
        self.simulate_button.clicked.connect(self.run_simulation)
        self.clear_button = QPushButton("Wyczyść")
        self.clear_button.clicked.connect(self.clear_results)
        button_layout.addWidget(self.simulate_button)
        button_layout.addWidget(self.clear_button)
        simulation_layout.addLayout(button_layout)

        back_button = QPushButton("Powrót")
        back_button.clicked.connect(lambda: self.central_widget.setCurrentIndex(0))
        simulation_layout.addWidget(back_button)

        # Result display
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFixedHeight(100)
        simulation_layout.addWidget(self.result_text)

        # Matplotlib canvas
        self.figure = Figure(facecolor='#1e1e2e' if self.current_theme == "dark" else '#f5f5f5')
        self.canvas = FigureCanvas(self.figure)
        simulation_layout.addWidget(self.canvas)

        # Settings screen
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        settings_layout.setAlignment(Qt.AlignCenter)
        settings_layout.setSpacing(20)

        settings_header = QLabel("Ustawienia")
        settings_header.setStyleSheet("font-size: 24px; font-weight: bold; color: #f38ba8;" if self.current_theme == "dark" else "font-size: 24px; font-weight: bold; color: #2563eb;")
        settings_layout.addWidget(settings_header)

        theme_layout = QHBoxLayout()
        theme_label = QLabel("Motyw:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Ciemny", "Jasny"])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        settings_layout.addLayout(theme_layout)

        settings_back_button = QPushButton("Powrót")
        settings_back_button.clicked.connect(lambda: self.central_widget.setCurrentIndex(0))
        settings_layout.addWidget(settings_back_button)

        # Add widgets to stacked layout
        self.central_widget.addWidget(main_menu_widget)
        self.central_widget.addWidget(simulation_widget)
        self.central_widget.addWidget(settings_widget)

        # Animation data
        self.positions = []
        self.x_landing = []
        self.y_landing = []

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

    def change_theme(self, theme):
        self.current_theme = "dark" if theme == "Ciemny" else "light"
        self.setStyleSheet(self.themes[self.current_theme])
        title_color = "#f38ba8" if self.current_theme == "dark" else "#2563eb"
        for i in range(self.central_widget.count()):
            widget = self.central_widget.widget(i)
            for label in widget.findChildren(QLabel):
                if "Ski Jumping Simulator" in label.text() or "Symulacja skoku" in label.text() or "Ustawienia" in label.text():
                    label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {title_color};")
        self.figure.set_facecolor('#1e1e2e' if self.current_theme == "dark" else '#f5f5f5')
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
            while current_position_y > self.selected_hill.y_landing(current_position_x):
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
                self.positions.append((current_position_x, current_position_y))
            self.x_landing = np.linspace(0, current_position_x + 50, 200)
            self.y_landing = [self.selected_hill.y_landing(x_val) for x_val in self.x_landing]

            # Animate plot
            plt.style.use('ggplot')
            self.figure.clear()
            ax = self.figure.add_subplot(111, facecolor='#313244' if self.current_theme == "dark" else '#ffffff')
            line1, = ax.plot([], [], 'r-', linewidth=2.5, label='Trajektoria lotu', alpha=0.8)
            line2, = ax.plot([], [], 'g-', linewidth=2.5, label='Profil lądowania', alpha=0.8)

            def init():
                ax.set_xlabel('Odległość (m)', fontsize=12, color='#cdd6f4' if self.current_theme == "dark" else '#1c2526')
                ax.set_ylabel('Wysokość (m)', fontsize=12, color='#cdd6f4' if self.current_theme == "dark" else '#1c2526')
                ax.set_title(
                    f'Trajektoria skoku (belka={gate}, kąt wybicia={math.degrees(takeoff_angle_rad):.1f}°, siła wybicia={self.selected_jumper.jump_force} N)',
                    fontsize=14, color='#cdd6f4' if self.current_theme == "dark" else '#1c2526', pad=15
                )
                ax.legend(facecolor='#313244' if self.current_theme == "dark" else '#ffffff', edgecolor='#45475a' if self.current_theme == "dark" else '#d1d5db', fontsize=10, labelcolor='#cdd6f4' if self.current_theme == "dark" else '#1c2526')
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.set_facecolor('#313244' if self.current_theme == "dark" else '#ffffff')
                self.figure.patch.set_facecolor('#1e1e2e' if self.current_theme == "dark" else '#f5f5f5')
                ax.tick_params(colors='#cdd6f4' if self.current_theme == "dark" else '#1c2526')
                ax.spines['bottom'].set_color('#cdd6f4' if self.current_theme == "dark" else '#1c2526')
                ax.spines['top'].set_color('#cdd6f4' if self.current_theme == "dark" else '#1c2526')
                ax.spines['left'].set_color('#cdd6f4' if self.current_theme == "dark" else '#1c2526')
                ax.spines['right'].set_color('#cdd6f4' if self.current_theme == "dark" else '#1c2526')
                return line1, line2

            def update(frame):
                if frame < len(self.positions):
                    x, y = zip(*self.positions[:frame+1])
                    line1.set_data(x, y)
                if frame < len(self.x_landing):
                    line2.set_data(self.x_landing[:frame], self.y_landing[:frame])
                ax.relim()
                ax.autoscale_view()
                return line1, line2

            ani = animation.FuncAnimation(self.figure, update, init_func=init, frames=max(len(self.positions), len(self.x_landing)), interval=20, blit=True)
            self.canvas.draw()

        except ValueError as e:
            self.result_text.setText(f"BŁĄD: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())