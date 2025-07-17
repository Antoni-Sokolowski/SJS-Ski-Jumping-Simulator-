#src/hill.py

'''Klasa skocznia'''

# Nazewnictwo według nomenklatury FIS
# https://assets.fis-ski.com/f/252177/5ba64e29f2/construction-norm-2018-2.pdf

import math
import numpy as np
import scipy.optimize as so

class Hill:

    '''Wprowadzamy atrybuty skoczni'''

    def __init__(self,
                 name: str,                 # Nazwa skoczni
                 country: str,              # Kraj
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


                 inrun_friction_coefficient: float = 0.02  # Współczynnik tarcia na najeździe
                 ):

        self.name = name
        self.country = country
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

        # Współczynniki dla pierwszej krzywej (polinom 3. stopnia) i drugiej paraboli
        self.a_landing2 = 0.0
        self.b_landing2 = 0.0
        self.c_landing2 = 0.0
        self.landing_segment_boundaries = {'polynomial1': (0, self.K), 'parabola2': (self.K, self.L)}

        # Dodatkowe punkt dla pierwszej krzywej
        self.x_F = 0.05 * self.L
        self.y_F = -self.s - 1

        # Oblicz współczynniki parabol
        self.calculate_landing_parabola_coefficients()


    def get_inrun_angle(self,
                        distance_from_takeoff: float  # Odległość po krzywej od progu (T) w górę rozbiegu
                        ) -> float:

        '''Funkcja zwracająca kąt nachylenia najazdu w dowolnym jego miejscu'''

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

    def calculate_landing_profile(self, v, segment='polynomial1'):

        '''Funkcja, która tworzy nasz zeskok'''

        if segment == 'polynomial1':
            # Punkty dla pierwszej krzywej: (0, -s), (x_F, y_F), (n, -h), nachylenie w x=n
            O_coord_x = 0.0
            O_coord_y = -self.s
            F_coord_x = self.x_F
            F_coord_y = self.y_F
            K_coord_x = self.n
            K_coord_y = -self.h
            slope_K = -math.tan(self.beta_rad)

            a, b, c, d = v
            R = [0, 0, 0, 0]
            R[0] = a * O_coord_x ** 3 + b * O_coord_x ** 2 + c * O_coord_x + d - O_coord_y  # y(0) = -s
            R[1] = a * F_coord_x ** 3 + b * F_coord_x ** 2 + c * F_coord_x + d - F_coord_y  # y(x_F) = y_F
            R[2] = a * K_coord_x ** 3 + b * K_coord_x ** 2 + c * K_coord_x + d - K_coord_y  # y(n) = -h
            R[3] = 3 * a * K_coord_x ** 2 + 2 * b * K_coord_x + c - slope_K  # y'(n) = -tan(beta_rad)
            return R
        else:
            # Punkty dla drugiej paraboli: (n, -h), (L, -Zu)
            K_coord_x = self.n
            K_coord_y = -self.h
            U_coord_x = self.n + 50
            U_coord_y = -self.Zu
            slope_K = -math.tan(self.beta_rad)

            a, b, c = v
            R = [0, 0, 0]
            R[0] = a * K_coord_x ** 2 + b * K_coord_x + c - K_coord_y  # y(n) = -h
            R[1] = a * U_coord_x ** 2 + b * U_coord_x + c - U_coord_y  # y(L) = -Zu
            R[2] = 2 * a * K_coord_x + b - slope_K  # y'(n) = -tan(beta_rad)
            return R

    def calculate_landing_parabola_coefficients(self):

        '''Funkcja, która oblicza współczynniki krzywych, tworzących zeskok'''

        # Obliczanie współczynników pierwszej krzywej (polinom 3. stopnia)
        coeffs1 = so.fsolve(self.calculate_landing_profile, np.array([0, 0, 0, 0]), args=('polynomial1',))
        self.a_landing1 = coeffs1[0]
        self.b_landing1 = coeffs1[1]
        self.c_landing1 = coeffs1[2]
        self.d_landing1 = coeffs1[3]

        # Obliczanie współczynników drugiej paraboli
        coeffs2 = so.fsolve(self.calculate_landing_profile, np.array([0, 0, 0]), args=('parabola2',))
        self.a_landing2 = coeffs2[0]
        self.b_landing2 = coeffs2[1]
        self.c_landing2 = coeffs2[2]

        return {'polynomial1': coeffs1, 'parabola2': coeffs2}

    def y_landing(self, x: float) -> float:

        '''Funkcja, która zwraca wysokość zeskoku w danym miejscu'''

        # Ograniczenie dziedziny
        if not (0 <= x <= self.n + self.a_finish + 50):
            raise ValueError(f"Wartość x={x} poza dziedziną [0, {self.n + self.a_finish + 50}]")

        # Sprawdzenie, czy współczynniki są obliczone
        if (self.a_landing1 == 0.0 and self.b_landing1 == 0.0 and self.c_landing1 == 0.0 and self.d_landing1 == 0.0) or \
                (self.a_landing2 == 0.0 and self.b_landing2 == 0.0 and self.c_landing2 == 0.0):
            print("OSTRZEŻENIE: Współczynniki krzywych nie zostały prawidłowo obliczone. Zwracam 0.")
            return 0.0

        # Wybór odpowiedniej krzywej
        if x <= self.n:
            return self.a_landing1 * x ** 3 + self.b_landing1 * x ** 2 + self.c_landing1 * x + self.d_landing1
        else:
            return self.a_landing2 * x ** 2 + self.b_landing2 * x + self.c_landing2

    def __str__(self):
        return f'{self.name} K{self.K} HS{self.L}'