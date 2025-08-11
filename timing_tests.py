import statistics
import random

from src.simulation import load_data_from_json, fly_simulation


def run_tests(num_runs_per_level: int = 200):
    hills, jumpers = load_data_from_json()
    assert hills and jumpers, "Brak danych hills/jumpers"

    # Wybierz średnią/dużą skocznię, np. pierwszą z listy
    hill = sorted(hills, key=lambda h: h.L)[0]
    jumper_template = jumpers[0]

    timing_levels = [0, 25, 50, 75, 100]
    results = {}

    # Ustal ziarno losowe dla powtarzalności porównań
    random.seed(12345)

    for timing in timing_levels:
        distances = []
        for _ in range(num_runs_per_level):
            # Skopiuj jumpersa z podmienionym timingiem
            from src.jumper import Jumper

            j = Jumper(
                name=jumper_template.name,
                last_name=jumper_template.last_name,
                nationality=jumper_template.nationality,
                mass=jumper_template.mass,
                height=jumper_template.height,
                inrun_drag_coefficient=jumper_template.inrun_drag_coefficient,
                inrun_frontal_area=jumper_template.inrun_frontal_area,
                inrun_lift_coefficient=jumper_template.inrun_lift_coefficient,
                takeoff_drag_coefficient=jumper_template.takeoff_drag_coefficient,
                takeoff_frontal_area=jumper_template.takeoff_frontal_area,
                takeoff_lift_coefficient=jumper_template.takeoff_lift_coefficient,
                jump_force=jumper_template.jump_force,
                flight_drag_coefficient=jumper_template.flight_drag_coefficient,
                flight_frontal_area=jumper_template.flight_frontal_area,
                flight_lift_coefficient=jumper_template.flight_lift_coefficient,
                landing_drag_coefficient=jumper_template.landing_drag_coefficient,
                landing_frontal_area=jumper_template.landing_frontal_area,
                landing_lift_coefficient=jumper_template.landing_lift_coefficient,
                telemark=jumper_template.telemark,
                timing=timing,
            )

            dist = fly_simulation(hill, j)
            distances.append(dist)

        results[timing] = {
            "mean": statistics.mean(distances),
            "stdev": statistics.pstdev(distances),
            "min": min(distances),
            "max": max(distances),
        }

    return hill, jumper_template, results


if __name__ == "__main__":
    import json

    hill, jumper, results = run_tests()
    lines = []
    lines.append(f"Hill: {hill}")
    lines.append(f"Jumper: {jumper}")
    lines.append("Results (distance in meters):")
    for timing in sorted(results.keys()):
        r = results[timing]
        lines.append(
            f"Timing {timing:3d} -> mean: {r['mean']:.2f} m, stdev: {r['stdev']:.2f}, min: {r['min']:.2f}, max: {r['max']:.2f}"
        )

    # Print to console
    for l in lines:
        print(l)

    # Save to files
    with open("timing_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open("timing_results.json", "w", encoding="utf-8") as f:
        json.dump(
            {"hill": str(hill), "jumper": str(jumper), "results": results},
            f,
            ensure_ascii=False,
            indent=2,
        )
