import sys
import os
from typing import Optional, Dict
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox,QListWidget, QListWidgetItem, QAbstractItemView)
from PySide6.QtCore import Qt, QStringListModel, QItemSelectionModel
from functools import partial

try:
    from UIv1 import Ui_MainWindow

    from file_selector import FileSelector
    from config_manager import ConfigManager
    from safety_dialog import SafetyConfirmDialog
    from validating import validate
    from firmware_config_manager import FirmwareConfigManager
    from sender import FirmwareSender

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

        # Инициализация состояния Safety mode из config.ini
        self._init_safety_checkbox()

        # Инициализация логики выбора IP
        self._init_ip_checkboxes()
        self._init_config_ip_checkboxes()

        # Менеджер конфигов прошивок
        self.fw_config = FirmwareConfigManager()
        self.sender = FirmwareSender()
        
        # Состояние для вкладки Config
        self.current_editing_section = None
        self.is_modifying = False
        
        # Инициализация вкладки Config
        self._init_config_tab()

        # Подключения сигналов
        self.ui.SelectionButton_Auto.clicked.connect(self.select_file_auto)
        self.ui.SelectionButton_Manual.clicked.connect(self.select_file_manual)
        self.ui.checkBox_Safety_Mode_Manual.stateChanged.connect(self._on_safety_checkbox_changed)
        self.ui.loadBatton_Manual.clicked.connect(self._on_manual_load_clicked)
        self.ui.loadBatton_Auto.clicked.connect(self._on_auto_load_clicked)

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

            # Если YES выключили (пользователь кликнул по нему повторно),
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

            # YES выключили — NO обязан включиться
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
        
        # Подключаем кнопки
        self.ui.toolButton_Delete_Config.clicked.connect(self._delete_config)
        self.ui.toolButton_Modify_Config.clicked.connect(self._modify_config)
        self.ui.toolButton_Add_New_Config__Accept_Config.clicked.connect(self._add_or_accept_config)
        
        # Загружаем список прошивок
        self._reload_config_list()
        
        # Подключаем клик по пустому месту в таблице
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

        # Очистить поля ввода конфига и сбросить IP-чекбоксы в NO
        self.ui.plainText_Name_Config.clear()
        self.ui.plainText_Specifier_Config.clear()
        self.ui.plainText_ID_Config.clear()
        self.ui.plainText_Port_Config.clear()
        self.ui.plainText_Specifier_Optional_Config.clear()
        self.ui.plainText_IP_Config.clear()

        # Сброс IP-чекбоксов в NO
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

        # Загрузка в Auto Mode с проверкой актуальности конфига и сравнением с эталоном
        if not self.auto_file_path:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран.")
            return

        # повторно читает конфиг с диска на случий удалили/изменили
        firmware, match_type = self.fw_config.find_firmware_for_file(self.auto_file_path)

        if match_type != "full":
            QMessageBox.critical(
                self,
                "❌ Конфиг изменился",
                "Конфигурация для этого файла больше не найдена или стала недействительной\n"
                "Пожалуйста, выберите файл заново"
            )
            self.ui.loadBatton_Auto.setEnabled(False)
            self.auto_reference_config = None
            return

        # Считывает текущие значения из полей
        current = {
            "name": self.ui.plainText_Name_Auto.toPlainText().strip(),
            "specifier": self.ui.plainText_Type_Auto.toPlainText().strip(),
            "id": self.ui.plainText_ID_Auto.toPlainText().strip(),
            "port": self.ui.plainText_Port_Auto.toPlainText().strip(),
            "ip": self.ui.plainText_IP_Auto.toPlainText().strip(),
        }

        # Нормализует эталон для сравнения
        ref_ip_raw = firmware.get("ip", "none")
        reference = {
            "name": firmware.get("name", "").strip(),
            "specifier": firmware.get("specifier", "").strip(),
            "id": firmware.get("id", "").strip(),
            "port": firmware.get("port", "").strip(),
            "ip": "" if ref_ip_raw.lower() == "none" else ref_ip_raw.strip(),
        }

        # Базовая валидация (обязательные поля)
        if not current["id"] or not current["port"]:
            QMessageBox.warning(self, "Неполные данные","Поля ID и Port обязательны для заполнения")
            return

        # Сравнивает с эталоном
        changed = (current != reference)

        # Формирует список изменений для отчёта пользователю
        diff_lines = []
        labels = {"name": "Name", "specifier": "Specifier", "id": "ID", "port": "Port", "ip": "IP"}
        for key in ("name", "specifier", "id", "port", "ip"):
            if current[key] != reference[key]:
                diff_lines.append(f"  * {labels[key]}: «{reference[key]}» -> «{current[key]}»")

    # Запуск 
        if changed:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("⚠️ Рекомендация изменена ⚠️")
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
                print("[AUTO LOAD] Отменено пользователем")
                return

            # Запуск с измененными параметрами
            tag = "AUTO MODE MODIFIED"
            params = current
        else:
            QMessageBox.information(
                self, "✅ Всё готово",
                f"Конфиг найден: {reference['name']}\n"
                f"Параметры совпадают с рекомендованными\n\n"
                f"Запускаю загрузку..."
            )

            # Запуск с рекомендовыными параметрами
            tag = "AUTO MODE SAFE"
            params = reference

        # Собирает и запускает команду
        ip_for_cmd = params["ip"] if params["ip"] else None
        command = self.sender.build_command(
            file_path=self.auto_file_path,
            dev_id=params["id"],
            port=params["port"],
            ip=ip_for_cmd
        )
        self.sender._run_command(command, tag=tag)

    # - Auto Mode с проверкой конфига -

    def select_file_auto(self):

        # Выбор файла для Auto Mode + поиск конфига + сохранение эталона
        full_path, display_path = FileSelector.select_firmware_file(self, "Выберите файл прошивки (Auto Mode)")

        if not full_path:
            return

        self.auto_file_path = full_path
        self.ui.path_Auto.setPlainText(display_path)

        # Ищет конфиг (с автоматическим reload внутри find_firmware_for_file)
        firmware, match_type = self.fw_config.find_firmware_for_file(full_path)

        if match_type == "full":

            # Сохраняет эталон
            self.auto_reference_config = firmware

            # Заполняет поля рекомендованными значениями
            self.ui.plainText_Name_Auto.setPlainText(firmware.get("name", ""))
            self.ui.plainText_Type_Auto.setPlainText(firmware.get("specifier", ""))
            self.ui.plainText_ID_Auto.setPlainText(firmware.get("id", ""))
            self.ui.plainText_Port_Auto.setPlainText(firmware.get("port", ""))

            ip_value = firmware.get("ip", "none")
            self.ui.plainText_IP_Auto.setPlainText("" if ip_value.lower() == "none" else ip_value)

            QMessageBox.information(
                self, "✅ Конфиг найден",
                "Прошивка найдена в базе\n"
                "Вы можете изменить параметры перед загрузкой"
            )
            self.ui.loadBatton_Auto.setEnabled(True)

        elif match_type == "partial":
            self.auto_reference_config = None
            QMessageBox.warning(
                self, "⚠️ Неполное совпадение",
                "Найдено частичное совпадение конфигурации\n"
                "Загрузка в Auto Mode запрещена"
            )
            self.ui.loadBatton_Auto.setEnabled(False)

        else:
            self.auto_reference_config = None
            QMessageBox.critical(
                self, "❌ Не найдено",
                "Файл конфигурации прошивки не найден\n"
                "Загрузка в Auto Mode запрещена"
            )
            self.ui.loadBatton_Auto.setEnabled(False)


    # - Manual Mode -
    def _on_manual_load_clicked(self):

        # Загрузка в Manual Mode с проверкой конфига
        self.sender.send_manual(
            parent=self,
            file_path=self.manual_file_path,
            dev_id=self.ui.plainTextID_Manual.toPlainText().strip(),
            port=self.ui.plainTextPort_Manual.toPlainText().strip(),
            ip=self.ui.plainTextIP_Manual.toPlainText().strip(),
            ip_required=self.is_manual_ip_required,
            safety_enabled=self.ui.checkBox_Safety_Mode_Manual.isChecked(),
        )

    def select_file_manual(self):

        # Обработчик выбора файла для Manual Mode
        full_path, display_path = FileSelector.select_firmware_file( self, "Выберите файл прошивки (Manual Mode)")
        
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