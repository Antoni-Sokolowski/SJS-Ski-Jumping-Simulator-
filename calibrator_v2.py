#!/usr/bin/env python3
"""
Kalibrator V2 - Poprawiony kalibrator dla symulatora skoków narciarskich
Zapewnia synchronizację z GUI main.py i optymalizuje parametry skoczków
ADAPTED FOR NEW SIMPLIFIED PARAMETERS
"""

import json
from tqdm import tqdm
from colorama import init, Fore, Style
from src.simulation import load_data_from_json, fly_simulation

# Inicjalizacja colorama
init(autoreset=True)


# Dodaj funkcje mapowania z main.py
def slider_to_drag_coefficient(slider_value: int) -> float:
    """
    Konwertuje wartość slidera (0-100) na współczynnik oporu aerodynamicznego (0.5-0.38).
    """
    return 0.5 - (slider_value / 100.0) * (0.5 - 0.38)


def drag_coefficient_to_slider(drag_coefficient: float) -> int:
    """
    Konwertuje współczynnik oporu aerodynamicznego (0.5-0.38) na wartość slidera (0-100).
    """
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
    return 1000.0 + (slider_value / 100.0) * (2000.0 - 1000.0)


def jump_force_to_slider(jump_force: float) -> int:
    """
    Konwertuje siłę wybicia (1000N-2000N) na wartość slidera (0-100).
    """
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
    return 0.5 + (slider_value / 100.0) * (1.0 - 0.5)


def lift_coefficient_to_slider(lift_coefficient: float) -> int:
    """
    Konwertuje współczynnik siły nośnej (0.5-1.0) na wartość slidera (0-100).
    """
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
    return 0.5 - (slider_value / 100.0) * (0.5 - 0.4)


def drag_coefficient_flight_to_slider(drag_coefficient: float) -> int:
    """
    Konwertuje współczynnik oporu aerodynamicznego w locie (0.5-0.4) na wartość slidera (0-100).
    """
    if drag_coefficient >= 0.5:
        return 0
    elif drag_coefficient <= 0.4:
        return 100
    else:
        return int(((0.5 - drag_coefficient) / (0.5 - 0.4)) * 100)


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


