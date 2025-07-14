# main.py

'''Witaj w kodzie projektu SJS'''

import menu_functions as mf

def main_loop():
    while True:
        choice = mf.main_menu()
        if choice == 0:
            break
        elif choice == 1:
            choice2 = mf.simulate_jump_menu()
            if choice2 == 0:
                continue
            elif choice2 == 1:
                pass
            elif choice2 == 2:
                pass
            elif choice2 == 3:
                pass



if __name__ == '__main__':
    print("\n---Witaj w Ski Jumping Simulator!---\n")
    main_loop()