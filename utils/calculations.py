"""Functions for jump calculations and physics conversions."""


def calculate_jump_points(distance: float, k_point: float) -> float:
    """
    Oblicza punkty za skok na podstawie odległości i punktu K.

    Args:
        distance: Odległość skoku w metrach
        k_point: Punkt K skoczni w metrach

    Returns:
        Punkty za skok (60 punktów za skok na K-point, +/- za każdy metr)
    """
    # Oblicz różnicę od K-point
    difference = distance - k_point

    # Określ meter value na podstawie K-point
    meter_value = get_meter_value(k_point)

    # Oblicz punkty: 60 + (różnica * meter_value)
    points = 60.0 + (difference * meter_value)

    return points


def get_meter_value(k_point: float) -> float:
    """Returns the meter value based on the K-point, as per FIS table."""
    if k_point <= 24:
        return 4.8
    elif k_point <= 29:
        return 4.4
    elif k_point <= 34:
        return 4.0
    elif k_point <= 39:
        return 3.6
    elif k_point <= 49:
        return 3.2
    elif k_point <= 59:
        return 2.8
    elif k_point <= 69:
        return 2.4
    elif k_point <= 79:
        return 2.2
    elif k_point <= 99:
        return 2.0
    elif k_point <= 169:
        return 1.8
    else:
        return 1.2


def round_distance_to_half_meter(distance: float) -> float:
    """Rounds distance to the nearest 0.5m precision."""
    return round(distance * 2) / 2


def get_qualification_limit(k_point: float) -> int:
    """
    Określa liczbę zawodników awansujących z kwalifikacji na podstawie typu skoczni.

    Args:
        k_point: Punkt K skoczni w metrach

    Returns:
        int: Liczba zawodników awansujących (40 dla mamucich, 50 dla pozostałych)
    """
    # Skocznie mamucie (K >= 170) mają przelicznik 1.2 i limit 40 zawodników
    if k_point >= 170:
        return 40
    else:
        return 50


def slider_to_drag_coefficient(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na współczynnik oporu aerodynamicznego (0.5-0.38).
    """
    # Mapowanie: 0 -> 0.5, 100 -> 0.38
    return 0.5 - (slider_value / 100.0) * (0.5 - 0.38)


def drag_coefficient_to_slider(drag_coefficient: float) -> int:
    """
    Konwertuje współczynnik oporu aerodynamicznego (0.5-0.38) na wartość slidera (0-100).
    """
    # Mapowanie: 0.5 -> 0, 0.38 -> 100
    if drag_coefficient >= 0.5:
        return 0
    elif drag_coefficient <= 0.38:
        return 100
    else:
        return int(((0.5 - drag_coefficient) / (0.5 - 0.38)) * 100)


def slider_to_jump_force(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na siłę wybicia (1000N-2000N).
    """
    # Mapowanie: 0 -> 1000N, 100 -> 2000N
    return 1000.0 + (slider_value / 100.0) * (2000.0 - 1000.0)


def jump_force_to_slider(jump_force: float) -> int:
    """
    Konwertuje siłę wybicia (1000N-2000N) na wartość slidera (0-100).
    """
    # Mapowanie: 1000N -> 0, 2000N -> 100
    if jump_force <= 1000.0:
        return 0
    elif jump_force >= 2000.0:
        return 100
    else:
        return int(((jump_force - 1000.0) / (2000.0 - 1000.0)) * 100)


def slider_to_lift_coefficient(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na współczynnik siły nośnej (0.5-1.0).
    """
    # Mapowanie: 0 -> 0.5, 100 -> 1.0
    return 0.5 + (slider_value / 100.0) * (1.0 - 0.5)


def lift_coefficient_to_slider(lift_coefficient: float) -> int:
    """
    Konwertuje współczynnik siły nośnej (0.5-1.0) na wartość slidera (0-100).
    """
    # Mapowanie: 0.5 -> 0, 1.0 -> 100
    if lift_coefficient <= 0.5:
        return 0
    elif lift_coefficient >= 1.0:
        return 100
    else:
        return int(((lift_coefficient - 0.5) / (1.0 - 0.5)) * 100)


def slider_to_drag_coefficient_flight(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na współczynnik oporu aerodynamicznego w locie (0.5-0.4).
    """
    # Mapowanie: 0 -> 0.5, 100 -> 0.4
    result = 0.5 - (slider_value / 100.0) * (0.5 - 0.4)
    return result


def drag_coefficient_flight_to_slider(drag_coefficient: float) -> int:
    """
    Konwertuje współczynnik oporu aerodynamicznego w locie (0.5-0.4) na wartość slidera (0-100).
    """
    # Mapowanie: 0.5 -> 0, 0.4 -> 100
    if drag_coefficient >= 0.5:
        return 0
    elif drag_coefficient <= 0.4:
        return 100
    else:
        result = round(((0.5 - drag_coefficient) / (0.5 - 0.4)) * 100)
        return result


def style_to_frontal_area(style: str) -> float:
    """
    Konwertuje styl lotu na powierzchnię czołową.
    """
    style_mapping = {"Normalny": 0.52, "Agresywny": 0.5175, "Pasywny": 0.5225}
    return style_mapping.get(style, 0.52)  # Default to Normalny


def frontal_area_to_style(frontal_area: float) -> str:
    """
    Konwertuje powierzchnię czołową na styl lotu.
    """
    if abs(frontal_area - 0.5175) < 0.002:
        return "Agresywny"
    elif abs(frontal_area - 0.5225) < 0.002:
        return "Pasywny"
    else:
        return "Normalny"


def apply_style_physics(jumper, style: str):
    """
    Aplikuje styl lotu z zrównoważonymi efektami fizycznymi.
    Każdy styl ma małe zmiany (±0.5%) w różnych parametrach.
    """
    if style == "Agresywny":
        # Mniejsza powierzchnia = lepsze wykorzystanie siły nośnej i mniejszy opór
        jumper.flight_frontal_area = 0.5175
        jumper.flight_lift_coefficient *= 1.005  # +0.5% siły nośnej
        jumper.flight_drag_coefficient *= 0.995  # -0.5% oporu

    elif style == "Pasywny":
        # Większa powierzchnia = gorsze wykorzystanie siły nośnej i większy opór
        jumper.flight_frontal_area = 0.5225
        jumper.flight_lift_coefficient *= 0.995  # -0.5% siły nośnej
        jumper.flight_drag_coefficient *= 1.005  # +0.5% oporu

    else:  # Normalny
        # Neutralny styl - bez zmian w innych parametrach
        jumper.flight_frontal_area = 0.52
        # Bez zmian w flight_lift_coefficient i flight_drag_coefficient
