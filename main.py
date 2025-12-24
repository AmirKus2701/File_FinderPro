import sys
import os
import string
import subprocess
import json
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QFrame,
    QDialog,
    QCheckBox,
    QDialogButtonBox,
    QMenu,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import (
    QCursor,
    QIcon,
    QKeySequence,
    QShortcut,
)  # Добавил QKeySequence и QShortcut


# --- ВСТАВИТЬ ЭТУ ФУНКЦИЮ ПОСЛЕ ИМПОРТОВ ---
def resource_path(relative_path):
    """ Помогает найти файлы рядом с EXE (для режима --onedir) """
    if getattr(sys, 'frozen', False):
        # Если запущено как EXE, ищем в папке с программой
        base_path = os.path.dirname(sys.executable)
    else:
        # Если запущено из Python, ищем в текущей папке
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# --- 0. НАСТРОЙКИ ЦВЕТОВ (ТЕМЫ) ---
THEMES = {
    "dark": {
        "bg_main": "#13131F",
        "bg_secondary": "#1C1C2E",
        "bg_alternate": "#232336",
        "text_main": "#FFFFFF",
        "text_secondary": "#8F90A6",
        "text_path": "#888899",
        "accent": "#FF2E63",
        "accent_hover": "#D92050",
        "hover": "#2D2D44",
        "border": "#2B2B40",
        "input_bg": "#232336",
        "card_bg": "#1C1C2E",
        "combo_list_bg": "#1C1C2E",
        "combo_list_text": "#FFFFFF",
        "combo_list_hover": "#2D2D44",
        "dialog_bg": "#1C1C2E",
        "accent_text": "#FFFFFF",
    },
    "light": {
        "bg_main": "#F4F5F9",
        "bg_secondary": "#FFFFFF",
        "bg_alternate": "#F0F0F5",
        "text_main": "#111111",
        "text_secondary": "#666666",
        "text_path": "#444444",
        "accent": "#FF2E63",
        "accent_hover": "#D92050",
        "hover": "#E8EAF6",
        "border": "#D1D1D6",
        "input_bg": "#F0F0F5",
        "card_bg": "#FFFFFF",
        "combo_list_bg": "#FFFFFF",
        "combo_list_text": "#111111",
        "combo_list_hover": "#E8EAF6",
        "dialog_bg": "#FFFFFF",
        "accent_text": "#FFFFFF",
    },
}


