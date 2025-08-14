"""Settings page."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from ui import ModernComboBox, ModernSlider


def create_settings_page(main_window):
    """Create the settings page."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(40)
    layout.setContentsMargins(50, 20, 50, 50)
    layout.addLayout(
        main_window._create_top_bar("Ustawienia", main_window.MAIN_MENU_IDX)
    )

    main_window.window_mode_combo = ModernComboBox()
    main_window.window_mode_combo.addItems(
        ["W oknie", "Pełny ekran w oknie", "Pełny ekran"]
    )
    main_window.window_mode_combo.setCurrentText("Pełny ekran w oknie")
    main_window.window_mode_combo.currentTextChanged.connect(
        main_window._change_window_mode
    )
    layout.addLayout(
        main_window._create_form_row("Tryb okna:", main_window.window_mode_combo)
    )

    volume_label = QLabel("Głośność:")
    main_window.volume_slider = ModernSlider(Qt.Horizontal)
    main_window.volume_slider.setRange(0, 100)
    main_window.volume_slider.setValue(int(main_window.volume_level * 100))
    main_window.volume_slider.valueChanged.connect(main_window.change_volume)
    main_window.volume_slider.setStyleSheet("")
    layout.addLayout(
        main_window._create_form_row(volume_label.text(), main_window.volume_slider)
    )

    contrast_label = QLabel("Kontrast:")
    main_window.contrast_slider = ModernSlider(Qt.Horizontal)
    main_window.contrast_slider.setRange(50, 150)  # 0.50x – 1.50x
    main_window.contrast_slider.setValue(int(main_window.contrast_level * 100))
    main_window.contrast_slider.valueChanged.connect(main_window.change_contrast)
    main_window.contrast_slider.setStyleSheet("")
    layout.addLayout(
        main_window._create_form_row(contrast_label.text(), main_window.contrast_slider)
    )

    layout.addStretch()

    return widget
