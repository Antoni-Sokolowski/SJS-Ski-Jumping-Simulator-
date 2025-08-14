"""Main menu page."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QGridLayout
from PySide6.QtCore import Qt


def create_main_menu(main_window):
    """Create the main menu page."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(50, 30, 50, 50)
    layout.setSpacing(24)

    # Hero section
    hero = QVBoxLayout()
    hero.setSpacing(6)

    title = QLabel("Ski Jumping Simulator")
    title.setProperty("class", "headerLabel")
    title.setAlignment(Qt.AlignCenter)
    hero.addWidget(title)

    subtitle = QLabel("Wybierz tryb lub przejdź do edytora danych")
    subtitle.setProperty("role", "subtitle")
    subtitle.setAlignment(Qt.AlignCenter)
    hero.addWidget(subtitle)

    layout.addLayout(hero)

    # Cards grid
    grid_container = QWidget()
    grid = QGridLayout(grid_container)
    grid.setSpacing(16)

    def make_card(text, sub, on_click):
        btn = QPushButton(f"{text}\n{sub}")
        btn.setProperty("class", "cardButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: [main_window.play_sound(), on_click()])
        return btn

    card_single = make_card(
        "Skok",
        "Pojedyncza symulacja",
        lambda: main_window.central_widget.setCurrentIndex(main_window.SINGLE_JUMP_IDX),
    )
    card_comp = make_card(
        "Zawody",
        "Konkurs i kwalifikacje",
        lambda: main_window.central_widget.setCurrentIndex(main_window.COMPETITION_IDX),
    )
    card_editor = make_card(
        "Edytor",
        "Zawodnicy i skocznie",
        lambda: main_window.central_widget.setCurrentIndex(main_window.DATA_EDITOR_IDX),
    )
    card_settings = make_card(
        "Ustawienia",
        "Grafika i dźwięk",
        lambda: main_window.central_widget.setCurrentIndex(main_window.SETTINGS_IDX),
    )

    grid.addWidget(card_single, 0, 0)
    grid.addWidget(card_comp, 0, 1)
    grid.addWidget(card_editor, 1, 0)
    grid.addWidget(card_settings, 1, 1)

    layout.addWidget(grid_container)

    # Minimal – bez dodatkowych przycisków i podpowiedzi
    layout.addStretch(1)

    return widget
