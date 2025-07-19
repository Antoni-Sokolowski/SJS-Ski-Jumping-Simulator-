'''Logika symulacji'''

import json
import os
import sys
import math

from PySide6.QtWidgets import QMessageBox

from src.hill import Hill
from src.jumper import Jumper
from utils.constants import GRAVITY, AIR_DENSITY
from utils.helpers import gravity_force_parallel, friction_force, drag_force


def get_data_path(filename):
    """
    Zwraca poprawną ścieżkę do pliku w folderze 'data', który ma znajdować się
    obok pliku .exe lub w głównym folderze projektu.
    """
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
    else:
        script_path = os.path.abspath(__file__)
        application_path = os.path.dirname(os.path.dirname(script_path))

    return os.path.join(application_path, 'data', filename)


def load_data_from_json():
    """Wczytuje dane skoczków i skoczni z jednego, zewnętrznego pliku data.json."""
    try:
        data_path = get_data_path('data.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        hills = [Hill(**h) for h in data['hills']]
        jumpers = [Jumper(**j) for j in data['jumpers']]

        return hills, jumpers

    except Exception as e:
        title = "Błąd Krytyczny - Nie można wczytać danych"
        message = (
            f"Nie udało się wczytać lub przetworzyć pliku 'data.json'!\n\n"
            f"Błąd: {type(e).__name__}: {e}\n\n"
            f"Program szukał pliku w lokalizacji:\n{get_data_path('data.json')}\n\n"
            f"Sprawdź, czy:\n"
            f"1. Folder 'data' na pewno znajduje się obok pliku .exe.\n"
            f"2. Plik 'data.json' nie jest uszkodzony i ma poprawną strukturę."
        )
        QMessageBox.critical(None, title, message)
        return [], []


def inrun_simulation(Hill, Jumper, gate_number=None, time_contact=0.1):
    gate_number = Hill.gates if gate_number is None else gate_number
    time_step = 0.001
    current_velocity = 0
    distance_to_takeoff = Hill.e2 + (gate_number - 1) * Hill.gate_diff
    if distance_to_takeoff > Hill.e1 or distance_to_takeoff < Hill.e2:
        raise ValueError(f"Belka startowa {gate_number} jest poza zakresem najazdu (max {Hill.gates})")

    while distance_to_takeoff > 0:
        current_angle = Hill.get_inrun_angle(distance_to_takeoff)
        g_force = gravity_force_parallel(Jumper.mass, current_angle)
        f_force = friction_force(Hill.inrun_friction_coefficient, Jumper.mass, current_angle)
        d_force = drag_force(current_velocity,
                             Jumper.inrun_drag_coefficient if distance_to_takeoff > 3 else Jumper.takeoff_drag_coefficient,
                             Jumper.inrun_frontal_area if distance_to_takeoff > 3 else Jumper.takeoff_frontal_area)

        net_force = g_force - f_force - d_force
        acceleration = net_force / Jumper.mass
        current_velocity += acceleration * time_step
        distance_to_takeoff -= current_velocity * time_step

    return current_velocity


def fly_simulation(Hill, Jumper, gate_number=None, time_contact=0.1):
    current_position_x, current_position_y = 0, 0
    initial_total_velocity = inrun_simulation(Hill, Jumper, gate_number=gate_number, time_contact=time_contact)
    initial_velocity_x = initial_total_velocity * math.cos(-Hill.alpha_rad)
    initial_velocity_y = initial_total_velocity * math.sin(-Hill.alpha_rad)
    velocity_takeoff = (Jumper.jump_force * time_contact) / Jumper.mass
    velocity_takeoff_x = velocity_takeoff * math.sin(Hill.alpha_rad)
    velocity_takeoff_y = velocity_takeoff * math.cos(Hill.alpha_rad)
    velocity_x_final = initial_velocity_x + velocity_takeoff_x
    velocity_y_final = initial_velocity_y + velocity_takeoff_y
    takeoff_angle_rad = math.atan2(velocity_y_final, velocity_x_final)

    v_perpendicular = (Jumper.jump_force * time_contact) / Jumper.mass
    current_velocity_x = initial_total_velocity * math.cos(takeoff_angle_rad)
    current_velocity_y = initial_total_velocity * math.sin(takeoff_angle_rad) + v_perpendicular

    time_step = 0.01
    max_hill_length = Hill.n + Hill.a_finish + 50

    while current_position_y > Hill.y_landing(current_position_x) and current_position_x < max_hill_length:
        total_velocity = math.sqrt(current_velocity_x ** 2 + current_velocity_y ** 2)
        angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)
        force_g_y = -Jumper.mass * GRAVITY
        force_drag_magnitude = 0.5 * AIR_DENSITY * Jumper.flight_drag_coefficient * Jumper.flight_frontal_area * total_velocity ** 2
        force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
        force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)
        force_lift_magnitude = 0.5 * AIR_DENSITY * Jumper.flight_lift_coefficient * Jumper.flight_frontal_area * total_velocity ** 2
        force_lift_x = -force_lift_magnitude * math.sin(angle_of_flight_rad)
        force_lift_y = force_lift_magnitude * math.cos(angle_of_flight_rad)
        acceleration_x = (force_drag_x + force_lift_x) / Jumper.mass
        acceleration_y = (force_g_y + force_drag_y + force_lift_y) / Jumper.mass
        current_velocity_x += acceleration_x * time_step
        current_velocity_y += acceleration_y * time_step
        current_position_x += current_velocity_x * time_step
        current_position_y += current_velocity_y * time_step

    return current_position_x