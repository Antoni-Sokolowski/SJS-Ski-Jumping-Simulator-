# main.py

'''Witaj w kodzie projektu SJS'''

import menu_functions as mf
from physics.simulation import *


def main_loop():
    # Wczytaj dane raz, na początku programu
    all_hills, all_jumpers = load_data_from_json()
    selected_jumper = None
    selected_hill = None

    while True:
        choice = mf.main_menu()
        if choice == 0:
            break
        elif choice == 1:
            while True:
                # Przekazuj aktualnie wybrane obiekty do menu
                choice2 = mf.simulate_jump_menu(selected_jumper, selected_hill)

                if choice2 == 0:
                    break  # Wróć do menu głównego

                elif choice2 == 1:
                    # Pozwól użytkownikowi wybrać zawodnika z listy
                    chosen_jumper = mf.select_item_menu(all_jumpers, "zawodnika")
                    if chosen_jumper:
                        selected_jumper = chosen_jumper
                        print(f"\nWybrano: {selected_jumper}")

                elif choice2 == 2:
                    # Pozwól użytkownikowi wybrać skocznię z listy
                    chosen_hill = mf.select_item_menu(all_hills, "skocznię")
                    if chosen_hill:
                        selected_hill = chosen_hill
                        print(f"\nWybrano: {selected_hill}")

                elif choice2 == 3:
                    # Uruchom symulację tylko jeśli wszystko jest wybrane
                    if selected_jumper and selected_hill:
                        while True:
                            try:
                                prompt = f"Podaj belkę startową w zakresie 1-{selected_hill.gates}: "
                                chosen_gate = int(input(prompt))
                                if chosen_gate in range(1, selected_hill.gates + 1):
                                    break
                                else:
                                    print("Musisz wybrać belkę z podanego zakresu")
                            except ValueError:
                                print("Musisz wybrać belkę z podanego zakresu")
                        print("\n---URUCHAMIANIE SYMULACJI---")

                        inrun_velocity = inrun_simulation(selected_hill, selected_jumper, gate_number=chosen_gate)
                        distance = fly_simulation(selected_hill, selected_jumper, chosen_gate)

                        print(f"Prędkość na progu: {round(3.6*inrun_velocity, 2)}km/h")
                        print(f"Odległość: {distance:.2f}m")

                        plot_flight_trajectory(selected_hill, selected_jumper, chosen_gate)
                    else:
                        print("\nBŁĄD: Musisz najpierw wybrać zawodnika i skocznię!")


if __name__ == '__main__':
    print("\n---Witaj w Ski Jumping Simulator!---")
    main_loop()