'''Funkcje pomocnicze'''

import math
from .constants import GRAVITY, AIR_DENSITY

# Siła grawitacji (pionowo w dół)
def gravity_force(mass):
    return mass * GRAVITY

# Siła grawitacji (równolegle do najazdu)
def gravity_force_parallel(mass, angle_rad):
    return gravity_force(mass) * math.sin(angle_rad)

# Siła nacisku normalnego (prostopadle od najazdu)
def normal_force(mass, angle_rad):
    return gravity_force(mass) * math.cos(angle_rad)

# Siła oporu
def drag_force(velocity, drag_coefficient, frontal_area):
    return 0.5 * AIR_DENSITY * (velocity ** 2) * drag_coefficient * frontal_area

# Siła tarcia
def friction_force(friction_coefficient, mass, angle_rad):
    return friction_coefficient * normal_force(mass, angle_rad)

# Siła nośna
def lift_force(velocity, lift_coefficient, frontal_area):
    return 0.5 * AIR_DENSITY * (velocity ** 2) * lift_coefficient * frontal_area