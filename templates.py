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
from PyQt6.QtGui import QCursor, QIcon

# --- 0. НАСТРОЙКИ ЦВЕТОВ (ТЕМЫ) ---
THEMES = {
    "dark": {
        "bg_main": "#11111B",
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
"""
Этот класс отвечает за выбор расширений.
Здесь мы просто убеждаемся,
что используются цвета
из нашей новой темы.
"""


class ExtensionSelectionDialog(QDialog):
    def __init__(self, current_exts, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка форматов")
        self.setMinimumWidth(320)
        self.selected_extensions = current_exts  # Сохраняем начальные данные

        t = theme
        # Применяем дизайн (теперь он точно не слетит)
        self.setStyleSheet(
            f"""
            QDialog {{ background-color: {t['dialog_bg']}; }}
            QLabel {{ color: {t['text_main']}; font-size: 15px; font-weight: bold; margin-bottom: 5px; }}
            QCheckBox {{ color: {t['text_secondary']}; spacing: 10px; font-size: 13px; padding: 5px; }}
            QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 4px; }}
            QPushButton#SaveBtn {{ 
                background-color: {t['accent']}; color: {t['accent_text']}; 
                border-radius: 10px; padding: 12px; font-weight: bold; font-size: 14px;
                margin-top: 10px;
            }}
            QPushButton#SaveBtn:hover {{ background-color: {t['accent_hover']}; }}
        """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)

        layout.addWidget(QLabel("Доступные расширения:"))

        # Группируем чекбоксы для удобства
        self.checkboxes = {}
        options = [
            ".txt",
            ".pdf",
            ".docx",
            ".xlsx",
            ".py",
            ".cpp",
            ".jpg",
            ".png",
            ".mp3",
            ".mp4",
        ]

        for ext in options:
            cb = QCheckBox(ext)
            cb.setChecked(ext in current_exts)
            self.checkboxes[ext] = cb
            layout.addWidget(cb)

        # Кнопка сохранения
        self.save_btn = QPushButton("Сохранить изменения")
        self.save_btn.setObjectName("SaveBtn")  # Для стилей
        self.save_btn.clicked.connect(self.handle_save)  # Вот она!
        layout.addWidget(self.save_btn)

    def handle_save(self):
        """Собираем выбранные расширения и закрываем окно"""
        self.selected_extensions = [
            ext for ext, cb in self.checkboxes.items() if cb.isChecked()
        ]
        print(
            f"DEBUG: Выбрано расширений: {len(self.selected_extensions)}"
        )  # Для контроля
        self.accept()  # Закрывает диалог с результатом True

    def get_selected(self):
        """Метод, который вызовет ModernSearchApp после закрытия окна"""
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
        """
        )
        self.history_list = history_list

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Выберите ранее использованную папку:"))

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.select_path_and_accept)
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
    # ВАЖНО: Сигналы объявляются ЗДЕСЬ (вне __init__)
    file_found = pyqtSignal(str, str) # Передает: имя файла, полный путь
    finished = pyqtSignal()          # Сигнал об окончании работы

    def __init__(self, root_path, search_text, extensions, category):
        super().__init__()
        self.root_path = root_path
        self.search_text = search_text.lower()
        self.extensions = extensions
        self.category = category
        self.is_running = True

    def stop(self):
        """Метод для безопасной остановки потока"""
        self.is_running = False

    def run(self):
        """Основной цикл поиска"""
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Проверяем, не нажали ли мы "Стоп"
                if not self.is_running:
                    break
                
                for file in files:
                    if not self.is_running:
                        break
                    
                    # Логика фильтрации
                    if self.search_text in file.lower():
                        ext = os.path.splitext(file)[1].lower()
                        
                        # Если выбрана категория "Все" или расширение совпадает
                        if self.category == "Все" or ext in self.extensions:
                            # ОТПРАВЛЯЕМ СИГНАЛ в главное окно
                            self.file_found.emit(file, os.path.join(root, file))
                            
        except Exception as e:
            print(f"Ошибка в потоке поиска: {e}")
        
        # Сообщаем, что всё закончили
        self.finished.emit()


# --- 3. ЭЛЕМЕНТ СПИСКА ---
class FileItemWidget(QWidget):
    def __init__(self, filename, full_path, path_color, parent=None):
        super().__init__(parent)
        # Делаем прозрачным, чтобы видеть "зебру" из QListWidget
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")

        lay = QVBoxLayout(self)
        # ВАЖНО: Центрируем текст по вертикали внутри карточки
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(15, 10, 15, 10)  # Отступы, чтобы не было слипания
        lay.setSpacing(4)  # Расстояние между заголовком и путем

        name = QLabel(filename)
        # color: inherit позволяет тексту становиться белым при выделении строки
        name.setStyleSheet(
            "font-weight: bold; font-size: 14px; color: inherit; background: transparent;"
        )

        path = QLabel(full_path)
        path.setStyleSheet(
            f"color: {path_color}; font-size: 11px; background: transparent;"
        )

        lay.addWidget(name)
        lay.addWidget(path)

        # Высота 65px — золотой стандарт для читаемости
        self.setFixedHeight(65)


# --- 4. ИНТЕРФЕЙС (UI) ---
class ModernSearchApp(QMainWindow):
    LAST_ROOT_DIR_KEY = "last_root_dir"
    SEARCH_HISTORY_KEY = "search_history"
    HISTORY_MAX_SIZE = 15

    def __init__(self):
        super().__init__()

        # --- БАЗОВАЯ ИНИЦИАЛИЗАЦИЯ (ФУНДАМЕНТ) ---
        self.current_path = os.path.expanduser("~")  # Путь по умолчанию
        self.current_category = "Все"  # Категория по умолчанию
        self.search_thread = None  # Потока пока нет

        # Набор расширений для категорий (то, чего не хватало программе)
        self.extensions = {
            "Все": [],
            "Видео": [".mp4", ".mkv", ".avi", ".mov"],
            "Фото": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "Аудио": [".mp3", ".wav", ".flac", ".ogg"],
            "Документы": [".pdf", ".docx", ".txt", ".xlsx", ".pptx"],
        }

        # Список для хранения истории поиска
        self.search_history = []

        # ------------------------------------------

        # Инициализируем важные переменные сразу
        self.current_path = os.path.expanduser(
            "~"
        )  # По умолчанию - домашняя папка пользователя
        self.search_thread = None
        self.current_category = "Все"

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

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.interval = 600
        self.search_timer.timeout.connect(self.start_search)

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

        self.change_category("ALL_FILES", self.menu_buttons[0])

    def apply_theme(self):
        t = self.theme
        self.setStyleSheet(
            f"background-color: {t['bg_main']}; color: {t['text_main']};"
        )

        style = f"""
            QMainWindow {{ background-color: {t['bg_main']}; }}
            
            /* БОКОВАЯ ПАНЕЛЬ */
            QFrame#Sidebar {{
                background-color: {t['bg_secondary']};
                border-right: 1px solid {t['border']};
                border-top-right-radius: 20px;
                border-bottom-right-radius: 20px;
            }}
            
            /* КНОПКИ КАТЕГОРИЙ */
            QPushButton#CategoryBtn {{
                background-color: transparent;
                color: {t['text_secondary']};
                border-radius: 12px;
                text-align: left;
                padding: 12px 15px;
                font-size: 13px;
                border: none;
            }}
            QPushButton#CategoryBtn:hover {{
                background-color: {t['hover']};
                color: {t['text_main']};
            }}
            QPushButton#CategoryBtn[active="true"] {{
                background-color: {t['accent']};
                color: {t['accent_text']};
            }}
            
            /* СПИСОК РЕЗУЛЬТАТОВ (БЕЗ БЕЛЫХ УГЛОВ) */
            QListWidget {{
                background-color: {t['bg_secondary']};
                border-radius: 15px;
                border: none;
                padding: 5px;
                outline: none;
            }}
            QListWidget::viewport {{
                background: transparent;
                border: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border-radius: 12px;
                margin: 2px 5px; /* Зазор между файлами */
            }}
            /* ЗЕБРА: Четные элементы */
            QListWidget::item:nth-child(even) {{
                background-color: {t['bg_alternate']};
            }}
            QListWidget::item:hover {{
                background-color: {t['hover']};
            }}
            QListWidget::item:selected {{
                background-color: {t['accent']};
                color: {t['accent_text']};
            }}

            /* ИНФО-КАРТОЧКИ */
            QFrame#InfoCard {{
                background-color: {t['card_bg']};
                border-radius: 15px;
                border: 1px solid {t['border']};
            }}
            
            /* ПОЛЕ ПОИСКА */
            QLineEdit {{
                background-color: {t['input_bg']};
                color: {t['text_main']};
                border: 1px solid {t['border']};
                border-radius: 12px;
                padding: 10px 15px;
                font-size: 14px;
            }}
            
            /* АКЦЕНТНАЯ КНОПКА (НАЙТИ/СТОП) */
            QPushButton#AccentButton {{
                background-color: {t['accent']};
                color: {t['accent_text']};
                border-radius: 12px;
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton#AccentButton:hover {{
                background-color: {t['accent_hover']};
            }}
            QPushButton#AccentButton:disabled {{
                background-color: {t['hover']};
                color: {t['text_secondary']};
            }}
        """
        self.setStyleSheet(style)

    def load_extensions_json(self):
        file_path = "extensions.json"
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
            "office_old": "./images/ms_office.png",
            "xmind": "./images/XMind_icon.png",
            "word": "./images/word.png",
            "excel": "./images/excel.png",
            "power-bi": "./images/power-bi_icon.png",
            "pdf": "./images/pdf.png",
            "архивы": "./images/archive.png",
            "эцп": "./images/ncalayer.png",
        }

        self.categories_map = {
            "📂 Все файлы": "ALL_FILES",
            "📄 Документы": "office",
            " PowerBI": "power-bi",
            " Word": "word",
            " Excel": "excel",
            " PDF": "pdf",
            "🖼️ Изображения": "фото",
            "🎥 Видео": "видео",
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
        self.search_input.textChanged.connect(self.restart_timer)
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
        self.refresh_btn.clicked.connect(self.update_path_display)
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
        # self.start_search()

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

    def handle_search_click(self):
        """Единая точка запуска и остановки"""
        # ПРОВЕРКА: Если поток существует И он реально работает в данный момент
        if self.search_thread is not None and self.search_thread.isRunning():
            self.stop_all_threads()
            self.set_ui_locked(False)
            self.status_labels["status"].setText("Поиск остановлен")
        else:
            # Если поток не запущен — проверяем ввод и запускаем новый
            search_text = self.search_input.text().strip()
            if search_text:
                self.start_search()  # Вызываем запуск
            else:
                self.status_labels["status"].setText("Введите текст для поиска")

    def set_ui_locked(self, is_locked):
        """Блокирует или разблокирует интерфейс"""
        # Меняем текст кнопки
        # self.search_btn.setText("Стоп" if is_locked else "Найти")
        self.refresh_btn.setText("Стоп" if is_locked else "Найти")

        # Блокируем ввод и категории
        self.sidebar.setEnabled(not is_locked)
        self.search_input.setEnabled(not is_locked)
        self.browse_btn.setEnabled(not is_locked)

        if is_locked:
            self.status_labels["status"].setText("Идет поиск...")

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
                self.start_search()
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
        # self.start_search()

    def restart_timer(self):
        self.search_timer.start()

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
        # 1. Проверяем наличие пути
        if not hasattr(self, "current_path") or not self.current_path:
            self.status_labels["status"].setText("Сначала выберите папку!")
            return

        # 2. Очищаем старое
        self.stop_all_threads()
        self.results_list.clear()
        self.set_ui_locked(True)  # Блокируем кнопки

        # 3. Берем текст из поля ввода
        search_text = self.search_input.text()

        # 4. СОЗДАЕМ ПОТОК (теперь self.extensions уже существует в памяти)
        self.search_thread = SearchThread(
            self.current_path,
            search_text,
            self.extensions.get(self.current_category, []),
            self.current_category,
        )

        # 5. Соединяем сигналы и запускаем
        self.search_thread.file_found.connect(self.add_result)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.start()

    def on_search_finished(self):
        """Вызывается автоматически, когда поиск дошел до конца"""
        self.set_ui_locked(False)  # РАЗМОРАЖИВАЕМ интерфейс
        self.status_labels["status"].setText("Поиск завершен")

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
        self.search_thread.start()

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
                background-image: url(./images/refresh_icon.png); 
                background-repeat: no-repeat;
                background-position: center;
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
                background-color: {t['bg_secondary']}; border-radius: 15px; border: 1px solid {t['border']}; 
                padding: 5px; outline: none;
            }}
            
            QListWidget::item:!has-children {{ 
                padding: 0; 
            }}
            QListWidget::item:nth-child(even) {{
                background-color: {t['bg_alternate']}; 
                border-radius: 5px; 
            }}
            QListWidget::item:selected {{ 
                background-color: {t['hover']}; 
            }}
        """
        self.setStyleSheet(style)

    def start_search(self):
        # Проверяем, существует ли путь
        if not hasattr(self, "current_path") or not self.current_path:
            self.status_labels["status"].setText("Ошибка: выберите папку для поиска!")
            return

        self.stop_all_threads()
        self.results_list.clear()
        self.set_ui_locked(True)

        # Теперь self.current_path точно существует
        self.search_thread = SearchThread(
            self.current_path,
            self.search_input.text(),
            self.extensions.get(self.current_category, []),
            self.current_category,
        )

        # Метод создания и запуска потока
        self.stop_all_threads()  # Очищаем старые потоки
        self.results_list.clear()
        self.set_ui_locked(True)  # Блокируем интерфейс

        # 1. Сначала СОЗДАЕМ объект (теперь он не будет None)
        self.search_thread = SearchThread(
            self.current_path,
            self.search_input.text(),
            self.extensions.get(self.current_category, []),
            self.current_category,
        )

        # 2. Подключаем сигналы
        self.search_thread.file_found.connect(self.add_result)
        self.search_thread.finished.connect(self.on_search_finished)

        # 3. И только теперь ЗАПУСКАЕМ
        self.search_thread.start()

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if path:
            self.current_path = path
            self.status_labels["status"].setText(f"Папка: {os.path.basename(path)}")

    def add_result(self, filename, full_path):
        """Принимает данные из потока и создает карточку файла в списке"""
        # 1. Создаем объект нашего красивого виджета
        # Используем цвет пути из текущей темы
        t = THEMES[self.current_theme]
        item_widget = FileItemWidget(filename, full_path, t['text_path'])
        
        # 2. Создаем контейнер для QListWidget
        item = QListWidgetItem(self.results_list)
        item.setSizeHint(item_widget.sizeHint()) # Передаем размер виджета контейнеру
        
        # 3. Соединяем их: вставляем виджет внутрь строки списка
        self.results_list.addItem(item)
        self.results_list.setItemWidget(item, item_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernSearchApp()
    window.show()
    window.showMaximized()
    sys.exit(app.exec())
