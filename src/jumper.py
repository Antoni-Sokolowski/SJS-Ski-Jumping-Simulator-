"""Klasa skoczek"""


class Jumper:
    """Wprowadzamy atrybuty skoczka"""

    def __init__(
        self,
        name: str,  # Imię
        last_name: str,  # Nazwisko
        nationality: str = None,  # Narodowość
        mass: float = 60,  # Waga (stała dla wszystkich skoczków)
        height: float = 1.7,  # Wzrost (stały dla wszystkich skoczków)
        # --- NAJAZD ---
        inrun_drag_coefficient: float = 0.46,  # Współczynnik oporu aerodynamicznego zawodnika w pozycji najazdowej
        inrun_frontal_area: float = 0.42,  # Powierzchnia czołowa zawodnika w pozycji najazdowej
        inrun_lift_coefficient: float = 0,  # Współczynnik siły nośnej zawodnika w pozycji najazdowej
        # --- WYBICIE ---
        takeoff_drag_coefficient: float = 1,  # Współczynnik oporu aerodynamicznego zawodnika podczas wybicia
        takeoff_frontal_area: float = 0.8,  # Powierzchnia czołowa zawodnika podczas wybicia
        takeoff_lift_coefficient: float = 0,  # Współczynnik siły nośnej zawodnika podczas wybicia
        jump_force=1500,  # Siła wybicia
        # --- LOT ---
        flight_drag_coefficient: float = 0.5,  # Współczynnik oporu aerodynamicznego zawodnika w locie
        flight_frontal_area: float = 0.5,  # Powierzchnia czołowa zawodnika w locie
        flight_lift_coefficient: float = 0.8,  # Współczynnik siły nośnej zawodnika w locie
        # --- LĄDOWANIE ---
        landing_drag_coefficient: float = 3,  # Współczynnik oporu aerodynamicznego zawodnika podczas lądowania
        landing_frontal_area: float = 1,  # Powierzchnia czołowa zawodnika podczas lądowania
        landing_lift_coefficient: float = 0,  # Współczynnik siły nośnej zawodnika podczas lądowania
        telemark: float = 50,  # Umiejętność lądowania telemarkiem (0-100)
        # --- STATYSTYKI DODATKOWE ---
        timing: float = 50,  # Precyzja timingu wybicia (0-100)
    ):
        self.name = name
        self.last_name = last_name
        self.nationality = nationality
        self.mass = mass
        self.height = height
        self.inrun_drag_coefficient = inrun_drag_coefficient
        self.inrun_frontal_area = inrun_frontal_area
        self.inrun_lift_coefficient = inrun_lift_coefficient
        self.takeoff_drag_coefficient = takeoff_drag_coefficient
        self.takeoff_frontal_area = takeoff_frontal_area
        self.takeoff_lift_coefficient = takeoff_lift_coefficient
        self.jump_force = jump_force
        self.flight_drag_coefficient = flight_drag_coefficient
        self.flight_frontal_area = flight_frontal_area
        self.flight_lift_coefficient = flight_lift_coefficient
        self.landing_drag_coefficient = landing_drag_coefficient
        self.landing_frontal_area = landing_frontal_area
        self.landing_lift_coefficient = landing_lift_coefficient
        self.telemark = telemark
        self.timing = timing

        # Atrybut dla UI - pozycja najazdowa (0-100)
        self.inrun_position = (
            None  # Będzie obliczane na podstawie inrun_drag_coefficient
        )
        # Atrybut dla UI - siła wybicia (0-100)
        self.takeoff_force = None  # Będzie obliczane na podstawie jump_force

        # Atrybuty dla UI - grupa Lot
        self.flight_technique = (
            None  # Będzie obliczane na podstawie flight_lift_coefficient
        )
        self.flight_style = None  # Będzie obliczane na podstawie flight_frontal_area
        self.flight_resistance = (
            None  # Będzie obliczane na podstawie flight_drag_coefficient
        )

    def __str__(self):
        return f"{self.name} {self.last_name}"

    def to_dict(self):
        """Konwertuje obiekt Jumper do słownika w celu serializacji do JSON."""
        return {
            "name": self.name,
            "last_name": self.last_name,
            "nationality": self.nationality,
            "mass": self.mass,
            "height": self.height,
            "inrun_drag_coefficient": self.inrun_drag_coefficient,
            "inrun_frontal_area": self.inrun_frontal_area,
            "inrun_lift_coefficient": self.inrun_lift_coefficient,
            "takeoff_drag_coefficient": self.takeoff_drag_coefficient,
            "takeoff_frontal_area": self.takeoff_frontal_area,
            "takeoff_lift_coefficient": self.takeoff_lift_coefficient,
            "jump_force": self.jump_force,
            "flight_drag_coefficient": self.flight_drag_coefficient,
            "flight_frontal_area": self.flight_frontal_area,
            "flight_lift_coefficient": self.flight_lift_coefficient,
            "landing_drag_coefficient": self.landing_drag_coefficient,
            "landing_frontal_area": self.landing_frontal_area,
            "landing_lift_coefficient": self.landing_lift_coefficient,
            "telemark": self.telemark,
            "timing": self.timing,
        }
