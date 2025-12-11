import sys
import os
import string
import subprocess
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QLabel, QListWidget, QListWidgetItem,
                             QPushButton, QFrame, QComboBox, QDialog, QCheckBox, 
                             QDialogButtonBox, QMenu, QMessageBox, QFileDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QCoreApplication, QSize
from PyQt6.QtGui import QCursor, QIcon

# --- 0. НАСТРОЙКИ ЦВЕТОВ (ТЕМЫ) ---
THEMES = {
    "dark": {
        "bg_main": "#13131F", "bg_secondary": "#1C1C2E", "bg_alternate": "#232336",  
        "text_main": "#FFFFFF", "text_secondary": "#8F90A6", "text_path": "#888899",      
        "accent": "#FF2E63", "accent_hover": "#D92050", "hover": "#2D2D44",         
        "border": "#2B2B40", "input_bg": "#232336", "card_bg": "#1C1C2E",
        "combo_list_bg": "#1C1C2E", "combo_list_text": "#FFFFFF", "combo_list_hover": "#2D2D44",
        "dialog_bg": "#1C1C2E",
        "accent_text": "#FFFFFF" # Цвет текста для акцентных кнопок
    },
    "light": {
        "bg_main": "#F4F5F9", "bg_secondary": "#FFFFFF", "bg_alternate": "#F0F0F5",
        "text_main": "#111111", "text_secondary": "#666666", "text_path": "#444444",      
        "accent": "#FF2E63", "accent_hover": "#D92050", "hover": "#E8EAF6",
        "border": "#D1D1D6", "input_bg": "#F0F0F5", "card_bg": "#FFFFFF",
        "combo_list_bg": "#FFFFFF", "combo_list_text": "#111111", "combo_list_hover": "#E8EAF6",
        "dialog_bg": "#FFFFFF",
        "accent_text": "#FFFFFF"
    }
}

# --- 1. КЛАСС ВЫБОРОЧНОГО ПОИСКА (Диалог с чекбоксами) ---
class ExtensionSelectionDialog(QDialog):
    def __init__(self, category_name, extensions, theme_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Выбор типов для {category_name}")
        self.setStyleSheet(f"background-color: {theme_data['dialog_bg']}; color: {theme_data['text_main']};")
        self.selected_extensions = []
        self.checkboxes = []

        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"Отметьте, какие форматы файлов вы хотите искать в категории '{category_name}':")
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)
        
        # 1. Чекбоксы расширений
        grid_layout = QHBoxLayout()
        ext_per_column = 8 
        
        v_layout = None
        for i, ext in enumerate(extensions):
            if i % ext_per_column == 0:
                v_layout = QVBoxLayout()
                grid_layout.addLayout(v_layout)

            cb = QCheckBox(ext)
            cb.setStyleSheet(f"color: {theme_data['text_main']};")
            cb.setChecked(True)  # По умолчанию все включены
            self.checkboxes.append(cb)
            if v_layout is not None:
                v_layout.addWidget(cb)
        
        layout.addLayout(grid_layout)
        
        # 2. Кнопки "Применить", "Отмена" и "Сбросить"
        
        reset_button = QPushButton("Сбросить")
        reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_button.clicked.connect(self.uncheck_all)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        h_box = QHBoxLayout()
        h_box.addWidget(reset_button)
        h_box.addStretch()
        h_box.addWidget(button_box)
        
        layout.addLayout(h_box)

    def uncheck_all(self):
        """Снимает все флажки (чекбоксы) в диалоге."""
        for cb in self.checkboxes:
            cb.setChecked(False)

    def accept(self):
        self.selected_extensions = [cb.text() for cb in self.checkboxes if cb.isChecked()]
        super().accept()

    def get_selected_extensions(self):
        return self.selected_extensions

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
        
        # Проверка корневой папки
        if not os.path.exists(self.root_dir):
            self.update_status.emit("Ошибка", "Путь не найден")
            self.finished.emit()
            return
            
        try:
            for root, dirs, files in os.walk(self.root_dir):
                if self.isInterruptionRequested(): return
                
                # Логика ГЛУБОКОГО СКАНИРОВАНИЯ для ЭЦП
                if not self.deep_scan:
                    dirs[:] = [d for d in dirs if not d.startswith('.') and '$' not in d]
                
                for file in files:
                    if self.isInterruptionRequested(): return
                    processed_count += 1
                    if processed_count % 300 == 0: 
                        self.update_status.emit("Сканирование", f"{processed_count} файлов...")

                    file_lower = file.lower()
                    
                    match_name = self.search_term in file_lower
                    
                    match_ext = True
                    if self.extensions:
                        match_ext = any(file_lower.endswith(ext) for ext in self.extensions)
                        
                    if match_name and match_ext:
                        full_path = os.path.join(root, file)
                        results.append((file, full_path))

        except Exception as e:
            self.update_status.emit("Ошибка", "Доступ запрещен или ошибка чтения")
        
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
        self.path_label.setStyleSheet(f"color: {path_color}; font-size: 12px; font-weight: normal;")
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.path_label)
        
        self.setLayout(layout)
        self.setFixedHeight(50)


