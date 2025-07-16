# jumper.py

'''Klasa skoczek'''

import math

class Jumper:
    def __init__(self,
                 name: str,                                     # Imię
                 last_name: str,                                # Nazwisko
                 mass: float = 60,                              # Waga
                 height: float = 1.72,                          # Wzrost

                 # --- NAJAZD ---
                 inrun_drag_coefficient: float = 0.46,          # Współczynnik oporu aerodynamicznego zawodnika w pozycji najazdowej
                 inrun_frontal_area: float = 0.42,              # Powierzchnia czołowa zawodnika w pozycji najazdowej
                 inrun_lift_coefficient: float = 0,             # Współczynnik siły nośnej zawodnika w pozycji najazdowej

                 # --- WYBICIE ---
                 takeoff_drag_coefficient: float = 1,           # Współczynnik oporu aerodynamicznego zawodnika podczas wybicia
                 takeoff_frontal_area: float = 0.8,             # Powierzchnia czołowa zawodnika podczas wybicia
                 takeoff_lift_coefficient: float = 0,           # Współczynnik siły nośnej zawodnika podczas wybicia
                 takeoff_angle_changer_deg: float = 31,         # Wartość zmiany kątu wybicia zawodnika w stopniach
                 jump_force = 1500,                             # Siła wybicia

                 # --- LOT ---
                 flight_drag_coefficient: float = 0.88,         # Współczynnik oporu aerodynamicznego zawodnika w locie
                 flight_frontal_area: float = 0.6,             # Powierzchnia czołowa zawodnika w locie
                 flight_lift_coefficient: float = 0.55,          # Współczynnik siły nośnej zawodnika w locie

                 # --- LĄDOWANIE ---
                 landing_drag_coefficient: float = 3,           # Współczynnik oporu aerodynamicznego zawodnika podczas lądowania
                 landing_frontal_area: float = 1,               # Powierzchnia czołowa zawodnika podczas lądowania
                 landing_lift_coefficient: float = 0            # Współczynnik siły nośnej zawodnika podczas lądowania
                 ):

        self.name = name
        self.last_name = last_name
        self.mass = mass
        self.height = height
        self.inrun_drag_coefficient = inrun_drag_coefficient
        self.inrun_frontal_area = inrun_frontal_area
        self.inrun_lift_coefficient = inrun_lift_coefficient
        self.takeoff_drag_coefficient = takeoff_drag_coefficient
        self.takeoff_frontal_area = takeoff_frontal_area
        self.takeoff_lift_coefficient = takeoff_lift_coefficient
        self.takeoff_angle_changer_deg = takeoff_angle_changer_deg
        self.jump_force = jump_force
        self.flight_drag_coefficient = flight_drag_coefficient
        self.flight_frontal_area = flight_frontal_area
        self.flight_lift_coefficient = flight_lift_coefficient
        self.landing_drag_coefficient = landing_drag_coefficient
        self.landing_frontal_area = landing_frontal_area
        self.landing_lift_coefficient = landing_lift_coefficient

        # Konwersja stopni na radiany
        self.takeoff_angle_changer_rad = math.radians(self.takeoff_angle_changer_deg)


    def __str__(self):
        return f'{self.name} {self.last_name}'