# --- 1. КЛАСС ВЫБОРОЧНОГО ПОИСКА (Диалог с чекбоксами) ---
class ExtensionSelectionDialog(QDialog):
    def __init__(self, category_name, extensions, theme_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Выбор типов для {category_name}")
        self.setStyleSheet(
            f"background-color: {theme_data['dialog_bg']}; color: {theme_data['text_main']};"
        )
        self.selected_extensions = []
        self.checkboxes = []

        layout = QVBoxLayout(self)

        title_label = QLabel(
            f"Отметьте, какие форматы файлов вы хотите искать в категории '{category_name}':"
        )
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        grid_layout = QHBoxLayout()
        ext_per_column = 8

        v_layout = None
        for i, ext in enumerate(extensions):
            if i % ext_per_column == 0:
                v_layout = QVBoxLayout()
                grid_layout.addLayout(v_layout)

            cb = QCheckBox(ext)
            cb.setStyleSheet(f"color: {theme_data['text_main']};")
            cb.setChecked(True)
            self.checkboxes.append(cb)
            if v_layout is not None:
                v_layout.addWidget(cb)

        layout.addLayout(grid_layout)

        reset_button = QPushButton("Сбросить")
        reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_button.clicked.connect(self.uncheck_all)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        h_box = QHBoxLayout()
        h_box.addWidget(reset_button)
        h_box.addStretch()
        h_box.addWidget(button_box)

        layout.addLayout(h_box)

    def uncheck_all(self):
        for cb in self.checkboxes:
            cb.setChecked(False)

    def accept(self):
        self.selected_extensions = [
            cb.text() for cb in self.checkboxes if cb.isChecked()
        ]
        super().accept()

    def get_selected_extensions(self):
        return self.selected_extensions


# --- 1.5. КЛАСС ДИАЛОГА ИСТОРИИ ПОИСКА ---
class HistoryDialog(QDialog):
    path_selected = pyqtSignal(str)

    def __init__(self, history_list, theme_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("История путей поиска")

        self.setStyleSheet(
            f"""
            background-color: {theme_data['dialog_bg']}; 
            color: {theme_data['text_main']};
            QPushButton {{ background-color: {theme_data['accent']}; color: {theme_data['accent_text']}; border-radius: 8px; padding: 10px; }}
            QPushButton:hover {{ background-color: {theme_data['accent_hover']}; }}
            QListWidget {{ background-color: {theme_data['input_bg']}; border: 1px solid {theme_data['border']}; border-radius: 8px; }}
            QListWidget::item {{ padding: 5px; }}
            QListWidget::item:hover {{ background-color: {theme_data['hover']}; }}
            QListWidget::item:selected {{
                background-color: {theme_data['hover']}; 
                color: {theme_data['text_main']};
                border: none;
            }}
        """
        )
        self.history_list = history_list

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Выберите ранее использованную папку:"))

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.select_path_and_accept)
        self._populate_list()
        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()

        self.clear_button = QPushButton("Очистить историю путей")
        self.clear_button.clicked.connect(self.clear_history_and_close)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.resize(500, 400)

    def _populate_list(self):
        self.list_widget.clear()

        for path in reversed(self.history_list):
            if os.path.exists(path):
                display_name = f"{os.path.basename(path)} ({path})"

                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                self.list_widget.addItem(item)

    def select_path_and_accept(self, item):
        full_path = item.data(Qt.ItemDataRole.UserRole)
        self.path_selected.emit(full_path)
        self.accept()

    def clear_history_and_close(self):
        self.list_widget.clear()
        self.history_list.clear()
        QMessageBox.information(
            self,
            "Готово",
            "История путей поиска очищена.",
            QMessageBox.StandardButton.Ok,
        )
        self.reject()


# --- 2. ЛОГИКА ПОИСКА (Локальный движок) ---
class SearchThread(QThread):
    update_results = pyqtSignal(list)
    update_status = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, search_term, extensions, root_dir, deep_scan=False):
        super().__init__()
        self.search_term = search_term.lower()
        self.extensions = extensions
        self.root_dir = root_dir
        self.deep_scan = deep_scan

    def run(self):
        results = []
        processed_count = 0

        if not os.path.exists(self.root_dir):
            self.update_status.emit("Ошибка", "Путь не найден")
            self.finished.emit()
            return

        try:
            for root, dirs, files in os.walk(self.root_dir):
                if self.isInterruptionRequested():
                    self.update_status.emit("Отменено", "Поиск прерван")
                    return

                if not self.deep_scan:
                    dirs[:] = [
                        d for d in dirs if not d.startswith(".") and "$" not in d
                    ]

                for file in files:
                    if self.isInterruptionRequested():
                        self.update_status.emit("Отменено", "Поиск прерван")
                        return

                    processed_count += 1
                    if processed_count % 300 == 0:
                        self.update_status.emit(
                            "Сканирование", f"{processed_count} файлов..."
                        )

                    file_lower = file.lower()

                    match_name = self.search_term in file_lower

                    match_ext = True
                    if self.extensions:
                        match_ext = any(
                            file_lower.endswith(ext) for ext in self.extensions
                        )

                    if (match_name and match_ext) or (
                        not self.search_term and not self.extensions
                    ):
                        full_path = os.path.join(root, file)
                        results.append((file, full_path))

        except Exception as e:
            self.update_status.emit("Ошибка", "Доступ запрещен или ошибка чтения")
            self.finished.emit()
            return

        self.update_results.emit(results)
        self.update_status.emit("Готово", f"Найдено: {len(results)}")
        self.finished.emit()


