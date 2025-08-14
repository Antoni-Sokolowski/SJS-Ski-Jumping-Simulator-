"""Data editor page."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QListWidget,
    QScrollArea,
    QPushButton,
)
from PySide6.QtCore import Qt
from ui import ModernComboBox, AnimatedStackedWidget


def create_data_editor_page(main_window):
    """Create the data editor page."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(20)
    layout.setContentsMargins(50, 20, 50, 50)
    layout.addLayout(
        main_window._create_top_bar("Edytor Danych", main_window.MAIN_MENU_IDX)
    )

    main_hbox = QHBoxLayout()
    layout.addLayout(main_hbox, 1)

    # Left panel (Selection)
    left_panel = QVBoxLayout()
    left_panel.setSpacing(10)

    editor_sort_layout = QHBoxLayout()
    editor_sort_layout.addWidget(QLabel("Sortuj:"))
    main_window.editor_sort_combo = ModernComboBox()
    main_window.editor_sort_combo.addItems(["Alfabetycznie (A-Z)", "Wg Kraju (A-Z)"])
    editor_sort_layout.addWidget(main_window.editor_sort_combo)
    left_panel.addLayout(editor_sort_layout)

    main_window.editor_search_bar = QLineEdit()
    main_window.editor_search_bar.setPlaceholderText("🔍 Szukaj...")
    left_panel.addWidget(main_window.editor_search_bar)

    main_window.editor_tab_widget = QTabWidget()

    jumper_tab = QWidget()
    jumper_tab_layout = QVBoxLayout(jumper_tab)
    jumper_tab_layout.setContentsMargins(0, 0, 0, 0)
    main_window.editor_jumper_list = QListWidget()
    jumper_tab_layout.addWidget(main_window.editor_jumper_list)
    main_window.editor_tab_widget.addTab(jumper_tab, "Skoczkowie")

    hill_tab = QWidget()
    hill_tab_layout = QVBoxLayout(hill_tab)
    hill_tab_layout.setContentsMargins(0, 0, 0, 0)
    main_window.editor_hill_list = QListWidget()
    hill_tab_layout.addWidget(main_window.editor_hill_list)
    main_window.editor_tab_widget.addTab(hill_tab, "Skocznie")

    # Placeholder for _repopulate_editor_lists
    main_window._repopulate_editor_lists()

    main_window.editor_jumper_list.currentItemChanged.connect(
        main_window._populate_editor_form
    )
    main_window.editor_hill_list.currentItemChanged.connect(
        main_window._populate_editor_form
    )

    main_window.editor_sort_combo.currentTextChanged.connect(
        main_window._sort_editor_lists
    )
    main_window.editor_tab_widget.currentChanged.connect(
        main_window._filter_editor_lists
    )
    main_window.editor_search_bar.textChanged.connect(main_window._filter_editor_lists)

    left_panel.addWidget(main_window.editor_tab_widget)

    editor_button_layout = QHBoxLayout()
    main_window.clone_button = QPushButton("Klonuj")
    main_window.add_new_button = QPushButton("+ Dodaj")
    main_window.delete_button = QPushButton("- Usuń zaznaczone")
    editor_button_layout.addWidget(main_window.clone_button)
    editor_button_layout.addWidget(main_window.add_new_button)
    editor_button_layout.addWidget(main_window.delete_button)
    left_panel.addLayout(editor_button_layout)

    main_window.clone_button.clicked.connect(main_window._clone_selected_item)
    main_window.add_new_button.clicked.connect(main_window._add_new_item)
    main_window.delete_button.clicked.connect(main_window._delete_selected_item)

    main_hbox.addLayout(left_panel, 1)

    # Right panel (Form)
    right_panel = QVBoxLayout()

    main_window.editor_placeholder_label = QLabel(
        "Wybierz obiekt z listy po lewej, aby edytować jego właściwości."
    )
    main_window.editor_placeholder_label.setAlignment(Qt.AlignCenter)
    main_window.editor_placeholder_label.setWordWrap(True)

    jumper_form_scroll = QScrollArea()
    jumper_form_scroll.setWidgetResizable(True)
    main_window.jumper_form_widget = QWidget()
    main_window.jumper_form_widget.setObjectName("editorForm")
    main_window.jumper_edit_widgets = main_window._create_editor_form_content(
        main_window.jumper_form_widget, "Jumper"
    )
    jumper_form_scroll.setWidget(main_window.jumper_form_widget)

    hill_form_scroll = QScrollArea()
    hill_form_scroll.setWidgetResizable(True)
    main_window.hill_form_widget = QWidget()
    main_window.hill_form_widget.setObjectName("editorForm")
    main_window.hill_edit_widgets = main_window._create_editor_form_content(
        main_window.hill_form_widget, "Hill"
    )
    hill_form_scroll.setWidget(main_window.hill_form_widget)

    main_window.editor_form_stack = AnimatedStackedWidget()
    main_window.editor_form_stack.addWidget(main_window.editor_placeholder_label)
    main_window.editor_form_stack.addWidget(jumper_form_scroll)
    main_window.editor_form_stack.addWidget(hill_form_scroll)

    right_panel.addWidget(main_window.editor_form_stack, 1)

    form_button_layout = QHBoxLayout()
    apply_button = QPushButton("Zastosuj zmiany")
    apply_button.clicked.connect(main_window._save_current_edit)
    save_to_file_button = QPushButton("Zapisz wszystko do pliku...")
    save_to_file_button.clicked.connect(main_window._save_data_to_json)

    form_button_layout.addWidget(apply_button)
    form_button_layout.addWidget(save_to_file_button)
    right_panel.addLayout(form_button_layout)

    main_hbox.addLayout(right_panel, 2)

    return widget
