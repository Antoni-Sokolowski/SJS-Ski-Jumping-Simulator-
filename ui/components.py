from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPalette
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QSlider,
)


class NavigationSidebar(QWidget):
    """
    Minimalistyczny, nowoczesny lewy pasek nawigacji z przyciskami tekstowymi.
    Używa prostych przycisków bez ikon, aby zachować czystość wizualną.
    """

    def __init__(self, title: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("navSidebar")

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 14, 14, 14)
        self._layout.setSpacing(8)

        if title:
            lbl = QLabel(title)
            lbl.setProperty("class", "headerLabel")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lbl.setObjectName("navTitle")
            self._layout.addWidget(lbl)

        self._layout.addSpacing(8)
        self._layout.addStretch(0)

        self._buttons: list[QPushButton] = []

    def add_nav(self, text: str, on_click: Callable[[], None]) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.clicked.connect(on_click)
        self._buttons.append(btn)
        self._layout.addWidget(btn, 0, Qt.AlignTop)
        return btn

    def finalize(self) -> None:
        self._layout.addStretch(1)

    def set_active(self, btn: QPushButton) -> None:
        for b in self._buttons:
            b.setChecked(b is btn)


class ModernComboBox(QComboBox):
    """
    QComboBox z własnym rysowaniem strzałki (chevron), aby uniknąć problemów
    ze stylami QSS i zapewnić spójny wygląd.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Ukryj domyślną strzałkę/dopasuj drop-down, aby nic nie zasłaniało naszego rysowania
        self.setObjectName("modernCombo")
        self.setStyleSheet(
            """
            QComboBox#modernCombo { padding-right: 26px; }
            QComboBox#modernCombo::down-arrow { image: none; width: 0; height: 0; }
            QComboBox#modernCombo::drop-down { width: 0; border: none; }
            QComboBox#modernCombo QAbstractItemView { background: #0f1115; color: #e8eaf1; border: 1px solid #2a2f3a; }
            QComboBox#modernCombo QAbstractItemView::item { background: #0f1115; padding: 8px 12px; }
            QComboBox#modernCombo QAbstractItemView::item:selected { background: #1e2636; color: #e8eaf1; }
            QComboBox#modernCombo QAbstractItemView::item:hover { background: #151923; }
            """
        )
        self._hover = False
        self.setMinimumHeight(32)

    def enterEvent(self, event):
        self._hover = True
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        # Dorysuj chevron po prawej stronie
        rect = self.rect()
        arrow_width = 10
        arrow_height = 6
        right_margin = 10
        cx = rect.right() - right_margin - arrow_width // 2
        cy = rect.center().y()

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        # Zakryj ewentualne artefakty drop-down kolorem tła pola (szerszy obszar)
        cover_width = 34
        cover_rect = QRectF(
            rect.right() - cover_width,
            rect.top() + 1,
            cover_width,
            rect.height() - 2,
        )
        base_brush = self.palette().brush(QPalette.Base)
        p.setPen(Qt.NoPen)
        p.fillRect(cover_rect, base_brush)
        color = QColor("#e8eaf1" if self._hover else "#cfd5e3")
        pen = QPen(color, 1.8)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        # rysujemy znak V (chevron): (cx-4, cy-2) -> (cx, cy+2) -> (cx+4, cy-2)
        p.drawPolyline(
            [
                QPointF(cx - arrow_width / 2, cy - arrow_height / 2),
                QPointF(cx, cy + arrow_height / 2),
                QPointF(cx + arrow_width / 2, cy - arrow_height / 2),
            ]
        )
        p.end()


class ModernSlider(QSlider):
    """
    QSlider malowany w całości w paintEvent, aby uzyskać nowoczesny, minimalistyczny wygląd.
    """

    def __init__(self, orientation=Qt.Horizontal, parent: Optional[QWidget] = None):
        super().__init__(orientation, parent)
        self._hover = False
        self._pressed = False
        self.setMouseTracking(True)
        self.setMinimumHeight(24)

    def enterEvent(self, event):
        self._hover = True
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        super().leaveEvent(event)
        self.update()

    def mousePressEvent(self, event):
        self._pressed = True
        super().mousePressEvent(event)
        self.update()

    def mouseReleaseEvent(self, event):
        self._pressed = False
        super().mouseReleaseEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        if self.orientation() == Qt.Horizontal:
            groove_height = 8
            handle_diameter = 20
            cy = rect.center().y()
            left = rect.left() + handle_diameter // 2
            right = rect.right() - handle_diameter // 2
            groove_rect = QRectF(
                left, cy - groove_height / 2, right - left, groove_height
            )

            # Tło toru
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#2a2f3a"))
            p.drawRoundedRect(groove_rect, 4, 4)

            # Wypełnienie (sub-page)
            rng = max(1, self.maximum() - self.minimum())
            ratio = (self.value() - self.minimum()) / rng
            active_width = groove_rect.width() * ratio
            active_rect = QRectF(
                groove_rect.left(),
                groove_rect.top(),
                active_width,
                groove_rect.height(),
            )
            p.setBrush(QColor("#4c84ff"))
            p.drawRoundedRect(active_rect, 4, 4)

            # Uchwyt
            handle_x = groove_rect.left() + active_width
            handle_color = QColor("#4c84ff")
            if self._pressed:
                handle_color = QColor("#3a68c8")
            elif self._hover:
                handle_color = QColor("#5b90ff")

            p.setBrush(handle_color)
            p.setPen(QPen(QColor("#0f1115"), 3))
            p.drawEllipse(
                QPointF(handle_x, cy), handle_diameter / 2, handle_diameter / 2
            )
        else:
            # Minimalne wsparcie dla pionowego w razie potrzeby
            groove_width = 8
            handle_diameter = 20
            cx = rect.center().x()
            top = rect.top() + handle_diameter // 2
            bottom = rect.bottom() - handle_diameter // 2
            groove_rect = QRectF(cx - groove_width / 2, top, groove_width, bottom - top)

            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#2a2f3a"))
            p.drawRoundedRect(groove_rect, 4, 4)

            rng = max(1, self.maximum() - self.minimum())
            ratio = (self.value() - self.minimum()) / rng
            active_height = groove_rect.height() * ratio
            active_rect = QRectF(
                groove_rect.left(),
                groove_rect.bottom() - active_height,
                groove_rect.width(),
                active_height,
            )
            p.setBrush(QColor("#4c84ff"))
            p.drawRoundedRect(active_rect, 4, 4)

            handle_y = groove_rect.bottom() - active_height
            handle_color = QColor("#4c84ff")
            if self._pressed:
                handle_color = QColor("#3a68c8")
            elif self._hover:
                handle_color = QColor("#5b90ff")

            p.setBrush(handle_color)
            p.setPen(QPen(QColor("#0f1115"), 3))
            p.drawEllipse(
                QPointF(cx, handle_y), handle_diameter / 2, handle_diameter / 2
            )

        p.end()
