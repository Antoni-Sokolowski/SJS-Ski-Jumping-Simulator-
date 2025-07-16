# simulation.py

'''Logika symulacji'''

from utils.constants import GRAVITY, AIR_DENSITY
import math
import numpy as np
import scipy.optimize as so
from hill import Hill
from jumper import Jumper
from utils.helpers import gravity_force_parallel, friction_force, drag_force

Zakopane = Hill("Wielka Krokiew",
                97.8,
                77,
                34,
                6.5,
                35,
                11,
                90,
                62.37,
                107.76,
                3.13,
                16,
                15,
                103,
                37,
                34.3,
                31.3,
                310,
                168,
                99.3,
                109,
                125,
                140,
                89.11
                )

Kamil = Jumper("Kamil",
               "Stoch",
               60,
               1.72,
               )


def inrun_simulation(Hill, Jumper, gate_number=None, time_contact=0.1):
    gate_number = Hill.gates if gate_number is None else gate_number
    time_step = 0.001
    current_velocity = 0
    distance_to_takeoff = Hill.e2 + (gate_number - 1) * Hill.gate_diff
    if distance_to_takeoff > Hill.e1:
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
        if distance_to_takeoff < 0.1:
            takeoff_angle_rad = -Hill.alpha_rad + Jumper.takeoff_angle_changer_rad
            net_force += Jumper.jump_force * math.sin(takeoff_angle_rad)  # Siła w kierunku kąta wybicia

        acceleration = net_force / Jumper.mass
        current_velocity += acceleration * time_step
        distance_to_takeoff -= current_velocity * time_step

    return current_velocity


def fly_simulation(Hill, Jumper, gate_number=None, time_contact=0.1):
    positions = [(0, 0)]
    current_position_x, current_position_y = 0, 0
    initial_total_velocity = inrun_simulation(Hill, Jumper, gate_number=gate_number, time_contact=time_contact)
    takeoff_angle_rad = -Hill.alpha_rad + Jumper.takeoff_angle_changer_rad

    # Dodaj prędkość pionową z wybicia
    v_perpendicular = (Jumper.jump_force * time_contact) / Jumper.mass
    current_velocity_x = initial_total_velocity * math.cos(takeoff_angle_rad)
    current_velocity_y = initial_total_velocity * math.sin(takeoff_angle_rad) + v_perpendicular

    time_step = 0.001
    max_iterations = 1000000
    iteration = 0

    while current_position_y > Hill.y_landing(current_position_x) + 1:
        iteration += 1
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
        if iteration >= max_iterations:
            print("Symulacja przerwana: Osiągnięto maksymalną liczbę iteracji")
            return -1

    while current_position_y > Hill.y_landing(current_position_x):
        iteration += 1
        total_velocity = math.sqrt(current_velocity_x ** 2 + current_velocity_y ** 2)
        angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)
        force_g_y = -Jumper.mass * GRAVITY
        force_drag_magnitude = 0.5 * AIR_DENSITY * Jumper.landing_drag_coefficient * Jumper.landing_frontal_area * total_velocity ** 2
        force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
        force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)
        force_lift_magnitude = 0.5 * AIR_DENSITY * Jumper.flight_lift_coefficient * Jumper.landing_frontal_area * total_velocity ** 2
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

    print(f"Skoczek wylądował na x={landing_x:.2f}, y={current_position_y:.2f} po {iteration} krokach.")
    print(f"Długość skoku: {arc_length:.2f} metrów")
    return arc_length


abc = Zakopane.calculate_landing_parabola_coefficients()
print(abc)
speed = inrun_simulation(Zakopane, Kamil, 34)
print(f"{round(speed*3.6, 2)} km/h")



fly_simulation(Zakopane, Kamil, 1)