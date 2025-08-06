"""Klasa skocznia"""

# Nazewnictwo według nomenklatury FIS
# https://assets.fis-ski.com/f/252177/5ba64e29f2/construction-norm-2018-2.pdf

import math
import numpy as np
import scipy.optimize as so


class Hill:
    """Wprowadzamy atrybuty skoczni"""

    def __init__(
        self,
        name: str,  # Nazwa skoczni
        country: str,  # Kraj
        e1: float,  # Długość najazdu po krzywej (najwyższa belka - próg)
        e2: float,  # Długość najazdu po krzywej (najniższa belka - próg)
        gates: int,  # Liczba bramek startowych
        t: float,  # Długość progu (E2 - próg)
        gamma_deg: float,  # Kąt nachylenia górnej części najadzu (A - E1)
        alpha_deg: float,  # Kąt nachylenia dolnej części najazdu (E2 - próg)
        r1: float,  # Promień klotoidy w E2
        h: float,  # Różnica wysokości między progiem a punktem K
        n: float,  # Odległość w poziomie między progiem a punktem K
        s: float,  # Wysokość progu
        l1: float,  # Odległość po krzywej od P do K
        l2: float,  # Odległość po krzywej od K do L
        a_finish: float,  # Długść od U do końca
        betaP_deg: float,  # Kąt nachylenia stycznej w punkcie P
        beta_deg: float,  # Kąt nachylenia stycznej w punkcie K
        betaL_deg: float,  # Kąt nachylenia stycznej w punkcie L
        P: float,  # Początek strefy lądowania
        K: float,  # Punkt konstrukcyjny
        L: float,  # Koniec sterfy lądowania (zazwyczaj HS)
        Zu: float,  # Różnica wysokości między progiem a najniższym punktem zeskoku
        inrun_friction_coefficient: float = 0.02,  # Współczynnik tarcia na najeździe
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
        self.P = P
        self.K = K
        self.L = L
        self.Zu = Zu
        self.inrun_friction_coefficient = inrun_friction_coefficient

        # Oblicz wszystkie atrybuty pochodne
        self.recalculate_derived_attributes()

    def recalculate_derived_attributes(self):
        """Przelicza wszystkie atrybuty pochodne na podstawie wartości bazowych."""
        # Konwersja stopni na radiany
        self.gamma_rad = math.radians(self.gamma_deg)
        self.alpha_rad = math.radians(self.alpha_deg)
        self.betaP_rad = math.radians(self.betaP_deg)
        self.beta_rad = math.radians(self.beta_deg)
        self.betaL_rad = math.radians(self.betaL_deg)

        # Zmienne pomocnicze
        self.es = abs(self.e1 - self.e2)
        self.gate_diff = self.es / (self.gates - 1) if self.gates > 1 else 0.0
        self.r1_min = self.r1 / 2

        # Wartości klotoidy
        self.clothoid_length = 2 * self.r1_min * (abs(self.gamma_rad - self.alpha_rad))
        self.clothoid_parameter = self.r1_min * math.sqrt(
            2 * abs(self.gamma_rad - self.alpha_rad)
        )

        # Współczynniki dla krzywych zeskoku
        self.landing_segment_boundaries = {
            "polynomial1": (0, self.K),
            "parabola2": (self.K, self.L),
        }
        self.calculate_landing_parabola_coefficients()

    def get_inrun_angle(
        self,
        distance_from_takeoff: float,  # Odległość po krzywej od progu (T) w górę rozbiegu
    ) -> float:
        """Funkcja zwracająca kąt nachylenia najazdu w dowolnym jego miejscu"""
        if distance_from_takeoff <= self.t:
            return self.alpha_rad
        elif self.t < distance_from_takeoff < (self.t + self.clothoid_length):
            L_aktualne_na_klotoidzie = (
                self.t + self.clothoid_length
            ) - distance_from_takeoff
            theta_obrotu_rad = (L_aktualne_na_klotoidzie**2) / (
                2 * self.clothoid_parameter**2
            )
            return self.gamma_rad - theta_obrotu_rad
        elif distance_from_takeoff >= (self.t + self.clothoid_length):
            return self.gamma_rad
        else:
            return 0.0

    def calculate_landing_profile(self, v, segment="polynomial1"):
        """Funkcja, która tworzy nasz zeskok"""
        if segment == "polynomial1":
            O_coord_x, O_coord_y = 0.0, -self.s
            K_coord_x, K_coord_y = self.n, -self.h
            slope_K, slope_O = -math.tan(self.beta_rad), 0
            a, b, c, d = v
            R = [0, 0, 0, 0]
            R[0] = a * O_coord_x**3 + b * O_coord_x**2 + c * O_coord_x + d - O_coord_y
            R[1] = a * K_coord_x**3 + b * K_coord_x**2 + c * K_coord_x + d - K_coord_y
            R[2] = 3 * a * K_coord_x**2 + 2 * b * K_coord_x + c - slope_K
            R[3] = 3 * a * O_coord_x**2 + 2 * b * O_coord_x + c - slope_O
            return R
        else:
            K_coord_x, K_coord_y = self.n, -self.h
            U_coord_x = (
                self.n + (self.Zu - self.h) / math.tan(self.betaL_rad)
                if math.tan(self.betaL_rad) != 0
                else self.n
            )
            U_coord_y = -self.Zu
            slope_K = -math.tan(self.beta_rad)
            a, b, c = v
            R = [0, 0, 0]
            R[0] = a * K_coord_x**2 + b * K_coord_x + c - K_coord_y
            R[1] = a * U_coord_x**2 + b * U_coord_x + c - U_coord_y
            R[2] = 2 * a * K_coord_x + b - slope_K
            return R

    def calculate_landing_parabola_coefficients(self):
        """Funkcja, która oblicza współczynniki krzywych, tworzących zeskok"""
        try:
            # Lepsze początkowe przybliżenia dla solvera
            initial_guess1 = np.array([0.001, -0.1, 0.1, -self.s])
            coeffs1 = so.fsolve(
                self.calculate_landing_profile,
                initial_guess1,
                args=("polynomial1",),
                full_output=True,
            )
            if coeffs1[2] == 1:  # Sprawdź czy solver się zbiegł
                self.a_landing1, self.b_landing1, self.c_landing1, self.d_landing1 = (
                    coeffs1[0]
                )
            else:
                # Fallback do prostszego rozwiązania
                self.a_landing1 = 0.001
                self.b_landing1 = -0.1
                self.c_landing1 = 0.1
                self.d_landing1 = -self.s

            initial_guess2 = np.array([0.001, -0.1, -self.h])
            coeffs2 = so.fsolve(
                self.calculate_landing_profile,
                initial_guess2,
                args=("parabola2",),
                full_output=True,
            )
            if coeffs2[2] == 1:  # Sprawdź czy solver się zbiegł
                self.a_landing2, self.b_landing2, self.c_landing2 = coeffs2[0]
            else:
                # Fallback do prostszego rozwiązania
                self.a_landing2 = 0.001
                self.b_landing2 = -0.1
                self.c_landing2 = -self.h

        except Exception as e:
            print(f"Błąd przy obliczaniu profilu zeskoku: {e}")
            # Domyślne wartości bezpieczne
            self.a_landing1 = 0.001
            self.b_landing1 = -0.1
            self.c_landing1 = 0.1
            self.d_landing1 = -self.s
            self.a_landing2 = 0.001
            self.b_landing2 = -0.1
            self.c_landing2 = -self.h

    def y_landing(self, x: float) -> float:
        """Funkcja, która zwraca wysokość zeskoku w danym miejscu"""
        if x <= self.n:
            return (
                self.a_landing1 * x**3
                + self.b_landing1 * x**2
                + self.c_landing1 * x
                + self.d_landing1
            )
        else:
            return self.a_landing2 * x**2 + self.b_landing2 * x + self.c_landing2

    def __str__(self):
        k_point = int(self.K) if self.K == int(self.K) else self.K
        hill_size = int(self.L) if self.L == int(self.L) else self.L
        return f"{self.name} K-{k_point} HS{hill_size}"

    def to_dict(self):
        """Konwertuje obiekt Hill do słownika w celu serializacji do JSON."""
        return {
            "name": self.name,
            "country": self.country,
            "e1": self.e1,
            "e2": self.e2,
            "gates": self.gates,
            "t": self.t,
            "gamma_deg": self.gamma_deg,
            "alpha_deg": self.alpha_deg,
            "r1": self.r1,
            "h": self.h,
            "n": self.n,
            "s": self.s,
            "l1": self.l1,
            "l2": self.l2,
            "a_finish": self.a_finish,
            "betaP_deg": self.betaP_deg,
            "beta_deg": self.beta_deg,
            "betaL_deg": self.betaL_deg,
            "P": self.P,
            "K": self.K,
            "L": self.L,
            "Zu": self.Zu,
            "inrun_friction_coefficient": self.inrun_friction_coefficient,
        }
