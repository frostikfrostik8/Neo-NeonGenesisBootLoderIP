import sys
from typing import Optional, Dict
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PySide6.QtGui import QStandardItemModel, QStandardItem

try:
    from UIv1 import Ui_MainWindow

    from file_selector import FileSelector
    from config_manager import ConfigManager
    from safety_dialog import SafetyConfirmDialog
    from validating import validate
    from firmware_config_manager import FirmwareConfigManager
    from sender import FirmwareSender
    from loader_thread import LoaderThread

except ImportError as e:
    print(f"Ошибка импорта: {e}")
    sys.exit(1)

class EasyLoaderWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        
        # Инициализация UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Переменные для хранения полных путей (раздельно для каждого режима)
        self.auto_file_path = ""
        self.manual_file_path = ""

        # Эталонный конфиг для Auto Mode (запоминается при выборе файла)
        self.auto_reference_config = None

        # Менеджер конфигурации
        self.config = ConfigManager()
        self.fw_config = FirmwareConfigManager()
        self.sender = FirmwareSender(self.config)

        # Ссылка на активный поток чтобы не собрался сборщиком мусора
        self.loader_thread: Optional[LoaderThread] = None
        self.current_mode: str = ""  # "auto" или "manual"

        # Максимальный прогресс (защита от отката)
        self.max_progress = 0

        # Модели для логов
        self.auto_log_model = QStandardItemModel()
        self.manual_log_model = QStandardItemModel()
        self.ui.Stages_List_View_Auto.setModel(self.auto_log_model)
        self.ui.Stages_List_View_Manual.setModel(self.manual_log_model)


        # Инициализация состояния Safety mode из config.ini
        # Инициализация логики выбора IP
        # Инициализация вкладки Config
        self._init_safety_checkbox()
        self._init_ip_checkboxes()
        self._init_config_ip_checkboxes()
        self._init_config_tab()
        
        # Состояние для вкладки Config
        self.current_editing_section = None
        self.is_modifying = False

        # Подключения сигналов
        self.ui.SelectionButton_Auto.clicked.connect(self.select_file_auto)
        self.ui.SelectionButton_Manual.clicked.connect(self.select_file_manual)
        self.ui.checkBox_Safety_Mode_Manual.stateChanged.connect(self._on_safety_checkbox_changed)
        self.ui.loadBatton_Manual.clicked.connect(self._on_manual_load_clicked)
        self.ui.loadBatton_Auto.clicked.connect(self._on_auto_load_clicked)
        self.ui.resetButton_Auto.clicked.connect(self._on_auto_reset_clicked)
        self.ui.resetButton_Manual.clicked.connect(self._on_manual_reset_clicked)

    # --- Запуск загрузчика ---

    def _start_loader(self, parent, args: list, tag: str):

        # Общий метод запуска EasyLoader в отдельном потоке
        if self.loader_thread and self.loader_thread.isRunning():
            QMessageBox.warning(self, "Занят", "Предыдущая загрузка ещё идёт.")
            return

        # Определяет режим
        self.current_mode = "auto" if parent == self and tag.startswith("AUTO") else "manual"

        # Определяет целевые виджеты
        if self.current_mode == "auto":
            progress_bar = self.ui.progressBar_Auto
            log_model = self.auto_log_model
            load_button = self.ui.loadBatton_Auto
        else:
            progress_bar = self.ui.progress_Bar_Manual
            log_model = self.manual_log_model
            load_button = self.ui.loadBatton_Manual

        # Сброс состояния
        self.max_progress = 0
        progress_bar.setValue(0)
        log_model.clear()
        load_button.setEnabled(False)

        # Создаёт и запускает поток
        exe_name = self.config.get_exe_name()
        self.loader_thread = LoaderThread(exe_name, args)

        self.loader_thread.log_received.connect(lambda line: self._on_log_received(line, log_model))
        self.loader_thread.progress_received.connect(lambda p: self._on_progress_received(p, progress_bar))
        self.loader_thread.process_finished.connect(lambda: self._on_process_finished(load_button))
        self.loader_thread.error_occurred.connect(self._on_error)

        print("=" * 60)
        print(f"[{tag}] Запуск: {exe_name} {' '.join(args)}")
        print("=" * 60)

        self.loader_thread.start()

    def _on_log_received(self, line: str, model: QStandardItemModel):

        # Добавление строки лога в QListView
        item = QStandardItem(line)
        item.setEditable(False)
        model.appendRow(item)

        # Прокрутка в конец
        list_view = self.ui.Stages_List_View_Auto if model == self.auto_log_model else self.ui.Stages_List_View_Manual
        list_view.scrollToBottom()

    def _on_progress_received(self, progress: int, progress_bar):

        # Обновление прогресс бара
        if progress > self.max_progress:
            self.max_progress = progress
            progress_bar.setValue(self.max_progress)

    def _on_process_finished(self, load_button):

        # Завершение процесса и разблокировка кнопки
        load_button.setEnabled(True)
        print("[INFO] Процесс EasyLoader завершён")
        QMessageBox.information(self, "Завершено", "Загрузка завершена")

    def _on_error(self, error_text: str):

        # Обработка ошибок запуска
        QMessageBox.critical(self, "Ошибка", error_text)
        print(f"[ERROR] {error_text}")

    # - IP Manual Mode -

    def _init_ip_checkboxes(self):

        # Инициализация чекбоксов IP, при запуске всегда активно NO

        # Блокируем сигналы на время начальной настройки, чтобы не сработали обработчики

        self.ui.checkBox_NO_IP.blockSignals(True)
        self.ui.checkBox_Yes_IP.blockSignals(True)
        
        # По умолчанию всегда NO
        self.ui.checkBox_NO_IP.setChecked(True)
        self.ui.checkBox_Yes_IP.setChecked(False)
        
        self.ui.checkBox_NO_IP.blockSignals(False)
        self.ui.checkBox_Yes_IP.blockSignals(False)
        
        # Флаг состояния: True = YES (IP нужен), False = NO (IP не нужен)
        self.manual_ip_enabled = False
        
        # Поле ввода IP неактивно, так как выбрано NO
        self.ui.plainTextIP_Manual.setEnabled(False)
        
        # Подключаем обработчики
        self.ui.checkBox_Yes_IP.toggled.connect(self._on_yes_ip_toggled)
        self.ui.checkBox_NO_IP.toggled.connect(self._on_no_ip_toggled)

    def _on_yes_ip_toggled(self, checked: bool):

        # Обработчик нажатия на YES
        if checked:

            # Снимаем NO
            self.ui.checkBox_NO_IP.blockSignals(True)
            self.ui.checkBox_NO_IP.setChecked(False)
            self.ui.checkBox_NO_IP.blockSignals(False)
            
            self.manual_ip_enabled = True
            self.ui.plainTextIP_Manual.setEnabled(True)
        else:

            # Если YES выключили (пользователь кликнул по нему повторно)
            # NO должен включиться принудительно
            self.ui.checkBox_NO_IP.blockSignals(True)
            self.ui.checkBox_NO_IP.setChecked(True)
            self.ui.checkBox_NO_IP.blockSignals(False)

    def _on_no_ip_toggled(self, checked: bool):

        # Обработчик нажатия на NO
        if checked:

            # Снимаем YES
            self.ui.checkBox_Yes_IP.blockSignals(True)
            self.ui.checkBox_Yes_IP.setChecked(False)
            self.ui.checkBox_Yes_IP.blockSignals(False)
            
            self.manual_ip_enabled = False
            self.ui.plainTextIP_Manual.setEnabled(False)
            self.ui.plainTextIP_Manual.setPlainText("") # Очищстка при отказе от IP
        else:

            # Заприщает снимать NO, если YES не активен (возвращает галочку)
            if not self.ui.checkBox_Yes_IP.isChecked():
                self.ui.checkBox_NO_IP.blockSignals(True)
                self.ui.checkBox_NO_IP.setChecked(True)
                self.ui.checkBox_NO_IP.blockSignals(False)

    @property
    def is_manual_ip_required(self) -> bool:

        # Свойство-флаг для удобной проверки в других частях кода
        # Возвращает True, если в Manual Mode выбран YES (IP используется)
        return self.manual_ip_enabled
    
    # - IP Config Mode -

    def _init_config_ip_checkboxes(self):

        # Инициализация чекбоксов IP во вкладке Config всегда активно NO
        self.ui.checkBox_NO_IP_2.blockSignals(True)
        self.ui.checkBox_Yes_IP_2.blockSignals(True)

        self.ui.checkBox_NO_IP_2.setChecked(True)
        self.ui.checkBox_Yes_IP_2.setChecked(False)

        self.ui.checkBox_NO_IP_2.blockSignals(False)
        self.ui.checkBox_Yes_IP_2.blockSignals(False)

        # Флаг состояния True = YES (IP задан), False = NO (ip = none)
        self.config_ip_enabled = False

        # Поле IP неактивно, т.к. выбрано NO
        self.ui.plainText_IP_Config.setEnabled(False)

        # Подключаем обработчики
        self.ui.checkBox_Yes_IP_2.toggled.connect(self._on_config_yes_ip_toggled)
        self.ui.checkBox_NO_IP_2.toggled.connect(self._on_config_no_ip_toggled)

    def _on_config_yes_ip_toggled(self, checked: bool):

        # Обработчик нажатия YES во вкладке Config
        if checked:
            self.ui.checkBox_NO_IP_2.blockSignals(True)
            self.ui.checkBox_NO_IP_2.setChecked(False)
            self.ui.checkBox_NO_IP_2.blockSignals(False)

            self.config_ip_enabled = True
            self.ui.plainText_IP_Config.setEnabled(True)
        else:

            # YES выключили NO обязан включиться
            self.ui.checkBox_NO_IP_2.blockSignals(True)
            self.ui.checkBox_NO_IP_2.setChecked(True)
            self.ui.checkBox_NO_IP_2.blockSignals(False)

    def _on_config_no_ip_toggled(self, checked: bool):

        # Обработчик нажатия NO во вкладке Config
        if checked:
            self.ui.checkBox_Yes_IP_2.blockSignals(True)
            self.ui.checkBox_Yes_IP_2.setChecked(False)
            self.ui.checkBox_Yes_IP_2.blockSignals(False)

            self.config_ip_enabled = False
            self.ui.plainText_IP_Config.setEnabled(False)
            self.ui.plainText_IP_Config.setPlainText("")  # очищстка
        else:

            # Запрещаем снимать NO, если YES не активен
            if not self.ui.checkBox_Yes_IP_2.isChecked():
                self.ui.checkBox_NO_IP_2.blockSignals(True)
                self.ui.checkBox_NO_IP_2.setChecked(True)
                self.ui.checkBox_NO_IP_2.blockSignals(False)

    @property
    def is_config_ip_required(self) -> bool:

        # True, если во вкладке Config выбрано YES (IP будет сохранён)
        return self.config_ip_enabled


    # - Config Tab -

    def _init_config_tab(self):

        # Инициализация вкладки Config
        # Создаётся список прошивок (заменяет QTableView на QListWidget для простоты)
        # В UIv1.py это Configuration_List_Config, но он QTableView
        # Для простоты создадил новый QListWidget
        # Да костыли, и что? (нужно поправить, но лень)
        
        # Подключает кнопки
        self.ui.toolButton_Delete_Config.clicked.connect(self._delete_config)
        self.ui.toolButton_Modify_Config.clicked.connect(self._modify_config)
        self.ui.toolButton_Add_New_Config__Accept_Config.clicked.connect(self._add_or_accept_config)
        
        # Загружает список прошивок
        self._reload_config_list()
        
        # Подключает клик по пустому месту в таблице
        # (для QTableView это сложо, нужно использовать selectionModel)

    def _reload_config_list(self):

        # Перезагружает список прошивок в таблицу
        # Для простоты будем использовать модель/вью
        # Но так как в UI QTableView, нужно создать модель
        from PySide6.QtCore import QStringListModel
        
        firmwares = self.fw_config.get_all_firmwares()
        names = [fw["name"] for fw in firmwares]
        
        # Создаётся простая модель
        self.config_list_model = QStringListModel(names)
        self.ui.Configuration_List_Config.setModel(self.config_list_model)
        
        # Сохраняеться маппинг индексов
        self.config_list_data = firmwares

    def _get_selected_config(self) -> Optional[Dict[str, str]]:

        # Получить выделенную прошивку из списка
        indexes = self.ui.Configuration_List_Config.selectedIndexes()
        if not indexes:
            return None
        
        row = indexes[0].row()
        if 0 <= row < len(self.config_list_data):
            return self.config_list_data[row]
        return None

    def _delete_config(self):

        # Удалить выделенную прошивку
        firmware = self._get_selected_config()
        if not firmware:
            QMessageBox.warning(self, "Ошибка", "Выберите прошивку для удаления")
            return
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить прошивку '{firmware['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.fw_config.delete_firmware(firmware["section"])
            self._reload_config_list()
            self._clear_config_fields()

    def _modify_config(self):

        # Заполнить поля данными выделенной прошивки
        firmware = self._get_selected_config()
        if not firmware:
            QMessageBox.warning(self, "Ошибка", "Выберите прошивку для редактирования")
            return

        self.is_modifying = True
        self.current_editing_section = firmware["section"]

        self.ui.plainText_Name_Config.setPlainText(firmware.get("name", ""))
        self.ui.plainText_Specifier_Config.setPlainText(firmware.get("specifier", ""))
        self.ui.plainText_ID_Config.setPlainText(firmware.get("id", ""))
        self.ui.plainText_Port_Config.setPlainText(firmware.get("port", ""))

        # Specifier 2 (optional)
        spec2 = firmware.get("specifier_2", "none")
        self.ui.plainText_Specifier_Optional_Config.setPlainText("" if spec2.lower() == "none" else spec2)

        # IP - устанавливаем чекбоксы в зависимости от значения в конфиге
        ip_value = firmware.get("ip", "none")
        if ip_value.lower() == "none" or not ip_value.strip():

            # В конфиге нет IP -> NO
            self.ui.checkBox_NO_IP_2.blockSignals(True)
            self.ui.checkBox_Yes_IP_2.blockSignals(True)
            self.ui.checkBox_NO_IP_2.setChecked(True)
            self.ui.checkBox_Yes_IP_2.setChecked(False)
            self.ui.plainText_IP_Config.setPlainText("")
            self.ui.checkBox_NO_IP_2.blockSignals(False)
            self.ui.checkBox_Yes_IP_2.blockSignals(False)
            self.config_ip_enabled = False
            self.ui.plainText_IP_Config.setEnabled(False)
        else:

            # В конфиге есть IP -> YES
            self.ui.checkBox_NO_IP_2.blockSignals(True)
            self.ui.checkBox_Yes_IP_2.blockSignals(True)
            self.ui.checkBox_Yes_IP_2.setChecked(True)
            self.ui.checkBox_NO_IP_2.setChecked(False)
            self.ui.plainText_IP_Config.setPlainText(ip_value)
            self.ui.checkBox_NO_IP_2.blockSignals(False)
            self.ui.checkBox_Yes_IP_2.blockSignals(False)
            self.config_ip_enabled = True
            self.ui.plainText_IP_Config.setEnabled(True)

    def _add_or_accept_config(self):

        # Добавить новую или сохранить изменения
        name = self.ui.plainText_Name_Config.toPlainText().strip()
        specifier = self.ui.plainText_Specifier_Config.toPlainText().strip()
        dev_id = self.ui.plainText_ID_Config.toPlainText().strip()
        port = self.ui.plainText_Port_Config.toPlainText().strip()
        spec2 = self.ui.plainText_Specifier_Optional_Config.toPlainText().strip()

        # IP - читаем ТОЛЬКО если выбрано YES
        if self.is_config_ip_required:
            ip = self.ui.plainText_IP_Config.toPlainText().strip()
            if not ip:
                QMessageBox.warning(self, "Ошибка", "Выбран IP=YES, но адрес не введён")
                return
        else:
            ip = "none"

        if not all([name, specifier, dev_id, port]):
            QMessageBox.warning(self, "Ошибка","Заполните обязательные поля: Name, Specifier, ID, Port")
            return

        if self.is_modifying and self.current_editing_section:
            self.fw_config.update_firmware(
                self.current_editing_section, name, specifier, dev_id, port, spec2, ip
            )
            QMessageBox.information(self, "✅ Сохранено", "Конфигурация обновлена")
        else:
            self.fw_config.add_firmware(name, specifier, dev_id, port, spec2, ip)
            QMessageBox.information(self, "✅ Добавлено", "Новая прошивка добавлена")

        self._reload_config_list()
        self._clear_config_fields()

    def _clear_config_fields(self):

        # Очистить поля ввода конфига и сбросить IP чекбоксы в NO
        self.ui.plainText_Name_Config.clear()
        self.ui.plainText_Specifier_Config.clear()
        self.ui.plainText_ID_Config.clear()
        self.ui.plainText_Port_Config.clear()
        self.ui.plainText_Specifier_Optional_Config.clear()
        self.ui.plainText_IP_Config.clear()

        # Сброс IP чекбоксов в NO
        self.ui.checkBox_NO_IP_2.blockSignals(True)
        self.ui.checkBox_Yes_IP_2.blockSignals(True)
        self.ui.checkBox_NO_IP_2.setChecked(True)
        self.ui.checkBox_Yes_IP_2.setChecked(False)
        self.ui.checkBox_NO_IP_2.blockSignals(False)
        self.ui.checkBox_Yes_IP_2.blockSignals(False)

        self.config_ip_enabled = False
        self.ui.plainText_IP_Config.setEnabled(False)

        self.is_modifying = False
        self.current_editing_section = None