class CalibratorV2:
    def __init__(self):
        """Inicjalizacja kalibratora"""
        self.hills, self.jumpers = load_data_from_json()

        # Znajdź Daniela TSCHOFENIG
        self.daniel = None
        for jumper in self.jumpers:
            if jumper.name == "Daniel" and jumper.last_name == "TSCHOFENIG":
                self.daniel = jumper
                break

        if not self.daniel:
            raise ValueError("Nie znaleziono Daniela TSCHOFENIG!")

        # Pozostali skoczkowie
        self.other_jumpers = [j for j in self.jumpers if j != self.daniel]

        # Zapisz oryginalne parametry (nowe parametry UI + fizyczne)
        self.original_params = {}
        for jumper in self.jumpers:
            self.original_params[f"{jumper.name} {jumper.last_name}"] = {
                # Parametry fizyczne
                "jump_force": jumper.jump_force,
                "flight_lift_coefficient": jumper.flight_lift_coefficient,
                "flight_drag_coefficient": jumper.flight_drag_coefficient,
                "flight_frontal_area": jumper.flight_frontal_area,
                "inrun_drag_coefficient": jumper.inrun_drag_coefficient,
                # Parametry UI (obliczone)
                "inrun_position": drag_coefficient_to_slider(
                    jumper.inrun_drag_coefficient
                ),
                "takeoff_force": jump_force_to_slider(jumper.jump_force),
                "flight_technique": lift_coefficient_to_slider(
                    jumper.flight_lift_coefficient
                ),
                "flight_style": frontal_area_to_style(jumper.flight_frontal_area),
                "flight_resistance": drag_coefficient_flight_to_slider(
                    jumper.flight_drag_coefficient
                ),
            }

        print(f"{Fore.GREEN}Kalibrator V2 zainicjalizowany{Style.RESET_ALL}")
        print(f"Znaleziono {len(self.hills)} skoczni i {len(self.jumpers)} skoczków")
        print(
            f"Daniel TSCHOFENIG: jump_force={self.daniel.jump_force}, lift={self.daniel.flight_lift_coefficient}"
        )

    def calculate_target_gate(self, hill):
        """Oblicza numer belki stanowiącej 45% wszystkich dostępnych"""
        return max(1, int(hill.gates * 0.45))

    def calculate_target_distance(self, hill):
        """Oblicza docelową odległość (HS)"""
        return hill.L

    def simulate_jump(self, hill, jumper, gate_number):
        """Symuluje skok i zwraca odległość"""
        try:
            distance = fly_simulation(hill, jumper, gate_number=gate_number)
            return distance
        except Exception as e:
            print(f"{Fore.RED}Błąd symulacji: {e}{Style.RESET_ALL}")
            return 0

    def test_daniel_on_all_hills(self):
        """Testuje Daniela na wszystkich skoczniach"""
        results = []

        print(
            f"\n{Fore.CYAN}Testowanie Daniela na wszystkich skoczniach...{Style.RESET_ALL}"
        )

        for hill in tqdm(self.hills, desc="Testowanie skoczni"):
            target_gate = self.calculate_target_gate(hill)
            target_distance = self.calculate_target_distance(hill)

            distance = self.simulate_jump(hill, self.daniel, target_gate)
            error = abs(distance - target_distance)

            results.append(
                {
                    "hill": hill,
                    "target_gate": target_gate,
                    "target_distance": target_distance,
                    "actual_distance": distance,
                    "error": error,
                }
            )

        return results

    def optimize_daniel_parameters(self, results):
        """Optymalizuje parametry Daniela z nowymi parametrami UI"""
        print(
            f"\n{Fore.YELLOW}Optymalizacja parametrów Daniela (nowe parametry UI)...{Style.RESET_ALL}"
        )

        # Oblicz średni błąd
        avg_error = sum(r["error"] for r in results) / len(results)
        print(f"Średni błąd przed optymalizacją: {avg_error:.2f}m")

        # Nowe parametry do optymalizacji (UI-friendly)
        slider_params = [
            ("inrun_position", 0, 100, 5),  # Slider 0-100, krok 5
            ("takeoff_force", 0, 100, 5),  # Slider 0-100, krok 5
            ("flight_technique", 0, 100, 5),  # Slider 0-100, krok 5
            ("flight_resistance", 0, 100, 5),  # Slider 0-100, krok 5
        ]
        dropdown_params = [
            ("flight_style", ["Normalny", "Agresywny", "Pasywny"]),  # Dropdown
        ]

        best_error = avg_error
        best_params = {
            "inrun_position": drag_coefficient_to_slider(
                self.daniel.inrun_drag_coefficient
            ),
            "takeoff_force": jump_force_to_slider(self.daniel.jump_force),
            "flight_technique": lift_coefficient_to_slider(
                self.daniel.flight_lift_coefficient
            ),
            "flight_resistance": drag_coefficient_flight_to_slider(
                self.daniel.flight_drag_coefficient
            ),
            "flight_style": frontal_area_to_style(self.daniel.flight_frontal_area),
        }

        # Iteracyjna optymalizacja
        for iteration in range(20):  # Zmniejszona liczba iteracji
            improved = False

            # Optymalizuj parametry slider
            for param_name, min_val, max_val, step in slider_params:
                current_val = best_params[param_name]

                # Testuj zwiększenie
                new_val = min(max_val, current_val + step)
                self._apply_ui_param_to_jumper(param_name, new_val)

                test_results = self.test_daniel_on_all_hills()
                test_error = sum(r["error"] for r in test_results) / len(test_results)

                if test_error < best_error:
                    best_error = test_error
                    best_params[param_name] = new_val
                    improved = True
                    print(
                        f"{Fore.GREEN}↑ {param_name}: {current_val} → {new_val} (błąd: {test_error:.2f}m){Style.RESET_ALL}"
                    )
                else:
                    # Testuj zmniejszenie
                    new_val = max(min_val, current_val - step)
                    self._apply_ui_param_to_jumper(param_name, new_val)

                    test_results = self.test_daniel_on_all_hills()
                    test_error = sum(r["error"] for r in test_results) / len(
                        test_results
                    )

                    if test_error < best_error:
                        best_error = test_error
                        best_params[param_name] = new_val
                        improved = True
                        print(
                            f"{Fore.GREEN}↓ {param_name}: {current_val} → {new_val} (błąd: {test_error:.2f}m){Style.RESET_ALL}"
                        )
                    else:
                        # Przywróć oryginalną wartość
                        self._apply_ui_param_to_jumper(param_name, current_val)

            # Optymalizuj parametry dropdown
            for param_name, options in dropdown_params:
                current_style = frontal_area_to_style(self.daniel.flight_frontal_area)
                current_index = ["Normalny", "Agresywny", "Pasywny"].index(
                    current_style
                )

                # Testuj inne style
                for test_index in range(3):
                    if test_index != current_index:
                        test_style = ["Normalny", "Agresywny", "Pasywny"][test_index]

                        # Zapisz oryginalne wartości
                        original_frontal_area = self.daniel.flight_frontal_area
                        original_lift = self.daniel.flight_lift_coefficient
                        original_drag = self.daniel.flight_drag_coefficient

                        # Aplikuj styl z balansowanymi efektami
                        apply_style_physics(self.daniel, test_style)

                        test_results = self.test_daniel_on_all_hills()
                        test_error = sum(r["error"] for r in test_results) / len(
                            test_results
                        )

                        if test_error < best_error:
                            best_error = test_error
                            best_params[param_name] = test_style
                            improved = True
                            print(
                                f"{Fore.GREEN}↔ {param_name}: {current_style} → {test_style} (błąd: {test_error:.2f}m){Style.RESET_ALL}"
                            )
                        else:
                            # Przywróć oryginalne wartości
                            self.daniel.flight_frontal_area = original_frontal_area
                            self.daniel.flight_lift_coefficient = original_lift
                            self.daniel.flight_drag_coefficient = original_drag

            if not improved:
                print(
                    f"{Fore.YELLOW}Brak dalszych ulepszeń po {iteration + 1} iteracjach{Style.RESET_ALL}"
                )
                break

        # Zastosuj najlepsze parametry
        for param_name, value in best_params.items():
            self._apply_ui_param_to_jumper(param_name, value)

        print(
            f"\n{Fore.GREEN}Najlepszy średni błąd: {best_error:.2f}m{Style.RESET_ALL}"
        )
        return best_error

    def _apply_ui_param_to_jumper(self, param_name, value):
        """Aplikuje parametr UI do skoczka (konwertuje na fizyczny parametr)"""
        if param_name == "inrun_position":
            self.daniel.inrun_drag_coefficient = slider_to_drag_coefficient(value)
        elif param_name == "takeoff_force":
            self.daniel.jump_force = slider_to_jump_force(value)
        elif param_name == "flight_technique":
            self.daniel.flight_lift_coefficient = slider_to_lift_coefficient(value)
        elif param_name == "flight_resistance":
            self.daniel.flight_drag_coefficient = slider_to_drag_coefficient_flight(
                value
            )
        elif param_name == "flight_style":
            # Aplikuj styl z balansowanymi efektami
            apply_style_physics(self.daniel, value)

    def optimize_hill_friction(self):
        """Optymalizuje tarcie skoczni aby błąd był jak najbliżej 0"""
        print(
            f"\n{Fore.CYAN}Optymalizacja tarcia skoczni - dążenie do błędu 0...{Style.RESET_ALL}"
        )

        # Optymalizuj tarcie dla każdej skoczni osobno
        for hill in tqdm(self.hills, desc="Optymalizacja tarcia"):
            target_gate = self.calculate_target_gate(hill)
            target_distance = self.calculate_target_distance(hill)

            # Sprawdź aktualny wynik Daniela na tej skoczni
            current_distance = self.simulate_jump(hill, self.daniel, target_gate)
            current_error = abs(current_distance - target_distance)

            original_friction = hill.inrun_friction_coefficient
            best_friction = original_friction
            best_error = current_error

            # Testuj wszystkie możliwe wartości tarcia
            all_friction_tests = [
                0.0,
                0.01,
                0.02,
                0.03,
                0.04,
                0.05,
                0.06,
                0.07,
                0.08,
                0.09,
                0.10,
                0.11,
                0.12,
            ]

            print(
                f"{Fore.YELLOW}{hill.name} (HS{hill.L}): Daniel skacze {current_distance:.1f}m vs {target_distance}m (błąd: {current_error:.1f}m){Style.RESET_ALL}"
            )

            # Testuj wszystkie wartości tarcia i znajdź najlepszą
            for friction_test in all_friction_tests:
                try:
                    hill.inrun_friction_coefficient = friction_test

                    # Testuj Daniela na tej skoczni
                    test_distance = self.simulate_jump(hill, self.daniel, target_gate)
                    test_error = abs(test_distance - target_distance)

                    if test_error < best_error:
                        best_error = test_error
                        best_friction = friction_test
                except Exception as e:
                    print(
                        f"{Fore.RED}Błąd przy tarcia {friction_test}: {e}{Style.RESET_ALL}"
                    )
                    continue

            # Zastosuj najlepsze tarcie
            hill.inrun_friction_coefficient = best_friction

            if best_friction != original_friction:
                print(
                    f"{Fore.GREEN}  Tarcie: {original_friction:.3f} → {best_friction:.3f} (błąd: {current_error:.1f}m → {best_error:.1f}m){Style.RESET_ALL}"
                )
            else:
                print(
                    f"{Fore.CYAN}  Tarcie bez zmian: {original_friction:.3f} (błąd: {current_error:.1f}m){Style.RESET_ALL}"
                )

        # Sprawdź końcowy błąd
        final_results = self.test_daniel_on_all_hills()
        final_error = sum(r["error"] for r in final_results) / len(final_results)

        print(
            f"{Fore.GREEN}Końcowy błąd po optymalizacji tarcia: {final_error:.2f}m{Style.RESET_ALL}"
        )
        return final_error

    def proportionally_adjust_other_jumpers(self):
        """Proporcjonalnie dostosowuje parametry pozostałych skoczków"""
        print(
            f"\n{Fore.CYAN}Dostosowywanie parametrów pozostałych skoczków...{Style.RESET_ALL}"
        )

        # Oblicz współczynniki zmian dla Daniela (parametry fizyczne)
        daniel_ratios = {}
        for param in [
            "jump_force",
            "flight_lift_coefficient",
            "flight_drag_coefficient",
            "flight_frontal_area",
            "inrun_drag_coefficient",
        ]:
            original = self.original_params[
                f"{self.daniel.name} {self.daniel.last_name}"
            ][param]
            current = getattr(self.daniel, param)
            daniel_ratios[param] = current / original

        print(f"{Fore.YELLOW}Współczynniki zmian Daniela:{Style.RESET_ALL}")
        for param, ratio in daniel_ratios.items():
            percent_change = (ratio - 1) * 100
            print(f"  {param}: {ratio:.3f} ({percent_change:+.1f}%)")

        # Dostosuj pozostałych skoczków
        for jumper in tqdm(self.other_jumpers, desc="Dostosowywanie skoczków"):
            jumper_name = f"{jumper.name} {jumper.last_name}"

            for param in [
                "jump_force",
                "flight_lift_coefficient",
                "flight_drag_coefficient",
                "flight_frontal_area",
                "inrun_drag_coefficient",
            ]:
                original = self.original_params[jumper_name][param]
                ratio = daniel_ratios[param]

                # Zastosuj dokładnie ten sam współczynnik co u Daniela
                new_value = original * ratio

                # Zastosuj realistyczne limity
                if param == "jump_force":
                    new_value = max(1000, min(2000, new_value))
                elif param == "flight_lift_coefficient":
                    new_value = max(0.5, min(1.0, new_value))
                elif param == "flight_drag_coefficient":
                    new_value = max(0.4, min(0.5, new_value))
                elif param == "flight_frontal_area":
                    new_value = max(0.5175, min(0.5225, new_value))
                elif param == "inrun_drag_coefficient":
                    new_value = max(0.38, min(0.5, new_value))

                setattr(jumper, param, new_value)

        print(
            f"{Fore.GREEN}✓ Wszyscy skoczkowie zostali dostosowani proporcjonalnie{Style.RESET_ALL}"
        )

    def save_to_data_json(self):
        """Zapisuje zmiany do data.json"""
        print(f"\n{Fore.YELLOW}Zapisywanie zmian do data.json...{Style.RESET_ALL}")

        try:
            # Wczytaj aktualny plik
            with open("data/data.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            # Zaktualizuj dane skoczków
            for jumper_data in data["jumpers"]:
                jumper_name = f"{jumper_data['name']} {jumper_data['last_name']}"

                # Znajdź odpowiadający obiekt Jumper
                for jumper in self.jumpers:
                    if f"{jumper.name} {jumper.last_name}" == jumper_name:
                        # Zaktualizuj parametry fizyczne
                        jumper_data["jump_force"] = jumper.jump_force
                        jumper_data["flight_lift_coefficient"] = (
                            jumper.flight_lift_coefficient
                        )
                        jumper_data["flight_drag_coefficient"] = (
                            jumper.flight_drag_coefficient
                        )
                        jumper_data["flight_frontal_area"] = jumper.flight_frontal_area
                        jumper_data["inrun_drag_coefficient"] = (
                            jumper.inrun_drag_coefficient
                        )

                        # Ustaw stałe wartości
                        jumper_data["mass"] = 60
                        jumper_data["height"] = 1.7
                        break

            # Zaktualizuj tarcie skoczni
            for hill_data in data["hills"]:
                for hill in self.hills:
                    if (
                        hill_data["name"] == hill.name
                        and hill_data["country"] == hill.country
                        and hill_data["K"] == hill.K
                    ):
                        hill_data["inrun_friction_coefficient"] = (
                            hill.inrun_friction_coefficient
                        )
                        break

            # Zapisz z powrotem
            with open("data/data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(
                f"{Fore.GREEN}✓ Zmiany zostały zapisane do data.json{Style.RESET_ALL}"
            )

        except Exception as e:
            print(f"{Fore.RED}✗ Błąd podczas zapisywania: {e}{Style.RESET_ALL}")
            return False

        return True

    def show_final_results(self):
        """Pokazuje końcowe wyniki kalibracji"""
        print(f"\n{Fore.CYAN}=== KOŃCOWE WYNIKI KALIBRACJI ==={Style.RESET_ALL}")

        # Testuj Daniela na wszystkich skoczniach
        final_results = self.test_daniel_on_all_hills()

        print(f"\n{Fore.YELLOW}Wyniki Daniela TSCHOFENIG:{Style.RESET_ALL}")
        total_error = 0

        for result in final_results:
            hill = result["hill"]
            target_gate = result["target_gate"]
            target_distance = result["target_distance"]
            actual_distance = result["actual_distance"]
            error = result["error"]

            total_error += error

            status = (
                f"{Fore.GREEN}✓"
                if error < 5
                else f"{Fore.YELLOW}~"
                if error < 10
                else f"{Fore.RED}✗"
            )

            print(
                f"{status} {hill.name}: belka {target_gate}, cel {target_distance}m, "
                f"skok {actual_distance:.1f}m, błąd {error:.1f}m"
            )

        avg_error = total_error / len(final_results)
        print(f"\n{Fore.CYAN}Średni błąd: {avg_error:.2f}m{Style.RESET_ALL}")

        # Pokaż parametry Daniela (UI + fizyczne)
        print(f"\n{Fore.YELLOW}Parametry Daniela TSCHOFENIG:{Style.RESET_ALL}")
        print(f"Fizyczne parametry:")
        print(f"  jump_force: {self.daniel.jump_force:.1f}N")
        print(f"  flight_lift_coefficient: {self.daniel.flight_lift_coefficient:.3f}")
        print(f"  flight_drag_coefficient: {self.daniel.flight_drag_coefficient:.3f}")
        print(f"  flight_frontal_area: {self.daniel.flight_frontal_area:.3f}")
        print(f"  inrun_drag_coefficient: {self.daniel.inrun_drag_coefficient:.3f}")

        print(f"\nParametry UI:")
        print(
            f"  Pozycja najazdowa: {drag_coefficient_to_slider(self.daniel.inrun_drag_coefficient)}"
        )
        print(f"  Siła wybicia: {jump_force_to_slider(self.daniel.jump_force)}")
        print(
            f"  Technika lotu: {lift_coefficient_to_slider(self.daniel.flight_lift_coefficient)}"
        )
        print(f"  Styl lotu: {frontal_area_to_style(self.daniel.flight_frontal_area)}")
        print(
            f"  Opór powietrza: {drag_coefficient_flight_to_slider(self.daniel.flight_drag_coefficient)}"
        )

        return avg_error

    def run_calibration(self):
        """Uruchamia pełną kalibrację z optymalizacją tarcia"""
        print(
            f"{Fore.CYAN}=== KALIBRATOR V2 - ROZPOCZYNA KALIBRACJĘ (NOWE PARAMETRY) ==={Style.RESET_ALL}"
        )

        # Test początkowy
        initial_results = self.test_daniel_on_all_hills()
        initial_error = sum(r["error"] for r in initial_results) / len(initial_results)
        print(
            f"\n{Fore.YELLOW}Początkowy średni błąd: {initial_error:.2f}m{Style.RESET_ALL}"
        )

        # Optymalizuj Daniela
        daniel_error = self.optimize_daniel_parameters(initial_results)

        # Optymalizuj tarcie skoczni
        friction_error = self.optimize_hill_friction()

        # Dostosuj pozostałych skoczków
        self.proportionally_adjust_other_jumpers()

        # Pokaż końcowe wyniki
        self.show_final_results()

        # Zapisz zmiany
        if self.save_to_data_json():
            print(
                f"\n{Fore.GREEN}=== KALIBRACJA ZAKOŃCZONA POMYŚLNIE ==={Style.RESET_ALL}"
            )
            print(f"Zmiany zostały zapisane do data.json")
            print(f"Możesz teraz uruchomić main.py i sprawdzić wyniki w zawodach")
        else:
            print(f"\n{Fore.RED}=== BŁĄD PODCZAS ZAPISYWANIA ==={Style.RESET_ALL}")


def main():
    """Główna funkcja"""
    try:
        calibrator = CalibratorV2()

        print(f"\n{Fore.CYAN}Wybierz opcję:{Style.RESET_ALL}")
        print("1. Uruchom kalibrację")
        print("2. Wyjdź")

        choice = input("\nTwój wybór (1-2): ").strip()

        if choice == "1":
            calibrator.run_calibration()
        elif choice == "2":
            print(f"{Fore.YELLOW}Do widzenia!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Nieprawidłowy wybór{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}Błąd: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
