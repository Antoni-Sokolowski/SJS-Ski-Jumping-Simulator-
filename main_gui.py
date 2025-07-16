import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox, QPushButton, QTextEdit, QLabel
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from physics.simulation import load_data_from_json, inrun_simulation, fly_simulation
import numpy as np
import math

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ski Jumping Simulator")
        self.setGeometry(100, 100, 900, 700)

        # Load data
        self.all_hills, self.all_jumpers = load_data_from_json()
        self.selected_jumper = None
        self.selected_hill = None

        # Set dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2d42;
            }
            QLabel {
                color: #edf2f4;
                font-size: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QComboBox {
                background-color: #3d405b;
                color: #edf2f4;
                border: 1px solid #5c6370;
                padding: 8px;
                border-radius: 5px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(none);
                width: 10px;
                height: 10px;
            }
            QSpinBox {
                background-color: #3d405b;
                color: #edf2f4;
                border: 1px solid #5c6370;
                padding: 8px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #ef233c;
                color: #edf2f4;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: #d90429;
            }
            QPushButton:pressed {
                background-color: #8d5524;
            }
            QTextEdit {
                background-color: #3d405b;
                color: #edf2f4;
                border: 1px solid #5c6370;
                border-radius: 5px;
                font-size: 14px;
                padding: 5px;
            }
        """)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_label = QLabel("Ski Jumping Simulator")
        header_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ef233c;")
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

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
        main_layout.addLayout(jumper_layout)

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
        main_layout.addLayout(hill_layout)

        # Gate selection
        gate_layout = QHBoxLayout()
        gate_label = QLabel("Belka startowa:")
        self.gate_spin = QSpinBox()
        self.gate_spin.setMinimum(1)
        self.gate_spin.setMaximum(1)  # Updated when hill is selected
        gate_layout.addWidget(gate_label)
        gate_layout.addWidget(self.gate_spin)
        main_layout.addLayout(gate_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.simulate_button = QPushButton("Uruchom symulację")
        self.simulate_button.clicked.connect(self.run_simulation)
        self.clear_button = QPushButton("Wyczyść")
        self.clear_button.clicked.connect(self.clear_results)
        button_layout.addWidget(self.simulate_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)

        # Result display
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFixedHeight(100)
        main_layout.addWidget(self.result_text)

        # Matplotlib canvas for trajectory
        self.figure = Figure(facecolor='#2b2d42')
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)

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

            # Plot trajectory with modern style
            plt.style.use('ggplot')
            self.figure.clear()
            ax = self.figure.add_subplot(111, facecolor='#3d405b')
            positions = [(0, 0)]
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
                positions.append((current_position_x, current_position_y))
            x, y = zip(*positions)
            x_landing = np.linspace(0, current_position_x + 50, 200)
            y_landing = [self.selected_hill.y_landing(x_val) for x_val in x_landing]
            ax.plot(x, y, 'r-', linewidth=2.5, label='Trajektoria lotu', alpha=0.8)
            ax.plot(x_landing, y_landing, 'g-', linewidth=2.5, label='Profil lądowania', alpha=0.8)
            ax.set_xlabel('Odległość (m)', fontsize=12, color='#edf2f4')
            ax.set_ylabel('Wysokość (m)', fontsize=12, color='#edf2f4')
            ax.set_title(
                f'Trajektoria skoku (belka={gate}, kąt wybicia={math.degrees(takeoff_angle_rad):.1f}°, siła wybicia={self.selected_jumper.jump_force} N)',
                fontsize=14, color='#edf2f4', pad=15
            )
            ax.legend(facecolor='#3d405b', edgecolor='#5c6370', fontsize=10, labelcolor='#edf2f4')
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.set_facecolor('#3d405b')
            self.figure.patch.set_facecolor('#2b2d42')
            ax.tick_params(colors='#edf2f4')
            ax.spines['bottom'].set_color('#edf2f4')
            ax.spines['top'].set_color('#edf2f4')
            ax.spines['left'].set_color('#edf2f4')
            ax.spines['right'].set_color('#edf2f4')
            self.figure.tight_layout()
            self.canvas.draw()

        except ValueError as e:
            self.result_text.setText(f"BŁĄD: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())