from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


class AnimatedStackedWidget(QStackedWidget):
    """
    Drop-in replacement for QStackedWidget that performs a subtle fade-in
    animation whenever the current index changes. Keeps logic identical for
    callers: setCurrentIndex works the same, only with a short animation.
    """

    def __init__(self, parent: Optional[QWidget] = None, animation_ms: int = 180):
        super().__init__(parent)
        self._animation_duration_ms: int = animation_ms
        self._active_animations: List[QPropertyAnimation] = []

    def setCurrentIndex(self, index: int) -> None:  # type: ignore[override]
        super().setCurrentIndex(index)
        self._fade_in_current()

    # Public helper in case manual triggering is needed elsewhere
    def fade_in_current(self, duration_ms: Optional[int] = None) -> None:
        self._fade_in_current(duration_ms)

    def _fade_in_current(self, duration_ms: Optional[int] = None) -> None:
        widget = self.currentWidget()
        if widget is None:
            return

        # Clear finished animations
        self._active_animations = [
            a
            for a in self._active_animations
            if a.state() != QPropertyAnimation.State.Stopped
        ]

        # Remove previous effect if any
        old_effect = widget.graphicsEffect()
        if isinstance(old_effect, QGraphicsOpacityEffect):
            widget.setGraphicsEffect(None)

        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(0.0)
        widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(
            duration_ms if duration_ms is not None else self._animation_duration_ms
        )
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def _cleanup() -> None:
            # Remove the effect to avoid stacking QGraphicsEffects
            widget.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        self._active_animations.append(anim)
        anim.start()
