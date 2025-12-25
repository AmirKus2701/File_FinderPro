import sys
import os
import json
import subprocess
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
from PyQt6.QtGui import QCursor, QIcon, QKeySequence, QShortcut


# --- ФУНКЦИЯ ПУТЕЙ ---
def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# --- ТЕМЫ ---
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


# --- ДИАЛОГ ВЫБОРА РАСШИРЕНИЙ ---
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
        title = QLabel(f"Отметьте форматы для '{category_name}':")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)

        grid = QHBoxLayout()
        v_layout = None
        for i, ext in enumerate(extensions):
            if i % 8 == 0:
                v_layout = QVBoxLayout()
                grid.addLayout(v_layout)
            cb = QCheckBox(ext)
            cb.setStyleSheet(f"color: {theme_data['text_main']};")
            cb.setChecked(True)
            self.checkboxes.append(cb)
            v_layout.addWidget(cb)
        layout.addLayout(grid)

        btns = QHBoxLayout()
        reset = QPushButton("Сбросить")
        reset.clicked.connect(self.uncheck_all)
        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        btns.addWidget(reset)
        btns.addStretch()
        btns.addWidget(box)
        layout.addLayout(btns)

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


# --- ДИАЛОГ ИСТОРИИ (С ЗЕБРОЙ) ---
class HistoryDialog(QDialog):
    path_selected = pyqtSignal(str)

    def __init__(self, history_list, theme_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("История путей")
        
        # Настраиваем цвета зебры
        self.setStyleSheet(f"""
            QDialog {{ background: {theme_data['dialog_bg']}; color: {theme_data['text_main']}; }}
            QPushButton {{ background: {theme_data['accent']}; color: {theme_data['accent_text']}; border-radius: 8px; padding: 10px; }}
            
            QListWidget {{ 
                background: {theme_data['input_bg']}; 
                alternate-background-color: {theme_data['bg_alternate']}; /* ЦВЕТ ПОЛОСКИ */
                border: 1px solid {theme_data['border']}; 
                border-radius: 8px; 
            }}
            QListWidget::item {{ 
                padding: 4px; /* Отступы между строками */
                color: {theme_data['text_main']}; 
                border: none; 
            }}
            QListWidget::item:hover {{ background: {theme_data['hover']}; }}
            QListWidget::item:selected {{ background: {theme_data['hover']}; color: {theme_data['text_main']}; border: none; }}
        """)
        self.history_list = history_list
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Выберите папку:"))
        
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True) # <--- ВКЛЮЧАЕМ РЕЖИМ ЗЕБРЫ
        self.list.itemDoubleClicked.connect(self.select_path)
        
        for p in reversed(self.history_list):
            if os.path.exists(p):
                item = QListWidgetItem(f"{os.path.basename(p)} ({p})")
                item.setData(Qt.ItemDataRole.UserRole, p)
                self.list.addItem(item)
        layout.addWidget(self.list)

        btns = QHBoxLayout()
        clear = QPushButton("Очистить")
        clear.clicked.connect(self.clear_hist)
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        btns.addWidget(clear)
        btns.addStretch()
        btns.addWidget(cancel)
        layout.addLayout(btns)
        self.resize(500, 400)

    def select_path(self, item):
        self.path_selected.emit(item.data(Qt.ItemDataRole.UserRole))
        self.accept()

    def clear_hist(self):
        self.list.clear()
        self.history_list.clear()
        self.reject()


# --- ПОТОК ПОИСКА (ПОШТУЧНЫЙ ВЫВОД) ---
class SearchThread(QThread):
    single_result_found = pyqtSignal(str, str)
    update_status = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, term, exts, root, deep):
        super().__init__()
        self.term = term.lower()
        self.exts = exts
        self.root = root
        self.deep = deep

    def run(self):
        total = 0
        count = 0

        if not os.path.exists(self.root):
            self.update_status.emit("Ошибка", "Путь не найден")
            self.finished.emit()
            return

        try:
            for root, dirs, files in os.walk(self.root):
                if self.isInterruptionRequested():
                    self.update_status.emit("Отменено", f"Стоп. Найдено: {total}")
                    self.finished.emit()
                    return

                if not self.deep:
                    dirs[:] = [
                        d for d in dirs if not d.startswith(".") and "$" not in d
                    ]

                for f in files:
                    if self.isInterruptionRequested():
                        self.update_status.emit("Отменено", f"Стоп. Найдено: {total}")
                        self.finished.emit()
                        return

                    count += 1
                    # Реже обновляем текст "Сканирование", чтобы не грузить UI
                    if count % 100 == 0:
                        self.update_status.emit(
                            "Сканирование", f"Проверено: {count}..."
                        )

                    f_low = f.lower()
                    match_name = self.term in f_low
                    match_ext = (
                        any(f_low.endswith(e) for e in self.exts) if self.exts else True
                    )

                    if (match_name and match_ext) or (not self.term and not self.exts):
                        full = os.path.join(root, f)
                        total += 1
                        self.single_result_found.emit(f, full)

        except Exception:
            self.update_status.emit("Ошибка", "Ошибка доступа")

        self.update_status.emit("Готово", f"Всего найдено: {total}")
        self.finished.emit()


