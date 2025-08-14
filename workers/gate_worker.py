"""Worker thread for calculating recommended gate."""

from PySide6.QtCore import QThread, Signal as pyqtSignal
from src.simulation import fly_simulation


class RecommendedGateWorker(QThread):
    """
    Worker thread do obliczania rekomendowanej belki w tle.
    """

    calculation_finished = pyqtSignal(int, float)  # recommended_gate, max_distance

    def __init__(self, hill, jumpers):
        super().__init__()
        self.hill = hill
        self.jumpers = jumpers

    def run(self):
        """
        Wykonuje obliczenia rekomendowanej belki w osobnym wątku.
        """
        if not self.jumpers or not self.hill:
            self.calculation_finished.emit(1, 0.0)
            return

        # Sprawdź każdą belkę od najwyższej do najniższej
        for gate in range(self.hill.gates, 0, -1):
            max_distance = 0
            safe_gate = True

            # Sprawdź wszystkich zawodników na tej belce
            for jumper in self.jumpers:
                try:
                    distance = fly_simulation(self.hill, jumper, gate_number=gate)
                    max_distance = max(max_distance, distance)

                    # Jeśli którykolwiek skoczek przekracza HS, ta belka nie jest bezpieczna
                    if distance > self.hill.L:
                        safe_gate = False
                        break

                except Exception:
                    # W przypadku błędu symulacji, uznaj belkę za niebezpieczną
                    safe_gate = False
                    break

            # Jeśli wszystkie skoki są bezpieczne, to jest rekomendowana belka
            if safe_gate:
                self.calculation_finished.emit(gate, max_distance)
                return

        # Jeśli żadna belka nie jest bezpieczna, zwróć najniższą
        self.calculation_finished.emit(1, 0.0)