# --- 3. ЭЛЕМЕНТ СПИСКА ---
class FileItemWidget(QWidget):
    def __init__(self, filename, full_path, path_color, parent=None):
        super().__init__(parent)
        self.full_path = full_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(1)

        self.name_label = QLabel(filename)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.path_label = QLabel(full_path)
        self.path_label.setStyleSheet(
            f"color: {path_color}; font-size: 12px; font-weight: normal;"
        )

        layout.addWidget(self.name_label)
        layout.addWidget(self.path_label)

        self.setLayout(layout)
        self.setFixedHeight(50)


# --- 4. ИНТЕРФЕЙС (UI) ---
class ModernSearchApp(QMainWindow):
    LAST_ROOT_DIR_KEY = "last_root_dir"
    SEARCH_HISTORY_KEY = "search_history"
    HISTORY_MAX_SIZE = 15

    def __init__(self):
        super().__init__()

        self.setWindowTitle("File Finder Pro (Проводник) v12.3")
        self.resize(1100, 750)

        self.current_theme = "dark"
        settings = self.load_settings()

        self.search_history = settings.get(self.SEARCH_HISTORY_KEY, [])

        if os.name == "nt":
            default_path = "C:\\" if os.path.exists("C:\\") else os.path.expanduser("~")
        else:
            default_path = "/"

        self.root_dir = settings.get(self.LAST_ROOT_DIR_KEY, default_path)

        self.current_filter_ext = []
        self.current_filter_key = None

        self.json_extension_data = self.load_extensions_json()

        # Добавлен флаг для предотвращения множественных поисков
        self.is_searching = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.search_thread = None
        self.raw_results_data = []

        self.setup_sidebar()
        self.setup_content_area()
        self.update_path_display()
        self.apply_theme()

        # --- ДОБАВЛЕНО: Глобальная клавиша F5 для обновления ---
        self.refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self.refresh_shortcut.activated.connect(self.start_search)

        self.change_category("ALL_FILES", self.menu_buttons[0])

    def load_extensions_json(self):
        file_path = resource_path("extensions.json")
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Ошибка Базы", f"Файл '{file_path}' не найден!")
            return {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            QMessageBox.critical(
                self,
                "Ошибка Базы",
                f"Файл '{file_path}' поврежден или имеет неверный формат JSON.",
            )
            return {}
        except Exception as e:
            QMessageBox.critical(self, "Ошибка Базы", f"Ошибка чтения файла: {e}")
            return {}

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_settings(self):
        settings = self.load_settings()
        settings[self.LAST_ROOT_DIR_KEY] = self.root_dir
        settings[self.SEARCH_HISTORY_KEY] = self.search_history
        try:
            with open("settings.json", "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def closeEvent(self, event):
        self.stop_all_threads()
        self.save_settings()
        super().closeEvent(event)

    def add_to_history(self, path):
        if path in self.search_history:
            self.search_history.remove(path)

        self.search_history.append(path)

        if len(self.search_history) > self.HISTORY_MAX_SIZE:
            self.search_history = self.search_history[-self.HISTORY_MAX_SIZE :]

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 30)
        sidebar_layout.setSpacing(10)

        self.app_logo = QLabel("FILE FINDER PRO")
        self.app_logo.setStyleSheet(
            "font-size: 16px; font-weight: bold; letter-spacing: 1px; color: #FF2E63;"
        )
        sidebar_layout.addWidget(self.app_logo)
        sidebar_layout.addSpacing(30)

        self.menu_buttons = []

        icon_paths = {
            "office_old": resource_path("images/ms_office.png"),
            "xmind": resource_path("images/XMind_icon.png"),
            "word": resource_path("images/word.png"),
            "excel": resource_path("images/excel.png"),
            "power-bi": resource_path("images/power-bi_icon.png"),
            "pdf": resource_path("images/pdf.png"),
            "архивы": resource_path("images/archive.png"),
            "эцп": resource_path("images/ncalayer.png"),
        }

        self.categories_map = {
            "📂 Все файлы": "ALL_FILES",
            " Документы": "docs",
            " PowerBI": "power-bi",
            " Word": "word",
            " Excel": "excel",
            " PowerPoint": "powerpoint",
            " PDF": "pdf",
            " Изображения": "picture",
            " Видео": "video",
            " Архивы/Образы": "архивы",
            " ЭЦП Ключи": "эцп",
            " XMind": "xmind",
            " Office (Старый/Новый)": "office_old",
        }

        for name, key in self.categories_map.items():
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            if key in icon_paths:
                icon = QIcon(icon_paths[key])
                btn.setIcon(icon)
                btn.setIconSize(QSize(20, 20))

            btn.clicked.connect(
                lambda checked, k=key, b=btn: self.handle_category_click(k, b)
            )

            self.menu_buttons.append(btn)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        self.theme_toggle = QPushButton("🌙 Тёмная тема")
        self.theme_toggle.setObjectName("ThemeToggle")
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.setChecked(True)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        self.theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_toggle.setFixedHeight(45)
        sidebar_layout.addWidget(self.theme_toggle)

    def setup_content_area(self):
        self.content_area = QFrame()
        self.content_area.setObjectName("ContentArea")

        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(10)

        self.path_display_label = QLabel(f"Текущий путь: {self.root_dir}")
        self.path_display_label.setObjectName("PathDisplayLabel")
        self.path_display_label.setFixedHeight(30)
        content_layout.addWidget(self.path_display_label)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите имя файла...")
        self.search_input.setFixedHeight(50)
        # Отключен автопоиск: убрано textChanged.connect
        self.search_input.returnPressed.connect(
            self.start_search
        )  # Поиск только по Enter
        top_bar.addWidget(self.search_input)
        top_bar.addStretch()

        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.setFixedHeight(50)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self.on_browse_folder)
        self.browse_btn.setObjectName("AccentButton")
        top_bar.addWidget(self.browse_btn)

        self.history_btn = QPushButton("История поиска")
        self.history_btn.setFixedWidth(150)
        self.history_btn.setFixedHeight(50)
        self.history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.history_btn.clicked.connect(self.show_history_dialog)
        self.history_btn.setObjectName("SecondaryButton")
        top_bar.addWidget(self.history_btn)

        self.refresh_btn = QPushButton("")
        self.refresh_btn.setFixedSize(50, 50)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # --- ДОБАВИЛ ЭТИ ДВЕ СТРОКИ: ---
        self.refresh_btn.setIcon(QIcon(resource_path("images/refresh_icon.png")))
        self.refresh_btn.setIconSize(QSize(24, 24))
        # -------------------------------

        self.refresh_btn.clicked.connect(self.start_search)
        self.refresh_btn.setObjectName("IconBtn")

        top_bar.addWidget(self.refresh_btn)

        content_layout.addLayout(top_bar)

        self.hint_label = QLabel("")
        self.hint_label.setObjectName("HintLabel")
        self.hint_label.setFixedHeight(20)
        content_layout.addWidget(self.hint_label)

        info_layout = QHBoxLayout()
        self.status_labels = {}

        for key, title in [("status", "Статус системы"), ("count", "Найдено файлов")]:
            card = QFrame()
            card.setObjectName("InfoCard")
            card.setFixedHeight(100)
            c_layout = QVBoxLayout(card)
            c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_title = QLabel(title)
            lbl_title.setObjectName("CardTitle")

            lbl_val = QLabel("Ожидание..." if key == "status" else "0")
            lbl_val.setObjectName("CardValue")
            lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

            c_layout.addWidget(lbl_title)
            c_layout.addWidget(lbl_val)

            self.status_labels[key] = lbl_val
            info_layout.addWidget(card)

        content_layout.addLayout(info_layout)

        lbl_res = QLabel("РЕЗУЛЬТАТЫ ПОИСКА")
        lbl_res.setStyleSheet("font-weight: bold; margin-top: 10px; opacity: 0.7;")
        content_layout.addWidget(lbl_res)

        self.results_list = QListWidget()
        self.results_list.setWordWrap(True)
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_context_menu)

        self.results_list.setAlternatingRowColors(True)

        self.results_list.itemDoubleClicked.connect(self.open_file_on_double_click)

        content_layout.addWidget(self.results_list)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

    def is_root_dir_too_broad(self):
        path = self.root_dir.strip()
        if not path:
            return True
        if os.name == "nt":
            drive, tail = os.path.splitdrive(path)
            if drive and not tail.strip(os.sep):
                return True
        if path == "/":
            return True
        if path == os.path.expanduser("~"):
            return True
        return False

    def _update_hint_only(self, key):
        hint_text = ""
        is_broad_search = self.is_root_dir_too_broad()
        if key in ["фото", "видео"]:
            if is_broad_search:
                hint_text = "⚠️ Внимание: Поиск медиафайлов на всем диске может занять много времени. Рекомендуется выбирать конкретную папку."
        elif key == "архивы":
            if is_broad_search:
                hint_text = "⚠️ Внимание: Поиск архивов может быть медленным. Рекомендуется использовать точные ключевые слова."
        elif key == "эцп":
            hint_text = "🔒 Активировано глубокое сканирование системных папок."
        self.hint_label.setText(hint_text)

    def update_path_display(self):
        display_text = f"Текущий путь: {self.root_dir}"
        self.path_display_label.setText(display_text)
        if self.current_filter_key:
            self._update_hint_only(self.current_filter_key)

    def on_browse_folder(self):
        selected_dir = QFileDialog.getExistingDirectory(
            self, "Выберите папку для поиска", self.root_dir
        )
        if selected_dir and selected_dir != self.root_dir:
            self.root_dir = selected_dir
            self.add_to_history(selected_dir)
            self.update_path_display()

    def set_new_root_dir(self, path):
        if path and path != self.root_dir:
            self.root_dir = path
            self.add_to_history(path)
            self.update_path_display()

    def show_history_dialog(self):
        self.search_history = [p for p in self.search_history if os.path.isdir(p)]
        if not self.search_history:
            QMessageBox.information(self, "История путей", "История поиска пуста.")
            return
        theme_data = THEMES[self.current_theme]
        dialog = HistoryDialog(self.search_history, theme_data, self)
        dialog.path_selected.connect(self.set_new_root_dir)
        dialog.exec()

    def handle_category_click(self, key, clicked_btn):
        for btn in self.menu_buttons:
            btn.setChecked(False)
        clicked_btn.setChecked(True)
        if key in ["фото", "архивы"]:
            self.show_extension_selection_dialog(key, clicked_btn)
        else:
            self.change_category(key, clicked_btn)

    def show_extension_selection_dialog(self, key, clicked_btn):
        if key not in self.json_extension_data:
            QMessageBox.critical(
                self, "Ошибка", f"Ключ '{key}' не найден в базе расширений."
            )
            all_files_btn = next(
                btn
                for btn, k in zip(self.menu_buttons, self.categories_map.values())
                if k == "ALL_FILES"
            )
            self.change_category("ALL_FILES", all_files_btn)
            return
        extensions = self.json_extension_data.get(key, [])
        theme_data = THEMES[self.current_theme]
        category_name_full = next(
            (name for name, k in self.categories_map.items() if k == key),
            "Выбранная категория",
        )
        category_name = category_name_full.lstrip().split(" ", 1)[-1]
        dialog = ExtensionSelectionDialog(category_name, extensions, theme_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_exts = dialog.get_selected_extensions()
            if selected_exts:
                self.current_filter_ext = selected_exts
                self.current_filter_key = key
                # Поиск не запускается автоматически
            else:
                QMessageBox.warning(
                    self,
                    "Внимание",
                    "Не выбрано ни одного формата. Сброс на 'Все файлы'.",
                )
                all_files_btn = next(
                    btn
                    for btn, k in zip(self.menu_buttons, self.categories_map.values())
                    if k == "ALL_FILES"
                )
                self.change_category("ALL_FILES", all_files_btn)
        else:
            all_files_btn = next(
                btn
                for btn, k in zip(self.menu_buttons, self.categories_map.values())
                if k == "ALL_FILES"
            )
            self.change_category("ALL_FILES", all_files_btn)

    def change_category(self, key, clicked_btn):
        for btn in self.menu_buttons:
            btn.setChecked(False)
        clicked_btn.setChecked(True)
        self.current_filter_key = key
        if key == "ALL_FILES":
            self.current_filter_ext = []
        else:
            self.current_filter_ext = self.json_extension_data.get(key, [])
            if not self.current_filter_ext:
                QMessageBox.warning(
                    self,
                    "Внимание",
                    f"Для '{clicked_btn.text().lstrip()}' не найдено расширений в базе.",
                )
        self._update_hint_only(key)
        # Поиск не запускается автоматически

    def stop_all_threads(self):
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.requestInterruption()
            if not self.search_thread.wait(2000):
                print(
                    "Внимание: Поток поиска не завершился за 2 секунды. Продолжаем работу UI."
                )
            try:
                self.search_thread.update_results.disconnect(self.update_ui_results)
                self.search_thread.update_status.disconnect(self.update_status_card)
            except (TypeError, RuntimeError):
                pass

    def is_searching_for_sensitive_files(self, key):
        return key in ["эцп"]

    def start_search(self):
        # --- ИЗМЕНЕНИЕ: УБРАНА БЛОКИРОВКА ПОВТОРНОГО ПОИСКА ---
        # Если поиск уже идет, мы его прерываем и запускаем новый
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.requestInterruption()
            # Не ждем вечно, просто посылаем сигнал остановки и перезапускаем

        self.is_searching = True

        # self.stop_all_threads() # Это уже частично сделано выше, но на всякий случай

        term = self.search_input.text().strip()
        is_all_files = self.current_filter_key == "ALL_FILES"
        if not term and not self.current_filter_ext and not is_all_files:
            self.results_list.clear()
            self.status_labels["status"].setText("Готов")
            self.status_labels["count"].setText("0")
            self.is_searching = False
            return
        self.run_local_search(term, self.current_filter_ext)

    def run_local_search(self, term, extensions):
        deep_scan = self.is_searching_for_sensitive_files(self.current_filter_key)
        self.results_list.clear()
        self.status_labels["status"].setText("Поиск...")
        self.status_labels["count"].setText("...")
        if self.search_thread:
            try:
                self.search_thread.update_results.disconnect(self.update_ui_results)
                self.search_thread.update_status.disconnect(self.update_status_card)
            except (TypeError, RuntimeError):
                pass
        if self.current_filter_key == "ALL_FILES" and not term:
            extensions = []
        self.search_thread = SearchThread(term, extensions, self.root_dir, deep_scan)
        self.search_thread.update_results.connect(self.update_ui_results)
        self.search_thread.update_status.connect(self.update_status_card)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.start()

    def on_search_finished(self):
        self.is_searching = False
        # Таймер больше не нужен для блокировки, так как мы разрешаем перезапуск

    def update_ui_results(self, results):
        self.results_list.clear()
        self.raw_results_data = results
        path_color = THEMES[self.current_theme]["text_path"]
        for filename, full_path in results:
            list_item = QListWidgetItem(self.results_list)
            item_widget = FileItemWidget(filename, full_path, path_color)
            list_item.setSizeHint(item_widget.sizeHint())
            self.results_list.setItemWidget(list_item, item_widget)
            list_item.setData(Qt.ItemDataRole.UserRole, full_path)

    def update_status_card(self, title, value):
        if title == "Готово":
            self.status_labels["status"].setText("Завершено")
            if "Найдено:" in value:
                self.status_labels["count"].setText(value.split(": ")[1])
        elif title == "Сканирование":
            self.status_labels["status"].setText("Сканирование...")
            self.status_labels["count"].setText(value.replace(" файлов...", ""))
        elif title == "Ошибка":
            self.status_labels["status"].setText("Ошибка")
            self.status_labels["count"].setText(value)
        elif title == "Отменено":
            self.status_labels["status"].setText("Отменено")

    def open_file_on_double_click(self, item):
        full_path = item.data(Qt.ItemDataRole.UserRole)
        self.open_file(full_path)

    def open_file(self, full_path):
        if not full_path or not os.path.exists(full_path):
            QMessageBox.warning(
                self, "Ошибка", "Путь к файлу не найден или файл удален."
            )
            return
        try:
            if sys.platform == "win32":
                os.startfile(full_path)
            elif sys.platform == "darwin":
                subprocess.call(("open", full_path))
            else:
                subprocess.call(("xdg-open", full_path))
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка открытия", f"Не удалось открыть файл: {e}"
            )

    def show_in_folder(self, full_path):
        if not full_path or not os.path.exists(full_path):
            QMessageBox.warning(
                self, "Ошибка", "Путь к файлу не найден или файл удален."
            )
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(full_path)])
            elif sys.platform == "darwin":
                subprocess.call(["open", "-R", full_path])
            else:
                parent_dir = os.path.dirname(full_path)
                subprocess.call(["xdg-open", parent_dir])
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка открытия", f"Не удалось открыть папку: {e}"
            )

    def show_context_menu(self, position):
        item = self.results_list.itemAt(position)
        if item:
            full_path = item.data(Qt.ItemDataRole.UserRole)
            if full_path and os.path.exists(full_path):
                menu = QMenu()
                menu.setStyleSheet(
                    f"""
                    QMenu {{
                        background-color: {THEMES[self.current_theme]['bg_secondary']}; 
                        color: {THEMES[self.current_theme]['text_main']};
                        border: 1px solid {THEMES[self.current_theme]['border']};
                        border-radius: 5px;
                    }}
                    QMenu::item {{
                        padding: 8px 25px 8px 20px;
                    }}
                    QMenu::item:selected {{
                        background-color: {THEMES[self.current_theme]['hover']};
                    }}
                """
                )
                show_in_folder_action = menu.addAction("📂 Показать в папке")
                show_in_folder_action.triggered.connect(
                    lambda: self.show_in_folder(full_path)
                )
                menu.exec(self.results_list.mapToGlobal(position))

    def toggle_theme(self):
        if self.current_theme == "dark":
            self.current_theme = "light"
            self.theme_toggle.setText("☀️ Светлая тема")
        else:
            self.current_theme = "dark"
            self.theme_toggle.setText("🌙 Тёмная тема")
        self.apply_theme()
        if self.raw_results_data:
            self.update_ui_results(self.raw_results_data)

    def apply_theme(self):
        t = THEMES[self.current_theme]
        path_label_style = f"""
            QLabel#PathDisplayLabel {{
                color: {t['text_secondary']}; 
                background-color: {t['input_bg']};
                border: 1px solid {t['border']};
                border-radius: 12px; 
                padding: 5px 15px;
                font-size: 13px;
                font-family: 'Consolas', monospace; 
                font-weight: 500;
                min-height: 30px;
                max-height: 30px;
            }}
        """
        hint_label_style = f"""
            QLabel#HintLabel {{
                color: #FF5733; 
                background-color: transparent;
                border: none;
                padding: 0 5px;
                font-size: 13px;
                font-weight: 500;
            }}
        """
        secondary_button_style = f"""
            QPushButton#SecondaryButton {{
                background-color: {t['input_bg']}; 
                border-radius: 12px; 
                border: 1px solid {t['border']};
                color: {t['text_main']};
                padding: 0 15px;
                font-weight: 500;
            }}
            QPushButton#SecondaryButton:hover {{ 
                background-color: {t['hover']}; 
                border: 1px solid {t['accent']};
                color: {t['accent']};
            }}
        """
        accent_button_style = f"""
            QPushButton#AccentButton {{
                background-color: {t['accent']}; 
                border-radius: 12px; 
                border: 1px solid {t['accent']};
                color: {t['accent_text']}; 
                padding: 0 15px;
                font-weight: bold;
            }}
            QPushButton#AccentButton:hover {{ 
                background-color: {t['accent_hover']}; 
                border: 1px solid {t['accent_hover']};
            }}
        """
        style = f"""
            QMainWindow {{ background-color: {t['bg_main']}; }}
            QWidget {{ color: {t['text_main']}; font-family: 'Segoe UI', sans-serif; font-size: 14px; }}
            QFrame#Sidebar {{ background-color: {t['bg_secondary']}; border-right: 1px solid {t['border']}; }}
            QPushButton {{
                background-color: transparent; border: none; text-align: left;
                padding-left: 20px; border-radius: 10px; color: {t['text_secondary']}; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {t['hover']}; color: {t['text_main']}; }}
            QPushButton:checked {{ 
                background-color: {t['hover']}; color: {t['accent']}; border-left: 4px solid {t['accent']};
            }}
            QPushButton#ThemeToggle {{
                padding-left: 15px;
                border-radius: 12px;
                border: 1px solid {t['border']}; 
                background-color: {t['bg_alternate']}; 
                color: {t['text_main']}; 
            }}
            {path_label_style}
            {hint_label_style}
            QLineEdit {{
                background-color: {t['input_bg']}; color: {t['text_main']};
                border: 1px solid {t['border']}; border-radius: 12px; padding: 0 15px; font-weight: 500;
            }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; }}
            {accent_button_style}
            {secondary_button_style}
            QPushButton#IconBtn {{
                background-color: {t['input_bg']}; 
                border-radius: 12px; 
                border: 1px solid {t['border']};
                color: transparent; 
                font-size: 0;
            }}
            QPushButton#IconBtn:hover {{ 
                background-color: {t['hover']}; 
                border: 1px solid {t['text_secondary']}; 
            }}
            QFrame#InfoCard {{
                background-color: {t['card_bg']}; border-radius: 15px; border: 1px solid {t['border']};
            }}
            QLabel#CardTitle {{ color: {t['text_secondary']}; font-size: 13px; }}
            QLabel#CardValue {{ color: {t['accent']}; font-size: 24px; font-weight: bold; }}

            QListWidget {{
                background-color: {t['bg_secondary']}; 
                alternate-background-color: {t['bg_alternate']}; /* Цвет полоски */
                border-radius: 15px; 
                border: 1px solid {t['border']}; 
                padding: 5px; 
                outline: none;
            }}
            
            QListWidget::item {{ 
                background: transparent;
                border: none;
                padding: 0px; 
            }}
            QListWidget::item:selected {{ 
                background-color: {t['hover']}; 
                border-radius: 5px;
            }}
            
            /* --- СТИЛЬ ДЛЯ QMessageBox (ВСПЛЫВАЮЩИЕ ОКНА) --- */
            QMessageBox {{
                background-color: {t['dialog_bg']};
                color: {t['text_main']};
            }}
            QMessageBox QLabel {{
                color: {t['text_main']};
            }}
            QMessageBox QPushButton {{
                background-color: {t['accent']};
                color: {t['accent_text']};
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 60px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {t['accent_hover']};
            }}
        """
        self.setStyleSheet(style)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernSearchApp()
    window.show()
    window.showMaximized()
    sys.exit(app.exec())