# --- 4. ИНТЕРФЕЙС (UI) ---
class ModernSearchApp(QMainWindow):
    LAST_ROOT_DIR_KEY = "last_root_dir" 
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Finder Pro v10.0 (JSON-База)")
        self.resize(1100, 750)
        
        self.current_theme = "dark"
        self.root_dir = self.load_settings().get(self.LAST_ROOT_DIR_KEY, "C:\\" if os.name == 'nt' else "/")
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
        self.populate_drives() 
        self.apply_theme()
        
        self.change_category("ALL_FILES", self.menu_buttons[0])

    def load_extensions_json(self):
        """Загружает базу расширений из файла JSON."""
        file_path = 'extensions.json'
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Ошибка Базы", f"Файл '{file_path}' не найден!")
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Ошибка Базы", f"Файл '{file_path}' поврежден или имеет неверный формат JSON.")
            return {}
        except Exception as e:
            QMessageBox.critical(self, "Ошибка Базы", f"Ошибка чтения файла: {e}")
            return {}

    def load_settings(self):
        """Загружает настройки (например, последний путь) из файла."""
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_settings(self):
        """Сохраняет настройки (например, последний путь) в файл."""
        settings = self.load_settings()
        settings[self.LAST_ROOT_DIR_KEY] = self.root_dir
        try:
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def closeEvent(self, event):
        """Вызывается при закрытии окна."""
        self.save_settings()
        super().closeEvent(event)

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(260)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 40, 20, 30)
        sidebar_layout.setSpacing(10)

        self.app_logo = QLabel("FILE FINDER PRO")
        self.app_logo.setStyleSheet("font-size: 16px; font-weight: bold; letter-spacing: 1px; color: #FF2E63;")
        sidebar_layout.addWidget(self.app_logo)
        sidebar_layout.addSpacing(30)

        self.menu_buttons = []
        
        # Словари для кастомных иконок
        icon_paths = {
            "office_old" : "./images/ms_office.png", 
            "xmind" : "./images/XMind_icon.png",
            "word" : "./images/word.png",
            "excel" : "./images/excel.png",
            "power-bi" : "./images/power-bi_icon.png",
            "pdf" : "./images/pdf.png",
            "архивы" : "./images/archive.png",
            "эцп" : "./images/ncalayer.png"
        }

        # Категории: Ключ - это текст кнопки; Значение - это ключ в JSON
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
            
            # --- УСТАНОВКА ИКОНКИ ---
            if key in icon_paths:
                icon = QIcon(icon_paths[key])
                btn.setIcon(icon)
                btn.setIconSize(QSize(20, 20))
            # ------------------------

            btn.clicked.connect(lambda checked, k=key, b=btn: self.handle_category_click(k, b))
            
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
        content_layout.setSpacing(20)

        # 1. Верхняя панель (Поиск и Диски/Обзор)
        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите имя файла...")
        self.search_input.setFixedHeight(50)
        self.search_input.textChanged.connect(self.restart_timer)
        top_bar.addWidget(self.search_input)
        
        # Выбор диска
        self.drive_select = QComboBox()
        self.drive_select.setFixedWidth(120)
        self.drive_select.setFixedHeight(50)
        self.drive_select.setCursor(Qt.CursorShape.PointingHandCursor)
        self.drive_select.currentIndexChanged.connect(self.on_drive_changed)
        top_bar.addWidget(self.drive_select)
        
        # Кнопка Обзор
        self.browse_btn = QPushButton("Обзор...") 
        self.browse_btn.setFixedWidth(100)
        self.browse_btn.setFixedHeight(50)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self.on_browse_folder) 
        self.browse_btn.setObjectName("AccentButton") # <<< Новое имя объекта для стилизации
        top_bar.addWidget(self.browse_btn)

        # Кнопка Обновить
        self.refresh_btn = QPushButton("") 
        self.refresh_btn.setFixedSize(50, 50)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.populate_drives)
        self.refresh_btn.setObjectName("IconBtn")
        top_bar.addWidget(self.refresh_btn)
        
        content_layout.addLayout(top_bar)

        # 2. Инфо-панель (Статус)
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


        # 3. Список результатов
        lbl_res = QLabel("РЕЗУЛЬТАТЫ ПОИСКА")
        lbl_res.setStyleSheet("font-weight: bold; margin-top: 10px; opacity: 0.7;")
        content_layout.addWidget(lbl_res)

        self.results_list = QListWidget()
        self.results_list.setWordWrap(True) 
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_context_menu)
        self.results_list.setAlternatingRowColors(True)
        content_layout.addWidget(self.results_list)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_area)

    def populate_drives(self):
        """Заполняет ComboBox дисками и специальными путями."""
        self.drive_select.blockSignals(True)
        self.drive_select.clear()
        
        drives = []
        if os.name == 'nt':
            # Windows: C:\, D:\ и т.д.
            drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        else:
            # Linux/macOS: корневой каталог
            drives = ["/"]
        
        # Добавляем диски в ComboBox
        self.drive_select.addItems(drives)
        
        # Проверяем, является ли текущий root_dir одним из дисков
        is_drive_selected = self.root_dir in drives
        
        if not is_drive_selected and os.path.isdir(self.root_dir):
            # Если текущий путь - это папка, которую выбрали через "Обзор", 
            # добавляем ее в ComboBox как первый элемент.
            self.drive_select.insertItem(0, f"Папка: {os.path.basename(self.root_dir)}")
            self.drive_select.setCurrentIndex(0)
            
        elif is_drive_selected:
            # Если текущий путь - это диск, выбираем его.
            idx = self.drive_select.findText(self.root_dir)
            if idx >= 0: self.drive_select.setCurrentIndex(idx)
        else:
            # Если текущий путь не существует (например, предыдущая папка удалена), 
            # сбрасываем на первый доступный диск.
            if drives:
                self.root_dir = drives[0]
                self.drive_select.setCurrentIndex(0)
            
        self.drive_select.blockSignals(False)

    def on_drive_changed(self):
        """Обрабатывает смену диска/папки в ComboBox."""
        current_text = self.drive_select.currentText()
        
        if current_text.startswith("Папка: "):
            # Если выбрана кастомная папка, root_dir уже установлен в on_browse_folder, 
            # здесь мы его не меняем, просто убеждаемся, что он существует.
            pass
        else:
            # Если выбран диск, обновляем root_dir
            self.root_dir = current_text
            self.start_search()

    def on_browse_folder(self):
        """Открывает диалог для выбора конкретной папки."""
        selected_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для поиска", self.root_dir)
        
        if selected_dir:
            self.root_dir = selected_dir
            
            # Обновление ComboBox: Вставляем выбранную папку и делаем ее активной.
            self.populate_drives() 
            self.start_search()

    def handle_category_click(self, key, clicked_btn):
        for btn in self.menu_buttons:
            btn.setChecked(False)
        clicked_btn.setChecked(True)
        
        # Только "фото" и "архивы" используют выборочный диалог
        if key in ["фото", "архивы"]:
            self.show_extension_selection_dialog(key, clicked_btn)
        else:
            self.change_category(key, clicked_btn)
    
    def show_extension_selection_dialog(self, key, clicked_btn):
        
        if key not in self.json_extension_data:
            QMessageBox.critical(self, "Ошибка", f"Ключ '{key}' не найден в базе расширений.")
            self.change_category("ALL_FILES", self.menu_buttons[0])
            return

        extensions = self.json_extension_data.get(key, [])
        theme_data = THEMES[self.current_theme]
        
        category_name_full = next((name for name, k in self.categories_map.items() if k == key), "Выбранная категория")
        category_name = category_name_full.lstrip().split(' ', 1)[-1] 
        
        dialog = ExtensionSelectionDialog(category_name, extensions, theme_data, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_exts = dialog.get_selected_extensions()
            if selected_exts:
                self.current_filter_ext = selected_exts
                self.current_filter_key = key 
                self.start_search()
            else:
                QMessageBox.warning(self, "Внимание", "Не выбрано ни одного формата. Сброс на 'Все файлы'.")
                all_files_btn = next(btn for btn, k in zip(self.menu_buttons, self.categories_map.values()) if k == "ALL_FILES")
                self.change_category("ALL_FILES", all_files_btn)
        else:
            all_files_btn = next(btn for btn, k in zip(self.menu_buttons, self.categories_map.values()) if k == "ALL_FILES")
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
                QMessageBox.warning(self, "Внимание", f"Для '{clicked_btn.text().lstrip()}' не найдено расширений в базе.")

        self.start_search()

    def restart_timer(self):
        """Перезапускает таймер для задержки поиска при вводе текста."""
        self.search_timer.start()

    def stop_all_threads(self):
        """Безопасно останавливает текущий поток поиска."""
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.requestInterruption()
            self.search_thread.wait()

    def is_searching_for_sensitive_files(self, key):
        """Проверяет, является ли запрос поиском ЭЦП/КриптоПро."""
        return key in ['эцп']

    def start_search(self):
        """Начинает или перезапускает поиск."""
        self.stop_all_threads() 

        term = self.search_input.text().strip()

        if not term and not self.current_filter_ext:
            self.results_list.clear()
            self.status_labels['status'].setText("Готов")
            self.status_labels['count'].setText("0")
            return

        self.run_local_search(term, self.current_filter_ext)

    def run_local_search(self, term, extensions):
        
        deep_scan = self.is_searching_for_sensitive_files(self.current_filter_key)
        
        self.results_list.clear()
        self.status_labels['status'].setText("Поиск...")
        self.status_labels['count'].setText("...")
        
        # --- КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ СБОЯ ---
        if self.search_thread:
            try:
                self.search_thread.update_results.disconnect(self.update_ui_results)
                self.search_thread.update_status.disconnect(self.update_status_card)
            except (TypeError, RuntimeError):
                pass
        # ------------------------------------
        
        self.search_thread = SearchThread(term, extensions, self.root_dir, deep_scan) 
        self.search_thread.update_results.connect(self.update_ui_results)
        self.search_thread.update_status.connect(self.update_status_card)
        self.search_thread.start()

    def update_ui_results(self, results):
        self.results_list.clear()
        self.raw_results_data = results
        
        path_color = THEMES[self.current_theme]['text_path']

        for filename, full_path in results:
            list_item = QListWidgetItem(self.results_list)
            item_widget = FileItemWidget(filename, full_path, path_color)
            list_item.setSizeHint(item_widget.sizeHint())
            self.results_list.setItemWidget(list_item, item_widget)
            list_item.setData(Qt.ItemDataRole.UserRole, full_path)

    def update_status_card(self, title, value):
        if title == "Готово":
            self.status_labels['status'].setText("Завершено")
            if "Найдено:" in value:
                self.status_labels['count'].setText(value.split(": ")[1])
        elif title == "Сканирование":
            self.status_labels['status'].setText("Сканирование...")
            self.status_labels['count'].setText(value.replace(" файлов...", ""))
        elif title == "Ошибка":
            self.status_labels['status'].setText("Ошибка")
            self.status_labels['count'].setText(value)


    def show_context_menu(self, position):
        item = self.results_list.itemAt(position)
        if item:
            full_path = item.data(Qt.ItemDataRole.UserRole)
            
            if full_path and os.path.exists(full_path):
                menu = QMenu()
                # Применение стилей темы к контекстному меню
                menu.setStyleSheet(f"""
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
                """)
                
                open_action = menu.addAction("📂 Открыть в папке")
                open_action.triggered.connect(lambda: subprocess.Popen(['explorer', '/select,', os.path.normpath(full_path)]))
                menu.exec(self.results_list.mapToGlobal(position))

    def toggle_theme(self):
        if self.current_theme == "dark":
            self.current_theme = "light"
            self.theme_toggle.setText("☀️ Светлая тема")
        else:
            self.current_theme = "dark"
            self.theme_toggle.setText("🌙 Тёмная тема")
        self.apply_theme()
        
        # Обновляем список, чтобы применить стили пути
        if self.raw_results_data:
            self.update_ui_results(self.raw_results_data) 

    def apply_theme(self):
        t = THEMES[self.current_theme]
        
        # --- ИЗМЕНЕНИЕ СТИЛЯ ДЛЯ АКЦЕНТНОЙ КНОПКИ (Обзор...) ---
        accent_button_style = f"""
            QPushButton#AccentButton {{
                background-color: {t['accent']}; 
                border-radius: 12px; 
                border: 1px solid {t['accent']};
                color: {t['accent_text']}; /* Белый текст на розовом фоне */
                padding: 0 15px;
                font-weight: bold;
            }}
            QPushButton#AccentButton:hover {{ 
                background-color: {t['accent_hover']}; 
                border: 1px solid {t['accent_hover']};
            }}
        """
        
        # Обновление стиля ComboBox
        combo_box_style = f"""
            QComboBox {{
                background-color: {t['input_bg']}; color: {t['text_main']};
                border: 1px solid {t['border']}; border-radius: 12px; padding: 0 15px; font-weight: 500;
            }}
            QComboBox:focus {{ border: 1px solid {t['accent']}; }}
            
            QComboBox::drop-down {{
                border: none;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                background-color: {t['input_bg']};
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            
            QComboBox QAbstractItemView {{
                border: 1px solid {t['border']};
                border-radius: 12px;
                background-color: {t['combo_list_bg']}; 
                color: {t['combo_list_text']}; 
                selection-background-color: {t['combo_list_hover']}; 
                padding: 5px;
            }}
            QComboBox QAbstractItemView::item {{
                color: {t['combo_list_text']};
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
            
            QLineEdit {{
                background-color: {t['input_bg']}; color: {t['text_main']};
                border: 1px solid {t['border']}; border-radius: 12px; padding: 0 15px; font-weight: 500;
            }}
            QLineEdit:focus {{ border: 1px solid {t['accent']}; }}

            /* Применяем стили для QComboBox */
            {combo_box_style}
            
            /* Применяем стили для кнопки "Обзор..." */
            {accent_button_style}
            
            QPushButton#IconBtn {{
                background-color: {t['input_bg']}; 
                border-radius: 12px; 
                border: 1px solid {t['border']};
                /* Стилизация для refresh_icon.png */
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernSearchApp()
    window.show()
    sys.exit(app.exec())