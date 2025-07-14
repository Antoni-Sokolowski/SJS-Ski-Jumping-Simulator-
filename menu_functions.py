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

def simulate_jump_menu():
    print("\n---SYMULUJ SKOK---\n")
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
