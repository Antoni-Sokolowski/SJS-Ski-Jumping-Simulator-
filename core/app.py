"""Main application entry point."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from utils.helpers import resource_path
from ui.widgets.custom_widgets import CustomProxyStyle
from core.main_window import MainWindow


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)

    app.setStyle("Fusion")
    app.setStyle(CustomProxyStyle())

    # Load minimalist modern QSS theme
    try:
        qss_path = resource_path(os.path.join("ui", "styles.qss"))
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
    except Exception:
        # Silent fallback to default style if QSS fails to load
        pass

    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
