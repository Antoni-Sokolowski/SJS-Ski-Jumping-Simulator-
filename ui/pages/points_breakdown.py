"""Points breakdown page for showing detailed points analysis from competition results."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QGroupBox,
    QHBoxLayout,
)
from PySide6.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


def create_points_breakdown_page(main_window):
    """Create the points breakdown page."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(8)
    layout.setContentsMargins(15, 8, 15, 15)

    # Top bar with back button
    top_bar_layout = main_window._create_top_bar(
        "Podział punktów", main_window.COMPETITION_IDX
    )
    layout.addLayout(top_bar_layout)

    # Hill information at the top
    main_window.points_hill_info_group = QGroupBox("Informacje o skoczni")
    hill_info_layout = QHBoxLayout(main_window.points_hill_info_group)

    main_window.points_hill_name = QLabel("Skocznia: ")
    main_window.points_hill_name.setAlignment(Qt.AlignLeft)
    hill_info_layout.addWidget(main_window.points_hill_name)

    main_window.points_gate_info = QLabel("Belka startowa: ")
    main_window.points_gate_info.setAlignment(Qt.AlignRight)
    hill_info_layout.addWidget(main_window.points_gate_info)

    layout.addWidget(main_window.points_hill_info_group)

    # Title label
    main_window.points_title_label = QLabel("Imię i nazwisko skoczka")
    main_window.points_title_label.setProperty("role", "title")
    main_window.points_title_label.setObjectName("pointsTitleLabel")
    main_window.points_title_label.setAlignment(Qt.AlignCenter)
    main_window.points_title_label.setSizePolicy(
        QSizePolicy.Preferred, QSizePolicy.Fixed
    )
    main_window.points_title_label.setMaximumHeight(36)
    layout.addWidget(main_window.points_title_label)

    # Info label
    main_window.points_info_label = QLabel("Informacje o skoku")
    main_window.points_info_label.setProperty("role", "subtitle")
    main_window.points_info_label.setObjectName("pointsInfoLabel")
    main_window.points_info_label.setAlignment(Qt.AlignCenter)
    main_window.points_info_label.setSizePolicy(
        QSizePolicy.Preferred, QSizePolicy.Fixed
    )
    main_window.points_info_label.setMaximumHeight(26)
    layout.addWidget(main_window.points_info_label)

    # Points breakdown layout (cards will be added here dynamically)
    main_window.points_breakdown_layout = QVBoxLayout()
    layout.addLayout(main_window.points_breakdown_layout)

    # Animation canvas
    main_window.points_figure = Figure(facecolor="#0f1115")
    main_window.points_canvas = FigureCanvas(main_window.points_figure)
    main_window.points_canvas.setSizePolicy(
        QSizePolicy.Expanding, QSizePolicy.Expanding
    )
    layout.addWidget(main_window.points_canvas)

    return widget
