"""Jump replay page for showing jump animations from competition results."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from ui.animations import AnimatedStackedWidget


def create_jump_replay_page(main_window):
    """Create the jump replay page."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(6)
    layout.setContentsMargins(15, 8, 15, 15)

    # Top bar with back button
    top_bar_layout = main_window._create_top_bar(
        "Powtórka skoku", main_window.COMPETITION_IDX
    )
    layout.addLayout(top_bar_layout)

    # Title label
    main_window.replay_title_label = QLabel("Imię i nazwisko skoczka")
    main_window.replay_title_label.setProperty("role", "title")
    main_window.replay_title_label.setObjectName("replayTitleLabel")
    main_window.replay_title_label.setAlignment(Qt.AlignCenter)
    main_window.replay_title_label.setSizePolicy(
        QSizePolicy.Preferred, QSizePolicy.Fixed
    )
    main_window.replay_title_label.setMaximumHeight(36)
    layout.addWidget(main_window.replay_title_label)

    # Stats label
    main_window.replay_stats_label = QLabel("Statystyki skoku")
    main_window.replay_stats_label.setProperty("role", "subtitle")
    main_window.replay_stats_label.setObjectName("replayStatsLabel")
    main_window.replay_stats_label.setAlignment(Qt.AlignCenter)
    main_window.replay_stats_label.setSizePolicy(
        QSizePolicy.Preferred, QSizePolicy.Fixed
    )
    main_window.replay_stats_label.setMaximumHeight(26)
    layout.addWidget(main_window.replay_stats_label)

    # Animation canvas
    main_window.replay_figure = Figure(facecolor="#0f1115")
    main_window.replay_canvas = FigureCanvas(main_window.replay_figure)
    main_window.replay_canvas.setSizePolicy(
        QSizePolicy.Expanding, QSizePolicy.Expanding
    )
    layout.addWidget(main_window.replay_canvas)

    # Placeholder for timing chip (created dynamically in _show_jump_replay)
    main_window.replay_timing_chip = None

    return widget
