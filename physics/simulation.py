# simulation.py

'''Logika symulacji'''

from utils.constants import GRAVITY, AIR_DENSITY
import math
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
    distance_to_takeoff1 = 97.8

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

    return current_velocity * 3.6

sak = inrun_simulation(Zakopane, Kamil)
print(sak)