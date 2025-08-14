from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


class AnimatedStackedWidget(QStackedWidget):
    """
    Drop-in replacement for QStackedWidget that performs a subtle fade-in
    animation whenever the current index changes. Keeps logic identical for
    callers: setCurrentIndex works the same, only with a short animation.
    """

    def __init__(self, parent: Optional[QWidget] = None, animation_ms: int = 220):
        super().__init__(parent)
        self._animation_duration_ms: int = animation_ms
        self._active_animations: List[QPropertyAnimation] = []
        self._transition_running: bool = False

    def setCurrentIndex(self, index: int) -> None:  # type: ignore[override]
        if self._transition_running:
            # Jeśli animacja trwa, zakończ natychmiast i przełącz
            super().setCurrentIndex(index)
            return
        self._fade_through_black(index)

    # Public helper in case manual triggering is needed elsewhere
    def fade_in_current(self, duration_ms: Optional[int] = None) -> None:
        # Zachowujemy starą metodę jako delikatny efekt pomocniczy
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

    def _fade_through_black(self, target_index: int) -> None:
        """Nowoczesna, czysta animacja: szybkie ściemnienie do czerni,
        przełączenie strony, rozjaśnienie. Eliminuje artefakt 'pół starej/pół nowej'."""
        if target_index == self.currentIndex():
            return

        overlay = QWidget(self)
        overlay.setObjectName("_transitionOverlay")
        overlay.setStyleSheet("background: #0b0d12;")
        overlay.setGeometry(self.rect())
        overlay.lower()  # umieść pod dziećmi, zaraz podniesiemy
        overlay.raise_()
        overlay.show()

        eff = QGraphicsOpacityEffect(overlay)
        eff.setOpacity(0.0)
        overlay.setGraphicsEffect(eff)

        dur = self._animation_duration_ms

        fade_in = QPropertyAnimation(eff, b"opacity", self)
        fade_in.setDuration(dur // 2)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutCubic)

        fade_out = QPropertyAnimation(eff, b"opacity", self)
        fade_out.setDuration(dur // 2)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._transition_running = True

        def _swap():
            try:
                super(AnimatedStackedWidget, self).setCurrentIndex(target_index)
            except Exception:
                pass

        def _cleanup():
            overlay.setGraphicsEffect(None)
            overlay.deleteLater()
            self._transition_running = False

        def _start_fade_out():
            _swap()
            fade_out.finished.connect(_cleanup)
            fade_out.start()

        fade_in.finished.connect(_start_fade_out)
        fade_in.start()
