"""Judge panel and individual judge classes."""

import random
import math
from src.jumper import Jumper


class Judge:
    """Reprezentuje pojedynczego sędziego"""

    def __init__(self, judge_id: int):
        self.judge_id = judge_id
        self.name = f"Sędzia {judge_id}"

    def score_jump(
        self,
        jumper: Jumper,
        distance: float,
        hill_size: float,
        telemark_landing: bool = False,
        hill=None,
    ) -> float:
        """
        Ocenia skok w skali 14-20 punktów.

        Args:
            jumper: Zawodnik
            distance: Odległość skoku
            hill_size: Rozmiar skoczni (HS)
            telemark_landing: Czy lądowanie telemarkiem

        Returns:
            Nota sędziego (14.0-20.0)
        """
        # Potrzebujemy dostępu do punktu K skoczni
        if hill is not None:
            k_point = hill.K
        else:
            # Fallback - przybliżenie punktu K jako 90% HS
            k_point = hill_size * 0.9

        # Określ położenie względem punktów K i HS
        is_before_k = distance < k_point
        is_at_or_after_k = distance >= k_point
        is_before_hs = distance < hill_size
        is_at_or_after_hs = distance >= hill_size

        if telemark_landing:
            # Z telemarkiem - interpolacja na podstawie statystyki Telemark
            telemark_factor = jumper.telemark / 100.0

            # Bazowa ocena zależna od statystyki Telemark
            # Telemark 0 → 16, Telemark 100 → 17
            base_score = 16.0 + (telemark_factor * 1.0)

            # Bonus za odległość
            if is_before_k:
                # Przed K - bez bonusu
                final_base = base_score
            elif is_at_or_after_k and is_before_hs:
                # Na lub za K, ale przed HS - bonus +1
                final_base = base_score + 1.0
            elif is_at_or_after_hs:
                # Na lub za HS - bonus +2
                final_base = base_score + 2.0
            else:
                final_base = base_score

            # Odchylenie ±1
            score = random.uniform(final_base - 1.0, final_base + 1.0)
        else:
            # Bez telemarku - nie zależy od statystyki Telemark
            if is_before_k:
                # Przed K - bazowa ocena 14
                base_score = 14.0
            elif is_at_or_after_k and is_before_hs:
                # Na lub za K, ale przed HS - bonus +1
                base_score = 15.0
            elif is_at_or_after_hs:
                # Na lub za HS - bonus +2
                base_score = 16.0
            else:
                base_score = 14.0

            # Odchylenie ±1
            score = random.uniform(base_score - 1.0, base_score + 1.0)

        # Ogranicz do zakresu 14-20
        score = max(14.0, min(20.0, score))

        # Zaokrąglij do 0.5
        return round(score * 2) / 2


class JudgePanel:
    """Panel 5 sędziów"""

    def __init__(self):
        self.judges = [Judge(i) for i in range(1, 6)]

    def score_jump(
        self, jumper: Jumper, distance: float, hill_size: float, hill=None
    ) -> dict:
        """
        Ocenia skok przez wszystkich sędziów.

        Returns:
            Dict z notami sędziów i podsumowaniem
        """
        # Nowa logika: losowanie zdarzenia lądowania (upadek / podpórka / ustanie)
        # Bazowe szanse (do HS): upadek 0.6%, podpórka 0.4%
        p_fall_base = 0.006
        p_hand_base = 0.004

        # Skala ryzyka za HS zależna od Stabilności: f(s) = 1.5 - 0.004*s (0→1.5, 50→1.3, 100→1.1)
        steps_05m = 0
        if distance > hill_size:
            steps_05m = int(math.floor(2 * (distance - hill_size)))
        stability_val = getattr(jumper, "stability", 50.0) or 50.0
        factor_per_step = max(1.0, 1.5 - 0.004 * float(stability_val))

        # Odds scaling, by nie przekroczyć 100%
        r_safe = 1.0
        r_fall = (p_fall_base / (1.0 - p_fall_base)) * (factor_per_step**steps_05m)
        r_hand = (p_hand_base / (1.0 - p_hand_base)) * (factor_per_step**steps_05m)
        Z = r_safe + r_fall + r_hand
        p_fall = r_fall / Z
        p_hand = r_hand / Z
        p_safe = r_safe / Z

        # Wybór zdarzenia
        rnd = random.random()
        if rnd < p_fall:
            event = "fall"
        elif rnd < p_fall + p_hand:
            event = "hand"
        else:
            event = "safe"

        judge_scores = []
        if event == "fall":
            # 5 not: 8–12, zaokrąglenie do 0.5
            for _ in range(5):
                val = random.uniform(8.0, 12.0)
                val = round(val * 2) / 2
                judge_scores.append(val)
        elif event == "hand":
            # 5 not: 11–14, zaokrąglenie do 0.5
            for _ in range(5):
                val = random.uniform(11.0, 14.0)
                val = round(val * 2) / 2
                judge_scores.append(val)
        else:
            # SAFE → wyznacz telemark wg dotychczasowej logiki (nie zmieniamy)
            telemark_chance = self._calculate_telemark_chance(
                jumper, distance, hill_size
            )
            telemark_landing = random.random() < telemark_chance
            for judge in self.judges:
                score = judge.score_jump(
                    jumper, distance, hill_size, telemark_landing, hill
                )
                judge_scores.append(score)

        # Usuń najwyższą i najniższą notę
        judge_scores.sort()
        final_scores = judge_scores[1:-1]

        # Suma not (bez najwyższej i najniższej)
        total_judge_score = sum(final_scores)

        return {
            "all_scores": judge_scores,
            "final_scores": final_scores,
            "total_score": total_judge_score,
            "event": event,
            # Jeśli SAFE, dołącz kontekst telemarku (dla spójności UI)
            "telemark_landing": (event == "safe" and telemark_landing)
            if "telemark_landing" in locals()
            else False,
            "telemark_chance": telemark_chance
            if "telemark_chance" in locals()
            else 0.0,
        }

    def _calculate_telemark_chance(
        self, jumper: Jumper, distance: float, hill_size: float
    ) -> float:
        """
        Oblicza szansę na lądowanie telemarkiem.

        Args:
            jumper: Zawodnik
            distance: Odległość skoku
            hill_size: Rozmiar skoczni (HS)

        Returns:
            Szansa na telemark (0.0-1.0)
        """
        # Interpolacja szansy na podstawie telemarku (50%→100%)
        telemark_factor = jumper.telemark / 100.0
        base_chance = 0.50 + (telemark_factor * 0.50)

        # Spadek 2.5 p.p. za każdy pełny 1 m za HS (zgodnie z ustaleniami)
        if distance > hill_size:
            meters_over_hs = max(0.0, distance - hill_size)
            distance_penalty = meters_over_hs * 0.025
            base_chance = max(0.0, base_chance - distance_penalty)

        return base_chance
