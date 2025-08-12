"""System obliczania punktów w skokach narciarskich"""


def calculate_jump_points(distance: float, k_point: float) -> float:
    """
    Oblicza punkty za skok na podstawie odległości i punktu K.
    
    Args:
        distance: Odległość skoku w metrach
        k_point: Punkt K skoczni w metrach
        
    Returns:
        Punkty za skok (60 punktów za skok na K-point, +/- za każdy metr)
    """
    difference = distance - k_point
    meter_value = get_meter_value(k_point)
    return 60.0 + (difference * meter_value)


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


def format_distance_with_unit(distance: float) -> str:
    """Formatuje odległość z jednostką, zaokrąglając do 0.5m."""
    rounded_distance = round_distance_to_half_meter(distance)
    return f"{rounded_distance:.1f} m"