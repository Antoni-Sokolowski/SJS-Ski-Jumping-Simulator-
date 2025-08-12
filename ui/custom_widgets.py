"""Niestandardowe widgety Qt dla aplikacji"""

from PySide6.QtWidgets import (
    QWidget, QSpinBox, QDoubleSpinBox, QPushButton, QSlider, 
    QHBoxLayout, QProxyStyle, QStyle, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QPixmap, QPainter, QColor, QPolygon, QPoint, QFont, QFontMetrics


class TimingIndicatorBar(QWidget):
    """Minimalistyczny pasek wizualizujący timing wybicia."""

    def __init__(self, parent=None, max_abs_seconds: float = 0.12):
        super().__init__(parent)
        self._max_abs_seconds = float(max_abs_seconds)
        self._epsilon_t_s = 0.0
        self._classification = "idealny"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(34)

    def sizeHint(self):  # noqa: N802 - Qt API
        return QSize(300, 38)

    def setTiming(self, epsilon_t_s: float, classification: str):  # noqa: N802 - Qt API
        self._epsilon_t_s = float(epsilon_t_s or 0.0)
        self._classification = str(classification or "idealny")
        self.update()

    def _interpolate_color(self, c1: QColor, c2: QColor, t: float) -> QColor:
        t = max(0.0, min(1.0, t))
        r = int(c1.red() + (c2.red() - c1.red()) * t)
        g = int(c1.green() + (c2.green() - c1.green()) * t)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
        return QColor(r, g, b)

    def _color_for_magnitude(self) -> QColor:
        """Zwraca kolor wg modułu błędu czasu: zielony→żółty→czerwony."""
        ratio = min(1.0, abs(self._epsilon_t_s) / max(1e-6, self._max_abs_seconds))
        green = QColor("#28a745")
        yellow = QColor("#ffc107")
        red = QColor("#dc3545")
        if ratio <= 0.5:
            return self._interpolate_color(green, yellow, ratio / 0.5)
        return self._interpolate_color(yellow, red, (ratio - 0.5) / 0.5)

    def paintEvent(self, event):  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(10, 8, -10, -8)

        # Tor paska
        track_h = 6
        track_y = rect.center().y() - track_h // 2

        # Rysuj szynę
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 40))
        painter.drawRoundedRect(rect.left(), track_y, rect.width(), track_h, 3, 3)

        # Znacznik środka (idealny)
        center_x = rect.left() + rect.width() // 2
        painter.setPen(QColor(255, 255, 255, 80))
        painter.drawLine(center_x, track_y - 5, center_x, track_y + track_h + 5)

        # Pozycja markera
        max_abs = max(0.001, self._max_abs_seconds)
        ratio = (self._epsilon_t_s / (2 * max_abs)) + 0.5
        ratio = max(0.0, min(1.0, ratio))
        marker_x = rect.left() + int(ratio * rect.width())

        # Marker (kółko)
        color = self._color_for_magnitude()
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 220))
        painter.setPen(Qt.NoPen)
        radius = 7
        painter.drawEllipse(QPoint(marker_x, rect.center().y()), radius, radius)

        # Delikatna obwódka
        painter.setPen(QColor(0, 0, 0, 60))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(marker_x, rect.center().y()), radius, radius)

        # Podpisy krańcowe
        font = painter.font()
        small_font = QFont(font)
        small_font.setPointSizeF(max(7.5, font.pointSizeF() - 1))
        painter.setFont(small_font)
        painter.setPen(QColor(255, 255, 255, 100))
        painter.drawText(rect.left(), rect.bottom(), "za wcześnie")
        metrics_small = QFontMetrics(small_font)
        painter.drawText(
            rect.right() - metrics_small.horizontalAdvance("za późno"),
            rect.bottom(),
            "za późno",
        )

        painter.end()


class CustomSpinBox(QSpinBox):
    """Niestandardowy SpinBox z własnymi przyciskami."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)

        self.up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.up_button.clicked.connect(self.stepUp)
        self.down_button.clicked.connect(self.stepDown)

    def set_button_icons(self, up_icon, down_icon):
        self.up_button.setIcon(up_icon)
        self.down_button.setIcon(down_icon)

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
    """Niestandardowy DoubleSpinBox z własnymi przyciskami."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.up_button = QPushButton(self)
        self.down_button = QPushButton(self)

        self.up_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.up_button.clicked.connect(self.stepUp)
        self.down_button.clicked.connect(self.stepDown)

    def set_button_icons(self, up_icon, down_icon):
        self.up_button.setIcon(up_icon)
        self.down_button.setIcon(down_icon)

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
    """Niestandardowy widget slider z edytowalnym wyświetlaniem wartości."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #2b2b2b;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                border: 2px solid #0078d4;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #106ebe;
                border-color: #106ebe;
            }
            QSlider::sub-page:horizontal {
                background: #0078d4;
                border-radius: 4px;
            }
        """)

        # Value spinbox
        self.value_spinbox = CustomDoubleSpinBox()
        self.value_spinbox.setRange(0.0, 100.0)
        self.value_spinbox.setDecimals(2)
        self.value_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                min-width: 60px;
                background: #2b2b2b;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px;
            }
        """)

        self.layout.addWidget(self.slider, 1)
        self.layout.addWidget(self.value_spinbox)

        # Connect signals
        self.slider.valueChanged.connect(self._update_spinbox)
        self.value_spinbox.valueChanged.connect(self._update_slider)

    def set_button_icons(self, up_icon, down_icon):
        """Ustawia ikony przycisków dla spinboxa."""
        self.value_spinbox.set_button_icons(up_icon, down_icon)

    def _update_spinbox(self, value):
        self.value_spinbox.blockSignals(True)
        self.value_spinbox.setValue(float(value))
        self.value_spinbox.blockSignals(False)

    def _update_slider(self, value):
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
    """Niestandardowy styl, który nadpisuje domyślny czas wyświetlania podpowiedzi."""

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return 100
        try:
            return super().styleHint(hint, option, widget, returnData)
        except TypeError:
            try:
                return super().styleHint(hint)
            except:
                return 0


def create_arrow_pixmap(direction, color):
    """Tworzy pixmapę ze strzałką (trójkątem) o danym kolorze."""
    pixmap = QPixmap(10, 10)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    if direction == "up":
        points = [QPoint(5, 2), QPoint(2, 7), QPoint(8, 7)]
    else:  # down
        points = [QPoint(5, 8), QPoint(2, 3), QPoint(8, 3)]
    painter.drawPolygon(QPolygon(points))
    painter.end()
    return pixmap