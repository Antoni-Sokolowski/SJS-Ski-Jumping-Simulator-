"""Główny plik uruchamiający aplikację symulatora skoków narciarskich."""

import sys
import os

# Add the project root to Python path to ensure modules can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the main function from the modular structure
from core.app import main

if __name__ == "__main__":
    main()