# --- ЭЛЕМЕНТ СПИСКА ---
class FileItemWidget(QWidget):
    def __init__(self, name, path, color, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(1)
        n = QLabel(name)
        n.setStyleSheet("font-weight: bold; font-size: 14px;")
        p = QLabel(path)
        p.setStyleSheet(f"color: {color}; font-size: 12px;")
        layout.addWidget(n)
        layout.addWidget(p)
        self.setFixedHeight(50)


# --- ГЛАВНОЕ ОКНО ---
class ModernSearchApp(QMainWindow):
    LAST_ROOT_DIR_KEY = "last_root_dir"
    SEARCH_HISTORY_KEY = "search_history"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Finder Pro (Проводник) v12.3")
        self.setWindowIcon(QIcon(resource_path("file-explorer.ico")))
        self.resize(1100, 750)

        self.current_theme = "dark"
        self.raw_results_data = []
        self.is_searching = False
        self.search_thread = None
        self.current_filter_ext = []
        self.current_filter_key = None
        self.found_count = 0  # СЧЕТЧИК НАЙДЕННЫХ

        self.settings = self.load_settings()
        self.search_history = self.settings.get(self.SEARCH_HISTORY_KEY, [])
        def_path = (
            "C:\\"
            if os.name == "nt" and os.path.exists("C:\\")
            else os.path.expanduser("~")
        )
        self.root_dir = self.settings.get(self.LAST_ROOT_DIR_KEY, def_path)
        self.json_data = self.load_extensions_json()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.setup_sidebar()
        self.setup_content_area()

        self.refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        self.refresh_shortcut.activated.connect(self.toggle_search)

        self.update_path_display()
        self.apply_theme()
        self.change_category("ALL_FILES", self.menu_buttons[0])

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                return json.load(f)
        except:
            return {}

    def save_settings(self):
        s = {
            self.LAST_ROOT_DIR_KEY: self.root_dir,
            self.SEARCH_HISTORY_KEY: self.search_history,
        }
        try:
            with open("settings.json", "w") as f:
                json.dump(s, f, indent=4)
        except:
            pass

    def load_extensions_json(self):
        p = resource_path("extensions.json")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def closeEvent(self, e):
        self.stop_search_process()
        self.save_settings()
        super().closeEvent(e)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)

        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(20, 40, 20, 30)
        layout.setSpacing(10)

        logo = QLabel("FILE FINDER PRO")
        logo.setStyleSheet(
            "font-size: 16px; font-weight: bold; letter-spacing: 1px; color: #FF2E63;"
        )
        layout.addWidget(logo)
        layout.addSpacing(30)

        self.menu_buttons = []
        icons = {
            "office": resource_path("images/doc_file.png"),
            "office_old": resource_path("images/ms_office.png"),
            "фото": resource_path("images/picture.png"),
            "видео": resource_path("images/video.png"),
            "xmind": resource_path("images/XMind.png"),
            "word": resource_path("images/word.png"),
            "excel": resource_path("images/excel.png"),
            "power-bi": resource_path("images/power-bi.png"),
            "pdf": resource_path("images/pdf.png"),
            "архивы": resource_path("images/archive.png"),
            "эцп": resource_path("images/ncalayer.png"),
        }
        cats = {
            "📂 Все файлы": "ALL_FILES",
            " Документы": "office",
            " PowerBI": "power-bi",
            " Word": "word",
            " Excel": "excel",
            " PDF": "pdf",
            " Изображения": "фото",
            " Видео": "видео",
            " Архивы/Образы": "архивы",
            " ЭЦП Ключи": "эцп",
            " XMind": "xmind",
            " Office (Старый/Новый)": "office_old",
        }

        for name, key in cats.items():
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(50)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if key in icons:
                btn.setIcon(QIcon(icons[key]))
                btn.setIconSize(QSize(20, 20))
            btn.clicked.connect(
                lambda c, k=key, b=btn: self.handle_category_click(k, b)
            )
            self.menu_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        self.theme_toggle = QPushButton("🌙 Тёмная тема")
        self.theme_toggle.setObjectName("ThemeToggle")
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.setChecked(True)
        self.theme_toggle.clicked.connect(self.toggle_theme)
        self.theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_toggle.setFixedHeight(45)
        layout.addWidget(self.theme_toggle)

    def setup_content_area(self):
        self.content_area = QFrame()
        self.content_area.setObjectName("ContentArea")
        layout = QVBoxLayout(self.content_area)
        layout.setContentsMargins(40, 20, 40, 40)
        layout.setSpacing(5)

        self.path_display_label = QLabel(f"Текущий путь: {self.root_dir}")
        self.path_display_label.setObjectName("PathDisplayLabel")
        self.path_display_label.setFixedHeight(30)
        layout.addWidget(self.path_display_label)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)
        
        # --- ПОЛЕ ПОИСКА С КРЕСТИКОМ ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите имя файла...")
        self.search_input.setFixedHeight(50)
        self.search_input.returnPressed.connect(self.start_search)
        
        # Добавляем действие (Action) внутрь поля ввода справа
        # Убедись, что clear_icon.png лежит в папке images!
        self.clear_action = self.search_input.addAction(
            QIcon(resource_path("images/clear_icon.png")), 
            QLineEdit.ActionPosition.TrailingPosition
        )
        # При клике очищаем текст
        self.clear_action.triggered.connect(self.search_input.clear)
        
        top_bar.addWidget(self.search_input)
        # -------------------------------

        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.setFixedHeight(50)
        self.browse_btn.clicked.connect(self.on_browse_folder)
        self.browse_btn.setObjectName("AccentButton")
        top_bar.addWidget(self.browse_btn)

        self.history_btn = QPushButton("История поиска")
        self.history_btn.setFixedWidth(150)
        self.history_btn.setFixedHeight(50)
        self.history_btn.clicked.connect(self.show_history_dialog)
        self.history_btn.setObjectName("SecondaryButton")
        top_bar.addWidget(self.history_btn)

        self.refresh_btn = QPushButton("")
        self.refresh_btn.setFixedSize(50, 50)
        self.refresh_btn.setIcon(QIcon(resource_path("images/refresh.png")))
        self.refresh_btn.setIconSize(QSize(24, 24))
        self.refresh_btn.clicked.connect(self.toggle_search)
        self.refresh_btn.setObjectName("IconBtn")
        top_bar.addWidget(self.refresh_btn)
        
        layout.addLayout(top_bar)
        
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("HintLabel")
        self.hint_label.setFixedHeight(20)
        layout.addWidget(self.hint_label)

        info = QHBoxLayout()
        self.status_labels = {}
        for key, title in [("status", "Статус системы"), ("count", "Найдено файлов")]:
            card = QFrame()
            card.setObjectName("InfoCard")
            card.setFixedHeight(100)
            cl = QVBoxLayout(card)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(QLabel(title))
            val = QLabel("Ожидание..." if key == "status" else "0")
            val.setObjectName("CardValue")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(val)
            self.status_labels[key] = val
            info.addWidget(card)
        layout.addLayout(info)

        layout.addWidget(QLabel("РЕЗУЛЬТАТЫ ПОИСКА"))
        self.results_list = QListWidget()
        self.results_list.setAlternatingRowColors(True)
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_context_menu)
        self.results_list.itemDoubleClicked.connect(self.open_file_on_double_click)
        layout.addWidget(self.results_list)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

    def set_controls_enabled(self, enabled):
        for b in self.menu_buttons:
            b.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.history_btn.setEnabled(enabled)
        self.theme_toggle.setEnabled(enabled)

    def toggle_search(self):
        if self.is_searching:
            self.stop_search_process()
        else:
            self.start_search()

    def stop_search_process(self):
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.requestInterruption()

    def start_search(self):
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.requestInterruption()

        self.is_searching = True
        self.set_controls_enabled(False)
        self.refresh_btn.setIcon(QIcon(resource_path("images/stop_icon.png")))
        self.results_list.clear()
        self.raw_results_data = []

        # СБРОС СЧЕТЧИКА
        self.found_count = 0
        self.status_labels["count"].setText("0")

        term = self.search_input.text().strip()
        is_all = self.current_filter_key == "ALL_FILES"
        if not term and not self.current_filter_ext and not is_all:
            self.on_search_finished()
            return

        exts = [] if is_all and not term else self.current_filter_ext
        deep = self.current_filter_key == "эцп"

        self.search_thread = SearchThread(term, exts, self.root_dir, deep)
        self.search_thread.single_result_found.connect(self.add_single_result)
        self.search_thread.update_status.connect(self.update_status_card)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.start()

    def on_search_finished(self):
        self.is_searching = False
        self.set_controls_enabled(True)
        self.refresh_btn.setIcon(QIcon(resource_path("images/refresh.png")))

    def add_single_result(self, f, p):
        self.raw_results_data.append((f, p))
        c = THEMES[self.current_theme]["text_path"]

        item = QListWidgetItem(self.results_list)
        w = FileItemWidget(f, p, c)
        item.setSizeHint(w.sizeHint())
        self.results_list.setItemWidget(item, w)
        item.setData(Qt.ItemDataRole.UserRole, p)

        # ОБНОВЛЯЕМ СЧЕТЧИК МГНОВЕННО
        self.found_count += 1
        self.status_labels["count"].setText(str(self.found_count))

    def update_status_card(self, title, val):
        self.status_labels["status"].setText(
            title if title != "Сканирование" else "Поиск..."
        )
        # Удаляем обновление count отсюда, так как обновляем его мгновенно в add_single_result
        # Но оставляем обработку финального сообщения если нужно
        if "Найдено:" in val:
            # В конце можно сверяться, но основной счетчик уже накручен
            pass

    def update_path_display(self):
        self.path_display_label.setText(f"Текущий путь: {self.root_dir}")
        self._update_hint_only(self.current_filter_key)

    def on_browse_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Выбор папки", self.root_dir)
        if d and d != self.root_dir:
            self.root_dir = d
            if d in self.search_history:
                self.search_history.remove(d)
            self.search_history.append(d)
            self.update_path_display()

    def show_history_dialog(self):
        self.search_history = [p for p in self.search_history if os.path.isdir(p)]
        if not self.search_history:
            QMessageBox.information(self, "Инфо", "История пуста.")
            return
        d = HistoryDialog(self.search_history, THEMES[self.current_theme], self)
        d.path_selected.connect(self.set_new_root_dir)
        d.exec()

    def set_new_root_dir(self, path):
        self.root_dir = path
        self.update_path_display()

    def handle_category_click(self, key, btn):
        for b in self.menu_buttons:
            b.setChecked(False)
        btn.setChecked(True)
        if key in ["фото", "архивы"]:
            self.show_ext_dialog(key, btn)
        else:
            self.change_category(key, btn)

    def show_ext_dialog(self, key, btn):
        exts = self.json_data.get(key, [])
        if not exts:
            return self.change_category("ALL_FILES", self.menu_buttons[0])
        name = next(
            (n for n, k in self.categories_map.items() if k == key), "Категория"
        ).split(" ", 1)[-1]
        d = ExtensionSelectionDialog(name, exts, THEMES[self.current_theme], self)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.current_filter_ext = d.get_selected_extensions()
            self.current_filter_key = key
            self.update_path_display()
        else:
            self.menu_buttons[0].setChecked(True)

    def change_category(self, key, btn):
        self.current_filter_key = key
        self.current_filter_ext = (
            [] if key == "ALL_FILES" else self.json_data.get(key, [])
        )
        self.update_path_display()

    def _update_hint_only(self, key):
        hint = ""
        if self.is_root_dir_too_broad():
            if key in ["фото", "видео"]:
                hint = "⚠️ Поиск медиа на всем диске долгий."
            elif key == "архивы":
                hint = "⚠️ Поиск архивов медленный."
        if key == "эцп":
            hint = "🔒 Глубокое сканирование."
        self.hint_label.setText(hint)

    def is_root_dir_too_broad(self):
        p = self.root_dir.strip()
        if not p or p == "/" or p == os.path.expanduser("~"):
            return True
        if os.name == "nt":
            d, t = os.path.splitdrive(p)
            if d and not t.strip(os.sep):
                return True
        return False

    def open_file_on_double_click(self, item):
        self.open_file(item.data(Qt.ItemDataRole.UserRole))

    def open_file(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.call(
                    ("open" if sys.platform == "darwin" else "xdg-open", path)
                )
        except:
            pass

    def show_context_menu(self, pos):
        item = self.results_list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        m = QMenu()
        m.setStyleSheet(
            f"QMenu {{ background-color: {THEMES[self.current_theme]['bg_secondary']}; color: {THEMES[self.current_theme]['text_main']}; }}"
        )
        act = m.addAction("📂 Показать в папке")
        act.triggered.connect(lambda: self.show_in_folder(path))
        m.exec(self.results_list.mapToGlobal(pos))

    def show_in_folder(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            elif sys.platform == "darwin":
                subprocess.call(["open", "-R", path])
            else:
                subprocess.call(["xdg-open", os.path.dirname(path)])
        except:
            pass

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.theme_toggle.setText(
            "☀️ Светлая тема" if self.current_theme == "light" else "🌙 Тёмная тема"
        )
        self.apply_theme()

        if self.raw_results_data:
            self.results_list.clear()
            c = THEMES[self.current_theme]["text_path"]
            for f, p in self.raw_results_data:
                item = QListWidgetItem(self.results_list)
                w = FileItemWidget(f, p, c)
                item.setSizeHint(w.sizeHint())
                self.results_list.setItemWidget(item, w)
                item.setData(Qt.ItemDataRole.UserRole, p)

    def apply_theme(self):
        t = THEMES[self.current_theme]
        self.setStyleSheet(
            f"""
            QMainWindow {{ background-color: {t['bg_main']}; }}
            QWidget {{ color: {t['text_main']}; font-family: 'Segoe UI', sans-serif; font-size: 14px; }}
            
            QFrame#Sidebar {{ background-color: {t['bg_secondary']}; border-right: 1px solid {t['border']}; }}
            QPushButton {{ 
                background: transparent; border: none; text-align: left; 
                padding-left: 20px; color: {t['text_secondary']}; font-weight: 600;
                border-radius: 10px;
            }}
            QPushButton:hover {{ background: {t['hover']}; color: {t['text_main']}; }}
            QPushButton:checked {{ background: {t['hover']}; color: {t['accent']}; border-left: 4px solid {t['accent']}; }}
            
            QPushButton#ThemeToggle {{ 
                padding-left: 15px; border: 1px solid {t['border']}; 
                background: {t['bg_alternate']}; 
                border-radius: 15px;
            }}
            
            QLabel#PathDisplayLabel {{
                color: {t['text_secondary']}; 
                background-color: {t['input_bg']};
                border: 2px solid {t['border']};
                border-radius: 12px; 
                padding: 5px 15px;
                font-size: 13px;
                font-family: 'Consolas', monospace; 
                font-weight: bold;
            }}

            QLineEdit {{ background: {t['input_bg']}; color: {t['text_main']}; border: 1px solid {t['border']}; border-radius: 12px; padding: 0 15px; font-weight: 500; }}
            
            QPushButton#AccentButton {{ background: {t['accent']}; color: {t['accent_text']}; border-radius: 12px; font-weight: bold; padding: 0 15px; }}
            QPushButton#AccentButton:hover {{ background: {t['accent_hover']}; }}
            
            QPushButton#SecondaryButton {{ background: {t['input_bg']}; border: 1px solid {t['border']}; border-radius: 12px; padding: 0 15px; font-weight: 500; }}
            QPushButton#SecondaryButton:hover {{ background: {t['hover']}; border: 1px solid {t['accent']}; color: {t['accent']}; }}
            
            QPushButton#IconBtn {{ background: {t['input_bg']}; border: 1px solid {t['border']}; border-radius: 12px; padding-left: 12px; color: transparent; font-size: 0; }}
            QPushButton#IconBtn:hover {{ background: {t['hover']}; border: 1px solid {t['text_secondary']}; }}
            
            QFrame#InfoCard {{ background: {t['card_bg']}; border-radius: 15px; border: 1px solid {t['border']}; }}
            QLabel#CardTitle {{ color: {t['text_secondary']}; font-size: 13px; }}
            QLabel#CardValue {{ color: {t['accent']}; font-size: 24px; font-weight: bold; }}
            
            QListWidget {{ background: {t['bg_secondary']}; alternate-background-color: {t['bg_alternate']}; border-radius: 15px; border: 1px solid {t['border']}; padding: 5px; outline: none; }}
            QListWidget::item {{ border: none; padding: 0px; }}
            QListWidget::item:selected {{ background: {t['hover']}; border-radius: 5px; }}
            
            QLabel#HintLabel {{ color: #FF5733; background: transparent; border: none; padding: 0 5px; font-size: 13px; font-weight: 500; }}
            
            QMessageBox {{ background: {t['dialog_bg']}; color: {t['text_main']}; }}
            QMessageBox QLabel {{ color: {t['text_main']}; }}
            QMessageBox QPushButton {{ background: {t['accent']}; color: {t['accent_text']}; border-radius: 6px; padding: 6px 12px; min-width: 60px; }}
            QMessageBox QPushButton:hover {{ background: {t['accent_hover']}; }}
        """
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernSearchApp()
    window.show()
    window.showMaximized()
    sys.exit(app.exec())
