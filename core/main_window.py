"""Main window of the application."""

import os
import json
import copy
import random
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QListWidgetItem,
    QTableWidgetItem,
    QGroupBox,
    QFormLayout,
    QLineEdit,
)
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PIL import Image, ImageDraw, ImageFilter
import matplotlib.animation as animation
import numpy as np
import math

from src.simulation import load_data_from_json, fly_simulation, inrun_simulation
from src.jumper import Jumper
from src.hill import Hill
from ui import AnimatedStackedWidget, NavigationSidebar, ModernComboBox
from ui.widgets.custom_widgets import (
    CustomProxyStyle,
    CustomSpinBox,
    CustomDoubleSpinBox,
    CustomSlider,
)
from ui.widgets.judge_panel import JudgePanel
from utils.helpers import resource_path, create_arrow_pixmap, format_distance_with_unit
from utils.calculations import calculate_jump_points, round_distance_to_half_meter
from workers import RecommendedGateWorker

# Import pages
from ui.pages.main_menu import create_main_menu
from ui.pages.single_jump import create_single_jump_page
from ui.pages.competition import create_competition_page
from ui.pages.data_editor import create_data_editor_page
from ui.pages.settings import create_settings_page
from ui.pages.support import create_support_page
from ui.pages.jump_replay import create_jump_replay_page
from ui.pages.points_breakdown import create_points_breakdown_page


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji symulatora skoków narciarskich.
    Zarządza wszystkimi elementami UI, logiką przełączania stron i stanem aplikacji.
    """

    def __init__(self):
        """
        Konstruktor klasy MainWindow. Inicjalizuje całe UI, wczytuje dane
        i ustawia początkowy stan aplikacji.
        """
        super().__init__()
        self.setWindowTitle("Ski Jumping Simulator")

        icon_path = resource_path(os.path.join("assets", "SJS.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Page indices
        (
            self.MAIN_MENU_IDX,
            self.SIM_TYPE_MENU_IDX,
            self.SINGLE_JUMP_IDX,
            self.COMPETITION_IDX,
            self.DATA_EDITOR_IDX,
            self.DESCRIPTION_IDX,
            self.SETTINGS_IDX,
            self.JUMP_REPLAY_IDX,
            self.POINTS_BREAKDOWN_IDX,
            self.SUPPORT_IDX,
        ) = range(10)

        # Application state
        self.current_theme = "dark"
        self.contrast_level = 1.0
        self.volume_level = 0.3

        # Arrow icons
        self.up_arrow_icon_dark = QIcon(create_arrow_pixmap("up", "#b0b0b0"))
        self.down_arrow_icon_dark = QIcon(create_arrow_pixmap("down", "#b0b0b0"))
        self.up_arrow_icon_light = QIcon(create_arrow_pixmap("up", "#404040"))
        self.down_arrow_icon_light = QIcon(create_arrow_pixmap("down", "#404040"))

        # Audio setup
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        sound_file = resource_path(os.path.join("assets", "click.wav"))
        self.sound_loaded = os.path.exists(sound_file)
        if self.sound_loaded:
            self.player.setSource(QUrl.fromLocalFile(sound_file))
            self.audio_output.setVolume(self.volume_level)

        # Load data
        try:
            self.all_hills, self.all_jumpers = load_data_from_json()
        except Exception as e:
            title = "Błąd Krytyczny - Nie można wczytać danych"
            message = (
                f"Nie udało się wczytać lub przetworzyć pliku 'data.json'!\n\n"
                f"Błąd: {type(e).__name__}: {e}\n\n"
                f"Upewnij się, że folder 'data' z plikiem 'data.json' istnieje."
            )
            QMessageBox.critical(None, title, message)
            self.all_hills, self.all_jumpers = [], []

        if self.all_jumpers:
            self.all_jumpers.sort(key=lambda jumper: str(jumper))
        if self.all_hills:
            self.all_hills.sort(key=lambda hill: str(hill))

        # Setup UI
        self._setup_ui()
        self._setup_navigation()
        self._setup_state()
        self._create_pages()

    def _setup_ui(self):
        """Setup the main UI layout."""
        main_container = QWidget()
        shell_layout = QHBoxLayout(main_container)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # Left navigation sidebar
        self.nav_sidebar = NavigationSidebar("SJS")
        shell_layout.addWidget(self.nav_sidebar, 0)

        # Right content column: header + stacked content + footer
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(12)

        # Global header title (updates on page change)
        self.header_title_label = QLabel("Ski Jumping Simulator")
        self.header_title_label.setProperty("class", "headerLabel")
        content_layout.addWidget(self.header_title_label, 0, Qt.AlignLeft)

        self.central_widget = AnimatedStackedWidget()
        content_layout.addWidget(self.central_widget, 1)

        self.author_label = QLabel("Antoni Sokołowski")
        self.author_label.setObjectName("authorLabel")
        content_layout.addWidget(self.author_label, 0, Qt.AlignRight)

        shell_layout.addWidget(content_container, 1)
        self.setCentralWidget(main_container)

    def _setup_navigation(self):
        """Setup navigation and page mapping."""
        # Map indices to titles
        self.index_to_title = {
            self.MAIN_MENU_IDX: "Start",
            self.SINGLE_JUMP_IDX: "Symulacja skoku",
            self.COMPETITION_IDX: "Zawody",
            self.DATA_EDITOR_IDX: "Edytor danych",
            self.SETTINGS_IDX: "Ustawienia",
            self.JUMP_REPLAY_IDX: "Powtórka skoku",
            self.POINTS_BREAKDOWN_IDX: "Podział punktów",
            self.SUPPORT_IDX: "Wsparcie",
        }

        # Build navigation buttons and wire to pages
        def go(idx: int):
            return lambda: [self.play_sound(), self.central_widget.setCurrentIndex(idx)]

        self._nav_btn_start = self.nav_sidebar.add_nav("Start", go(self.MAIN_MENU_IDX))
        self._nav_btn_single = self.nav_sidebar.add_nav(
            "Skok", go(self.SINGLE_JUMP_IDX)
        )
        self._nav_btn_comp = self.nav_sidebar.add_nav(
            "Zawody", go(self.COMPETITION_IDX)
        )
        self._nav_btn_editor = self.nav_sidebar.add_nav(
            "Edytor", go(self.DATA_EDITOR_IDX)
        )
        self._nav_btn_settings = self.nav_sidebar.add_nav(
            "Ustawienia", go(self.SETTINGS_IDX)
        )
        self._nav_btn_support = self.nav_sidebar.add_nav(
            "Wsparcie", go(self.SUPPORT_IDX)
        )
        self.nav_sidebar.finalize()

        # React to page changes: update title and active nav
        self.central_widget.currentChanged.connect(self._on_page_changed)
        self._on_page_changed(self.central_widget.currentIndex())

        # Discord invite for Support page live stats
        self.discord_invite_code = "D445FhKEmT"

    def _setup_state(self):
        """Setup application state variables."""
        self.selection_order = []
        self.competition_results = []
        self.current_jumper_index = 0
        self.current_round = 1
        self.selected_jumper, self.selected_hill, self.ani = None, None, None
        self.points_ani = None
        self.replay_ani = None
        self.zoom_ani = None
        self.jumper_edit_widgets = {}
        self.hill_edit_widgets = {}

        # Panel sędziowski
        self.judge_panel = JudgePanel()

    def _on_page_changed(self, index: int):
        """Handle page change events."""
        # Update header title
        title = self.index_to_title.get(index, "Ski Jumping Simulator")
        self.header_title_label.setText(title)

        # Update active navigation button
        nav_buttons = [
            self._nav_btn_start,
            self._nav_btn_single,
            self._nav_btn_comp,
            self._nav_btn_editor,
            self._nav_btn_settings,
            self._nav_btn_support,
        ]

        for btn in nav_buttons:
            if btn:
                btn.setChecked(False)

        # Set active button based on index
        if index == self.MAIN_MENU_IDX and self._nav_btn_start:
            self._nav_btn_start.setChecked(True)
        elif index == self.SINGLE_JUMP_IDX and self._nav_btn_single:
            self._nav_btn_single.setChecked(True)
        elif index == self.COMPETITION_IDX and self._nav_btn_comp:
            self._nav_btn_comp.setChecked(True)
        elif index == self.DATA_EDITOR_IDX and self._nav_btn_editor:
            self._nav_btn_editor.setChecked(True)
        elif index == self.SETTINGS_IDX and self._nav_btn_settings:
            self._nav_btn_settings.setChecked(True)
        elif index == self.SUPPORT_IDX and self._nav_btn_support:
            self._nav_btn_support.setChecked(True)

    def _create_pages(self):
        """Create all application pages."""
        # Create pages in correct order according to indices
        self.central_widget.addWidget(create_main_menu(self))  # 0: MAIN_MENU_IDX

        # 1: SIM_TYPE_MENU_IDX - placeholder
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_widget)
        placeholder_label = QLabel(
            "Menu wyboru typu symulacji - w trakcie implementacji"
        )
        placeholder_label.setProperty("class", "heroLabel")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)
        self.central_widget.addWidget(placeholder_widget)

        self.central_widget.addWidget(
            create_single_jump_page(self)
        )  # 2: SINGLE_JUMP_IDX
        self.central_widget.addWidget(
            create_competition_page(self)
        )  # 3: COMPETITION_IDX
        self.central_widget.addWidget(
            create_data_editor_page(self)
        )  # 4: DATA_EDITOR_IDX

        # 5: DESCRIPTION_IDX - placeholder
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_widget)
        placeholder_label = QLabel("Opis projektu - w trakcie implementacji")
        placeholder_label.setProperty("class", "heroLabel")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)
        self.central_widget.addWidget(placeholder_widget)

        self.central_widget.addWidget(create_settings_page(self))  # 6: SETTINGS_IDX

        # 7: JUMP_REPLAY_IDX
        self.central_widget.addWidget(create_jump_replay_page(self))

        # 8: POINTS_BREAKDOWN_IDX
        self.central_widget.addWidget(create_points_breakdown_page(self))

        # 9: SUPPORT_IDX
        self.central_widget.addWidget(create_support_page(self))

    def _create_top_bar(self, title_text, back_index):
        """Create top bar with back button."""
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← Wróć")
        back_btn.clicked.connect(
            lambda: [self.play_sound(), self.central_widget.setCurrentIndex(back_index)]
        )
        back_btn.setFixedHeight(36)
        back_btn.setObjectName("backArrowButton")
        top_bar.addWidget(back_btn, 0, Qt.AlignLeft)
        top_bar.addStretch(1)
        return top_bar

    def _create_form_row(self, label_text, widget):
        """Create form row with label and widget."""
        row = QHBoxLayout()
        label = QLabel(label_text)
        # Stała szerokość etykiet, aby kolumna z polami wyrównywała się
        label.setFixedWidth(100)
        row.addWidget(label)
        # Pola wejściowe mają wypełniać dostępną szerokość i mieć wspólną minimalną szerokość
        try:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        except Exception:
            pass
        row.addWidget(widget)
        return row

    def _show_points_breakdown(
        self, jumper, distance, points, seria_num, judge_data=None
    ):
        """Wyświetla szczegółowy podział punktów za skok na pełnej stronie z animacją w tle."""
        from utils.calculations import get_meter_value

        k_point = self.competition_hill.K
        meter_value = get_meter_value(k_point)
        difference = distance - k_point

        # Aktualizuj tytuł i informacje
        self.points_title_label.setText(f"{jumper} - Seria {seria_num}")
        stats_text = (
            f"Odległość: {format_distance_with_unit(distance)}  |  "
            f"Punkty: {points:.1f} pkt  |  "
            f"K-point: {k_point:.1f} m"
        )
        self.points_info_label.setText(stats_text)

        # Clear existing breakdown cards
        while self.points_breakdown_layout.count() > 0:
            item = self.points_breakdown_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Calculate distance points
        distance_points = 60.0 + (difference * meter_value)

        # Create visual breakdown cards
        self._create_distance_card(
            distance, k_point, meter_value, difference, distance_points
        )

        if judge_data:
            self._create_judge_card(judge_data)

        self._create_total_card(distance_points, judge_data)

        # Aktualizuj informacje o skoczni
        self.points_hill_name.setText(f"Skocznia: {self.competition_hill}")
        self.points_gate_info.setText(f"Belka startowa: {self.competition_gate}")

        # Uruchom animację trajektorii w tle
        sim_data = self._calculate_trajectory(
            jumper, self.competition_hill, self.competition_gate
        )
        self._run_animation_on_canvas(
            self.points_canvas, self.points_figure, sim_data, self.competition_hill
        )

        # Przełącz na stronę podziału punktów
        self.central_widget.setCurrentIndex(self.POINTS_BREAKDOWN_IDX)

    def _show_total_points_breakdown(self, jumper, result_data, total_points):
        """Wyświetla dwie spójne tabele z punktami za I i II serię: za odległość, noty, suma."""
        from utils.calculations import get_meter_value

        k_point = self.competition_hill.K
        meter_value = get_meter_value(k_point)

        # Aktualizuj tytuł i informacje
        self.points_title_label.setText(f"{jumper} - Podsumowanie zawodów")
        stats_text = (
            f"Suma punktów: {total_points:.1f} pkt  |  "
            f"K-point: {k_point:.1f} m  |  "
            f"Meter value: {meter_value:.1f} pkt/m"
        )
        self.points_info_label.setText(stats_text)

        # Clear existing breakdown cards
        while self.points_breakdown_layout.count() > 0:
            item = self.points_breakdown_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # I seria – prosty, logiczny widok z trzema wartościami
        if result_data.get("d1", 0) > 0 and result_data.get("p1", 0) > 0:
            d1 = float(result_data["d1"])
            p1 = float(result_data["p1"])  # suma serii (odległość + noty)
            distance_points_1 = calculate_jump_points(d1, k_point)
            judges1 = result_data.get("judges1")
            judge_points_1 = (
                float(judges1["total_score"])
                if judges1
                else max(0.0, p1 - distance_points_1)
            )
            self._create_series_points_table(
                "I seria", distance_points_1, judge_points_1, p1
            )

        # II seria – analogicznie
        if result_data.get("d2", 0) > 0 and result_data.get("p2", 0) > 0:
            d2 = float(result_data["d2"])
            p2 = float(result_data["p2"])  # suma serii
            distance_points_2 = calculate_jump_points(d2, k_point)
            judges2 = result_data.get("judges2")
            judge_points_2 = (
                float(judges2["total_score"])
                if judges2
                else max(0.0, p2 - distance_points_2)
            )
            self._create_series_points_table(
                "II seria", distance_points_2, judge_points_2, p2
            )

        # Zwięzła karta sumy punktów pozostaje bez zmian
        self._create_total_card(total_points, None)

        # Aktualizuj informacje o skoczni
        self.points_hill_name.setText(f"Skocznia: {self.competition_hill}")
        self.points_gate_info.setText(f"Belka startowa: {self.competition_gate}")

        # Uruchom animację trajektorii w tle (użyj pierwszej serii jeśli dostępna)
        if result_data.get("d1", 0) > 0:
            sim_data = self._calculate_trajectory(
                jumper, self.competition_hill, self.competition_gate
            )
            self._run_animation_on_canvas(
                self.points_canvas, self.points_figure, sim_data, self.competition_hill
            )

        # Przełącz na stronę podziału punktów
        self.central_widget.setCurrentIndex(self.POINTS_BREAKDOWN_IDX)

    def _create_rounded_flag_pixmap(self, country_code, size=QSize(48, 33), radius=8):
        """Create rounded flag pixmap."""
        if not country_code:
            return QPixmap()
        flag_path = resource_path(
            os.path.join("assets", "flags", f"{country_code}.png")
        )
        if not os.path.exists(flag_path):
            return QPixmap()
        try:
            # Wysokiej jakości antyaliasing: rysuj maskę w skali i przeskaluj LANCZOS
            scale = 4
            target_w, target_h = size.width(), size.height()
            hi_w, hi_h = target_w * scale, target_h * scale
            with Image.open(flag_path) as img:
                img = img.convert("RGBA")
                img_resized = img.resize((hi_w, hi_h), Image.Resampling.LANCZOS)
            mask_hi = Image.new("L", (hi_w, hi_h), 0)
            draw = ImageDraw.Draw(mask_hi)
            draw.rounded_rectangle(
                ((0, 0), (hi_w, hi_h)), radius=radius * scale, fill=255
            )
            # Minimalne rozmycie krawędzi maski, by usunąć pikselowe rogi
            mask_hi = mask_hi.filter(ImageFilter.GaussianBlur(radius=scale * 0.35))
            img_resized.putalpha(mask_hi)
            # Downscale do docelowego rozmiaru z zachowaniem antyaliasingu
            final_img = img_resized.resize(
                (target_w, target_h), Image.Resampling.LANCZOS
            )
            qimage = QImage(
                final_img.tobytes("raw", "RGBA"),
                final_img.width,
                final_img.height,
                QImage.Format_RGBA8888,
            )
            return QPixmap.fromImage(qimage)
        except Exception as e:
            print(f"Error creating flag pixmap for {country_code}: {e}")
            return QPixmap()

    def _calculate_trajectory(self, jumper, hill, gate, timing_info=None):
        """Oblicza trajektorię do wyświetlenia."""
        early_shift = 0.0
        magnitude_scale = 1.0
        vertical_efficiency = 1.0
        if isinstance(timing_info, dict) and timing_info:
            try:
                eps_s = float(timing_info.get("epsilon_s_m", 0.0))
                early_shift = min(max(0.0, -eps_s), 1.0)
                magnitude_scale = float(timing_info.get("magnitude_scale", 1.0))
                vertical_efficiency = float(timing_info.get("vertical_efficiency", 1.0))
            except Exception:
                pass

        inrun_velocity = inrun_simulation(
            hill, jumper, gate_number=gate, early_takeoff_aero_shift_m=early_shift
        )

        base_cl = jumper.flight_lift_coefficient
        effective_cl = base_cl

        baseline_velocity_ms = 24.5
        max_bonus_velocity_ms = 28.5

        if inrun_velocity > baseline_velocity_ms:
            max_lift_bonus = 0.12

            velocity_factor = (inrun_velocity - baseline_velocity_ms) / (
                max_bonus_velocity_ms - baseline_velocity_ms
            )
            velocity_factor = min(1.0, max(0.0, velocity_factor))

            lift_bonus = max_lift_bonus * velocity_factor
            effective_cl = base_cl + lift_bonus

        positions = [(0, 0)]
        velocities = []
        current_position_x, current_position_y = 0, 0
        initial_total_velocity = inrun_velocity

        initial_velocity_x = initial_total_velocity * math.cos(-hill.alpha_rad)
        initial_velocity_y = initial_total_velocity * math.sin(-hill.alpha_rad)

        base_delta_v = (jumper.jump_force * 0.1) / jumper.mass
        velocity_takeoff = base_delta_v * magnitude_scale
        velocity_takeoff_x = velocity_takeoff * math.sin(hill.alpha_rad)
        velocity_takeoff_y = (
            velocity_takeoff * math.cos(hill.alpha_rad) * vertical_efficiency
        )

        velocity_x_final = initial_velocity_x + velocity_takeoff_x
        velocity_y_final = initial_velocity_y + velocity_takeoff_y

        takeoff_angle_rad = math.atan2(velocity_y_final, velocity_x_final)

        current_velocity_x = velocity_x_final
        current_velocity_y = velocity_y_final

        time_step = 0.01
        max_hill_length = (
            hill.n + hill.a_finish + 100
        )  # Zwiększ limit aby pokazać całą skocznię
        max_height = 0
        flight_time = 0

        while (
            current_position_y > hill.y_landing(current_position_x)
            and current_position_x < max_hill_length
        ):
            total_velocity = math.sqrt(current_velocity_x**2 + current_velocity_y**2)
            velocities.append(total_velocity)
            angle_of_flight_rad = math.atan2(current_velocity_y, current_velocity_x)
            force_g_y = -jumper.mass * 9.81

            c_d = jumper.flight_drag_coefficient
            c_l = effective_cl
            area = jumper.flight_frontal_area

            force_drag_magnitude = 0.5 * 1.225 * c_d * area * total_velocity**2
            force_drag_x = -force_drag_magnitude * math.cos(angle_of_flight_rad)
            force_drag_y = -force_drag_magnitude * math.sin(angle_of_flight_rad)
            force_lift_magnitude = 0.5 * 1.225 * c_l * area * total_velocity**2
            force_lift_x = -force_lift_magnitude * math.sin(angle_of_flight_rad)
            force_lift_y = force_lift_magnitude * math.cos(angle_of_flight_rad)

            acceleration_x = (force_drag_x + force_lift_x) / jumper.mass
            acceleration_y = (force_g_y + force_drag_y + force_lift_y) / jumper.mass

            current_velocity_x += acceleration_x * time_step
            current_velocity_y += acceleration_y * time_step
            current_position_x += current_velocity_x * time_step
            current_position_y += current_velocity_y * time_step
            # Calculate height above the landing area
            height_above_landing = current_position_y - hill.y_landing(
                current_position_x
            )
            max_height = max(max_height, height_above_landing)
            flight_time += time_step
            positions.append((current_position_x, current_position_y))

        x_landing = np.linspace(
            0, hill.n + hill.a_finish + 50, 100
        )  # Zawsze pokazuj całą skocznię
        y_landing = [hill.y_landing(x_val) for x_val in x_landing]

        # Calculate additional statistics
        max_velocity = max(velocities) if velocities else 0
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0

        return {
            "positions": positions,
            "x_landing": x_landing,
            "y_landing": y_landing,
            "max_height": max_height,
            "max_hill_length": max_hill_length,
            "inrun_velocity_kmh": inrun_velocity * 3.6,
            "takeoff_angle_deg": math.degrees(takeoff_angle_rad),
            "flight_time": flight_time,
            "max_velocity_kmh": max_velocity * 3.6,
            "avg_velocity_kmh": avg_velocity * 3.6,
        }

    def _run_animation_on_canvas(self, canvas, figure, sim_data, hill):
        """Run animation on canvas."""
        # Zatrzymaj poprzednią animację jeśli istnieje
        # Użyj różnych zmiennych animacji dla różnych canvasów
        if canvas == getattr(self, "points_canvas", None):
            animation_var = "points_ani"
        elif canvas == getattr(self, "replay_canvas", None):
            animation_var = "replay_ani"
        else:
            animation_var = "ani"  # fallback dla innych canvasów

        # Zatrzymaj wszystkie animacje dla tego canvasu
        for var in ["ani", "points_ani", "replay_ani", "zoom_ani"]:
            if hasattr(self, var) and getattr(self, var) is not None:
                try:
                    current_ani = getattr(self, var)
                    if (
                        hasattr(current_ani, "event_source")
                        and current_ani.event_source is not None
                    ):
                        current_ani.event_source.stop()
                except Exception:
                    pass  # Ignoruj błędy przy zatrzymywaniu animacji
                setattr(self, var, None)

        # Wyczyść figure przed rozpoczęciem nowej animacji
        figure.clear()
        ax = figure.add_subplot(111)
        # Ciemne tło zgodne z motywem
        ax.set_facecolor("#0f1115")
        figure.patch.set_facecolor("#0f1115")
        ax.axis("off")
        ax.set_aspect("auto")

        inrun_length_to_show = 15.0
        x_inrun = np.linspace(-inrun_length_to_show, 0, 50)
        y_inrun = np.tan(-hill.alpha_rad) * x_inrun
        ax.plot(x_inrun, y_inrun, color="#4c84ff", linewidth=2.5)

        max_y_inrun = y_inrun[0] if len(y_inrun) > 0 else 0
        # Poprawione limity - animacja będzie wyżej i ładniej sformatowana
        ax.set_xlim(-inrun_length_to_show - 5, hill.n + hill.a_finish + 30)
        ax.set_ylim(
            min(min(sim_data["y_landing"]), 0) - 3,
            max(sim_data["max_height"] * 1.3, max_y_inrun) + 3,
        )

        (jumper_point,) = ax.plot(
            [],
            [],
            "o",
            color="#e8eaf1",
            markersize=7,
            markeredgecolor="#4c84ff",
            markeredgewidth=1.5,
        )
        (trail_line,) = ax.plot([], [], color="#5b90ff", linewidth=2.5, alpha=0.7)
        (landing_line,) = ax.plot([], [], color="#4c84ff", linewidth=3, alpha=0.8)
        plot_elements = [jumper_point, trail_line, landing_line]

        def init():
            for element in plot_elements:
                element.set_data([], [])
            return plot_elements

        def update(frame):
            positions, x_landing, y_landing = (
                sim_data["positions"],
                sim_data["x_landing"],
                sim_data["y_landing"],
            )
            if frame >= max(len(positions), len(x_landing)):
                # Zatrzymaj animację gdy się skończy
                try:
                    current_ani = getattr(self, animation_var)
                    if (
                        hasattr(current_ani, "event_source")
                        and current_ani.event_source is not None
                    ):
                        current_ani.event_source.stop()
                except Exception:
                    pass
                setattr(self, animation_var, None)
                return plot_elements
            if frame < len(positions):
                x, y = positions[frame]
                jumper_point.set_data([x], [y])
                trail_line.set_data(
                    [p[0] for p in positions[: frame + 1]],
                    [p[1] for p in positions[: frame + 1]],
                )
            if frame < len(x_landing):
                landing_line.set_data(x_landing[:frame], y_landing[:frame])
            return plot_elements

        new_ani = animation.FuncAnimation(
            figure,
            update,
            init_func=init,
            frames=max(len(sim_data["positions"]), len(sim_data["x_landing"])),
            interval=8,
            blit=False,
            repeat=False,
        )
        setattr(self, animation_var, new_ani)
        canvas.draw()

    def create_rounded_flag_icon(self, country_code, radius=6):
        """Create rounded flag icon."""
        pixmap = self._create_rounded_flag_pixmap(
            country_code, size=QSize(32, 22), radius=radius
        )
        if pixmap.isNull():
            return QIcon()
        return QIcon(pixmap)

    def update_jumper(self):
        """Update selected jumper."""
        if self.jumper_combo.currentIndex() > 0:
            self.selected_jumper = self.all_jumpers[
                self.jumper_combo.currentIndex() - 1
            ]
        else:
            self.selected_jumper = None

    def update_hill(self):
        """Update selected hill."""
        if self.hill_combo.currentIndex() > 0:
            self.selected_hill = self.all_hills[self.hill_combo.currentIndex() - 1]
            if self.selected_hill:
                self.gate_spin.setMaximum(self.selected_hill.gates)
        else:
            self.selected_hill = None

    def clear_results(self):
        """Clear simulation results."""
        self.jumper_combo.setCurrentIndex(0)
        self.hill_combo.setCurrentIndex(0)
        self.gate_spin.setValue(1)
        self.single_jump_stats_label.setText(
            "Wybierz zawodnika i skocznię, aby rozpocząć symulację"
        )
        self.single_jump_stats_label.setProperty("chip", True)
        self.single_jump_stats_label.setProperty("variant", "info")
        self.single_jump_stats_label.setStyleSheet("")
        if hasattr(self, "figure"):
            self.figure.clear()
            self.canvas.draw()
        # Zatrzymaj wszystkie animacje
        for animation_var in ["ani", "points_ani", "replay_ani", "zoom_ani"]:
            if (
                hasattr(self, animation_var)
                and getattr(self, animation_var) is not None
            ):
                try:
                    current_ani = getattr(self, animation_var)
                    if (
                        hasattr(current_ani, "event_source")
                        and current_ani.event_source is not None
                    ):
                        current_ani.event_source.stop()
                except Exception:
                    pass  # Ignoruj błędy przy zatrzymywaniu animacji
                setattr(self, animation_var, None)

    def run_simulation(self):
        """Run single jump simulation."""
        self.play_sound()
        if not self.selected_jumper or not self.selected_hill:
            self.single_jump_stats_label.setText(
                "BŁĄD: Musisz wybrać zawodnika i skocznię!"
            )
            self.single_jump_stats_label.setProperty("chip", True)
            self.single_jump_stats_label.setProperty("variant", "danger")
            self.single_jump_stats_label.setStyleSheet("")
            return
        gate = self.gate_spin.value()

        try:
            sim_data = self._calculate_trajectory(
                self.selected_jumper, self.selected_hill, gate
            )
            raw_distance = fly_simulation(
                self.selected_hill, self.selected_jumper, gate, perfect_timing=True
            )
            distance = round_distance_to_half_meter(raw_distance)

            # Oblicz punkty za skok
            points = calculate_jump_points(distance, self.selected_hill.K)

            # Wyświetl statystyki w tym samym stylu co w zawodach
            stats_text = (
                f"Odległość: {format_distance_with_unit(distance)}  |  "
                f"Prędkość na progu: {sim_data['inrun_velocity_kmh']:.2f} km/h  |  "
                f"Kąt wybicia: {sim_data['takeoff_angle_deg']:.2f}°  |  "
                f"Max wysokość: {sim_data['max_height']:.1f} m  |  "
                f"Czas lotu: {sim_data['flight_time']:.2f} s  |  "
                f"Max prędkość: {sim_data['max_velocity_kmh']:.1f} km/h  |  "
                f"Punkty: {points:.1f} pkt"
            )

            self.single_jump_stats_label.setText(stats_text)
            self.single_jump_stats_label.setProperty("chip", True)
            self.single_jump_stats_label.setProperty("variant", "success")
            self.single_jump_stats_label.setStyleSheet("")

            self._run_animation_on_canvas(
                self.canvas, self.figure, sim_data, self.selected_hill
            )

        except ValueError as e:
            self.single_jump_stats_label.setText(f"BŁĄD: {str(e)}")
            self.single_jump_stats_label.setProperty("chip", True)
            self.single_jump_stats_label.setProperty("variant", "danger")
            self.single_jump_stats_label.setStyleSheet("")

    def _toggle_all_jumpers(self):
        """Toggle all jumpers selection."""
        self.play_sound()
        checked_count = sum(
            1
            for i in range(self.jumper_list_widget.count())
            if self.jumper_list_widget.item(i).checkState() == Qt.Checked
        )

        if checked_count < self.jumper_list_widget.count():
            new_state = Qt.Checked
            self.toggle_all_button.setText("Odznacz wszystkich")
            self.toggle_all_button.setProperty("variant", "danger")
        else:
            new_state = Qt.Unchecked
            self.toggle_all_button.setText("Zaznacz wszystkich")
            self.toggle_all_button.setProperty("variant", "primary")

        self.jumper_list_widget.itemChanged.disconnect(self._on_jumper_item_changed)
        for i in range(self.jumper_list_widget.count()):
            self.jumper_list_widget.item(i).setCheckState(new_state)
        self.jumper_list_widget.itemChanged.connect(self._on_jumper_item_changed)

        self.selection_order.clear()
        if new_state == Qt.Checked:
            self.selection_order = [
                self.jumper_list_widget.item(i).data(Qt.UserRole)
                for i in range(self.jumper_list_widget.count())
            ]

        # Aktualizuj licznik wybranych zawodników po zmianie stanu (niebieski)
        if hasattr(self, "selected_count_label"):
            count = len(self.selection_order)
            self.selected_count_label.setText(f"Wybrano: {count} zawodników")
            self.selected_count_label.setProperty("variant", "primary")

        # Aktualizuj rekomendowaną belkę jeśli skocznia jest wybrana
        if hasattr(self, "comp_hill_combo") and self.comp_hill_combo.currentIndex() > 0:
            hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
            self._update_recommended_gate(hill)

    def _sort_jumper_list(self, sort_text):
        """Sort jumper list."""
        items_data = []
        for i in range(self.jumper_list_widget.count()):
            item = self.jumper_list_widget.item(i)
            jumper = item.data(Qt.UserRole)
            check_state = item.checkState()
            items_data.append((jumper, check_state))

        if sort_text == "Wg Kraju":
            items_data.sort(key=lambda data: (data[0].nationality, str(data[0])))
        else:
            items_data.sort(key=lambda data: str(data[0]))

        self.jumper_list_widget.itemChanged.disconnect(self._on_jumper_item_changed)
        self.jumper_list_widget.clear()

        for jumper, check_state in items_data:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(check_state)
            item.setData(Qt.UserRole, jumper)
            self.jumper_list_widget.addItem(item)

        self.jumper_list_widget.itemChanged.connect(self._on_jumper_item_changed)

    def _on_jumper_item_changed(self, item):
        """Handle jumper item change."""
        jumper = item.data(Qt.UserRole)
        if item.checkState() == Qt.Checked:
            if jumper not in self.selection_order:
                self.selection_order.append(jumper)
        else:
            if jumper in self.selection_order:
                self.selection_order.remove(jumper)

        # Aktualizuj licznik wybranych zawodników
        if hasattr(self, "selected_count_label"):
            count = len(self.selection_order)
            self.selected_count_label.setText(f"Wybrano: {count} zawodników")

        # Aktualizuj rekomendowaną belkę jeśli skocznia jest wybrana
        if hasattr(self, "comp_hill_combo") and self.comp_hill_combo.currentIndex() > 0:
            hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
            self._update_recommended_gate(hill)

    def update_competition_hill(self):
        """Update competition hill."""
        if self.comp_hill_combo.currentIndex() > 0:
            hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
            if hill:
                self.competition_hill = hill
                self.competition_gate = self.comp_gate_spin.value()
                self.comp_gate_spin.setMaximum(hill.gates)
                # Oblicz rekomendowaną belkę dla wybranych zawodników
                self._update_recommended_gate(hill)
        else:
            hill = None
            self.competition_hill = None
            self.competition_gate = None
            # Ukryj informację o rekomendowanej belce
            if hasattr(self, "recommended_gate_label"):
                self.recommended_gate_label.setVisible(False)

    def _on_gate_changed(self):
        """Handle gate value change."""
        if hasattr(self, "competition_hill") and self.competition_hill:
            self.competition_gate = self.comp_gate_spin.value()
            # Oblicz rekomendowaną belkę dla wybranych zawodników
            self._update_recommended_gate(self.competition_hill)

    def _update_recommended_gate(self, hill):
        """Update recommended gate."""
        if not hasattr(self, "recommended_gate_label") or not hasattr(
            self, "gate_info_label"
        ):
            return

        if not self.selection_order:
            self.recommended_gate_label.setVisible(False)
            self.gate_info_label.setVisible(False)
            return

        # Zatrzymaj poprzedni worker jeśli istnieje
        if (
            hasattr(self, "recommended_gate_worker")
            and self.recommended_gate_worker.isRunning()
        ):
            self.recommended_gate_worker.quit()
            self.recommended_gate_worker.wait()

        # Pokaż wskaźnik ładowania
        self.recommended_gate_label.setText("Obliczanie rekomendacji...")
        self.recommended_gate_label.setProperty("variant", "primary")
        self.recommended_gate_label.setVisible(True)
        self.gate_info_label.setVisible(False)

        # Utwórz i uruchom worker w osobnym wątku
        self.recommended_gate_worker = RecommendedGateWorker(hill, self.selection_order)
        self.recommended_gate_worker.calculation_finished.connect(
            self._on_recommended_gate_calculated
        )
        self.recommended_gate_worker.start()

    def _on_recommended_gate_calculated(self, recommended_gate, max_distance):
        """Handle recommended gate calculation finished."""
        if not hasattr(self, "recommended_gate_label") or not hasattr(
            self, "gate_info_label"
        ):
            return

        # Przywróć styl chip "info"
        self.recommended_gate_label.setProperty("variant", "info")

        # Aktualizuj wyświetlanie
        self.recommended_gate_label.setText(f"Rekomendowana: {recommended_gate}")
        self.recommended_gate_label.setVisible(True)

        # Ukryj informację o maksymalnej odległości
        self.gate_info_label.setVisible(False)

    def _on_competition_button_clicked(self):
        """Handle competition button click."""
        self.play_sound()

        # Sprawdź aktualny stan przycisku i wykonaj odpowiednią akcję
        button_text = self.run_comp_btn.text()

        if button_text == "Rozpocznij zawody":
            # Rozpocznij zawody
            self._start_competition()
        elif button_text == "Stop":
            # Zatrzymaj zawody
            self._stop_competition()
        elif button_text == "Kontynuuj":
            # Kontynuuj zawody
            self._continue_competition()
        elif button_text == "Rozpocznij I serię":
            # Rozpocznij pierwszą serię konkursu
            self._start_first_round()
        elif button_text == "Rozpocznij II serię":
            # Rozpocznij drugą serię
            self._start_second_round()

    def _start_competition(self):
        """Rozpocznij zawody."""
        if not self.selection_order:
            QMessageBox.warning(
                self, "Błąd", "Musisz wybrać przynajmniej jednego zawodnika!"
            )
            return

        if self.comp_hill_combo.currentIndex() == 0:
            QMessageBox.warning(self, "Błąd", "Musisz wybrać skocznię!")
            return

        # Inicjalizuj zawody
        self.competition_results = []
        self.current_jumper_index = 0
        self.current_round = 1
        self.simulation_running = True
        self.qualification_phase = self.qualification_checkbox.isChecked()

        # Przygotuj listę zawodników do konkursu
        if self.qualification_phase:
            # Faza kwalifikacji
            self._start_qualification()
        else:
            # Bezpośrednio konkurs
            self._start_first_round()

    def _start_qualification(self):
        """Rozpocznij kwalifikacje."""
        self.qualification_table.setVisible(True)
        self.results_table.setVisible(False)
        self._update_status_label("Kwalifikacje w toku...", "warning")
        self._update_competition_button("Stop", variant="danger")
        self.round_info_label.setText("Kwalifikacje")

        # Rozpocznij symulację kwalifikacji
        from PySide6.QtCore import QTimer

        QTimer.singleShot(500, self._process_qualification_jumper)

    def _process_qualification_jumper(self):
        """Przetwórz kolejnego zawodnika w kwalifikacjach."""
        if not self.simulation_running or self.current_jumper_index >= len(
            self.selection_order
        ):
            self._finish_qualification()
            return

        jumper = self.selection_order[self.current_jumper_index]
        hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
        gate = self.comp_gate_spin.value()

        # Symuluj skok
        try:
            distance = fly_simulation(hill, jumper, gate, perfect_timing=True)
            points = calculate_jump_points(distance, hill.K)

            # Dodaj do wyników kwalifikacji
            self.competition_results.append(
                {"jumper": jumper, "distance": distance, "points": points}
            )

            # Aktualizuj tabelę kwalifikacji
            self._update_qualification_table()

            # Aktualizuj postęp
            progress = int(
                (self.current_jumper_index + 1) / len(self.selection_order) * 100
            )
            self.progress_label.setText(f"Postęp: {progress}%")

        except Exception as e:
            print(f"Błąd symulacji dla {jumper}: {e}")

        self.current_jumper_index += 1

        # Kontynuuj z następnym zawodnikiem
        if self.simulation_running:
            from PySide6.QtCore import QTimer

            QTimer.singleShot(100, self._process_qualification_jumper)

    def _finish_qualification(self):
        """Zakończ kwalifikacje i przejdź do konkursu."""
        # Sortuj wyniki kwalifikacji
        self.competition_results.sort(key=lambda x: x["points"], reverse=True)

        # Wybierz najlepszych do konkursu (np. top 50)
        qualified_count = min(50, len(self.competition_results))
        self.selection_order = [
            r["jumper"] for r in self.competition_results[:qualified_count]
        ]

        # Przejdź do konkursu
        self._start_first_round()

    def _start_first_round(self):
        """Rozpocznij pierwszą serię konkursu."""
        self.simulation_running = True
        self.qualification_phase = False
        self.current_jumper_index = 0
        self.current_round = 1

        # Pokaż tabelę konkursu, ukryj tabelę kwalifikacji
        self.results_table.setVisible(True)
        self.qualification_table.setVisible(False)

        # Aktualizuj informację o serii
        self.round_info_label.setText("Seria: 1/2")
        self._update_status_label("I seria w toku...", "success")
        self._update_competition_button("Stop", variant="danger")

        # Rozpocznij symulację
        from PySide6.QtCore import QTimer

        QTimer.singleShot(500, self._process_competition_jumper)

    def _start_second_round(self):
        """Rozpocznij drugą serię konkursu."""
        self.simulation_running = True
        self.current_jumper_index = 0
        self.current_round = 2

        # Aktualizuj informację o serii
        self.round_info_label.setText("Seria: 2/2")
        self._update_status_label("II seria w toku...", "success")
        self._update_competition_button("Stop", variant="danger")

        # Rozpocznij symulację
        from PySide6.QtCore import QTimer

        QTimer.singleShot(500, self._process_competition_jumper)

    def _process_competition_jumper(self):
        """Przetwórz kolejnego zawodnika w konkursie."""
        if not self.simulation_running or self.current_jumper_index >= len(
            self.selection_order
        ):
            if self.current_round == 1:
                self._finish_first_round()
            else:
                self._finish_competition()
            return

        jumper = self.selection_order[self.current_jumper_index]
        hill = self.all_hills[self.comp_hill_combo.currentIndex() - 1]
        gate = self.comp_gate_spin.value()

        # Symuluj skok
        try:
            distance = fly_simulation(hill, jumper, gate, perfect_timing=True)
            points = calculate_jump_points(distance, hill.K)

            # Dodaj do wyników konkursu
            if self.current_round == 1:
                # Pierwsza seria
                self.competition_results.append(
                    {"jumper": jumper, "d1": distance, "p1": points, "d2": 0, "p2": 0}
                )
            else:
                # Druga seria - znajdź zawodnika i dodaj wyniki
                for result in self.competition_results:
                    if result["jumper"] == jumper:
                        result["d2"] = distance
                        result["p2"] = points
                        break

            # Aktualizuj tabelę wyników
            self._update_competition_table()

            # Aktualizuj postęp
            progress = int(
                (self.current_jumper_index + 1) / len(self.selection_order) * 100
            )
            self.progress_label.setText(f"Postęp: {progress}%")

        except Exception as e:
            print(f"Błąd symulacji dla {jumper}: {e}")

        self.current_jumper_index += 1

        # Kontynuuj z następnym zawodnikiem
        if self.simulation_running:
            from PySide6.QtCore import QTimer

            QTimer.singleShot(100, self._process_competition_jumper)

    def _finish_first_round(self):
        """Zakończ pierwszą serię."""
        # Sortuj wyniki po pierwszej serii
        self.competition_results.sort(key=lambda x: x.get("p1", 0), reverse=True)
        self._update_competition_table()

        # Zmień przycisk na rozpoczęcie drugiej serii
        self._update_competition_button("Rozpocznij II serię", variant="warning")
        self._update_status_label(
            "I seria zakończona. Kliknij 'Rozpocznij II serię'.", "warning"
        )

    def _finish_competition(self):
        """Zakończ zawody."""
        # Sortuj wyniki po sumie punktów
        self.competition_results.sort(
            key=lambda x: (x.get("p1", 0) + x.get("p2", 0)), reverse=True
        )
        self._update_competition_table()

        # Zmień przycisk na rozpoczęcie nowych zawodów
        self._update_competition_button("Rozpocznij zawody", variant="success")
        self._update_status_label(
            "Zawody zakończone! Kliknij 'Rozpocznij zawody' aby rozpocząć nowe.",
            "success",
        )
        self.progress_label.setText("Postęp: 100%")

    def _stop_competition(self):
        """Zatrzymaj zawody."""
        self.simulation_running = False
        self._update_status_label(
            "Symulacja zatrzymana. Kliknij 'Kontynuuj' aby wznowić.", "danger"
        )
        self._update_competition_button("Kontynuuj", variant="primary")

    def _continue_competition(self):
        """Kontynuuj zawody."""
        self.simulation_running = True
        self._update_status_label("Zawody w toku...", "success")
        self._update_competition_button("Stop", variant="danger")

        # Wznów symulację
        from PySide6.QtCore import QTimer

        if self.qualification_phase:
            QTimer.singleShot(500, self._process_qualification_jumper)
        else:
            QTimer.singleShot(500, self._process_competition_jumper)

    def _update_competition_button(self, text, variant=None):
        """Aktualizuj tekst i wariant przycisku zawodów."""
        self.run_comp_btn.setText(text)
        if variant:
            self.run_comp_btn.setProperty("variant", variant)
            self.run_comp_btn.style().unpolish(self.run_comp_btn)
            self.run_comp_btn.style().polish(self.run_comp_btn)

    def _update_status_label(self, text, variant):
        """Aktualizuj status label z odpowiednim kolorem."""
        self.competition_status_label.setText(text)
        self.competition_status_label.setProperty("variant", variant)
        self.competition_status_label.setProperty("chip", True)
        self.competition_status_label.style().unpolish(self.competition_status_label)
        self.competition_status_label.style().polish(self.competition_status_label)
        self.competition_status_label.update()

    def _update_competition_table(self):
        """Aktualizuj tabelę wyników konkursu."""
        self.results_table.setRowCount(len(self.competition_results))
        for i, res in enumerate(self.competition_results):
            jumper = res["jumper"]

            # Miejsce
            place_item = QTableWidgetItem(str(i + 1))
            place_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 0, place_item)

            # Flaga kraju
            flag_pix = self._create_rounded_flag_pixmap(
                jumper.nationality, size=QSize(24, 16), radius=4
            )
            flag_container = QWidget()
            flag_layout = QHBoxLayout(flag_container)
            flag_layout.setContentsMargins(0, 0, 0, 0)
            flag_layout.setSpacing(0)
            flag_label = QLabel()
            if not flag_pix.isNull():
                flag_label.setPixmap(flag_pix)
            flag_label.setAlignment(Qt.AlignCenter)
            flag_layout.addStretch(1)
            flag_layout.addWidget(flag_label, 0, Qt.AlignCenter)
            flag_layout.addStretch(1)
            self.results_table.setCellWidget(i, 1, flag_container)

            # Nazwa zawodnika
            jumper_item = QTableWidgetItem(str(jumper))
            f = jumper_item.font()
            f.setBold(True)
            jumper_item.setFont(f)
            self.results_table.setItem(i, 2, jumper_item)

            # I seria - dystans
            d1_item = QTableWidgetItem()
            d1_item.setText(format_distance_with_unit(res.get("d1", 0))) if res.get(
                "d1", 0
            ) > 0 else d1_item.setText("-")
            d1_item.setTextAlignment(Qt.AlignCenter)
            f = d1_item.font()
            f.setBold(True)
            d1_item.setFont(f)
            self.results_table.setItem(i, 3, d1_item)

            # I seria - punkty
            p1_item = QTableWidgetItem()
            p1_item.setText(f"{res.get('p1', 0):.1f}") if res.get(
                "p1", 0
            ) > 0 else p1_item.setText("-")
            p1_item.setTextAlignment(Qt.AlignCenter)
            f = p1_item.font()
            f.setBold(True)
            p1_item.setFont(f)
            self.results_table.setItem(i, 4, p1_item)

            # II seria - dystans
            d2_item = QTableWidgetItem()
            d2_item.setText(format_distance_with_unit(res.get("d2", 0))) if res.get(
                "d2", 0
            ) > 0 else d2_item.setText("-")
            d2_item.setTextAlignment(Qt.AlignCenter)
            f = d2_item.font()
            f.setBold(True)
            d2_item.setFont(f)
            self.results_table.setItem(i, 5, d2_item)

            # II seria - punkty
            p2_item = QTableWidgetItem()
            p2_item.setText(f"{res.get('p2', 0):.1f}") if res.get(
                "p2", 0
            ) > 0 else p2_item.setText("-")
            p2_item.setTextAlignment(Qt.AlignCenter)
            f = p2_item.font()
            f.setBold(True)
            p2_item.setFont(f)
            self.results_table.setItem(i, 6, p2_item)

            # Suma punktów
            total_points = res.get("p1", 0) + res.get("p2", 0)
            total_item = QTableWidgetItem()
            total_item.setText(
                f"{total_points:.1f}"
            ) if total_points > 0 else total_item.setText("-")
            f_total = total_item.font()
            f_total.setBold(True)
            total_item.setFont(f_total)
            total_item.setTextAlignment(Qt.AlignCenter)
            self.results_table.setItem(i, 7, total_item)

    def _update_qualification_table(self):
        """Aktualizuj tabelę kwalifikacji."""
        self.qualification_table.setRowCount(len(self.competition_results))
        for i, res in enumerate(self.competition_results):
            jumper = res["jumper"]

            # Miejsce
            place_item = QTableWidgetItem(str(i + 1))
            place_item.setTextAlignment(Qt.AlignCenter)
            self.qualification_table.setItem(i, 0, place_item)

            # Flaga kraju
            flag_pix = self._create_rounded_flag_pixmap(
                jumper.nationality, size=QSize(24, 16), radius=4
            )
            flag_container = QWidget()
            flag_layout = QHBoxLayout(flag_container)
            flag_layout.setContentsMargins(0, 0, 0, 0)
            flag_layout.setSpacing(0)
            flag_label = QLabel()
            if not flag_pix.isNull():
                flag_label.setPixmap(flag_pix)
            flag_label.setAlignment(Qt.AlignCenter)
            flag_layout.addStretch(1)
            flag_layout.addWidget(flag_label, 0, Qt.AlignCenter)
            flag_layout.addStretch(1)
            self.qualification_table.setCellWidget(i, 1, flag_container)

            # Nazwa zawodnika
            jumper_item = QTableWidgetItem(str(jumper))
            f = jumper_item.font()
            f.setBold(True)
            jumper_item.setFont(f)
            self.qualification_table.setItem(i, 2, jumper_item)

            # Dystans
            distance_item = QTableWidgetItem(format_distance_with_unit(res["distance"]))
            distance_item.setTextAlignment(Qt.AlignCenter)
            f = distance_item.font()
            f.setBold(True)
            distance_item.setFont(f)
            self.qualification_table.setItem(i, 3, distance_item)

            # Punkty
            points_item = QTableWidgetItem(f"{res['points']:.1f}")
            points_item.setTextAlignment(Qt.AlignCenter)
            f = points_item.font()
            f.setBold(True)
            points_item.setFont(f)
            self.qualification_table.setItem(i, 4, points_item)

    def _on_result_cell_clicked(self, row, column):
        self.play_sound()

        if row >= len(self.competition_results):
            return

        result_data = self.competition_results[row]
        jumper = result_data["jumper"]

        # Klik na kolumnę 2 (Zawodnik) – obecnie bez akcji
        if column == 2:
            return

        # Kolumny z dystansami to 3 (I seria) i 5 (II seria)
        if column in [3, 5]:
            seria_num = 1 if column == 3 else 2
            distance_str = self.results_table.item(row, column).text()

            if distance_str == "-":
                return

            try:
                # Extract distance value from format like "123.5 m"
                distance = float(distance_str.replace(" m", ""))
                # Użyj timingu zapisanej serii, jeśli dostępny; w innym razie fallback
                ti = result_data.get(f"timing{seria_num}") or getattr(
                    jumper, "last_timing_info", None
                )

                self._show_jump_replay(
                    jumper,
                    self.competition_hill,
                    self.competition_gate,
                    distance,
                    seria_num,
                    ti,
                )
            except (ValueError, TypeError):
                return

        # Kolumny z punktami to 4 (I seria) i 6 (II seria) - tutaj będą wyświetlane noty sędziów
        elif column in [4, 6]:
            seria_num = 1 if column == 4 else 2
            points_str = self.results_table.item(row, column).text()

            if points_str == "-":
                return

            try:
                points = float(points_str)
                distance = result_data[f"d{seria_num}"]
                judge_data = result_data[f"judges{seria_num}"]

                # Pokaż podział punktów z notami sędziów jeśli dostępne
                self._show_points_breakdown(
                    jumper,
                    distance,
                    points,
                    seria_num,
                    judge_data,
                )
            except (ValueError, TypeError):
                return

        # Kolumna z sumą punktów to 7
        elif column == 7:
            total_points_str = self.results_table.item(row, column).text()

            if total_points_str == "-":
                return

            try:
                total_points = float(total_points_str)
                self._show_total_points_breakdown(
                    jumper,
                    result_data,
                    total_points,
                )
            except (ValueError, TypeError):
                return

    def _on_qualification_cell_clicked(self, row, column):
        self.play_sound()

        if row >= len(self.qualification_results):
            return

        result_data = self.qualification_results[row]
        jumper = result_data["jumper"]

        # Klik na kolumnę 2 (Zawodnik) – obecnie bez akcji
        if column == 2:
            return

        # Kolumny z dystansami to 3 (I seria) i 5 (II seria)
        if column in [3, 5]:
            seria_num = 1 if column == 3 else 2
            distance_str = self.qualification_table.item(row, column).text()

            if distance_str == "-":
                return

            try:
                # Extract distance value from format like "123.5 m"
                distance = float(distance_str.replace(" m", ""))
                # Użyj timingu zapisanej serii, jeśli dostępny; w innym razie fallback
                ti = result_data.get(f"timing{seria_num}") or getattr(
                    jumper, "last_timing_info", None
                )

                self._show_jump_replay(
                    jumper,
                    self.competition_hill,
                    self.competition_gate,
                    distance,
                    seria_num,
                    ti,
                )
            except (ValueError, TypeError):
                return

        # Kolumny z punktami to 4 (I seria) i 6 (II seria) - tutaj będą wyświetlane noty sędziów
        elif column in [4, 6]:
            seria_num = 1 if column == 4 else 2
            points_str = self.qualification_table.item(row, column).text()

            if points_str == "-":
                return

            try:
                points = float(points_str)
                distance = result_data[f"d{seria_num}"]
                judge_data = result_data[f"judges{seria_num}"]

                # Pokaż podział punktów z notami sędziów jeśli dostępne
                self._show_points_breakdown(
                    jumper,
                    distance,
                    points,
                    seria_num,
                    judge_data,
                )
            except (ValueError, TypeError):
                return

        # Kolumna z sumą punktów to 7
        elif column == 7:
            total_points_str = self.qualification_table.item(row, column).text()

            if total_points_str == "-":
                return

            try:
                total_points = float(total_points_str)
                self._show_total_points_breakdown(
                    jumper,
                    result_data,
                    total_points,
                )
            except (ValueError, TypeError):
                return

    def _repopulate_editor_lists(self):
        """Repopulate editor lists."""
        # Clear existing items
        self.editor_jumper_list.clear()
        self.editor_hill_list.clear()

        # Add jumpers
        for jumper in self.all_jumpers:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )
            item.setData(Qt.UserRole, jumper)
            self.editor_jumper_list.addItem(item)

        # Add hills
        for hill in self.all_hills:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )
            item.setData(Qt.UserRole, hill)
            self.editor_hill_list.addItem(item)

    def _populate_editor_form(self, current, previous):
        """Populate editor form."""
        if not current:
            self.editor_form_stack.setCurrentIndex(0)
            return

        data_obj = current.data(Qt.UserRole)
        if isinstance(
            data_obj, type(self.all_jumpers[0]) if self.all_jumpers else None
        ):
            self.editor_form_stack.setCurrentIndex(1)
        elif isinstance(data_obj, type(self.all_hills[0]) if self.all_hills else None):
            self.editor_form_stack.setCurrentIndex(2)
        else:
            self.editor_form_stack.setCurrentIndex(0)

    def _sort_editor_lists(self, sort_text):
        """Sort editor lists."""
        current_tab = self.editor_tab_widget.currentIndex()

        if current_tab == 0:  # Jumpers
            items = []
            for i in range(self.editor_jumper_list.count()):
                item = self.editor_jumper_list.item(i)
                items.append((item.data(Qt.UserRole), item))

            if sort_text == "Wg Kraju (A-Z)":
                items.sort(key=lambda x: (x[0].nationality, str(x[0])))
            else:  # Alfabetycznie (A-Z)
                items.sort(key=lambda x: str(x[0]))

            self.editor_jumper_list.clear()
            for _, item in items:
                self.editor_jumper_list.addItem(item)

        elif current_tab == 1:  # Hills
            items = []
            for i in range(self.editor_hill_list.count()):
                item = self.editor_hill_list.item(i)
                items.append((item.data(Qt.UserRole), item))

            if sort_text == "Wg Kraju (A-Z)":
                items.sort(key=lambda x: (x[0].country, str(x[0])))
            else:  # Alfabetycznie (A-Z)
                items.sort(key=lambda x: str(x[0]))

            self.editor_hill_list.clear()
            for _, item in items:
                self.editor_hill_list.addItem(item)

    def _filter_editor_lists(self):
        """Filter editor lists."""
        search_text = self.editor_search_bar.text().lower()
        current_tab = self.editor_tab_widget.currentIndex()

        if current_tab == 0:  # Jumpers
            for i in range(self.editor_jumper_list.count()):
                item = self.editor_jumper_list.item(i)
                jumper = item.data(Qt.UserRole)
                item_text = str(jumper).lower()
                item.setHidden(search_text not in item_text)

        elif current_tab == 1:  # Hills
            for i in range(self.editor_hill_list.count()):
                item = self.editor_hill_list.item(i)
                hill = item.data(Qt.UserRole)
                item_text = str(hill).lower()
                item.setHidden(search_text not in item_text)

    def _clone_selected_item(self):
        """Clone selected item."""
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()

        if current_tab_index == 0:  # Skoczkowie
            selected_item = self.editor_jumper_list.currentItem()
            if not selected_item:
                QMessageBox.information(
                    self,
                    "Informacja",
                    "Aby sklonować skoczka, najpierw zaznacz go na liście.",
                )
                return

            jumper_to_clone = selected_item.data(Qt.UserRole)
            new_jumper = copy.deepcopy(jumper_to_clone)
            new_jumper.name = f"{jumper_to_clone.name} (kopia)"

            self.all_jumpers.append(new_jumper)

            item = QListWidgetItem(
                self.create_rounded_flag_icon(new_jumper.nationality), str(new_jumper)
            )
            item.setData(Qt.UserRole, new_jumper)
            self.editor_jumper_list.addItem(item)
            self._sort_editor_lists(self.editor_sort_combo.currentText())

        elif current_tab_index == 1:  # Skocznie
            selected_item = self.editor_hill_list.currentItem()
            if not selected_item:
                QMessageBox.information(
                    self,
                    "Informacja",
                    "Aby sklonować skocznię, najpierw zaznacz ją na liście.",
                )
                return

            hill_to_clone = selected_item.data(Qt.UserRole)
            new_hill = copy.deepcopy(hill_to_clone)
            new_hill.name = f"{hill_to_clone.name} (Kopia)"

            self.all_hills.append(new_hill)

            item = QListWidgetItem(
                self.create_rounded_flag_icon(new_hill.country), str(new_hill)
            )
            item.setData(Qt.UserRole, new_hill)
            self.editor_hill_list.addItem(item)
            self._sort_editor_lists(self.editor_sort_combo.currentText())

    def _add_new_item(self):
        """Add new item."""
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()

        if current_tab_index == 0:  # Skoczkowie
            from src.jumper import Jumper

            new_jumper = Jumper(name="Nowy", last_name="Skoczek", nationality="POL")
            self.all_jumpers.append(new_jumper)

            item = QListWidgetItem(
                self.create_rounded_flag_icon(new_jumper.nationality), str(new_jumper)
            )
            item.setData(Qt.UserRole, new_jumper)
            self.editor_jumper_list.addItem(item)
            self._sort_editor_lists(self.editor_sort_combo.currentText())

        elif current_tab_index == 1:  # Skocznie
            from src.hill import Hill

            new_hill = Hill(name="Nowa Skocznia", country="POL", K=90, L=120, gates=10)
            self.all_hills.append(new_hill)

            item = QListWidgetItem(
                self.create_rounded_flag_icon(new_hill.country), str(new_hill)
            )
            item.setData(Qt.UserRole, new_hill)
            self.editor_hill_list.addItem(item)
            self._sort_editor_lists(self.editor_sort_combo.currentText())

    def _delete_selected_item(self):
        """Delete selected item."""
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()
        active_list = (
            self.editor_jumper_list if current_tab_index == 0 else self.editor_hill_list
        )

        current_item = active_list.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "Błąd", "Nie zaznaczono żadnego elementu do usunięcia."
            )
            return

        data_obj = current_item.data(Qt.UserRole)

        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć '{str(data_obj)}'?\nTej operacji nie można cofnąć.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            row = active_list.row(current_item)
            active_list.takeItem(row)

            if hasattr(data_obj, "nationality"):  # Jumper
                self.all_jumpers.remove(data_obj)
            elif hasattr(data_obj, "country"):  # Hill
                self.all_hills.remove(data_obj)

            del data_obj
            QMessageBox.information(
                self, "Usunięto", "Wybrany element został usunięty."
            )

    def _create_editor_form_content(self, parent_widget, data_class):
        jumper_groups = {
            "Dane Podstawowe": ["name", "last_name", "nationality"],
            "Najazd": [
                "inrun_position",
            ],
            "Wybicie": [
                "takeoff_force",
                "timing",
            ],
            "Lot": [
                "flight_technique",
                "flight_style",
                "flight_resistance",
            ],
            "Lądowanie": [
                "telemark",
                "stability",
            ],
        }
        hill_groups = {
            "Dane Podstawowe": ["name", "country", "K", "L", "gates"],
            "Geometria Najazdu": ["e1", "e2", "t", "gamma_deg", "alpha_deg", "r1"],
            "Profil Zeskoku": [
                "h",
                "n",
                "s",
                "P",
                "l1",
                "l2",
                "a_finish",
                "beta_deg",
                "betaP_deg",
                "betaL_deg",
                "Zu",
            ],
            "Parametry Fizyczne": ["inrun_friction_coefficient"],
        }

        groups = jumper_groups if data_class == Jumper else hill_groups
        jumper_tooltips = {
            "name": "Imię zawodnika.",
            "last_name": "Nazwisko zawodnika.",
            "nationality": "Kod kraju (np. POL, GER, NOR). Wpływa na wyświetlaną flagę.",
            "inrun_position": "Pozycja najazdowa skoczka. Wyższe wartości = lepsza aerodynamika = wyższa prędkość na progu.",
            "takeoff_force": "Siła wybicia skoczka. Wyższe wartości = większa siła odbicia = dłuższe skoki. Kluczowy parametr wpływający na parabolę lotu.",
            "timing": "Timing wybicia. Wyższe wartości = bliżej optimum, lepsze ukierunkowanie impulsu i mniejsza losowość.",
            "flight_technique": "Technika lotu skoczka. Wyższe wartości = lepsze wykorzystanie siły nośnej = dłuższe skoki.",
            "flight_style": "Styl lotu skoczka. Normalny = zrównoważony styl. Agresywny = mniejsza powierzchnia czołowa. Pasywny = większa powierzchnia czołowa.",
            "flight_resistance": "Opór powietrza w locie. Wyższe wartości = mniejszy opór aerodynamiczny = dłuższe skoki.",
            "telemark": "Umiejętność lądowania telemarkiem. Wyższe wartości = częstsze i ładniejsze lądowania telemarkiem.",
            "stability": "Stabilność lądowania. Zmniejsza ryzyko podpórki i upadku daleko za HS.",
            "landing_drag_coefficient": "Opór aerodynamiczny podczas lądowania (bardzo wysoki).",
            "landing_frontal_area": "Powierzchnia czołowa podczas lądowania (największa).",
            "landing_lift_coefficient": "Siła nośna podczas lądowania (zazwyczaj 0).",
        }
        hill_tooltips = {
            "name": "Oficjalna nazwa skoczni.",
            "country": "Kod kraju (np. POL, GER, NOR). Wpływa na wyświetlaną flagę.",
            "gates": "Całkowita liczba belek startowych dostępnych na skoczni.",
            "e1": "Długość najazdu od najwyższej belki do progu (w metrach).",
            "e2": "Długość najazdu od najniższej belki do progu (w metrach).",
            "t": "Długość drugiej prostej najadzu (w metrach).",
            "inrun_friction_coefficient": "Współczynnik tarcia nart o tory. Wyższe wartości = niższa prędkość na progu. Typowo: 0.02.",
            "P": "Początek strefy lądowania (w metrach).",
            "K": "Punkt konstrukcyjny skoczni w metrach (np. 90, 120, 200).",
            "l1": "Odległość po zeskoku między punktem P a K (w metrach).",
            "l2": "Odległosć po zeskoku między punktem K a L (w metrach).",
            "a_finish": "Długość całego wypłaszczenia zeskoku (w metrach).",
            "L": "Rozmiar skoczni (HS) w metrach. Określa granicę bezpiecznego skoku.",
            "alpha_deg": "Kąt nachylenia progu w stopniach. Kluczowy dla kąta wybicia. Zwykle 10-11 stopni.",
            "gamma_deg": "Kąt nachylenia górnej, stromej części najazdu w stopniach.",
            "r1": "Promień krzywej przejściowej na najeździe (w metrach).",
            "h": "Różnica wysokości między progiem a punktem K.",
            "n": "Odległość w poziomie między progiem a punktem K.",
            "betaP_deg": "Kąt nachylenia zeskoku w punkcie P w stopniach.",
            "beta_deg": "Kąt nachylenia zeskoku w punkcie K w stopniach.",
            "betaL_deg": "Kąt nachylenia zeskoku w punkcie L w stopniach.",
            "Zu": "Wysokość progu nad pełnym wypłaszczeniem zeskoku (w metrach).",
            "s": "Wysokość progu nad zeskokiem.",
        }

        tooltips = jumper_tooltips if data_class == Jumper else hill_tooltips
        widgets = {}
        main_layout = QVBoxLayout(parent_widget)

        for group_title, attributes in groups.items():
            group_box = QGroupBox(group_title)
            form_layout = QFormLayout(group_box)

            for attr in attributes:
                widget = None
                if attr in ["K", "L", "gates"]:
                    widget = CustomSpinBox()
                    widget.setRange(0, 500)
                elif (
                    "coefficient" in attr
                    or "area" in attr
                    or attr
                    in [
                        "e1",
                        "e2",
                        "t",
                        "r1",
                        "h",
                        "n",
                        "s",
                        "l1",
                        "l2",
                        "a_finish",
                        "P",
                        "Zu",
                    ]
                ):
                    widget = CustomDoubleSpinBox()
                    widget.setRange(-10000.0, 10000.0)
                    widget.setDecimals(4)
                    widget.setSingleStep(0.01)
                elif attr in [
                    "inrun_position",
                    "takeoff_force",
                    "timing",
                    "flight_technique",
                    "flight_resistance",
                    "telemark",
                    "stability",
                ]:
                    widget = CustomSlider()
                    widget.setRange(0, 100)
                elif attr == "flight_style":
                    widget = ModernComboBox()
                    widget.addItems(["Normalny", "Agresywny", "Pasywny"])
                    widget.setFixedHeight(35)
                elif "deg" in attr:
                    widget = CustomDoubleSpinBox()
                    widget.setRange(-10000.0, 10000.0)
                    widget.setDecimals(2)
                else:
                    widget = QLineEdit()

                # Ustawienie ikon w zależności od motywu
                if isinstance(
                    widget, (CustomSpinBox, CustomDoubleSpinBox, CustomSlider)
                ):
                    if self.current_theme == "dark":
                        widget.set_button_icons(
                            self.up_arrow_icon_dark, self.down_arrow_icon_dark
                        )
                    else:
                        widget.set_button_icons(
                            self.up_arrow_icon_light, self.down_arrow_icon_light
                        )

                # Special case for Polish labels
                if attr == "inrun_position":
                    label_text = "Pozycja najazdowa:"
                elif attr == "takeoff_force":
                    label_text = "Siła wybicia:"
                elif attr == "timing":
                    label_text = "Timing wybicia:"
                elif attr == "flight_technique":
                    label_text = "Technika lotu:"
                elif attr == "flight_style":
                    label_text = "Styl lotu:"
                elif attr == "flight_resistance":
                    label_text = "Opór powietrza:"
                elif attr == "stability":
                    label_text = "Stabilność:"
                else:
                    label_text = (
                        attr.replace("_", " ").replace("deg", "(deg)").capitalize()
                        + ":"
                    )

                label_widget = QLabel(label_text)
                label_widget.setToolTip(tooltips.get(attr, ""))

                form_layout.addRow(label_widget, widget)
                widgets[attr] = widget

            main_layout.addWidget(group_box)

        main_layout.addStretch()
        return widgets

    def _save_current_edit(self):
        self.play_sound()
        current_tab_index = self.editor_tab_widget.currentIndex()
        active_list_widget = (
            self.editor_jumper_list if current_tab_index == 0 else self.editor_hill_list
        )

        current_item = active_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(
                self, "Błąd", "Nie wybrano żadnego elementu do zapisania."
            )
            return

        data_obj = current_item.data(Qt.UserRole)
        widgets = {}
        if isinstance(data_obj, Jumper):
            widgets = self.jumper_edit_widgets

        elif isinstance(data_obj, Hill):
            widgets = self.hill_edit_widgets

        for attr, widget in widgets.items():
            if not hasattr(data_obj, attr):
                continue

            try:
                if attr == "inrun_position":
                    # Konwertuj wartość slidera na inrun_drag_coefficient
                    slider_value = widget.value()
                    from utils.calculations import slider_to_drag_coefficient

                    drag_coefficient = slider_to_drag_coefficient(slider_value)
                    setattr(data_obj, "inrun_drag_coefficient", drag_coefficient)
                elif attr == "takeoff_force":
                    # Konwertuj wartość slidera na jump_force
                    slider_value = widget.value()
                    from utils.calculations import slider_to_jump_force

                    jump_force = slider_to_jump_force(slider_value)
                    setattr(data_obj, "jump_force", jump_force)
                elif attr == "timing":
                    slider_value = widget.value()
                    setattr(data_obj, "timing", slider_value)
                elif attr == "flight_technique":
                    # Konwertuj wartość slidera na flight_lift_coefficient
                    slider_value = widget.value()
                    from utils.calculations import slider_to_lift_coefficient

                    lift_coefficient = slider_to_lift_coefficient(slider_value)
                    setattr(data_obj, "flight_lift_coefficient", lift_coefficient)
                elif attr == "flight_style":
                    # Konwertuj styl na parametry fizyczne
                    style = widget.currentText()
                    old_style = getattr(data_obj, "flight_style", "Normalny")

                    # Sprawdź czy styl się rzeczywiście zmienił
                    if style != old_style:
                        from utils.calculations import (
                            style_to_frontal_area,
                            apply_style_physics,
                        )

                        frontal_area = style_to_frontal_area(style)
                        setattr(data_obj, "flight_frontal_area", frontal_area)
                        setattr(data_obj, "flight_style", style)

                        # Aplikuj dodatkowe efekty stylu na inne parametry
                        apply_style_physics(data_obj, style)
                    else:
                        # Jeśli styl się nie zmienił, tylko zaktualizuj flight_frontal_area
                        from utils.calculations import style_to_frontal_area

                        frontal_area = style_to_frontal_area(style)
                        setattr(data_obj, "flight_frontal_area", frontal_area)
                        setattr(data_obj, "flight_style", style)
                elif attr == "flight_resistance":
                    # Konwertuj wartość slidera na flight_drag_coefficient
                    slider_value = widget.value()
                    from utils.calculations import slider_to_drag_coefficient_flight

                    drag_coefficient = slider_to_drag_coefficient_flight(slider_value)
                    setattr(data_obj, "flight_drag_coefficient", drag_coefficient)
                elif attr == "telemark":
                    # Zapisz wartość telemark bezpośrednio (nie fizyczna)
                    slider_value = widget.value()
                    setattr(data_obj, "telemark", slider_value)
                elif attr == "stability":
                    # Zapisz wartość stabilności bezpośrednio (nie fizyczna)
                    slider_value = widget.value()
                    setattr(data_obj, "stability", slider_value)

                elif isinstance(widget, QLineEdit):
                    new_value = widget.text()
                    setattr(data_obj, attr, new_value)
                elif isinstance(widget, ModernComboBox):
                    new_value = widget.currentText()
                    setattr(data_obj, attr, new_value)
                elif isinstance(widget, CustomDoubleSpinBox):
                    new_value = widget.value()
                    setattr(data_obj, attr, new_value)
                elif isinstance(widget, CustomSpinBox):
                    new_value = widget.value()
                    setattr(data_obj, attr, new_value)
            except Exception as e:
                print(f"Nie udało się zapisać atrybutu '{attr}': {e}")

        if isinstance(data_obj, Hill):
            data_obj.recalculate_derived_attributes()

        current_item.setText(str(data_obj))
        if hasattr(data_obj, "country"):
            current_item.setIcon(self.create_rounded_flag_icon(data_obj.country))
        elif hasattr(data_obj, "nationality"):
            current_item.setIcon(self.create_rounded_flag_icon(data_obj.nationality))

        self._refresh_all_data_widgets()

        QMessageBox.information(
            self,
            "Sukces",
            "Zmiany zostały pomyślnie zapisane.",
        )

    def _refresh_all_data_widgets(self):
        sel_jumper_text = ""
        if self.jumper_combo.currentIndex() > -1:
            sel_jumper_text = self.jumper_combo.currentText()

        sel_hill_text = ""
        if self.hill_combo.currentIndex() > -1:
            sel_hill_text = self.hill_combo.currentText()

        sel_comp_hill_text = ""
        if self.comp_hill_combo.currentIndex() > -1:
            sel_comp_hill_text = self.comp_hill_combo.currentText()

        self.all_jumpers.sort(key=lambda jumper: str(jumper))
        self.all_hills.sort(key=lambda hill: str(hill))

        self.jumper_combo.clear()
        self.jumper_combo.addItem("Wybierz zawodnika")
        for jumper in self.all_jumpers:
            self.jumper_combo.addItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )

        self.hill_combo.clear()
        self.hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.hill_combo.addItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )

        self.comp_hill_combo.clear()
        self.comp_hill_combo.addItem("Wybierz skocznię")
        for hill in self.all_hills:
            self.comp_hill_combo.addItem(
                self.create_rounded_flag_icon(hill.country), str(hill)
            )

        self.jumper_list_widget.clear()
        for jumper in self.all_jumpers:
            item = QListWidgetItem(
                self.create_rounded_flag_icon(jumper.nationality), str(jumper)
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, jumper)
            self.jumper_list_widget.addItem(item)
        self._sort_jumper_list(self.sort_combo.currentText())

        self.jumper_combo.setCurrentText(sel_jumper_text)
        self.hill_combo.setCurrentText(sel_hill_text)
        self.comp_hill_combo.setCurrentText(sel_comp_hill_text)

        self._repopulate_editor_lists()

    def _show_jump_replay(
        self, jumper, hill, gate, distance, seria_num, timing_info=None
    ):
        # Użyj przekazanego timingu (konkretnej serii), a jeśli nie ma – ostatniego dostępnego
        ti = timing_info or getattr(jumper, "last_timing_info", None)
        sim_data = self._calculate_trajectory(jumper, hill, gate, ti)

        self.replay_title_label.setText(f"{jumper} - Seria {seria_num}")
        stats_text = (
            f"Odległość: {format_distance_with_unit(distance)}  |  "
            f"Prędkość na progu: {sim_data['inrun_velocity_kmh']:.2f} km/h  |  "
            f"Kąt wybicia: {sim_data['takeoff_angle_deg']:.2f}°  |  "
            f"Max wysokość: {sim_data['max_height']:.1f} m  |  "
            f"Czas lotu: {sim_data['flight_time']:.2f} s  |  "
            f"Max prędkość: {sim_data['max_velocity_kmh']:.1f} km/h"
        )
        self.replay_stats_label.setText(stats_text)

        self.central_widget.setCurrentIndex(self.JUMP_REPLAY_IDX)
        self._run_animation_on_canvas(
            self.replay_canvas, self.replay_figure, sim_data, hill
        )

        # Minimalistyczny pasek timingu pod statystykami
        try:
            parent_layout = self.central_widget.widget(self.JUMP_REPLAY_IDX).layout()

            # Usuń poprzednie wskaźniki (chip lub pasek), jeśli istnieją
            for attr_name in (
                "replay_timing_label",
                "replay_timing_bar",
                "replay_timing_chip",
            ):
                old_widget = getattr(self, attr_name, None)
                if old_widget is not None:
                    try:
                        parent_layout.removeWidget(old_widget)
                        old_widget.deleteLater()
                    except Exception:
                        pass
                    setattr(self, attr_name, None)

            ti_bar = timing_info or (getattr(jumper, "last_timing_info", None) or {})
            epsilon_t_s = float(ti_bar.get("epsilon_t_s", 0.0))
            classification = ti_bar.get("classification", "idealny")

            # Tytuł nad paskiem
            title_label = QLabel("Timing wybicia")
            title_label.setAlignment(Qt.AlignCenter)
            title_label.setStyleSheet(
                """
                QLabel {
                    color: #cccccc;
                    font-size: 11px;
                    padding: 0px;
                    margin: 2px 0 0 0;
                }
                """
            )

            from ui.widgets.timing_indicator import TimingIndicatorBar

            bar = TimingIndicatorBar(max_abs_seconds=0.12)
            bar.setTiming(epsilon_t_s, classification)
            # Wstaw pod stats_label: najpierw label (idx 3), potem pasek (idx 4)
            parent_layout.insertWidget(3, title_label, 0, Qt.AlignCenter)
            parent_layout.insertWidget(4, bar, 0, Qt.AlignCenter)
            self.replay_timing_label = title_label
            self.replay_timing_bar = bar
        except Exception:
            pass

    def _save_data_to_json(self):
        """Save data to JSON."""
        self.play_sound()
        from PySide6.QtWidgets import QFileDialog

        data_dir = resource_path("data")
        default_path = os.path.join(data_dir, "data.json")

        filePath, _ = QFileDialog.getSaveFileName(
            self, "Zapisz plik danych", default_path, "JSON Files (*.json)"
        )

        if not filePath:
            return

        try:
            data_to_save = {
                "hills": [h.to_dict() for h in self.all_hills],
                "jumpers": [j.to_dict() for j in self.all_jumpers],
            }
            with open(filePath, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)

            QMessageBox.information(
                self, "Sukces", f"Dane zostały pomyślnie zapisane do pliku:\n{filePath}"
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Błąd zapisu", f"Nie udało się zapisać pliku.\nBłąd: {e}"
            )

    def _change_window_mode(self, mode):
        """Change window mode."""
        if mode == "Pełny ekran":
            self.showFullScreen()
        elif mode == "Pełny ekran w oknie":
            self.showMaximized()
        else:  # "W oknie"
            self.showNormal()

    def change_volume(self):
        """Change volume."""
        self.volume_level = self.volume_slider.value() / 100.0
        if hasattr(self, "sound_loaded") and self.sound_loaded:
            self.audio_output.setVolume(self.volume_level)

    def change_contrast(self):
        """Change contrast."""
        self.contrast_level = self.contrast_slider.value() / 100.0
        self.update_styles()

    def update_styles(self):
        """Update styles."""
        # Placeholder - will be implemented later
        pass

    def play_sound(self):
        """Play click sound if available."""
        if self.sound_loaded:
            self.player.setPosition(0)
            self.player.play()

    def _create_distance_card(
        self, distance, k_point, meter_value, difference, distance_points
    ):
        """Tworzy kartę z informacjami o odległości i obliczeniach punktów."""
        card = QWidget()
        # Neutralna karta bez lokalnych kolorów; wygląd po stronie QSS
        card.setProperty("class", "card")

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Tytuł karty
        title = QLabel("Punkty za odległość")
        title.setProperty("chip", True)
        title.setProperty("variant", "primary")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Główna informacja o odległości
        distance_info = QLabel(f"Odległość: {format_distance_with_unit(distance)}")
        distance_info.setProperty("chip", True)
        distance_info.setProperty("variant", "success")
        distance_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(distance_info)

        # Szczegóły obliczeń
        details_layout = QHBoxLayout()

        # Lewa kolumna - wartości
        left_col = QVBoxLayout()

        k_point_label = QLabel(f"K-point: {k_point:.1f} m")
        left_col.addWidget(k_point_label)

        difference_label = QLabel(f"Różnica: {difference:+.1f} m")
        left_col.addWidget(difference_label)

        meter_value_label = QLabel(f"Meter value: {meter_value:.1f} pkt/m")
        left_col.addWidget(meter_value_label)

        # Prawa kolumna - obliczenia
        right_col = QVBoxLayout()

        base_points_label = QLabel("60.0 pkt")
        right_col.addWidget(base_points_label)

        bonus_label = QLabel(f"{difference * meter_value:+.1f} pkt")
        right_col.addWidget(bonus_label)

        total_label = QLabel(f"{distance_points:.1f} pkt")
        total_label.setProperty("chip", True)
        total_label.setProperty("variant", "success")
        right_col.addWidget(total_label)

        details_layout.addLayout(left_col)
        details_layout.addLayout(right_col)
        layout.addLayout(details_layout)

        self.points_breakdown_layout.addWidget(card)

    def _create_judge_card(self, judge_data, title_text: str = "Punkty za noty"):
        """Tworzy kartę z notami sędziów."""
        card = QWidget()
        card.setProperty("class", "card")

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Tytuł karty
        title = QLabel(title_text)
        title.setProperty("chip", True)
        title.setProperty("variant", "primary")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Noty sędziów w dwóch rzędach
        judges_layout = QHBoxLayout()

        # Pierwszy rząd sędziów (1-3)
        first_row = QVBoxLayout()
        for i in range(1, 4):
            judge_score = judge_data.get(f"judge{i}", 0.0)
            judge_label = QLabel(f"Sędzia {i}: {judge_score:.1f}")
            judge_label.setAlignment(Qt.AlignCenter)
            first_row.addWidget(judge_label)

        # Drugi rząd sędziów (4-5)
        second_row = QVBoxLayout()
        for i in range(4, 6):
            judge_score = judge_data.get(f"judge{i}", 0.0)
            judge_label = QLabel(f"Sędzia {i}: {judge_score:.1f}")
            judge_label.setAlignment(Qt.AlignCenter)
            second_row.addWidget(judge_label)

        judges_layout.addLayout(first_row)
        judges_layout.addLayout(second_row)
        layout.addLayout(judges_layout)

        # Suma not sędziów
        total_score = judge_data.get("total_score", 0.0)
        total_label = QLabel(f"Suma: {total_score:.1f} pkt")
        total_label.setProperty("chip", True)
        total_label.setProperty("variant", "success")
        total_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(total_label)

        self.points_breakdown_layout.addWidget(card)

    def _create_total_card(self, distance_points, judge_data):
        """Tworzy kartę z sumą punktów."""
        card = QWidget()
        card.setProperty("class", "card")

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Tytuł karty
        title = QLabel("Suma punktów")
        title.setProperty("chip", True)
        title.setProperty("variant", "primary")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Szczegóły sumy
        details_layout = QHBoxLayout()

        # Lewa kolumna - punkty za odległość
        left_col = QVBoxLayout()
        distance_label = QLabel("Odległość:")
        left_col.addWidget(distance_label)
        distance_points_label = QLabel(f"{distance_points:.1f} pkt")
        distance_points_label.setProperty("chip", True)
        distance_points_label.setProperty("variant", "success")
        left_col.addWidget(distance_points_label)

        # Prawa kolumna - punkty za noty
        right_col = QVBoxLayout()
        judge_label = QLabel("Noty:")
        right_col.addWidget(judge_label)

        if judge_data:
            judge_points = judge_data.get("total_score", 0.0)
            judge_points_label = QLabel(f"{judge_points:.1f} pkt")
        else:
            judge_points_label = QLabel("0.0 pkt")

        judge_points_label.setProperty("chip", True)
        judge_points_label.setProperty("variant", "success")
        right_col.addWidget(judge_points_label)

        details_layout.addLayout(left_col)
        details_layout.addLayout(right_col)
        layout.addLayout(details_layout)

        # Suma całkowita
        total_points = distance_points + (
            judge_data.get("total_score", 0.0) if judge_data else 0.0
        )
        total_label = QLabel(f"Razem: {total_points:.1f} pkt")
        total_label.setProperty("chip", True)
        total_label.setProperty("variant", "success")
        total_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(total_label)

        self.points_breakdown_layout.addWidget(card)

    def _create_series_points_table(
        self, series_name, distance_points, judge_points, total_points
    ):
        """Tworzy tabelę z punktami za serię."""
        card = QWidget()
        card.setProperty("class", "card")

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Tytuł karty
        title = QLabel(series_name)
        title.setProperty("chip", True)
        title.setProperty("variant", "primary")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Tabela z punktami
        table_layout = QHBoxLayout()

        # Kolumna odległości
        distance_col = QVBoxLayout()
        distance_header = QLabel("Odległość")
        distance_header.setAlignment(Qt.AlignCenter)
        distance_col.addWidget(distance_header)
        distance_value = QLabel(f"{distance_points:.1f} pkt")
        distance_value.setProperty("chip", True)
        distance_value.setProperty("variant", "success")
        distance_value.setAlignment(Qt.AlignCenter)
        distance_col.addWidget(distance_value)

        # Kolumna not
        judge_col = QVBoxLayout()
        judge_header = QLabel("Noty")
        judge_header.setAlignment(Qt.AlignCenter)
        judge_col.addWidget(judge_header)
        judge_value = QLabel(f"{judge_points:.1f} pkt")
        judge_value.setProperty("chip", True)
        judge_value.setProperty("variant", "success")
        judge_value.setAlignment(Qt.AlignCenter)
        judge_col.addWidget(judge_value)

        # Kolumna sumy
        total_col = QVBoxLayout()
        total_header = QLabel("Suma")
        total_header.setAlignment(Qt.AlignCenter)
        total_col.addWidget(total_header)
        total_value = QLabel(f"{total_points:.1f} pkt")
        total_value.setProperty("chip", True)
        total_value.setProperty("variant", "success")
        total_value.setAlignment(Qt.AlignCenter)
        total_col.addWidget(total_value)

        table_layout.addLayout(distance_col)
        table_layout.addLayout(judge_col)
        table_layout.addLayout(total_col)
        layout.addLayout(table_layout)

        self.points_breakdown_layout.addWidget(card)
