# Ski Jumping Simulator
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)


> An advanced ski jumping simulator with realistic flight physics, a competition mode, and a built-in, fully functional editor for hill and jumper data. This project was written in Python using the PySide6 library to create a modern and intuitive graphical user interface.

---

## 🚀 Getting Started

### 🎮 For Players (Recommended Method)

The easiest way to run the simulator is to download a pre-built version from the **Releases** section.

1.  Navigate to the [**Releases tab**](https://github.com/Antoni-Sokolowski/SJS-Ski-Jumping-Simulator-/releases) on the right side of this page.
2.  Download the asset from the latest release, e.g., `Ski.Jumping.Simulator.v1.3.zip`.
3.  Unzip the archive to any folder on your computer.
4.  Run the `SkiJumpingSimulator.exe` executable. Enjoy!

### 👨‍💻 For Developers (Running from Source)

If you wish to modify the code or run the project directly from the source files, follow these steps:

**Prerequisites:**
* Python 3.8+ installed.

**Installation:**

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/Antoni-Sokolowski/SJS-Ski-Jumping-Simulator-.git](https://github.com/Antoni-Sokolowski/SJS-Ski-Jumping-Simulator-.git)
    cd SJS-Ski-Jumping-Simulator-
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    (Ensure you have a `requirements.txt` file in the project's root directory)
    ```bash
    pip install -r requirements.txt
    ```

**Running the App:**
```bash
python main.py
```

---

## ✨ Key Features

* **Two Simulation Modes:**
    * **Single Jump:** Quickly test any jumper on any hill.
    * **Competition:** A complete two-round competition mode featuring a final round for the top 30 competitors.
* **Realistic Physics:**
    * The simulation accounts for the jumper's mass, inrun friction, takeoff power, as well as lift and drag forces during flight.
    * A **dynamic lift coefficient** adjusts to the takeoff speed, ensuring realistic distances on both small and large hills.
* **Visualization & Replays:**
    * Real-time graphical animation of the jumper's flight trajectory.
    * The ability to watch a replay of any jump from a competition.
* **Advanced Data Editor:**
    * Full editing of **every attribute** for both jumpers and hills.
    * Add new jumpers from scratch and clone existing hills.
    * Delete objects from the database.
    * **User-Friendly Interface:**
        * Logical **grouping of parameters** into sections (e.g., "Flight Physics," "Inrun Geometry").
        * Instant **searching** and **sorting** (alphabetically and by country).
        * Detailed **tooltips** explaining each parameter on hover.
* **Customization:**
    * Ability to change the theme (dark/light), contrast, and volume.
    * Choice of display modes (Windowed, Borderless Fullscreen, Fullscreen).

---

## 🛠️ Technologies Used

* **Python 3**
* **PySide6:** Official Qt for Python bindings for building the GUI.
* **Matplotlib:** For plotting and animating the jump trajectory.
* **NumPy & SciPy:** For numerical calculations in the physics simulation.
* **Pillow (PIL):** For image manipulation (rounded flag icons).

---
## 📸 Screenshots

| Main Menu | Jump Simulation |
| :---: | :---: |
|  |  |
| **Competition** | **Advanced Data Editor** |
|  |  |
---
## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. To do so, please fork the repository and create a pull request. You can also open an issue with the "enhancement" tag to suggest a new feature.

---

## 👨‍💻 Author

* **Antoni Sokołowski**

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE.md` file for details.
