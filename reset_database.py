#!/usr/bin/env python3
"""
Script to reset the history database for the official release.
This will clear all competition data and reset the auto-increment sequence to start from 1.
"""

import sys
import os

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.history_store import clear_history, init_db

def main():
    print("Resetting history database...")
    
    # Clear all history data and reset sequences
    clear_history()
    
    # Reinitialize the database structure
    init_db()
    
    print("Database reset complete! New records will start from ID 1.")
    print("Ready for official release packaging.")

if __name__ == "__main__":
    main()
