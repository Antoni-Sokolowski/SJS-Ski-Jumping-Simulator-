"""Logika symulacji"""

import json
import os
import sys
import math
import random

try:
    from PySide6.QtWidgets import QMessageBox  # type: ignore
except Exception:  # Headless / tests without Qt

    class QMessageBox:  # type: ignore
        @staticmethod
        def critical(parent, title, message):
            print(f"[CRITICAL] {title}:\n{message}")


from src.hill import Hill
from src.jumper import Jumper
from utils.constants import GRAVITY, AIR_DENSITY
from utils.helpers import gravity_force_parallel, friction_force, drag_force


def get_data_path(filename):
    """
    Zwraca poprawną ścieżkę do pliku w folderze 'data', który ma znajdować się
    obok pliku .exe lub w głównym folderze projektu.
    """
    if getattr(sys, "frozen", False):
        application_path = os.path.dirname(sys.executable)
    else:
        script_path = os.path.abspath(__file__)
        application_path = os.path.dirname(os.path.dirname(script_path))

    return os.path.join(application_path, "data", filename)


def load_data_from_json():
    """Wczytuje dane skoczków i skoczni z jednego, zewnętrznego pliku data.json."""
    try:
        data_path = get_data_path("data.json")
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        hills = [Hill(**h) for h in data["hills"]]
        jumpers = [Jumper(**j) for j in data["jumpers"]]

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


def inrun_simulation(
    Hill,
    Jumper,
    gate_number=None,
    time_contact=0.1,
    early_takeoff_aero_shift_m: float = 0.0,
):
    gate_number = Hill.gates if gate_number is None else gate_number
    time_step = 0.001
    current_velocity = 0
    distance_to_takeoff = Hill.e2 + (gate_number - 1) * Hill.gate_diff
    if distance_to_takeoff > Hill.e1 or distance_to_takeoff < Hill.e2:
        raise ValueError(
            f"Belka startowa {gate_number} jest poza zakresem najazdu (max {Hill.gates})"
        )

    # Próg przełączenia na współczynniki aerodynamiczne wybicia w metrach od progu.
    # Domyślnie 3 m, ale przy wczesnym timingu możemy wejść wcześniej (zwiększone opory wcześniej).
    aero_switch_distance = 3.0 + max(0.0, early_takeoff_aero_shift_m)

    while distance_to_takeoff > 0:
        current_angle = Hill.get_inrun_angle(distance_to_takeoff)
        g_force = gravity_force_parallel(Jumper.mass, current_angle)
        f_force = friction_force(
            Hill.inrun_friction_coefficient, Jumper.mass, current_angle
        )
        # W ostatnich metrach przełączamy na większe opory pozycji wybicia.
        use_inrun_aero = distance_to_takeoff > aero_switch_distance
        d_force = drag_force(
            current_velocity,
            Jumper.inrun_drag_coefficient
            if use_inrun_aero
            else Jumper.takeoff_drag_coefficient,
            Jumper.inrun_frontal_area
            if use_inrun_aero
            else Jumper.takeoff_frontal_area,
        )

        net_force = g_force - f_force - d_force
        acceleration = net_force / Jumper.mass
        current_velocity += acceleration * time_step
        distance_to_takeoff -= current_velocity * time_step

    return current_velocity


