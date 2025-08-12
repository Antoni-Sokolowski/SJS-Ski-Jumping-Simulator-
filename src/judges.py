"""System oceniania skoków przez sędziów"""

import random
from src.jumper import Jumper


class Judge:
    """Reprezentuje pojedynczego sędziego oceniającego skoki"""
    
    def __init__(self, judge_id: int):
        self.id = judge_id
        self.style_preference = random.uniform(0.8, 1.2)
        
    def score_jump(
        self,
        jumper: Jumper,
        distance: float,
        hill_size: float,
        telemark_landing: bool = False,
        hill=None,
    ) -> float:
        """Ocenia skok na podstawie różnych kryteriów"""
        # Bazowa ocena (16.5-19.0)
        base_score = random.uniform(16.5, 19.0)
        
        # Bonus za telemark (0-0.5 pkt)
        telemark_bonus = 0.5 if telemark_landing else 0
        base_score += telemark_bonus * random.uniform(0.7, 1.0)
        
        # Penalty za słaby timing (-0.5 do 0 pkt)
        if hasattr(jumper, 'last_timing_info') and jumper.last_timing_info:
            timing_error = abs(jumper.last_timing_info.get('epsilon_t_s', 0))
            if timing_error > 0.05:
                timing_penalty = min(0.5, timing_error * 5)
                base_score -= timing_penalty * random.uniform(0.5, 1.0)
        
        # Wpływ odległości
        if hill and hill.K:
            relative_distance = (distance - hill.K) / hill.K
            if relative_distance > 0.1:  # Daleko
                base_score += random.uniform(0.1, 0.3)
            elif relative_distance < -0.1:  # Blisko
                base_score -= random.uniform(0.1, 0.3)
        
        # Styl lotu
        if hasattr(jumper, 'flight_style'):
            if jumper.flight_style == "Agresywny":
                base_score += self.style_preference * random.uniform(-0.2, 0.3)
            elif jumper.flight_style == "Pasywny":
                base_score -= random.uniform(0.1, 0.3)
        
        # Ograniczenia
        return max(0.0, min(20.0, round(base_score * 2) / 2))


class JudgePanel:
    """Panel 5 sędziów oceniających skoki"""
    
    def __init__(self):
        self.judges = [Judge(i) for i in range(5)]
        
    def score_jump(
        self, jumper: Jumper, distance: float, hill_size: float, hill=None
    ) -> dict:
        """Zwraca oceny od wszystkich sędziów"""
        # Określ czy było lądowanie telemarkiem
        telemark_landing = self._determine_telemark_landing(jumper, distance, hill_size)
        
        # Zbierz oceny od wszystkich sędziów
        scores = []
        for judge in self.judges:
            score = judge.score_jump(
                jumper, distance, hill_size, telemark_landing, hill
            )
            scores.append(score)
        
        # Sortuj oceny
        scores.sort()
        
        # Usuń najwyższą i najniższą
        valid_scores = scores[1:-1]
        
        # Oblicz sumę punktów
        total = sum(valid_scores)
        
        return {
            "all_scores": scores,
            "valid_scores": valid_scores,
            "removed_scores": [scores[0], scores[-1]],
            "total": total,
            "telemark": telemark_landing,
        }
    
    def _determine_telemark_landing(
        self, jumper: Jumper, distance: float, hill_size: float
    ) -> bool:
        """Określa czy skoczek wylądował telemarkiem"""
        # Bazowa szansa na telemark
        base_chance = jumper.telemark / 100.0
        
        # Modyfikator za odległość (trudniej przy długich skokach)
        distance_ratio = distance / hill_size
        if distance_ratio > 0.95:
            distance_modifier = 0.7
        elif distance_ratio > 0.9:
            distance_modifier = 0.85
        else:
            distance_modifier = 1.0
        
        # Losowanie
        return random.random() < (base_chance * distance_modifier)
    
    def _calculate_telemark_chance(
        self, jumper: Jumper, distance: float, hill_size: float
    ) -> float:
        """Oblicza szansę na lądowanie telemarkiem"""
        base_chance = jumper.telemark / 100.0
        distance_ratio = distance / hill_size
        
        if distance_ratio > 0.95:
            return base_chance * 0.7
        elif distance_ratio > 0.9:
            return base_chance * 0.85
        else:
            return base_chance