"""Single jump page."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ui import ModernComboBox
from ui.widgets.custom_widgets import CustomSpinBox


def create_single_jump_page(main_window):
    """Create the single jump page."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(24)
    layout.setContentsMargins(50, 20, 50, 40)
    layout.addLayout(main_window._create_top_bar("Symulacja skoku", main_window.MAIN_MENU_IDX))

    # Główny layout z podziałem na sekcje
    main_hbox = QHBoxLayout()

    # Lewa sekcja - Konfiguracja skoku
    left_panel = QVBoxLayout()
    left_panel.setSpacing(15)

    # Sekcja wyboru parametrów
    config_group = QGroupBox("Konfiguracja skoku")
    config_group_layout = QVBoxLayout(config_group)
    config_group_layout.setSpacing(10)

    # Wybór zawodnika
    main_window.jumper_combo = ModernComboBox()
    main_window.jumper_combo.addItem("Wybierz zawodnika")
    for jumper in main_window.all_jumpers:
        main_window.jumper_combo.addItem(
            main_window.create_rounded_flag_icon(jumper.nationality), str(jumper)
        )
    main_window.jumper_combo.currentIndexChanged.connect(main_window.update_jumper)
    config_group_layout.addLayout(
        main_window._create_form_row("Zawodnik:", main_window.jumper_combo)
    )

    # Wybór skoczni
    main_window.hill_combo = ModernComboBox()
    main_window.hill_combo.addItem("Wybierz skocznię")
    for hill in main_window.all_hills:
        main_window.hill_combo.addItem(
            main_window.create_rounded_flag_icon(hill.country), str(hill)
        )
    main_window.hill_combo.currentIndexChanged.connect(main_window.update_hill)
    config_group_layout.addLayout(
        main_window._create_form_row("Skocznia:", main_window.hill_combo)
    )

    # Wybór belki
    main_window.gate_spin = CustomSpinBox()
    main_window.gate_spin.setMinimum(1)
    main_window.gate_spin.setMaximum(1)
    config_group_layout.addLayout(main_window._create_form_row("Belka:", main_window.gate_spin))

    # Przyciski akcji
    btn_layout = QHBoxLayout()
    main_window.simulate_button = QPushButton("Uruchom symulację")
    main_window.simulate_button.setProperty("variant", "primary")
    main_window.simulate_button.clicked.connect(main_window.run_simulation)

    main_window.clear_button = QPushButton("Wyczyść")
    main_window.clear_button.clicked.connect(main_window.clear_results)

    btn_layout.addWidget(main_window.simulate_button)
    btn_layout.addWidget(main_window.clear_button)
    config_group_layout.addLayout(btn_layout)

    left_panel.addWidget(config_group)

    # Sekcja statystyk
    stats_group = QGroupBox("Statystyki skoku")
    stats_group_layout = QVBoxLayout(stats_group)
    stats_group_layout.setSpacing(10)

    # Label na statystyki (zamiast QTextEdit)
    main_window.single_jump_stats_label = QLabel(
        "Wybierz zawodnika i skocznię, aby rozpocząć symulację"
    )
    main_window.single_jump_stats_label.setProperty("chip", True)
    main_window.single_jump_stats_label.setProperty("variant", "info")
    main_window.single_jump_stats_label.setStyleSheet("")
    main_window.single_jump_stats_label.setWordWrap(True)
    main_window.single_jump_stats_label.setAlignment(Qt.AlignCenter)
    stats_group_layout.addWidget(main_window.single_jump_stats_label)

    left_panel.addWidget(stats_group)
    left_panel.addStretch()

    main_hbox.addLayout(left_panel, 1)

    # Prawa sekcja - Animacja
    right_panel = QVBoxLayout()
    right_panel.setSpacing(10)

    animation_group = QGroupBox("Animacja trajektorii")
    animation_group_layout = QVBoxLayout(animation_group)

    main_window.figure = Figure(facecolor="#0f1115")
    main_window.canvas = FigureCanvas(main_window.figure)
    animation_group_layout.addWidget(main_window.canvas)

    right_panel.addWidget(animation_group)
    right_panel.addStretch()

    main_hbox.addLayout(right_panel, 2)

    layout.addLayout(main_hbox)
    
    return widget
