#!/usr/bin/env python3
"""
Kalibrator V2 - Poprawiony kalibrator dla symulatora skoków narciarskich
Zapewnia synchronizację z GUI main.py i optymalizuje parametry skoczków
"""

import json
import math
from tqdm import tqdm
from colorama import init, Fore, Style
from src.simulation import load_data_from_json, fly_simulation

# Inicjalizacja colorama
init(autoreset=True)


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

        # Zapisz oryginalne parametry
        self.original_params = {}
        for jumper in self.jumpers:
            self.original_params[f"{jumper.name} {jumper.last_name}"] = {
                "jump_force": jumper.jump_force,
                "flight_lift_coefficient": jumper.flight_lift_coefficient,
                "flight_drag_coefficient": jumper.flight_drag_coefficient,
                "flight_frontal_area": jumper.flight_frontal_area,
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
        """Optymalizuje parametry Daniela z bardziej realistycznymi limitami"""
        print(f"\n{Fore.YELLOW}Optymalizacja parametrów Daniela...{Style.RESET_ALL}")

        # Oblicz średni błąd
        avg_error = sum(r["error"] for r in results) / len(results)
        print(f"Średni błąd przed optymalizacją: {avg_error:.2f}m")

        # Bardziej realistyczne parametry do optymalizacji
        params_to_optimize = [
            ("jump_force", 1500, 2000, 0.015),  # Mniejszy krok, max 2000
            ("flight_lift_coefficient", 0.8, 1.0, 0.008),  # Mniejszy krok, max 1.0
            ("flight_drag_coefficient", 0.3, 0.8, 0.015),  # Min 0.3, mniejszy krok
            ("flight_frontal_area", 0.3, 0.6, 0.008),  # Mniejszy krok
        ]

        best_error = avg_error
        best_params = {
            "jump_force": self.daniel.jump_force,
            "flight_lift_coefficient": self.daniel.flight_lift_coefficient,
            "flight_drag_coefficient": self.daniel.flight_drag_coefficient,
            "flight_frontal_area": self.daniel.flight_frontal_area,
        }

        # Iteracyjna optymalizacja z mniejszą liczbą iteracji
        for iteration in range(30):
            improved = False

            for param_name, min_val, max_val, step in params_to_optimize:
                current_val = getattr(self.daniel, param_name)

                # Testuj zwiększenie
                new_val = min(max_val, current_val * (1 + step))
                setattr(self.daniel, param_name, new_val)

                test_results = self.test_daniel_on_all_hills()
                test_error = sum(r["error"] for r in test_results) / len(test_results)

                if test_error < best_error:
                    best_error = test_error
                    best_params[param_name] = new_val
                    improved = True
                    print(
                        f"{Fore.GREEN}↑ {param_name}: {current_val:.3f} → {new_val:.3f} (błąd: {test_error:.2f}m){Style.RESET_ALL}"
                    )
                else:
                    # Testuj zmniejszenie
                    new_val = max(min_val, current_val * (1 - step))
                    setattr(self.daniel, param_name, new_val)

                    test_results = self.test_daniel_on_all_hills()
                    test_error = sum(r["error"] for r in test_results) / len(
                        test_results
                    )

                    if test_error < best_error:
                        best_error = test_error
                        best_params[param_name] = new_val
                        improved = True
                        print(
                            f"{Fore.GREEN}↓ {param_name}: {current_val:.3f} → {new_val:.3f} (błąd: {test_error:.2f}m){Style.RESET_ALL}"
                        )
                    else:
                        # Przywróć oryginalną wartość
                        setattr(self.daniel, param_name, current_val)

            if not improved:
                print(
                    f"{Fore.YELLOW}Brak dalszych ulepszeń po {iteration + 1} iteracjach{Style.RESET_ALL}"
                )
                break

        # Zastosuj najlepsze parametry
        for param_name, value in best_params.items():
            setattr(self.daniel, param_name, value)

        print(
            f"\n{Fore.GREEN}Najlepszy średni błąd: {best_error:.2f}m{Style.RESET_ALL}"
        )
        return best_error

    def optimize_hill_friction(self):
        """Inteligentnie optymalizuje tarcie skoczni na podstawie wyników Daniela"""
        print(f"\n{Fore.CYAN}Inteligentna optymalizacja tarcia skoczni...{Style.RESET_ALL}")

        # Testuj Daniela na wszystkich skoczniach
        results = self.test_daniel_on_all_hills()
        current_error = sum(r["error"] for r in results) / len(results)

        # Optymalizuj tarcie dla każdej skoczni osobno
        for hill in tqdm(self.hills, desc="Optymalizacja tarcia"):
            target_gate = self.calculate_target_gate(hill)
            target_distance = self.calculate_target_distance(hill)
            
            # Sprawdź aktualny wynik Daniela na tej skoczni
            current_distance = self.simulate_jump(hill, self.daniel, target_gate)
            current_error = abs(current_distance - target_distance)
            
            # Jeśli błąd jest duży (>5m), dostosuj tarcie
            if current_error > 5:
                original_friction = hill.inrun_friction_coefficient
                best_friction = original_friction
                best_error = current_error
                
                # Sprawdź czy Daniel skacze za krótko czy za daleko
                if current_distance < target_distance:
                    # Skacze za krótko - zmniejsz tarcie
                    friction_tests = [0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10]
                    print(f"{Fore.YELLOW}{hill.name}: Daniel skacze za krótko ({current_distance:.1f}m vs {target_distance}m), zmniejszam tarcie{Style.RESET_ALL}")
                else:
                    # Skacze za daleko - zwiększ tarcie (ale max 0.12)
                    friction_tests = [0.06, 0.08, 0.10, 0.12]
                    print(f"{Fore.YELLOW}{hill.name}: Daniel skacze za daleko ({current_distance:.1f}m vs {target_distance}m), zwiększam tarcie{Style.RESET_ALL}")
                
                # Testuj różne wartości tarcia
                for friction_test in friction_tests:
                    if friction_test > 0.12:  # Limit tarcia
                        continue
                    
                    hill.inrun_friction_coefficient = friction_test
                    
                    # Testuj Daniela na tej skoczni
                    test_distance = self.simulate_jump(hill, self.daniel, target_gate)
                    test_error = abs(test_distance - target_distance)
                    
                    if test_error < best_error:
                        best_error = test_error
                        best_friction = friction_test
                
                # Zastosuj najlepsze tarcie
                hill.inrun_friction_coefficient = best_friction
                
                if best_friction != original_friction:
                    print(f"{Fore.GREEN}  Tarcie: {original_friction:.3f} → {best_friction:.3f} (błąd: {current_error:.1f}m → {best_error:.1f}m){Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}  Tarcie bez zmian: {original_friction:.3f} (błąd: {current_error:.1f}m){Style.RESET_ALL}")

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

        # Oblicz współczynniki zmian dla Daniela
        daniel_ratios = {}
        for param in [
            "jump_force",
            "flight_lift_coefficient",
            "flight_drag_coefficient",
            "flight_frontal_area",
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
            ]:
                original = self.original_params[jumper_name][param]
                ratio = daniel_ratios[param]

                # Zastosuj dokładnie ten sam współczynnik co u Daniela
                new_value = original * ratio

                # Zastosuj realistyczne limity
                if param == "jump_force":
                    new_value = max(1500, min(2000, new_value))
                elif param == "flight_lift_coefficient":
                    new_value = max(0.8, min(1.0, new_value))
                elif param == "flight_drag_coefficient":
                    new_value = max(0.3, min(0.8, new_value))  # Min 0.3
                elif param == "flight_frontal_area":
                    new_value = max(0.3, min(0.6, new_value))

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
                        jumper_data["jump_force"] = jumper.jump_force
                        jumper_data["flight_lift_coefficient"] = (
                            jumper.flight_lift_coefficient
                        )
                        jumper_data["flight_drag_coefficient"] = (
                            jumper.flight_drag_coefficient
                        )
                        jumper_data["flight_frontal_area"] = jumper.flight_frontal_area
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

        # Pokaż parametry Daniela
        print(f"\n{Fore.YELLOW}Parametry Daniela TSCHOFENIG:{Style.RESET_ALL}")
        print(f"jump_force: {self.daniel.jump_force}")
        print(f"flight_lift_coefficient: {self.daniel.flight_lift_coefficient}")
        print(f"flight_drag_coefficient: {self.daniel.flight_drag_coefficient}")
        print(f"flight_frontal_area: {self.daniel.flight_frontal_area}")

        return avg_error

    def run_calibration(self):
        """Uruchamia pełną kalibrację z optymalizacją tarcia"""
        print(
            f"{Fore.CYAN}=== KALIBRATOR V2 - ROZPOCZYNA KALIBRACJĘ ==={Style.RESET_ALL}"
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
