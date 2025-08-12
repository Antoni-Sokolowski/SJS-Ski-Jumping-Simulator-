"""Testy jednostkowe dla systemu punktacji"""

import unittest
from utils.scoring import (
    calculate_jump_points, get_meter_value, round_distance_to_half_meter,
    get_qualification_limit, format_distance_with_unit
)


class TestScoring(unittest.TestCase):
    """Testy dla funkcji obliczania punktów"""
    
    def test_k_point_jump(self):
        """Test skoku na punkt K - powinien dać dokładnie 60 punktów"""
        points = calculate_jump_points(120.0, 120.0)
        self.assertEqual(points, 60.0)
        
    def test_beyond_k_point(self):
        """Test skoku za punkt K"""
        points = calculate_jump_points(125.0, 120.0)
        meter_value = get_meter_value(120.0)
        expected = 60.0 + (5.0 * meter_value)
        self.assertEqual(points, expected)
        
    def test_before_k_point(self):
        """Test skoku przed punktem K"""
        points = calculate_jump_points(115.0, 120.0)
        meter_value = get_meter_value(120.0)
        expected = 60.0 + (-5.0 * meter_value)
        self.assertEqual(points, expected)
        
    def test_meter_values(self):
        """Test wartości metrowych dla różnych punktów K"""
        test_cases = [
            (20, 4.8),   # K <= 24
            (25, 4.4),   # K <= 29
            (30, 4.0),   # K <= 34
            (35, 3.6),   # K <= 39
            (45, 3.2),   # K <= 49
            (55, 2.8),   # K <= 59
            (65, 2.4),   # K <= 69
            (75, 2.2),   # K <= 79
            (90, 2.0),   # K <= 99
            (120, 1.8),  # K <= 169
            (200, 1.2),  # K > 169
        ]
        
        for k_point, expected_value in test_cases:
            with self.subTest(k_point=k_point):
                self.assertEqual(get_meter_value(k_point), expected_value)
                
    def test_round_distance(self):
        """Test zaokrąglania odległości do 0.5m"""
        test_cases = [
            (123.1, 123.0),
            (123.3, 123.5),
            (123.5, 123.5),
            (123.7, 123.5),
            (123.9, 124.0),
            (124.0, 124.0),
        ]
        
        for distance, expected in test_cases:
            with self.subTest(distance=distance):
                self.assertEqual(round_distance_to_half_meter(distance), expected)
                
    def test_qualification_limits(self):
        """Test limitów kwalifikacji"""
        # Normalne skocznie
        self.assertEqual(get_qualification_limit(90), 50)
        self.assertEqual(get_qualification_limit(120), 50)
        self.assertEqual(get_qualification_limit(169), 50)
        
        # Skocznie mamucie
        self.assertEqual(get_qualification_limit(170), 40)
        self.assertEqual(get_qualification_limit(200), 40)
        self.assertEqual(get_qualification_limit(250), 40)
        
    def test_format_distance(self):
        """Test formatowania odległości z jednostką"""
        self.assertEqual(format_distance_with_unit(123.1), "123.0 m")
        self.assertEqual(format_distance_with_unit(123.7), "123.5 m")
        self.assertEqual(format_distance_with_unit(124.0), "124.0 m")


class TestEdgeCases(unittest.TestCase):
    """Testy przypadków brzegowych"""
    
    def test_zero_distance(self):
        """Test skoku o zerowej odległości"""
        points = calculate_jump_points(0.0, 120.0)
        meter_value = get_meter_value(120.0)
        expected = 60.0 + (-120.0 * meter_value)
        self.assertEqual(points, expected)
        
    def test_very_long_jump(self):
        """Test bardzo długiego skoku"""
        points = calculate_jump_points(250.0, 200.0)
        meter_value = get_meter_value(200.0)
        expected = 60.0 + (50.0 * meter_value)
        self.assertEqual(points, expected)
        
    def test_negative_distance(self):
        """Test ujemnej odległości (teoretyczny przypadek)"""
        points = calculate_jump_points(-10.0, 120.0)
        meter_value = get_meter_value(120.0)
        expected = 60.0 + (-130.0 * meter_value)
        self.assertEqual(points, expected)


if __name__ == '__main__':
    unittest.main()