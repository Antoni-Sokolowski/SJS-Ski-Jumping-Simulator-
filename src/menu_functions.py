# menu_functions.py

'''Funkcje menu'''

def main_menu():
    print("\n---SKI JUMPING SIMULATOR---\n")
    print("0. Wyjdź")
    print("1. Symuluj skok")
    while True:
        try:
            choice = int(input("Wybierz opcję: "))
            if 0 <= choice <= 1:
                return choice
            else:
                print("Wybierz cyfrę od 0 do 1.")
        except ValueError:
            print("Wybierz cyfrę od 0 do 1.")


def simulate_jump_menu(jumper, hill):
    """Wyświetla menu symulacji, pokazując aktualnie wybrane opcje."""
    print("\n---SYMULUJ SKOK---\n")

    # Dynamicznie pokazuj, co jest wybrane
    jumper_status = str(jumper) if jumper else "Brak"
    hill_status = str(hill) if hill else "Brak"
    print(f"Wybrany zawodnik: {jumper_status}")
    print(f"Wybrana skocznia: {hill_status}\n")

    print("0. Wróć")
    print("1. Wybierz zawodnika")
    print("2. Wybierz skocznię")
    print("3. Uruchom symulację!")
    while True:
        try:
            choice2 = int(input("Wybierz opcję: "))
            if 0 <= choice2 <= 3:
                return choice2
            else:
                print("Wybierz cyfrę od 0 do 3.")
        except ValueError:
            print("Wybierz cyfrę od 0 do 3.")


def select_item_menu(items, title):
    """Uniwersalna funkcja do wyświetlania listy i wyboru elementu."""
    print(f"\n---WYBIERZ {title.upper()}---\n")
    print("0. Wróć")

    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")  # Wykorzystuje metodę __str__ obiektu

    while True:
        try:
            choice = int(input("Wybierz opcję: "))
            if 0 <= choice <= len(items):
                if choice == 0:
                    return None  # Użytkownik wybrał powrót
                return items[choice - 1]  # Zwróć wybrany obiekt
            else:
                print(f"Wybierz cyfrę od 0 do {len(items)}.")
        except ValueError:
            print(f"Wybierz cyfrę od 0 do {len(items)}.")