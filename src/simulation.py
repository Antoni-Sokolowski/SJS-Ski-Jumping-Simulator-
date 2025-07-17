#src/simulation.py

'''Logika symulacji'''

import json
from pathlib import Path
from utils.constants import GRAVITY, AIR_DENSITY
import math
import numpy as np
import matplotlib.pyplot as plt
from src.hill import Hill
from src.jumper import Jumper
from utils.helpers import gravity_force_parallel, friction_force, drag_force


def load_data_from_json(filename='data.json'):
    """
    Wczytuje dane z pliku JSON z głównego folderu projektu.
    """

    script_dir = Path(__file__).parent

    project_dir = script_dir.parent

    filepath = project_dir / "assets" / filename


    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    hills = [Hill(**h) for h in data['hills']]
    jumpers = [Jumper(**j) for j in data['jumpers']]

    return hills, jumpers

all_hills, all_jumpers = load_data_from_json()

Zakopane = next((h for h in all_hills if h.name == "Zakopane"), None)
Kamil = next((j for j in all_jumpers if j.name == "Kamil" and j.last_name == "Stoch"), None)


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

        # Aktywne wybicie w ostatnich 0.1 m
        net_force = g_force - f_force - d_force

        acceleration = net_force / Jumper.mass
        current_velocity += acceleration * time_step
        distance_to_takeoff -= current_velocity * time_step

    return current_velocity


def fly_simulation(Hill, Jumper, gate_number=None, time_contact=0.1):
    positions = [(0, 0)]
    current_position_x, current_position_y = 0, 0
    initial_total_velocity = inrun_simulation(Hill, Jumper, gate_number=gate_number, time_contact=time_contact)
    initial_velocity_x = initial_total_velocity * math.cos(-Hill.alpha_rad)
    initial_velocity_y = initial_total_velocity * math.sin(-Hill.alpha_rad)
    velocity_takeoff = (Jumper.jump_force * time_contact) / Jumper.mass  # Prędkość na progu uzyskana dzięki sile wybicia
    velocity_takeoff_x = velocity_takeoff * math.sin(Hill.alpha_rad)
    velocity_takeoff_y = velocity_takeoff * math.cos(Hill.alpha_rad)
    velocity_x_final = initial_velocity_x + velocity_takeoff_x
    velocity_y_final = initial_velocity_y + velocity_takeoff_y
    takeoff_angle_rad = math.atan2(velocity_y_final, velocity_x_final)

    # Dodaj prędkość pionową z wybicia
    v_perpendicular = (Jumper.jump_force * time_contact) / Jumper.mass
    current_velocity_x = initial_total_velocity * math.cos(takeoff_angle_rad)
    current_velocity_y = initial_total_velocity * math.sin(takeoff_angle_rad) + v_perpendicular

    time_step = 0.001
    max_iterations = 1000000
    iteration = 0

    while current_position_y > Hill.y_landing(current_position_x):
        iteration += 1
        total_velocity = math.sqrt(current_velocity_x ** 2 + current_velocity_y ** 2)
        angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)
        force_g_y = -Jumper.mass * GRAVITY
        force_drag_magnitude = 0.5 * AIR_DENSITY * (Jumper.flight_drag_coefficient if current_position_y > Hill.y_landing(current_position_x) + 1
                                                    else Jumper.landing_drag_coefficient) * (Jumper.flight_frontal_area if current_position_y > Hill.y_landing(current_position_x) + 1
                                                                                             else Jumper.landing_frontal_area) * total_velocity ** 2
        force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
        force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)
        force_lift_magnitude = 0.5 * AIR_DENSITY * (Jumper.flight_lift_coefficient if current_position_y > Hill.y_landing(current_position_x) + 1
                                                    else Jumper.landing_lift_coefficient) * Jumper.flight_frontal_area * total_velocity ** 2
        force_lift_x = -force_lift_magnitude * math.sin(angle_of_flight_rad)
        force_lift_y = force_lift_magnitude * math.cos(angle_of_flight_rad)
        acceleration_x = (force_drag_x + force_lift_x) / Jumper.mass
        acceleration_y = (force_g_y + force_drag_y + force_lift_y) / Jumper.mass
        current_velocity_x += acceleration_x * time_step
        current_velocity_y += acceleration_y * time_step
        current_position_x += current_velocity_x * time_step
        current_position_y += current_velocity_y * time_step
        positions.append((current_position_x, current_position_y))
        if iteration >= max_iterations:
            print("Symulacja przerwana: Osiągnięto maksymalną liczbę iteracji")
            return -1


    landing_x = current_position_x
    arc_length = 0.0
    x_current_arc = 0
    arc_segment_dx = 0.01
    while x_current_arc < landing_x:
        x_next_arc = min(x_current_arc + arc_segment_dx, landing_x)
        y1_parabola = Hill.y_landing(x_current_arc)
        y2_parabola = Hill.y_landing(x_next_arc)
        segment_length = math.sqrt((x_next_arc - x_current_arc) ** 2 + (y2_parabola - y1_parabola) ** 2)
        arc_length += segment_length
        x_current_arc = x_next_arc

    return arc_length


def plot_flight_trajectory(Hill, Jumper, gate_number=None, time_contact=0.1):
    positions = [(0, 0)]
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
    while current_position_y > Hill.y_landing(current_position_x):
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
        positions.append((current_position_x, current_position_y))
    x, y = zip(*positions)

    x_landing = np.linspace(0, current_position_x + 50, 200)

    y_landing = [Hill.y_landing(x_val) for x_val in x_landing]
    plt.plot(x, y, 'r-', label='Trajektoria lotu')
    plt.plot(x_landing, y_landing, 'g-', label='Profil lądowania')
    plt.xlabel('Odległość (m)')
    plt.ylabel('Wysokość (m)')
    plt.title(
        f'Trajektoria skoku (belka={gate_number or Hill.gates}, kąt wybicia={math.degrees(takeoff_angle_rad):.1f}°, siła wybicia={Jumper.jump_force} N)')
    plt.legend()
    plt.grid(True)
    plt.axis('equal')
    plt.show()
    return positions[-1][0]


if __name__ == "__main__":
    speed = inrun_simulation(Zakopane, Kamil,11)
    print(f"{round(speed*3.6, 2)} km/h")



    fly_simulation(Zakopane, Kamil, 11)

    plot_flight_trajectory(Zakopane, Kamil, 11)