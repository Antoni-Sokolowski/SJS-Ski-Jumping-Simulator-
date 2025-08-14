"""Competition page."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QTableWidget,
    QHeaderView,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFontMetrics
from ui import ModernComboBox
from ui.widgets.custom_widgets import CustomSpinBox


def create_competition_page(main_window):
    """Create the competition page."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(20)
    layout.setContentsMargins(50, 20, 50, 50)
    layout.addLayout(main_window._create_top_bar("Zawody", main_window.MAIN_MENU_IDX))

    # Główny layout z podziałem na sekcje
    main_hbox = QHBoxLayout()

    # Lewa sekcja - Konfiguracja zawodów
    left_panel = QVBoxLayout()
    left_panel.setSpacing(15)

    # Sekcja wyboru zawodników
    jumper_group = QGroupBox("Wybór zawodników")
    jumper_group_layout = QVBoxLayout(jumper_group)
    jumper_group_layout.setSpacing(10)

    # Kontrolki wyboru zawodników
    jumper_controls_layout = QHBoxLayout()
    main_window.toggle_all_button = QPushButton("Zaznacz wszystkich")
    main_window.toggle_all_button.setProperty("variant", "primary")
    main_window.toggle_all_button.clicked.connect(main_window._toggle_all_jumpers)
    jumper_controls_layout.addWidget(main_window.toggle_all_button)

    # Licznik wybranych zawodników
    main_window.selected_count_label = QLabel("Wybrano: 0 zawodników")
    main_window.selected_count_label.setProperty("chip", True)
    main_window.selected_count_label.setProperty("variant", "info")
    jumper_controls_layout.addWidget(main_window.selected_count_label)
    jumper_group_layout.addLayout(jumper_controls_layout)

    # Sortowanie zawodników
    sort_layout = QHBoxLayout()
    sort_layout.addWidget(QLabel("Sortuj:"))
    main_window.sort_combo = ModernComboBox()
    main_window.sort_combo.addItems(["Wg Nazwiska (A-Z)", "Wg Kraju"])
    main_window.sort_combo.currentTextChanged.connect(main_window._sort_jumper_list)
    sort_layout.addWidget(main_window.sort_combo)
    jumper_group_layout.addLayout(sort_layout)

    # Lista zawodników z lepszym stylem
    main_window.jumper_list_widget = QListWidget()
    main_window.jumper_list_widget.setMaximumHeight(300)

    for jumper in main_window.all_jumpers:
        item = QListWidgetItem(
            main_window.create_rounded_flag_icon(jumper.nationality), str(jumper)
        )
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        item.setData(Qt.UserRole, jumper)
        main_window.jumper_list_widget.addItem(item)
    main_window.jumper_list_widget.itemChanged.connect(
        main_window._on_jumper_item_changed
    )
    jumper_group_layout.addWidget(main_window.jumper_list_widget)

    left_panel.addWidget(jumper_group)

    # Sekcja konfiguracji zawodów
    competition_group = QGroupBox("Konfiguracja zawodów")
    competition_group_layout = QVBoxLayout(competition_group)
    competition_group_layout.setSpacing(15)

    # Kontener dla skoczni i belki w jednym wierszu
    hill_gate_container = QHBoxLayout()
    hill_gate_container.setSpacing(20)

    # Wybór skoczni z ikoną
    hill_layout = QVBoxLayout()
    hill_layout.setSpacing(5)
    hill_label = QLabel("Skocznia:")
    hill_layout.addWidget(hill_label)

    main_window.comp_hill_combo = ModernComboBox()
    main_window.comp_hill_combo.addItem("Wybierz skocznię")
    for hill in main_window.all_hills:
        main_window.comp_hill_combo.addItem(
            main_window.create_rounded_flag_icon(hill.country), str(hill)
        )
    main_window.comp_hill_combo.currentIndexChanged.connect(
        main_window.update_competition_hill
    )
    hill_layout.addWidget(main_window.comp_hill_combo)
    hill_gate_container.addLayout(hill_layout)

    # Wybór belki z rekomendacją
    gate_layout = QVBoxLayout()
    gate_layout.setSpacing(5)
    gate_label = QLabel("Belka:")
    gate_layout.addWidget(gate_label)

    # Kontener dla belki i rekomendacji
    gate_input_layout = QHBoxLayout()
    gate_input_layout.setSpacing(10)

    main_window.comp_gate_spin = CustomSpinBox()
    main_window.comp_gate_spin.setMinimum(1)
    main_window.comp_gate_spin.setMaximum(1)
    main_window.comp_gate_spin.valueChanged.connect(main_window._on_gate_changed)
    gate_input_layout.addWidget(main_window.comp_gate_spin)

    # Label z rekomendowaną belką
    main_window.recommended_gate_label = QLabel("")
    main_window.recommended_gate_label.setProperty("chip", True)
    main_window.recommended_gate_label.setProperty("variant", "primary")
    main_window.recommended_gate_label.setVisible(False)
    gate_input_layout.addWidget(main_window.recommended_gate_label)
    gate_input_layout.addStretch()

    gate_layout.addLayout(gate_input_layout)

    # Dolny wiersz z informacją o rekomendacji
    main_window.gate_info_label = QLabel("")
    main_window.gate_info_label.setProperty("chip", True)
    main_window.gate_info_label.setProperty("variant", "info")
    main_window.gate_info_label.setVisible(False)
    gate_layout.addWidget(main_window.gate_info_label)

    hill_gate_container.addLayout(gate_layout)
    competition_group_layout.addLayout(hill_gate_container)

    # Opcje kwalifikacji
    qualification_layout = QHBoxLayout()
    qualification_layout.setSpacing(10)

    main_window.qualification_checkbox = QCheckBox("Kwalifikacje")
    main_window.qualification_checkbox.setChecked(True)  # Domyślnie włączone
    qualification_layout.addWidget(main_window.qualification_checkbox)
    qualification_layout.addStretch()

    competition_group_layout.addLayout(qualification_layout)

    # Przycisk rozpoczęcia zawodów z lepszym stylem
    main_window.run_comp_btn = QPushButton("Rozpocznij zawody")
    main_window.run_comp_btn.setProperty("variant", "success")
    main_window.run_comp_btn.clicked.connect(main_window._on_competition_button_clicked)
    competition_group_layout.addWidget(main_window.run_comp_btn)

    left_panel.addWidget(competition_group)
    left_panel.addStretch()
    main_hbox.addLayout(left_panel, 1)

    # Prawa sekcja - Wyniki zawodów
    results_panel = QVBoxLayout()
    results_panel.setSpacing(15)

    # Status zawodów z lepszym stylem
    main_window.competition_status_label = QLabel(
        "Tabela wyników (kliknij odległość, aby zobaczyć powtórkę):"
    )
    main_window.competition_status_label.setProperty("chip", True)
    main_window.competition_status_label.setProperty("variant", "info")

    # Dodajemy informację o aktualnej serii
    main_window.round_info_label = QLabel("Seria: 1/2")
    main_window.round_info_label.setProperty("chip", True)
    main_window.round_info_label.setProperty("variant", "primary")
    main_window.round_info_label.setAlignment(Qt.AlignCenter)

    # Layout dla statusu i informacji o serii
    status_layout = QHBoxLayout()
    status_layout.addWidget(main_window.competition_status_label, 3)
    status_layout.addWidget(main_window.round_info_label, 1)
    results_panel.addLayout(status_layout)

    # Dodajemy pasek postępu
    main_window.progress_label = QLabel("Postęp: 0%")
    main_window.progress_label.setProperty("chip", True)
    main_window.progress_label.setProperty("variant", "primary")
    main_window.progress_label.setAlignment(Qt.AlignCenter)
    results_panel.addWidget(main_window.progress_label)

    # Tabela wyników z ulepszonym stylem
    main_window.results_table = QTableWidget()
    main_window.results_table.setColumnCount(8)
    main_window.results_table.setHorizontalHeaderLabels(
        [
            "",
            "",
            "Zawodnik",
            "I seria",
            "I seria (pkt)",
            "II seria",
            "II seria (pkt)",
            "Suma (pkt)",
        ]
    )
    main_window.results_table.verticalHeader().setDefaultSectionSize(34)
    main_window.results_table.verticalHeader().setVisible(False)
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        QHeaderView.Stretch
    )
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.ResizeToContents
    )
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.Fixed
    )
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        2, QHeaderView.Fixed
    )
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        3, QHeaderView.Stretch
    )
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        4, QHeaderView.Stretch
    )
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        5, QHeaderView.Stretch
    )
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        6, QHeaderView.Stretch
    )
    main_window.results_table.horizontalHeader().setSectionResizeMode(
        7, QHeaderView.Stretch
    )
    main_window.results_table.horizontalHeader().setMinimumSectionSize(24)

    # Compute and set name column width for ~25 characters (bold font used in cells)
    name_font = main_window.results_table.font()
    name_font.setBold(True)
    metrics_name = QFontMetrics(name_font)
    name_col_width = metrics_name.horizontalAdvance("W" * 25) + 20
    main_window.results_table.setColumnWidth(2, name_col_width)
    main_window.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
    main_window.results_table.setSelectionBehavior(QTableWidget.SelectRows)
    main_window.results_table.cellClicked.connect(main_window._on_result_cell_clicked)

    # Styl tabeli wyników ustalany globalnie przez QSS
    main_window.results_table.setAlternatingRowColors(True)
    main_window.results_table.setIconSize(QSize(24, 16))
    main_window.results_table.setColumnWidth(1, 42)

    # Tabela kwalifikacji - osobna tabela z inną strukturą
    main_window.qualification_table = QTableWidget()
    main_window.qualification_table.setColumnCount(5)
    main_window.qualification_table.setHorizontalHeaderLabels(
        ["", "", "Zawodnik", "Dystans", "Punkty"]
    )
    main_window.qualification_table.verticalHeader().setDefaultSectionSize(34)
    main_window.qualification_table.verticalHeader().setVisible(False)
    main_window.qualification_table.horizontalHeader().setSectionResizeMode(
        QHeaderView.Stretch
    )
    main_window.qualification_table.horizontalHeader().setSectionResizeMode(
        0, QHeaderView.ResizeToContents
    )
    main_window.qualification_table.horizontalHeader().setSectionResizeMode(
        1, QHeaderView.Fixed
    )
    main_window.qualification_table.horizontalHeader().setSectionResizeMode(
        2, QHeaderView.Stretch
    )
    main_window.qualification_table.setEditTriggers(QTableWidget.NoEditTriggers)
    main_window.qualification_table.setSelectionBehavior(QTableWidget.SelectRows)
    main_window.qualification_table.cellClicked.connect(
        main_window._on_qualification_cell_clicked
    )
    main_window.qualification_table.setVisible(False)  # Domyślnie ukryta

    # Styl tabeli kwalifikacji ustalany globalnie przez QSS
    main_window.qualification_table.setAlternatingRowColors(True)
    main_window.qualification_table.setIconSize(QSize(24, 16))
    main_window.qualification_table.setColumnWidth(1, 42)

    results_panel.addWidget(main_window.results_table)
    results_panel.addWidget(main_window.qualification_table)
    main_hbox.addLayout(results_panel, 2)

    layout.addLayout(main_hbox)

    return widget
