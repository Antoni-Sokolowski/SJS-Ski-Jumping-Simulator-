"""Custom UI widgets for the application."""

from PySide6.QtWidgets import (
    QSpinBox, QDoubleSpinBox, QAbstractSpinBox, QPushButton, 
    QWidget, QHBoxLayout, QProxyStyle, QStyle
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from ui import ModernSlider


class CustomSpinBox(QSpinBox):
    """
    Niestandardowy SpinBox z własnymi przyciskami, gwarantujący
    poprawny wygląd i blokadę scrolla.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)

        # Minimal, consistent arrow buttons
        self.up_button.setObjectName("spinUpButton")
        self.down_button.setObjectName("spinDownButton")
        self.up_button.setFlat(True)
        self.down_button.setFlat(True)
        self.up_button.setText("▲")
        self.down_button.setText("▼")

        self.up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.up_button.clicked.connect(self.stepUp)
        self.down_button.clicked.connect(self.stepDown)

    def set_button_icons(self, up_icon, down_icon):
        # Keep textual arrows for crisp, minimal look across DPI settings
        self.up_button.setIcon(QIcon())
        self.down_button.setIcon(QIcon())
        self.up_button.setText("▲")
        self.down_button.setText("▼")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        button_width = 25
        self.up_button.setGeometry(
            self.width() - button_width, 0, button_width, self.height() // 2
        )
        self.down_button.setGeometry(
            self.width() - button_width,
            self.height() // 2,
            button_width,
            self.height() // 2,
        )

    def wheelEvent(self, event):
        event.ignore()


class CustomDoubleSpinBox(QDoubleSpinBox):
    """
    Niestandardowy DoubleSpinBox z własnymi przyciskami, gwarantujący
    poprawny wygląd i blokadę scrolla.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)

        # Minimal, consistent arrow buttons
        self.up_button.setObjectName("spinUpButton")
        self.down_button.setObjectName("spinDownButton")
        self.up_button.setFlat(True)
        self.down_button.setFlat(True)
        self.up_button.setText("▲")
        self.down_button.setText("▼")

        self.up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.up_button.clicked.connect(self.stepUp)
        self.down_button.clicked.connect(self.stepDown)

    def set_button_icons(self, up_icon, down_icon):
        # Keep textual arrows for crisp, minimal look across DPI settings
        self.up_button.setIcon(QIcon())
        self.down_button.setIcon(QIcon())
        self.up_button.setText("▲")
        self.down_button.setText("▼")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        button_width = 25
        self.up_button.setGeometry(
            self.width() - button_width, 0, button_width, self.height() // 2
        )
        self.down_button.setGeometry(
            self.width() - button_width,
            self.height() // 2,
            button_width,
            self.height() // 2,
        )

    def wheelEvent(self, event):
        event.ignore()


class CustomSlider(QWidget):
    """
    Niestandardowy widget slider z edytowalnym wyświetlaniem wartości.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Slider
        self.slider = ModernSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        # Apply slider styles directly
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #1e2430;
                border-radius: 4px;
                border: none;
                margin: 0;
            }
            QSlider::sub-page:horizontal {
                background: #4c84ff;
                border-radius: 4px;
                border: none;
            }
            QSlider::add-page:horizontal {
                background: #2a2f3a;
                border-radius: 4px;
                border: none;
            }
            QSlider::handle:horizontal {
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
                background: #4c84ff;
                border: 3px solid #0f1115;
            }
            QSlider::handle:horizontal:hover {
                background: #5b90ff;
                border-color: #1e2430;
            }
        """)

        # Custom value spinbox with custom arrow buttons
        self.value_spinbox = CustomDoubleSpinBox()
        self.value_spinbox.setRange(0.0, 100.0)
        self.value_spinbox.setDecimals(2)

        self.layout.addWidget(self.slider, 1)
        self.layout.addWidget(self.value_spinbox)

        # Connect signals
        self.slider.valueChanged.connect(self._update_spinbox)
        self.value_spinbox.valueChanged.connect(self._update_slider)

    def set_button_icons(self, up_icon, down_icon):
        """Ustawia ikony przycisków dla spinboxa."""
        self.value_spinbox.set_button_icons(up_icon, down_icon)

    def _update_spinbox(self, value):
        # Prevent recursive calls
        self.value_spinbox.blockSignals(True)
        self.value_spinbox.setValue(float(value))
        self.value_spinbox.blockSignals(False)

    def _update_slider(self, value):
        # Prevent recursive calls
        self.slider.blockSignals(True)
        self.slider.setValue(int(value))
        self.slider.blockSignals(False)

    def value(self):
        return self.value_spinbox.value()

    def setValue(self, value):
        self.slider.setValue(int(value))
        self.value_spinbox.setValue(float(value))

    def setRange(self, min_val, max_val):
        self.slider.setRange(min_val, max_val)
        self.value_spinbox.setRange(float(min_val), float(max_val))


class CustomProxyStyle(QProxyStyle):
    """
    Niestandardowy styl, który nadpisuje domyślny czas wyświetlania podpowiedzi.
    """

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return 100
        try:
            return super().styleHint(hint, option, widget, returnData)
        except TypeError:
            # Fallback dla przypadków gdy argumenty są nieprawidłowych typów
            try:
                return super().styleHint(hint)
            except Exception:
                return 0
