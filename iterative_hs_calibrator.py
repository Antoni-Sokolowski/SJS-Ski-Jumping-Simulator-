import json
import math
from tqdm import tqdm
from colorama import init, Fore, Back, Style
from src.simulation import load_data_from_json, inrun_simulation, fly_simulation
from src.hill import Hill
from src.jumper import Jumper

# Initialize colorama for Windows compatibility
init()


class IterativeHSCalibrator:
    """Iterative calibrator that optimizes both jumper parameters and hill friction"""

    def __init__(self):
        print(f"{Fore.CYAN}Loading data...{Style.RESET_ALL}")
        self.hills, self.jumpers = load_data_from_json()
        self.daniel = None
        self.other_jumpers = []

        # Find Daniel TSCHOFENIG and separate other jumpers
        for jumper in self.jumpers:
            if jumper.name == "Daniel" and jumper.last_name == "TSCHOFENIG":
                self.daniel = jumper
            else:
                self.other_jumpers.append(jumper)

        if not self.daniel:
            raise ValueError("Daniel TSCHOFENIG not found in jumpers data")

        print(f"{Fore.GREEN}✓ Data loaded successfully{Style.RESET_ALL}")

    def get_45_percent_gate(self, hill):
        """Calculate the gate number that represents 45% of all gates"""
        total_gates = hill.gates
        gate_45_percent = int(total_gates * 0.45)
        return max(1, gate_45_percent)  # Ensure at least gate 1

    def simulate_daniel_jump(self, hill, gate_number):
        """Simulate Daniel's jump from a specific gate"""
        try:
            # Simulate inrun to get takeoff velocity
            takeoff_velocity = inrun_simulation(hill, self.daniel, gate_number, 0.1)

            # Simulate flight to get landing distance
            landing_distance = fly_simulation(hill, self.daniel, gate_number, 0.1)

            return {
                "takeoff_velocity": takeoff_velocity,
                "landing_distance": landing_distance,
                "target_distance": hill.L,  # HS (Hill Size)
                "gate_number": gate_number,
            }
        except Exception as e:
            print(
                f"{Fore.RED}Error simulating jump on {hill.name}: {e}{Style.RESET_ALL}"
            )
            return None

    def calculate_daniel_performance(self):
        """Calculate Daniel's current performance on all hills"""
        results = []

        print(
            f"{Fore.YELLOW}Analyzing Daniel's performance on all hills...{Style.RESET_ALL}"
        )

        # Use tqdm for progress bar
        for hill in tqdm(self.hills, desc="Simulating jumps", unit="hill"):
            gate_45 = self.get_45_percent_gate(hill)
            result = self.simulate_daniel_jump(hill, gate_45)

            if result:
                error = abs(result["landing_distance"] - result["target_distance"])
                results.append(
                    {
                        "hill": hill,
                        "gate_45": gate_45,
                        "current_distance": result["landing_distance"],
                        "target_distance": result["target_distance"],
                        "error": error,
                        "takeoff_velocity": result["takeoff_velocity"],
                    }
                )

        return results

    def optimize_daniel_parameters(self, hill_results, iteration):
        """Optimize Daniel's parameters to hit HS on all hills"""
        print(
            f"{Fore.YELLOW}Iteration {iteration}: Optimizing Daniel's parameters...{Style.RESET_ALL}"
        )

        # Calculate average error
        total_error = sum(result["error"] for result in hill_results)
        avg_error = total_error / len(hill_results)

        print(
            f"{Fore.CYAN}Current average error: {avg_error:.2f} meters{Style.RESET_ALL}"
        )

        # More aggressive parameter adjustment for early iterations
        adjustment_factor = max(
            0.95, 1.0 - (iteration * 0.01)
        )  # Reduce adjustment over iterations

        # Count short and long jumps
        short_jumps = sum(
            1 for r in hill_results if r["current_distance"] < r["target_distance"]
        )
        long_jumps = len(hill_results) - short_jumps

        print(
            f"{Fore.CYAN}Short jumps: {short_jumps}, Long jumps: {long_jumps}{Style.RESET_ALL}"
        )

        # Adjust jump_force (limited to max 1950)
        current_jump_force = self.daniel.jump_force
        if short_jumps > long_jumps:
            new_jump_force = min(
                1950, self.daniel.jump_force * (1.0 + 0.03 * adjustment_factor)
            )
            self.daniel.jump_force = new_jump_force
            print(
                f"{Fore.GREEN}↑ Increasing jump force (jumps too short) - Limited to 1950{Style.RESET_ALL}"
            )
        else:
            new_jump_force = max(
                1500, self.daniel.jump_force * (1.0 - 0.03 * adjustment_factor)
            )
            self.daniel.jump_force = new_jump_force
            print(
                f"{Fore.RED}↓ Decreasing jump force (jumps too long){Style.RESET_ALL}"
            )

        # Adjust flight_lift_coefficient (limited to max 1.0)
        current_lift = self.daniel.flight_lift_coefficient
        if short_jumps > long_jumps:
            new_lift = min(
                1.0,
                self.daniel.flight_lift_coefficient * (1.0 + 0.02 * adjustment_factor),
            )
            self.daniel.flight_lift_coefficient = new_lift
            print(
                f"{Fore.GREEN}↑ Increasing lift coefficient - Limited to 1.0{Style.RESET_ALL}"
            )
        else:
            new_lift = max(
                0.8,
                self.daniel.flight_lift_coefficient * (1.0 - 0.02 * adjustment_factor),
            )
            self.daniel.flight_lift_coefficient = new_lift
            print(f"{Fore.RED}↓ Decreasing lift coefficient{Style.RESET_ALL}")

        # Adjust flight_drag_coefficient (more aggressive adjustments)
        current_drag = self.daniel.flight_drag_coefficient
        if short_jumps > long_jumps:
            # Reduce drag more aggressively for longer jumps
            self.daniel.flight_drag_coefficient *= 1.0 - 0.05 * adjustment_factor
            print(
                f"{Fore.GREEN}↓ Reducing drag coefficient (more aggressive){Style.RESET_ALL}"
            )
        else:
            # Increase drag more aggressively for shorter jumps
            self.daniel.flight_drag_coefficient *= 1.0 + 0.05 * adjustment_factor
            print(
                f"{Fore.RED}↑ Increasing drag coefficient (more aggressive){Style.RESET_ALL}"
            )

        print(f"{Fore.CYAN}Adjusted Daniel's parameters:{Style.RESET_ALL}")
        print(
            f"  {Fore.YELLOW}jump_force:{Style.RESET_ALL} {current_jump_force:.2f} → {self.daniel.jump_force:.2f}"
        )
        print(
            f"  {Fore.YELLOW}flight_lift_coefficient:{Style.RESET_ALL} {current_lift:.3f} → {self.daniel.flight_lift_coefficient:.3f}"
        )
        print(
            f"  {Fore.YELLOW}flight_drag_coefficient:{Style.RESET_ALL} {current_drag:.3f} → {self.daniel.flight_drag_coefficient:.3f}"
        )

    def adjust_hill_friction(self, hill_results, iteration):
        """Adjust hill friction if jumper parameters aren't enough"""
        print(
            f"{Fore.YELLOW}Iteration {iteration}: Adjusting hill friction...{Style.RESET_ALL}"
        )

        # Calculate which hills need adjustment
        hills_to_adjust = []
        for result in hill_results:
            error = result["error"]
            hill = result["hill"]

            # If error is significant (>8m), consider adjusting friction
            if error > 8:
                current_friction = hill.inrun_friction_coefficient

                # Determine if we need to increase or decrease friction
                if result["current_distance"] < result["target_distance"]:
                    # Jump too short - decrease friction to increase speed
                    new_friction = max(0.02, current_friction * 0.97)
                    if new_friction != current_friction:
                        hills_to_adjust.append((hill, new_friction, "decrease"))
                else:
                    # Jump too long - increase friction to decrease speed
                    new_friction = min(0.15, current_friction * 1.03)
                    if new_friction != current_friction:
                        hills_to_adjust.append((hill, new_friction, "increase"))

        if hills_to_adjust:
            print(
                f"{Fore.CYAN}Adjusting friction for {len(hills_to_adjust)} hills:{Style.RESET_ALL}"
            )
            for hill, new_friction, direction in hills_to_adjust:
                old_friction = hill.inrun_friction_coefficient
                hill.inrun_friction_coefficient = new_friction
                print(
                    f"  {Fore.YELLOW}{hill.name}:{Style.RESET_ALL} {old_friction:.3f} → {new_friction:.3f} ({direction})"
                )
        else:
            print(f"{Fore.GREEN}No hill friction adjustments needed{Style.RESET_ALL}")

    def proportionally_adjust_other_jumpers(self):
        """Proportionally adjust drag coefficients for other jumpers to maintain skill differences"""
        print(
            f"{Fore.YELLOW}Proportionally adjusting other jumpers...{Style.RESET_ALL}"
        )

        # Calculate Daniel's current drag coefficient as reference
        daniel_drag = self.daniel.inrun_drag_coefficient

        # Calculate the ratio for each jumper relative to Daniel
        for jumper in tqdm(self.other_jumpers, desc="Adjusting jumpers", unit="jumper"):
            # Calculate the skill ratio (lower drag = better jumper)
            skill_ratio = jumper.inrun_drag_coefficient / daniel_drag

            # Adjust the jumper's drag coefficient proportionally
            # This maintains the relative skill differences
            jumper.inrun_drag_coefficient = daniel_drag * skill_ratio

        print(f"{Fore.GREEN}✓ All jumpers adjusted proportionally{Style.RESET_ALL}")

    def save_updated_data(self):
        """Save the updated jumper and hill data to data.json"""
        print(f"{Fore.YELLOW}Saving updated data...{Style.RESET_ALL}")

        # Load current data
        with open("data/data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # Update jumper data
        for jumper_data in data["jumpers"]:
            for jumper in self.jumpers:
                if (
                    jumper.name == jumper_data["name"]
                    and jumper.last_name == jumper_data["last_name"]
                ):
                    # Update all jumper parameters
                    jumper_data.update(
                        {
                            "inrun_drag_coefficient": jumper.inrun_drag_coefficient,
                            "jump_force": jumper.jump_force,
                            "flight_lift_coefficient": jumper.flight_lift_coefficient,
                            "flight_drag_coefficient": jumper.flight_drag_coefficient,
                        }
                    )
                    break

        # Update hill friction data
        for hill_data in data["hills"]:
            for hill in self.hills:
                if (
                    hill.name == hill_data["name"]
                    and hill.country == hill_data["country"]
                ):
                    hill_data["inrun_friction_coefficient"] = (
                        hill.inrun_friction_coefficient
                    )
                    break

        # Save updated data
        with open("data/data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"{Fore.GREEN}✓ Updated data saved to data.json{Style.RESET_ALL}")

    def run_iterative_calibration(self, max_iterations=200, target_avg_error=3.0):
        """Run iterative calibration process"""
        print(f"{Fore.CYAN}{'=' * 60}")
        print(f"{Fore.CYAN}=== Enhanced Iterative HS Calibrator ===")
        print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
        print(
            f"{Fore.WHITE}Goal: Make Daniel TSCHOFENIG jump HS from 45% gate on every hill{Style.RESET_ALL}"
        )
        print(
            f"{Fore.WHITE}Strategy: Focus on drag coefficient and hill friction, 200 iterations{Style.RESET_ALL}"
        )
        print(
            f"{Fore.WHITE}Limits: jump_force ≤ 1950, flight_lift_coefficient ≤ 1.0{Style.RESET_ALL}"
        )
        print()

        # Step 0: Set initial friction to 0.05 for all hills
        print(
            f"{Fore.CYAN}Step 0: Setting initial friction to 0.05...{Style.RESET_ALL}"
        )
        for hill in self.hills:
            hill.inrun_friction_coefficient = 0.05
        print(
            f"{Fore.GREEN}✓ Initial friction set to 0.05 for all hills{Style.RESET_ALL}"
        )

        best_avg_error = float("inf")
        best_iteration = 0

        for iteration in range(1, max_iterations + 1):
            print(f"\n{Fore.CYAN}{'=' * 40}")
            print(f"{Fore.CYAN}=== ITERATION {iteration}/{max_iterations} ===")
            print(f"{Fore.CYAN}{'=' * 40}{Style.RESET_ALL}")

            # Step 1: Analyze current performance
            hill_results = self.calculate_daniel_performance()

            # Calculate average error
            total_error = sum(result["error"] for result in hill_results)
            avg_error = total_error / len(hill_results)

            print(
                f"\n{Fore.CYAN}Current Daniel TSCHOFENIG performance:{Style.RESET_ALL}"
            )
            print(
                f"{Fore.YELLOW}{'Hill Name'.ljust(20)}{'Gate'.ljust(5)}{'Current'.ljust(8)}{'Target'.ljust(8)}{'Error'.ljust(8)}{Style.RESET_ALL}"
            )
            print(f"{Fore.YELLOW}{'-' * 50}{Style.RESET_ALL}")

            for result in hill_results:
                # Color code the error
                if result["error"] < 3:
                    error_color = Fore.GREEN
                elif result["error"] < 10:
                    error_color = Fore.YELLOW
                else:
                    error_color = Fore.RED

                print(
                    f"{result['hill'].name[:19].ljust(20)} "
                    f"{str(result['gate_45']).ljust(5)} "
                    f"{result['current_distance']:.1f}".ljust(8)
                    + f" {result['target_distance']:.1f}".ljust(8)
                    + f" {error_color}{result['error']:.1f}{Style.RESET_ALL}".ljust(8)
                )

            # Color code the average error
            if avg_error < target_avg_error:
                avg_color = Fore.GREEN
            elif avg_error < target_avg_error * 2:
                avg_color = Fore.YELLOW
            else:
                avg_color = Fore.RED

            print(
                f"\n{Fore.CYAN}Average error: {avg_color}{avg_error:.2f} meters{Style.RESET_ALL}"
            )

            # Check if we've improved
            if avg_error < best_avg_error:
                best_avg_error = avg_error
                best_iteration = iteration
                print(f"{Fore.GREEN}✓ New best average error!{Style.RESET_ALL}")

            # Check if we've reached target
            if avg_error <= target_avg_error:
                print(f"{Fore.GREEN}✓ Target average error reached!{Style.RESET_ALL}")
                break

            # Step 2: Optimize Daniel's parameters
            self.optimize_daniel_parameters(hill_results, iteration)

            # Step 3: Adjust hill friction if needed (every 2nd iteration)
            if iteration % 2 == 0:
                self.adjust_hill_friction(hill_results, iteration)

            # Step 4: Proportionally adjust other jumpers
            self.proportionally_adjust_other_jumpers()

        # Final step: Save updated data
        print(f"\n{Fore.CYAN}Final step: Saving updated data...{Style.RESET_ALL}")
        self.save_updated_data()

        print(f"\n{Fore.GREEN}{'=' * 60}")
        print(
            f"{Fore.GREEN}✓ Enhanced iterative calibration completed!{Style.RESET_ALL}"
        )
        print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
        print(
            f"{Fore.CYAN}Best average error: {best_avg_error:.2f} meters (iteration {best_iteration}){Style.RESET_ALL}"
        )
        print(
            f"{Fore.YELLOW}Note: Enhanced algorithm with 50 iterations and parameter limits.{Style.RESET_ALL}"
        )


if __name__ == "__main__":
    calibrator = IterativeHSCalibrator()
    calibrator.run_iterative_calibration()
