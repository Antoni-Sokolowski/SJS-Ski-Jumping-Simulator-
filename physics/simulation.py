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


def inrun_simulation(Hill, Jumper):
    time_step = 0.01
    current_velocity = 0
    distance_to_takeoff1 = 77

    if distance_to_takeoff1 > Hill.e1:
        return 0.0

    while distance_to_takeoff1 > 3:
        current_angle = Hill.get_inrun_angle(distance_to_takeoff1)  # Pobierz kąt przed użyciem

        # Obliczanie sił
        g_force = gravity_force_parallel(Jumper.mass, current_angle)
        d_force = drag_force(current_velocity, Jumper.inrun_drag_coefficient, Jumper.inrun_frontal_area)
        f_force = friction_force(Hill.inrun_friction_coefficient, Jumper.mass, current_angle)

        # Obliczanie siły wypadkowej
        net_force = g_force - d_force - f_force

        # Obliczanie przyspieszenia
        acceleration = net_force / Jumper.mass

        # Aktualizacja prędkości i pozycji
        current_velocity += acceleration * time_step
        distance_to_takeoff1 -= current_velocity * time_step

    while distance_to_takeoff1 > 0:

        # Obliczanie sił
        g_force = gravity_force_parallel(Jumper.mass, current_angle)
        d_force = drag_force(current_velocity, Jumper.takeoff_drag_coefficient, Jumper.takeoff_frontal_area)
        f_force = friction_force(Hill.inrun_friction_coefficient, Jumper.mass, current_angle)

        # Obliczanie siły wypadkowej
        net_force = g_force - d_force - f_force

        # Obliczanie przyspieszenia
        acceleration = net_force / Jumper.mass

        # Aktualizacja prędkości i pozycji
        current_velocity += acceleration * time_step
        distance_to_takeoff1 -= current_velocity * time_step

    return current_velocity


abc = Zakopane.calculate_landing_parabola_coefficients()
print(abc)
speed = inrun_simulation(Zakopane, Kamil)
print(speed*3.6)

def fly_simulation(Hill, Jumper):
    current_position_x = 0
    current_position_y = 0

    initial_total_velocity = inrun_simulation(Hill, Jumper)

    takeoff_angle_rad = Hill.alpha_rad + Jumper.takeoff_angle_changer_rad

    current_velocity_x = initial_total_velocity * math.cos(takeoff_angle_rad)
    current_velocity_y = initial_total_velocity * math.sin(takeoff_angle_rad)

    g = GRAVITY
    mass = Jumper.mass
    air_density = AIR_DENSITY
    Cd = Jumper.flight_drag_coefficient
    Cl = Jumper.flight_lift_coefficient
    A = Jumper.flight_frontal_area

    time_step = 0.01
    max_iterations = 1000000

    iteration = 0

    while current_position_y > Hill.y_landing(current_position_x):
        iteration += 1

        total_velocity = math.sqrt(current_velocity_x ** 2 + current_velocity_y ** 2)
        angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)

        force_g_y = -mass * g

        force_drag_magnitude = 0.5 * air_density * Cd * A * total_velocity ** 2
        force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
        force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)

        force_lift_magnitude = 0.5 * air_density * Cl * A * total_velocity ** 2
        force_lift_x = -force_lift_magnitude * math.sin(angle_of_flight_rad)
        force_lift_y = force_lift_magnitude * math.cos(angle_of_flight_rad)

        acceleration_x = (force_drag_x + force_lift_x) / mass
        acceleration_y = (force_g_y + force_drag_y + force_lift_y) / mass

        current_velocity_x += acceleration_x * time_step
        current_velocity_y += acceleration_y * time_step

        current_position_x += current_velocity_x * time_step
        current_position_y += current_velocity_y * time_step

    if iteration >= max_iterations:
        print("Simulation ended: Max iterations reached (jumper may not have landed or is in an infinite loop).")
        return -1

    print(f"Jumper landed at x={current_position_x:.2f}, y={current_position_y:.2f} after {iteration} steps.")

    landing_x = current_position_x

    a_parabola = Hill.a_landing
    b_parabola = Hill.b_landing
    c_parabola = Hill.c_landing

    start_of_landing_x = 0

    arc_segment_dx = 0.01

    arc_length = 0.0

    x_current_arc = start_of_landing_x

    while x_current_arc < landing_x:

        x_next_arc = min(x_current_arc + arc_segment_dx, landing_x)

        y1_parabola = Hill.y_landing(x_current_arc)
        y2_parabola = Hill.y_landing(x_next_arc)

        segment_length = math.sqrt((x_next_arc - x_current_arc) ** 2 + (y2_parabola - y1_parabola) ** 2)

        arc_length += segment_length

        x_current_arc = x_next_arc

    print(f"Obliczona długość skoku po paraboli: {arc_length:.2f} metrów")
    return arc_length

fly_simulation(Zakopane, Kamil)