# - Safety mode -
    def _init_safety_checkbox(self):

        # Устанавливает начальное состояние чекбокса при запуске
        # permanent disable = True -> галочка снята, окно не показывается
        # permanent disable = False -> галочка установлена (temp сброшен в True)
        
        self.config.reset_temp_on_startup()

        self.ui.checkBox_Safety_Mode_Manual.blockSignals(True)
        self.ui.checkBox_Safety_Mode_Manual.setChecked(self.config.is_safety_enabled())
        self.ui.checkBox_Safety_Mode_Manual.blockSignals(False)

    def _on_safety_checkbox_changed(self, state):

        # state == 0 -> пользователь пытается снять галочку (показать диалог)
        # state == 2 -> пользователь поставил галочку обратно

        if state == 0:

            # Если проверка отключена навсегда - просто обновляем temp, диалог показывать не нужно
            if self.config.is_safety_check_permanently_disabled():
                self.config.set_safety_temp(False)
                return

            dialog = SafetyConfirmDialog(self)
            
            confirmed = dialog.exec() == SafetyConfirmDialog.Accepted

            if confirmed:

                # Успех - фиксируем в конфиге
                self.config.set_safety_temp(False)

            else:

                # Возвращаем галочку и показываем "Ты не уверен в себе"
                self.ui.checkBox_Safety_Mode_Manual.blockSignals(True)
                self.ui.checkBox_Safety_Mode_Manual.setChecked(True)
                self.ui.checkBox_Safety_Mode_Manual.blockSignals(False)
                
                QMessageBox.information(self, "Результат", "Ты не уверен в себе")

        else:

            # Галочку вернули вручную - обновляем temp в TrueА
            self.config.set_safety_temp(True)

    # - Загрузка -
    def _on_manual_load_clicked(self):

    # Загрузка в Manual Mode с учётом Safety mode и наличия конфига
        FirmwareSender.send_manual(
            parent=self,
            file_path=self.manual_file_path,
            dev_id=self.ui.plainTextID_Manual.toPlainText().strip(),
            port=self.ui.plainTextPort_Manual.toPlainText().strip(),
            ip=self.ui.plainTextIP_Manual.toPlainText().strip(),
            ip_required=self.is_manual_ip_required,   
            safety_enabled=self.ui.checkBox_Safety_Mode_Manual.isChecked(),
        )

    def _on_auto_load_clicked(self):
        if not self.auto_file_path:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран")
            return

        firmware, match_type = self.fw_config.find_firmware_for_file(self.auto_file_path)

        if match_type != "full":
            QMessageBox.critical(self, "❌ Конфиг изменился","Конфиг больше не найден. Выберите файл заново")
            self.ui.loadBatton_Auto.setEnabled(False)
            self.auto_reference_config = None
            return

        current = {
            "name": self.ui.plainText_Name_Auto.toPlainText().strip(),
            "specifier": self.ui.plainText_Type_Auto.toPlainText().strip(),
            "id": self.ui.plainText_ID_Auto.toPlainText().strip(),
            "port": self.ui.plainText_Port_Auto.toPlainText().strip(),
            "ip": self.ui.plainText_IP_Auto.toPlainText().strip(),
        }

        ref_ip_raw = firmware.get("ip", "none")
        reference = {
            "name": firmware.get("name", "").strip(),
            "specifier": firmware.get("specifier", "").strip(),
            "id": firmware.get("id", "").strip(),
            "port": firmware.get("port", "").strip(),
            "ip": "" if ref_ip_raw.lower() == "none" else ref_ip_raw.strip(),
        }

        if not current["id"] or not current["port"]:
            QMessageBox.warning(self, "Неполные данные", "ID и Port обязательны ")
            return

        changed = (current != reference)
        labels = {"name": "Name", "specifier": "Specifier", "id": "ID", "port": "Port", "ip": "IP"}
        diff_lines = [
            f"  📎 {labels[k]}: <<{reference[k]}>> -> <<{current[k]}>>"
            for k in ("name", "specifier", "id", "port", "ip") if current[k] != reference[k]
        ]

        if changed:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("⚠️ Рекомендация изменена")
            box.setText(
                "Вы изменили рекомендованные параметры:\n\n"
                + "\n".join(diff_lines)
                + "\n\nЗапустить загрузку с новыми параметрами?"
            )
            box.setStandardButtons(QMessageBox.Cancel)
            btn_run = box.addButton("Запустить", QMessageBox.AcceptRole)
            box.setDefaultButton(btn_run)
            box.exec()
            if box.clickedButton() != btn_run:
                return
            tag = "AUTO MODE MODIFIED"
            params = current
        else:
            QMessageBox.information(
                self, "✅ Всё готово",f"Конфиг: {reference['name']}\nЗапускаю...")
            tag = "AUTO MODE SAFE"
            params = reference

        ip_for_cmd = params["ip"] if params["ip"] else None
        args = self.sender.build_command_args(self.auto_file_path, params["id"], params["port"], ip_for_cmd)
        self._start_loader(self, args, tag)

    def _on_auto_reset_clicked(self):

        # Сброс устройства в Auto Mode
        # Берет параметры из полей Auto и запрашивает подтверждение

        dev_id = self.ui.plainText_ID_Auto.toPlainText().strip()
        port = self.ui.plainText_Port_Auto.toPlainText().strip()
        ip = self.ui.plainText_IP_Auto.toPlainText().strip()

        # Базовая валидация
        if not dev_id or not port:
            QMessageBox.warning(self, "Неполные данные", "Поля ID и Port обязательны для заполнения")
            return

        # Формируем аргументы с "Reset" вместо пути к файлу
        args = self.sender.build_command_args("Reset", dev_id, port, ip if ip else None)

        # Окно подтверждения (так как Reset - деструктивное действие)
        reply = QMessageBox.question(
            self, 
            "⚠️ Подтверждение Reset",
            f"Вы уверены, что хотите выполнить сброс устройства?\n\n"
            f"Параметры:\n"
            f"  0 ID: {dev_id}\n"
            f"  0 Port: {port}\n"
            f"  0 IP: {ip if ip else 'none'}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._start_loader(self, args, "AUTO RESET")

    # - Auto Mode с проверкой конфига -

    def select_file_auto(self):

        full_path, display_path = FileSelector.select_firmware_file(self, "Выберите файл прошивки (Auto Mode)")
        if not full_path:
            return

        self.auto_file_path = full_path
        self.ui.path_Auto.setPlainText(display_path)

        firmware, match_type = self.fw_config.find_firmware_for_file(full_path)

        if match_type == "full":
            self.auto_reference_config = firmware
            self.ui.plainText_Name_Auto.setPlainText(firmware.get("name", ""))
            self.ui.plainText_Type_Auto.setPlainText(firmware.get("specifier", ""))
            self.ui.plainText_ID_Auto.setPlainText(firmware.get("id", ""))
            self.ui.plainText_Port_Auto.setPlainText(firmware.get("port", ""))
            ip_value = firmware.get("ip", "none")
            self.ui.plainText_IP_Auto.setPlainText("" if ip_value.lower() == "none" else ip_value)
            QMessageBox.information(self, "✅ Конфиг найден","Прошивка найдена. Параметры можно изменить")
            self.ui.loadBatton_Auto.setEnabled(True)
        elif match_type == "partial":
            self.auto_reference_config = None
            QMessageBox.warning(self, "⚠️ Неполное совпадение", "Загрузка запрещена")
            self.ui.loadBatton_Auto.setEnabled(False)
        else:
            self.auto_reference_config = None
            QMessageBox.critical(self, "❌ Не найдено", "Конфиг не найден. Загрузка запрещена")
            self.ui.loadBatton_Auto.setEnabled(False)


    # - Manual Mode -
    def _on_manual_load_clicked(self):

        self.sender.send_manual(
            parent=self,
            file_path=self.manual_file_path,
            dev_id=self.ui.plainTextID_Manual.toPlainText().strip(),
            port=self.ui.plainTextPort_Manual.toPlainText().strip(),
            ip=self.ui.plainTextIP_Manual.toPlainText().strip(),
            ip_required=self.is_manual_ip_required,
            safety_enabled=self.ui.checkBox_Safety_Mode_Manual.isChecked(),
            on_run=lambda parent, args, tag: self._start_loader(parent, args, f"MANUAL {tag}")
        )

    # - Manual Mode Reset -

    def _on_manual_reset_clicked(self):

        # Сброс устройства в Manual Mode с соблюдением логики Safety mode
        self.sender.send_manual(
            parent=self,
            file_path="Reset",
            dev_id=self.ui.plainTextID_Manual.toPlainText().strip(),
            port=self.ui.plainTextPort_Manual.toPlainText().strip(),
            ip=self.ui.plainTextIP_Manual.toPlainText().strip(),
            ip_required=self.is_manual_ip_required,
            safety_enabled=self.ui.checkBox_Safety_Mode_Manual.isChecked(),
            on_run=lambda parent, args, tag: self._start_loader(parent, args, f"MANUAL {tag}")
        )

    def select_file_manual(self):

        full_path, display_path = FileSelector.select_firmware_file(
            self, "Выберите файл прошивки (Manual Mode)"
        )
        if full_path:
            self.manual_file_path = full_path
            self.ui.path_Manual.setPlainText(display_path)


def main():

    # Создание приложения и главного окна
    app = QApplication(sys.argv)
    
    window = EasyLoaderWindow()
    window.setWindowTitle("UI-mode for EasyLoader")
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()