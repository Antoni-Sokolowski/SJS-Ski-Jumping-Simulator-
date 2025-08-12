"""Konwertery parametrów między UI a wartościami fizycznymi"""


def slider_to_drag_coefficient(slider_value: int) -> float:
    """Konwertuje wartość slidera (0-100) na współczynnik oporu aerodynamicznego (0.5-0.38)."""
    return 0.5 - (slider_value / 100.0) * (0.5 - 0.38)


def drag_coefficient_to_slider(drag_coefficient: float) -> int:
    """Konwertuje współczynnik oporu aerodynamicznego (0.5-0.38) na wartość slidera (0-100)."""
    if drag_coefficient >= 0.5:
        return 0
    elif drag_coefficient <= 0.38:
        return 100
    else:
        return int(((0.5 - drag_coefficient) / (0.5 - 0.38)) * 100)


def slider_to_jump_force(slider_value: int) -> float:
    """Konwertuje wartość slidera (0-100) na siłę wybicia (1000N-2000N)."""
    return 1000.0 + (slider_value / 100.0) * (2000.0 - 1000.0)


def jump_force_to_slider(jump_force: float) -> int:
    """Konwertuje siłę wybicia (1000N-2000N) na wartość slidera (0-100)."""
    if jump_force <= 1000.0:
        return 0
    elif jump_force >= 2000.0:
        return 100
    else:
        return int(((jump_force - 1000.0) / (2000.0 - 1000.0)) * 100)


def slider_to_lift_coefficient(slider_value: int) -> float:
    """Konwertuje wartość slidera (0-100) na współczynnik siły nośnej (0.5-1.0)."""
    return 0.5 + (slider_value / 100.0) * (1.0 - 0.5)


def lift_coefficient_to_slider(lift_coefficient: float) -> int:
    """Konwertuje współczynnik siły nośnej (0.5-1.0) na wartość slidera (0-100)."""
    if lift_coefficient <= 0.5:
        return 0
    elif lift_coefficient >= 1.0:
        return 100
    else:
        return int(((lift_coefficient - 0.5) / (1.0 - 0.5)) * 100)


def slider_to_drag_coefficient_flight(slider_value: int) -> float:
    """Konwertuje wartość slidera (0-100) na współczynnik oporu aerodynamicznego w locie (0.5-0.4)."""
    return 0.5 - (slider_value / 100.0) * (0.5 - 0.4)


def drag_coefficient_flight_to_slider(drag_coefficient: float) -> int:
    """Konwertuje współczynnik oporu aerodynamicznego w locie (0.5-0.4) na wartość slidera (0-100)."""
    if drag_coefficient >= 0.5:
        return 0
    elif drag_coefficient <= 0.4:
        return 100
    else:
        return round(((0.5 - drag_coefficient) / (0.5 - 0.4)) * 100)


def style_to_frontal_area(style: str) -> float:
    """Konwertuje styl lotu na powierzchnię czołową."""
    style_mapping = {"Normalny": 0.52, "Agresywny": 0.5175, "Pasywny": 0.5225}
    return style_mapping.get(style, 0.52)


def frontal_area_to_style(frontal_area: float) -> str:
    """Konwertuje powierzchnię czołową na styl lotu."""
    if abs(frontal_area - 0.5175) < 0.002:
        return "Agresywny"
    elif abs(frontal_area - 0.5225) < 0.002:
        return "Pasywny"
    else:
        return "Normalny"


def apply_style_physics(jumper, style: str):
    """Aplikuje styl lotu z zrównoważonymi efektami fizycznymi."""
    if style == "Agresywny":
        jumper.flight_frontal_area = 0.5175
        jumper.flight_lift_coefficient *= 1.005  # +0.5% siły nośnej
        jumper.flight_drag_coefficient *= 0.995  # -0.5% oporu
    elif style == "Pasywny":
        jumper.flight_frontal_area = 0.5225
        jumper.flight_lift_coefficient *= 0.995  # -0.5% siły nośnej
        jumper.flight_drag_coefficient *= 1.005  # +0.5% oporu
    else:  # Normalny
        jumper.flight_frontal_area = 0.52