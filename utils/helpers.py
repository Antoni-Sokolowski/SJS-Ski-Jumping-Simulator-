"""Helper functions for the application."""

import os
import sys
import math
from PySide6.QtGui import QPixmap, QPainter, QColor, QPolygon
from PySide6.QtCore import Qt, QPoint
from .calculations import round_distance_to_half_meter
from .constants import GRAVITY, AIR_DENSITY


def calculate_recommended_gate(hill, jumpers):
    """
    Oblicza rekomendowaną belkę na podstawie skoczni i listy zawodników.
    Rekomendowana belka to najwyższa belka, z której żaden skoczek nie skacze powyżej HS.

    Args:
        hill: Obiekt skoczni
        jumpers: Lista zawodników do sprawdzenia

    Returns:
        int: Numer rekomendowanej belki (1-based)
    """
    if not jumpers or not hill:
        return 1

    # Sprawdź każdą belkę od najwyższej do najniższej
    for gate in range(hill.gates, 0, -1):
        max_distance = 0
        safe_gate = True

        # Sprawdź wszystkich zawodników na tej belce
        for jumper in jumpers:
            try:
                from src.simulation import fly_simulation
                distance = fly_simulation(hill, jumper, gate_number=gate)
                max_distance = max(max_distance, distance)

                # Jeśli którykolwiek skoczek przekracza HS, ta belka nie jest bezpieczna
                if distance > hill.L:
                    safe_gate = False
                    break

            except Exception:
                # W przypadku błędu symulacji, uznaj belkę za niebezpieczną
                safe_gate = False
                break

        # Jeśli wszystkie skoki są bezpieczne, to jest rekomendowana belka
        if safe_gate:
            return gate

    # Jeśli żadna belka nie jest bezpieczna, zwróć najniższą
    return 1


def format_distance_with_unit(distance: float) -> str:
    """Formatuje odległość z jednostką, zaokrąglając do 0.5m."""
    rounded_distance = round_distance_to_half_meter(distance)
    return f"{rounded_distance:.1f} m"


def create_arrow_pixmap(direction, color):
    """Tworzy pixmapę ze strzałką (trójkątem) o danym kolorze."""
    pixmap = QPixmap(10, 10)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    if direction == "up":
        points = [QPoint(5, 2), QPoint(2, 7), QPoint(8, 7)]
    else:  # down
        points = [QPoint(5, 8), QPoint(2, 3), QPoint(8, 3)]
    painter.drawPolygon(QPolygon(points))
    painter.end()
    return pixmap


def resource_path(relative_path):
    """
    Zwraca ścieżkę do zasobu, preferując zasoby obok pliku .exe w trybie
    zapakowanym (onefile). Jeśli nie ma zasobu obok .exe, używa rozpakowanych
    plików wewnątrz katalogu tymczasowego (_MEIPASS). W trybie uruchamiania ze
    źródeł zwraca ścieżkę względną do bieżącego katalogu.
    """
    if getattr(sys, "frozen", False):
        # Preferuj zasoby zewnętrzne obok .exe
        external_base = os.path.dirname(sys.executable)
        candidate_external = os.path.join(external_base, relative_path)
        if os.path.exists(candidate_external):
            return candidate_external

        # Fallback: zasoby rozpakowane do katalogu tymczasowego przez PyInstaller
        internal_base = getattr(sys, "_MEIPASS", external_base)
        return os.path.join(internal_base, relative_path)

    # Uruchamianie ze źródeł
    return os.path.join(os.path.abspath("."), relative_path)


# Physics helper functions
def gravity_force(mass):
    """Siła grawitacji (pionowo w dół)"""
    return mass * GRAVITY


def gravity_force_parallel(mass, angle_rad):
    """Siła grawitacji (równolegle do najazdu)"""
    return gravity_force(mass) * math.sin(angle_rad)


def normal_force(mass, angle_rad):
    """Siła nacisku normalnego (prostopadle od najazdu)"""
    return gravity_force(mass) * math.cos(angle_rad)


def drag_force(velocity, drag_coefficient, frontal_area):
    """Siła oporu"""
    return 0.5 * AIR_DENSITY * (velocity ** 2) * drag_coefficient * frontal_area


def friction_force(friction_coefficient, mass, angle_rad):
    """Siła tarcia"""
    return friction_coefficient * normal_force(mass, angle_rad)


def lift_force(velocity, lift_coefficient, frontal_area):
    """Siła nośna"""
    return 0.5 * AIR_DENSITY * (velocity ** 2) * lift_coefficient * frontal_area