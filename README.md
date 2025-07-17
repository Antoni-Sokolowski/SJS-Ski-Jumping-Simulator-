# SJS (Ski Jumping Simulator)

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

SJS is an advanced ski jumping simulator written in Python, utilizing a physics-based model to realistically represent the dynamics of a ski jumper's flight. The application features a graphical user interface built with the PySide6 (Qt for Python) library.

The simulation's data (jumpers and hills) is loaded from an external `data.json` file, allowing users to easily customize and add their own content.

![SJS Screenshot](.Images/Simulation_overview.png)

---

## Key Features

* **Two Simulation Modes:**
    * **Single Jump:** Analyze a single jump by a selected athlete on a chosen hill.
    * **Competition:** Run a full, two-round competition for a group of selected jumpers, with results updated in real-time.
* **2D Flight Visualization:** A real-time graphical representation of the jump trajectory, created using `matplotlib`.
* **External & Editable Data:** The application loads all jumper and hill data from an external `data/data.json` file. Users can easily add, remove, or edit entries.
* **Customizable UI:** Users can choose between light and dark themes and adjust the interface contrast and volume.
* **Interactive Options:** Ability to select the start gate, dynamically sort the jumper list by name or country, and view distance-based results.

---

## Technology Stack

* **Language:** Python 3
* **GUI Framework:** PySide6 (Qt for Python)
* **Data Visualization:** Matplotlib
* **Numerical Computing:** NumPy
* **Scientific Computing:** SciPy
* **Image Manipulation:** Pillow (for creating rounded flag icons)
* **Packaging:** PyInstaller

---

## Installation and Usage

There are two ways to run the simulator.

### 1. For Users (Recommended)

This method is the easiest and does not require a Python installation.

1.  Navigate to the **[Releases](https://github.com/Antoni-Sokolowski/SJS_Simulator/releases)** section of this repository.
2.  Download the latest `.zip` package (e.g., `SJS_Simulator_v1.0.zip`).
3.  Unzip the package to a location on your computer.
4.  Run the application by double-clicking the `SJS_Simulator.exe` file.

**Important:** The `.exe` file must be in the **same folder** as the `data` directory to function correctly.

### 2. For Developers (From Source Code)

This method allows you to view and modify the code.

**Prerequisites:**
* Python 3.8+
* Git

**Steps:**

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/SJS_Simulator.git](https://github.com/YOUR_USERNAME/SJS_Simulator.git)
    cd SJS_Simulator
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate
    ```

3.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python main.py
    ```

---

## Customization (Adding Jumpers & Hills)

You can easily add your own jumpers and hills by editing the `data/data.json` file. I'll show you how to do it below.

**Jumpers**


---

## Building from Source

This project uses a `.spec` file for reliable builds with PyInstaller.

1.  Make sure all dependencies from `requirements.txt` are installed.
2.  Run the following command from the project's root directory:
    ```bash
    pyinstaller main.spec
    ```
3.  The final executable will be located in the `dist` folder. Remember to package it with the `data` folder for distribution.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
