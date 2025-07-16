'''Klasa skocznia'''
# Nazewnictwo według nomenklatury FIS
# https://assets.fis-ski.com/f/252177/5ba64e29f2/construction-norm-2018-2.pdf

import math
import numpy as np
import scipy.optimize as so

class Hill:
    def __init__(self,
                 name: str,                 # Nazwa skoczni
                 e1: float,                 # Długość najazdu po krzywej (najwyższa belka - próg)
                 e2: float,                 # Długość najazdu po krzywej (najniższa belka - próg)
                 gates: int,                # Liczba bramek startowych
                 t: float,                  # Długość progu (E2 - próg)
                 gamma_deg: float,          # Kąt nachylenia górnej części najadzu (A - E1)
                 alpha_deg: float,          # Kąt nachylenia dolnej części najazdu (E2 - próg)
                 r1: float,                 # Promień klotoidy w E2
                 h: float,                  # Różnica wysokości między progiem a punktem K
                 n: float,                  # Odległość w poziomie między progiem a punktem K
                 s: float,                  # Wysokość progu
                 l1: float,                 # Odległość po krzywej od P do K
                 l2: float,                 # Odległość po krzywej od K do L
                 a_finish: float,           # Długść od U do końca
                 betaP_deg: float,          # Kąt nachylenia stycznej w punkcie P
                 beta_deg: float,           # Kąt nachylenia stycznej w punkcie K
                 betaL_deg: float,          # Kąt nachylenia stycznej w punkcie L
                 rl: float,                 # Promień okrągłego obszaru lądowania
                 r2l: float,                # Promień krzywej przejściowej z L do U w punkcie L
                 r2: float,                 # Promień krzywej przejściower z L do U w punkcie U
                 P: float,                  # Początek strefy lądowania
                 K: float,                  # Punkt konstrukcyjny
                 L: float,                  # Koniec sterfy lądowania (zazwyczaj HS)
                 Zu: float,                 # Różnica wysokości między progiem a najniższym punktem zeskoku

                 inrun_friction_coefficient: float = 0.025  # Współczynnik tarcia na najeździe
                 ):

        self.name = name
        self.e1 = e1
        self.e2 = e2
        self.gates = gates
        self.t = t
        self.gamma_deg = gamma_deg
        self.alpha_deg = alpha_deg
        self.r1 = r1
        self.h = h
        self.n = n
        self.s = s
        self.l1 = l1
        self.l2 = l2
        self.a_finish = a_finish
        self.betaP_deg = betaP_deg
        self.beta_deg = beta_deg
        self.betaL_deg = betaL_deg
        self.rl = rl
        self.r2l = r2l
        self.r2 = r2
        self.P = P
        self.K = K
        self.L = L
        self.Zu = Zu
        self.inrun_friction_coefficient = inrun_friction_coefficient

        # Konwersja stopni na radiany
        self.gamma_rad = math.radians(self.gamma_deg)
        self.alpha_rad = math.radians(self.alpha_deg)
        self.betaP_rad = math.radians(self.betaP_deg)
        self.beta_rad = math.radians(self.beta_deg)
        self.betaL_rad = math.radians(self.betaL_deg)

        # Zmienne pomocnicze
        self.es = abs(e1 - e2) # Wyznacza długość najazdu po krzywej, gdzie znajdują się belki
        self.gate_diff = self.es / (gates -1) if gates > 1 else 0.0  # Przedstawia różnice odległości między belkami
        self.r1_min = r1 / 2

        # Wartości klotoidy
        self.clothoid_length = 2 * self.r1_min * (abs(self.gamma_rad - self.alpha_rad))  # Wyznacza długość klotoidy
        self.clothoid_parameter = self.r1_min * math.sqrt(2*abs(self.gamma_rad - self.alpha_rad))  # Parametr klotoidy (A)

        # Atrybuty dla profilu lądowania - zostaną obliczone
        self.a_landing = 0.0
        self.b_landing = 0.0
        self.c_landing = 0.0
        self.landing_segment_boundaries = {}  # Słownik do przechowywania zakresów x dla segmentów



    def get_inrun_angle(self,
                        distance_from_takeoff: float  # Odległość po krzywej od progu (T) w górę rozbiegu
                        ) -> float:

        if distance_from_takeoff <= self.t:
            return self.alpha_rad

        elif distance_from_takeoff > self.t and distance_from_takeoff < (self.t + self.clothoid_length):

            L_aktualne_na_klotoidzie = (self.t + self.clothoid_length) - distance_from_takeoff

            theta_obrotu_rad = (L_aktualne_na_klotoidzie ** 2) / (2 * self.clothoid_parameter ** 2)

            return self.gamma_rad - theta_obrotu_rad

        elif distance_from_takeoff >= (self.t + self.clothoid_length):
            return self.gamma_rad

        else:
            return 0.0


    # Funkcja budująca wzór funkcji, który jest zeskokiem danej skoczni
    def calculate_landing_profile(self, v):

        # Współrzędne punktu O na zeskoku (Start zeskoku)
        O_coord_x = 0.0
        O_coord_y = -self.s

        # Współrzędne punktu K na zeskoku
        K_coord_x = self.n
        K_coord_y = -self.h

        # Współrzędne punkt L na zeskoku
        L_coord_x = K_coord_x + math.cos(self.betaL_rad) * abs(self.L - self.K)
        L_coord_y = K_coord_y - math.sin(self.betaL_rad) * abs(self.L - self.K)

        # Układ równań 3 niewiadomych
        # O_coord_y = self.a_landing * O_coord_x ** 2 + self.b_landing * O_coord_x + self.c_landing
        # K_coord_y = self.a_landing * K_coord_x ** 2 + self.b_landing * K_coord_x + self.c_landing
        # L_coord_y = self.a_landing * L_coord_x ** 2 + self.b_landing * L_coord_x + self.c_landing


        a = v[0]
        b = v[1]
        c = v[2]
        R = [0, 0, 0]
        R[0] = a * pow(O_coord_x, 2) + b * O_coord_x + c - O_coord_y
        R[1] = a * pow(K_coord_x, 2) + b * K_coord_x + c - K_coord_y
        R[2] = a * pow(L_coord_x, 2) + b * L_coord_x + c - L_coord_y

        return R


    def calculate_landing_parabola_coefficients(self):
        coefficients = so.fsolve(self.calculate_landing_profile, np.array([0, 0, 0]))
        self.a_landing = coefficients[0]
        self.b_landing = coefficients[1]
        self.c_landing = coefficients[2]

        return coefficients


    # Funkcja określająca wysokść zeskoku dla poziomej odległości od progu
    def y_landing(self, x: float) -> float:
       if self.a_landing == 0.0 and self.b_landing == 0.0 and self.c_landing == 0.0:
            print("OSTRZEŻENIE: Współczynniki paraboli nie zostały prawidłowo obliczone. Zwracam 0.")
            return 0.0

       return self.a_landing * pow(x, 2) + self.b_landing * x + self.c_landing


    def __str__(self):
        return f'Hill: {self.name} {self.K} {self.L}'