def fly_simulation(
    Hill, Jumper, gate_number=None, time_contact=0.1, perfect_timing: bool = False
):
    current_position_x, current_position_y = 0, 0

    # 1) Najpierw oszacuj prędkość najazdową bez korekt timingu
    initial_total_velocity = inrun_simulation(
        Hill, Jumper, gate_number=gate_number, time_contact=time_contact
    )

    # 2) Błąd czasu zależny od statystyki timingu; w trybie idealnym brak losowości
    if perfect_timing:
        epsilon_t = 0.0
    else:
        timing_value = getattr(Jumper, "timing", 50) or 50
        # σ_t: 60 ms przy 0 → 10 ms przy 100 (liniowo)
        sigma_ms = 60.0 - 0.5 * max(0.0, min(100.0, timing_value))
        sigma_s = sigma_ms / 1000.0
        epsilon_t = random.gauss(0.0, sigma_s)
        # Ogranicz do rozsądnych wartości
        epsilon_t = max(-0.12, min(0.12, epsilon_t))

    # 3) Przeliczenie na przesunięcie po łuku (m)
    epsilon_s = initial_total_velocity * epsilon_t  # m
    # Wcześnie (epsilon_s < 0): wcześniejsze wejście w sylwetkę wybicia → większe opory wcześniej
    early_takeoff_aero_shift_m = 0.0 if perfect_timing else max(0.0, -epsilon_s)
    # Ogranicz wpływ do 1.0 m
    early_takeoff_aero_shift_m = min(early_takeoff_aero_shift_m, 1.0)

    # 4) Przelicz prędkość najazdową z korektą aero dla wczesnego timingu
    if early_takeoff_aero_shift_m > 1e-6:
        initial_total_velocity = inrun_simulation(
            Hill,
            Jumper,
            gate_number=gate_number,
            time_contact=time_contact,
            early_takeoff_aero_shift_m=early_takeoff_aero_shift_m,
        )

    inrun_velocity_x = initial_total_velocity * math.cos(-Hill.alpha_rad)
    inrun_velocity_y = initial_total_velocity * math.sin(-Hill.alpha_rad)

    # 5) Skuteczność impulsu wybicia zależna od błędu czasu
    base_delta_v = (Jumper.jump_force * time_contact) / Jumper.mass
    if perfect_timing:
        magnitude_scale = 1.0
        delta_v_from_jump = base_delta_v
        vertical_efficiency = 1.0
    else:
        # Skala modułu impulsu: do ~25% straty przy |epsilon_t| >= 0.08 s
        ratio_time = min(abs(epsilon_t) / 0.08, 1.0)
        magnitude_scale = 1.0 - 0.25 * (ratio_time**1.2)
        delta_v_from_jump = base_delta_v * magnitude_scale
        # Korekta „kątowa” – redukcja składowej pionowej przy dużym błędzie fazy
        # Do 25% redukcji przy |epsilon_s| >= 1.0 m
        vertical_efficiency = 1.0 - 0.25 * min(abs(epsilon_s), 1.0)
        vertical_efficiency = max(
            0.6, vertical_efficiency
        )  # dolny limit bezpieczeństwa

    jump_velocity_x = delta_v_from_jump * math.sin(Hill.alpha_rad)
    jump_velocity_y = delta_v_from_jump * math.cos(Hill.alpha_rad) * vertical_efficiency

    # 6) Zapamiętaj informację o timingu w obiekcie Jumper (na potrzeby UI)
    classification = "idealny"
    if not perfect_timing:
        if abs(epsilon_t) < 0.01:
            classification = "idealny"
        elif epsilon_t < 0:
            classification = "za wcześnie"
        else:
            classification = "za późno"
    try:
        Jumper.last_timing_info = {
            "epsilon_t_s": float(epsilon_t),
            "epsilon_s_m": float(epsilon_s),
            "magnitude_scale": float(magnitude_scale if not perfect_timing else 1.0),
            "vertical_efficiency": float(vertical_efficiency),
            "classification": classification,
        }
    except Exception:
        pass

    current_velocity_x = inrun_velocity_x + jump_velocity_x
    current_velocity_y = inrun_velocity_y + jump_velocity_y

    # Obliczanie efektywnej siły nośnej
    base_cl = Jumper.flight_lift_coefficient
    effective_cl = base_cl

    baseline_velocity_ms = 24.5
    max_bonus_velocity_ms = 28.5

    if initial_total_velocity > baseline_velocity_ms:
        max_lift_bonus = 0.12

        velocity_factor = (initial_total_velocity - baseline_velocity_ms) / (
            max_bonus_velocity_ms - baseline_velocity_ms
        )
        velocity_factor = min(1.0, max(0.0, velocity_factor))

        lift_bonus = max_lift_bonus * velocity_factor
        effective_cl = base_cl + lift_bonus

    time_step = 0.01
    max_hill_length = Hill.n + Hill.a_finish + 50

    while (
        current_position_y > Hill.y_landing(current_position_x)
        and current_position_x < max_hill_length
    ):
        total_velocity = math.sqrt(current_velocity_x**2 + current_velocity_y**2)
        angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)
        force_g_y = -Jumper.mass * GRAVITY

        force_drag_magnitude = (
            0.5
            * AIR_DENSITY
            * Jumper.flight_drag_coefficient
            * Jumper.flight_frontal_area
            * total_velocity**2
        )
        force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
        force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)

        force_lift_magnitude = (
            0.5
            * AIR_DENSITY
            * effective_cl
            * Jumper.flight_frontal_area
            * total_velocity**2
        )
        force_lift_x = -force_lift_magnitude * math.sin(angle_of_flight_rad)
        force_lift_y = force_lift_magnitude * math.cos(angle_of_flight_rad)

        acceleration_x = (force_drag_x + force_lift_x) / Jumper.mass
        acceleration_y = (force_g_y + force_drag_y + force_lift_y) / Jumper.mass

        current_velocity_x += acceleration_x * time_step
        current_velocity_y += acceleration_y * time_step
        current_position_x += current_velocity_x * time_step
        current_position_y += current_velocity_y * time_step

    return current_position_x
