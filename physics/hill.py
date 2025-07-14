'''Klasa skocznia'''
# Nazewnictwo według nomenklatury FIS
# https://assets.fis-ski.com/f/252177/5ba64e29f2/construction-norm-2018-2.pdf

import math

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
                 a: float,                  # Długść od U do końca
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

                 inrun_friction_coefficient: float = 0.01  # Współczynnik tarcia na najeździe
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
        self.a = a
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
        self.es = e1 - e2  # Wyznacza długość najazdu po krzywej, gdzie znajdują się belki
        self.gate_diff = self.es / (gates -1) if gates > 1 else 0.0  # Przedstawia różnice odległości między belkami
        self.r1_min = r1 / 2

        # Wartości klotoidy
        self.clothoid_length = 2 * self.r1_min * (abs(self.gamma_rad - self.alpha_rad))  # Wyznacza długość klotoidy
        self.clothoid_parameter = self.r1_min * math.sqrt(2*abs(self.gamma_rad - self.alpha_rad))  # Parametr klotoidy (A)

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
            # Ta sekcja powinna być rzadko osiągana, jeśli warunki są wyczerpujące
            return 0  # Domyślna wartość w przypadku nieprzewidzianej odległości

    def __str__(self):
        return f'Hill: {self.name} {self.K} {self.L}'
