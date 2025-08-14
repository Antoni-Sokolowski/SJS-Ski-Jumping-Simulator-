"""Timing indicator widget for jump timing visualization."""

from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics


class TimingIndicatorBar(QWidget):
    """Minimalistyczny pasek wizualizujący timing wybicia.

    Zakres: od -max_abs_seconds (za wcześnie) do +max_abs_seconds (za późno).
    Marker pokazuje przesunięcie czasu (εt) oraz kolor zależny od klasyfikacji.
    """

    def __init__(self, parent=None, max_abs_seconds: float = 0.12):
        super().__init__(parent)
        self._max_abs_seconds = float(max_abs_seconds)
        self._epsilon_t_s = 0.0
        self._classification = "idealny"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(44)

    def sizeHint(self):  # noqa: N802 - Qt API
        return QSize(300, 48)

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
        """Zwraca kolor wg modułu błędu czasu: zielony→żółty→czerwony.

        0% = zielony (#28a745), ~50% = żółty (#ffc107), 100% = czerwony (#dc3545)
        """
        ratio = min(1.0, abs(self._epsilon_t_s) / max(1e-6, self._max_abs_seconds))
        green = QColor("#28a745")
        yellow = QColor("#ffc107")
        red = QColor("#dc3545")
        if ratio <= 0.5:
            # 0.0..0.5 → green→yellow
            return self._interpolate_color(green, yellow, ratio / 0.5)
        # 0.5..1.0 → yellow→red
        return self._interpolate_color(yellow, red, (ratio - 0.5) / 0.5)

    def paintEvent(self, event):  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Kompaktowe marginesy zgodne z motywem (większy dolny margines na napisy)
        rect = self.rect().adjusted(8, 6, -8, -14)

        # Tło (transparentne, nie rysujemy pełnego panelu żeby było minimalistycznie)

        # Tor paska (ciemna szyna zgodna z motywem)
        track_h = 8
        track_y = rect.center().y() - track_h // 2

        # Rysuj szynę
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1e2430"))
        painter.drawRoundedRect(rect.left(), track_y, rect.width(), track_h, 4, 4)

        # Znacznik środka (idealny)
        center_x = rect.left() + rect.width() // 2
        painter.setPen(QColor(76, 132, 255, 120))  # akcent motywu
        painter.drawLine(center_x, track_y - 6, center_x, track_y + track_h + 6)

        # Pozycja markera
        max_abs = max(0.001, self._max_abs_seconds)
        ratio = (self._epsilon_t_s / (2 * max_abs)) + 0.5  # map [-max, +max] -> [0,1]
        ratio = max(0.0, min(1.0, ratio))
        marker_x = rect.left() + int(ratio * rect.width())

        # Marker (kółko) w kolorze zależnym od wielkości błędu
        color = self._color_for_magnitude()
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 230))
        painter.setPen(Qt.NoPen)
        radius = 7
        painter.drawEllipse(QPoint(marker_x, rect.center().y()), radius, radius)

        # Delikatna obwódka dopasowująca do tła
        painter.setPen(QColor(15, 17, 21, 180))  # #0f1115 z lekką alfą
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QPoint(marker_x, rect.center().y()), radius, radius)

        # Podpisy krańcowe subtelne
        font = painter.font()
        small_font = QFont(font)
        small_font.setPointSizeF(max(7.5, font.pointSizeF() - 1))
        painter.setFont(small_font)
        painter.setPen(QColor(200, 208, 227, 140))
        # Ustaw podpisy w bezpiecznej strefie wewnątrz widgetu, tuż nad krawędzią
        metrics_small = QFontMetrics(small_font)
        text_y = self.rect().bottom() - 4
        painter.drawText(rect.left(), text_y, "za wcześnie")
        painter.drawText(
            rect.right() - metrics_small.horizontalAdvance("za późno"),
            text_y,
            "za późno",
        )

        painter.end()
