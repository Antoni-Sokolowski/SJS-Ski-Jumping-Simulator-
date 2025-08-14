"""Support page."""

import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap, QDesktopServices
from utils.helpers import resource_path


def create_support_page(main_window):
    """Create the support page."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(12)
    layout.setContentsMargins(50, 20, 50, 50)
    layout.addLayout(main_window._create_top_bar("Wsparcie", main_window.MAIN_MENU_IDX))

    title = QLabel("Potrzebujesz pomocy?")
    title.setStyleSheet("font-size: 24px; font-weight: 600;")
    title.setAlignment(Qt.AlignCenter)

    # Karta zaproszenia w stylu Discord
    card_btn = QPushButton()
    card_btn.setCursor(Qt.PointingHandCursor)
    card_btn.setFlat(True)
    card_btn.setStyleSheet(
        "QPushButton{background:#11151d; border:1px solid #232a36; border-radius:12px; padding:0;}"
        "QPushButton:hover{border-color:#2f3a4d;}"
    )
    card_btn.clicked.connect(
        lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/D445FhKEmT"))
    )

    card = QWidget(card_btn)
    card_layout = QVBoxLayout(card)
    card_layout.setSpacing(12)
    card_layout.setContentsMargins(16, 16, 16, 16)

    # Pasek z ikoną SJS (wycentrowany) z pliku assets/SJS.ico
    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    top_row.setSpacing(12)
    icon_holder = QWidget()
    icon_holder.setFixedSize(60, 60)
    icon_holder.setStyleSheet(
        "background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #1b2230, stop:1 #0f1115); border-radius: 12px;"
    )
    icon_inner = QVBoxLayout(icon_holder)
    icon_inner.setContentsMargins(8, 8, 8, 8)
    icon_inner.setSpacing(0)
    ico_label = QLabel()
    ico_pix = QPixmap(resource_path(os.path.join("assets", "SJS.ico")))
    if not ico_pix.isNull():
        ico_label.setPixmap(
            ico_pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
    ico_label.setAlignment(Qt.AlignCenter)
    icon_inner.addWidget(ico_label)
    top_row.addStretch(1)
    top_row.addWidget(icon_holder, 0, Qt.AlignCenter)
    top_row.addStretch(1)
    card_layout.addLayout(top_row)

    name = QLabel("SJS (Ski Jumping Simulator)")
    name.setStyleSheet("font-size: 18px; font-weight: 600;")
    name.setAlignment(Qt.AlignCenter)
    card_layout.addWidget(name)

    open_btn = QPushButton("Przejdź do serwera")
    open_btn.setProperty("variant", "success")
    open_btn.setStyleSheet("font-size: 16px; font-weight: 600;")
    open_btn.setFixedHeight(48)
    open_btn.clicked.connect(
        lambda: QDesktopServices.openUrl(QUrl("https://discord.gg/D445FhKEmT"))
    )
    card_layout.addWidget(open_btn)

    card_btn.setMinimumWidth(600)
    card_btn.setMinimumHeight(300)
    card_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    lay_btn = QVBoxLayout(card_btn)
    lay_btn.setContentsMargins(0, 0, 0, 0)
    lay_btn.addWidget(card)

    # Wycentrowanie pionowe i horyzontalne: tytuł + kafelek jako jeden blok
    layout.addStretch(1)
    center_widget = QWidget()
    center_layout = QVBoxLayout(center_widget)
    center_layout.setSpacing(16)
    center_layout.addWidget(title, 0, Qt.AlignHCenter)
    center_layout.addWidget(card_btn, 0, Qt.AlignHCenter)
    layout.addWidget(center_widget, 0, Qt.AlignCenter)
    layout.addStretch(1)

    return widget
