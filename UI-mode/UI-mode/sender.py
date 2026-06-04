# Модуль отправки прошивки через внешний EasyLoader.
# С проверкой конфигурации и 3 режимами уведомлений.

import os
from PySide6.QtWidgets import QMessageBox
from firmware_config_manager import FirmwareConfigManager
from loader_thread import LoaderThread
from config_manager import ConfigManager 


class FirmwareSender:
    EXE_NAME = "EasyLoader"

    def __init__(self, config_manager: ConfigManager):
        self.fw_config = FirmwareConfigManager()
        self.config = config_manager  # ConfigManager для получения exe_name

    @staticmethod
    def build_command_args(file_path: str, dev_id: str, port: str, ip: str | None) -> list:

        # Собирает строку EasyLoader [ID] [PORT] [FILE] [IP]
        parts = [str(dev_id), str(port), file_path]
        if ip and ip.strip().lower() != "none":
            parts.append(ip.strip())
        return parts

    @staticmethod
    def _validate_manual_fields(dev_id: str, port: str, ip: str | None, ip_required: bool) -> str | None:
        if not dev_id or not dev_id.strip():
            return "Не указан ID устройства"
        if not port or not port.strip():
            return "Не указан порт"
        if ip_required and (not ip or not ip.strip()):
            return "Выбран IP=YES, но адрес не введён"
        return None

    def send_auto(self, parent, file_path: str, ui_fields: dict) -> bool:
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.critical(parent, "Ошибка", "Файл прошивки не выбран")
            return False

        firmware, match_type = self.fw_config.find_firmware_for_file(file_path)

        if match_type == "full":
            ui_fields["name"].setPlainText(firmware.get("name", ""))
            ui_fields["specifier"].setPlainText(firmware.get("specifier", ""))
            ui_fields["id"].setPlainText(firmware.get("id", ""))
            ui_fields["port"].setPlainText(firmware.get("port", ""))
            ip_value = firmware.get("ip", "none")
            ui_fields["ip"].setPlainText("" if ip_value.lower() == "none" else ip_value)

            QMessageBox.information(parent, "✅ Конфиг найден", "Прошивка найдена. Можно редактировать и загружать")
            return True
        elif match_type == "partial":
            QMessageBox.warning(parent, "⚠️ Неполное совпадение", "Частичное совпадение. Загрузка запрещена")
            return False
        else:
            QMessageBox.critical(parent, "❌ Не найдено", "Конфиг не найден. Загрузка запрещена")
            return False

    def send_manual(self, parent, file_path: str, dev_id: str, port: str,ip: str | None, ip_required: bool, safety_enabled: bool,on_run) -> None:
        
        is_reset = (file_path == "Reset")

        # Проверка файла (пропуск для Reset)
        if not is_reset:
            if not file_path or not os.path.isfile(file_path):
                QMessageBox.critical(parent, "Ошибка", "Файл прошивки не выбран или не существует")
                return

        # Валидация полей (ID, Port, IP)
        err = self._validate_manual_fields(dev_id, port, ip, ip_required)
        if err:
            QMessageBox.warning(parent, "Неполные данные", err)
            return

        # Формирует аргументы (file_path может быть "Reset" или путь к файлу)
        args = self.build_command_args(file_path, dev_id, port, ip if ip_required else None)

        # - Safety OFF -
        if not safety_enabled:
            self._show_unsafe_dialog(parent, args, on_run)
            return

        # - Safety ON -
        if is_reset:
            # Для Reset конфига нет, сразу идем в окно "на свой страх и риск"
            self._show_unknown_dialog(parent, args, on_run, file_path="Reset")
            return

        # Ищет конфиг для файла
        firmware, match_type = self.fw_config.find_firmware_for_file(file_path)

        if match_type == "full":

            # Проверяет совпадение параметров
            errors = []
            if firmware.get("id") != dev_id:
                errors.append(f"ID: введено '{dev_id}', в конфиге '{firmware.get('id')}'")
            if firmware.get("port") != port:
                errors.append(f"Port: введено '{port}', в конфиге '{firmware.get('port')}'")
            
            config_ip = firmware.get("ip", "none")

            if ip_required:
                if config_ip.lower() == "none":
                    errors.append("IP: введено значение, но в конфиге IP не указан")
                elif config_ip != ip:
                    errors.append(f"IP: введено '{ip}', в конфиге '{config_ip}'")
            else:
                if config_ip.lower() != "none" and ip:
                    errors.append(f"IP: введено '{ip}', но в конфиге указан '{config_ip}'")

            if errors:
                error_text = "\n".join(errors)
                QMessageBox.warning(parent, "⚠️ Параметры не совпадают", f"Конфиг найден, но параметры отличаются:\n\n{error_text}")
                return

            # Всё совпало - запускаем
            self._show_ok_dialog(parent, args, firmware, on_run)

        elif match_type == "partial":
            QMessageBox.warning(
                parent,
                "⚠️ Неполное совпадение",
                "Найдено частичное совпадение конфигурации\n"
                "Загрузка запрещена в защищённом режиме"
            )
        else:

            # Конфиг не найден, окно "на свой страх и риск"
            self._show_unknown_dialog(parent, args, on_run, file_path="")

    def _show_ok_dialog(self, parent, args: list, firmware: dict, on_run) -> None:
        QMessageBox.information(parent, "✅ Всё готово", f"Конфиг найден: {firmware.get('name', '?')}\nЗапускаю загрузку...")
        on_run(parent, args, "SAFE MATCHED")

    def _show_unsafe_dialog(self, parent, args: list, on_run) -> None:
        QMessageBox.warning(parent, "⚠️ Внимание", "Safety mode отключен! Загрузка без проверки")
        on_run(parent, args, "UNSAFE")

    def _show_unknown_dialog(self, parent, args: list, on_run, file_path: str = "") -> None:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Warning)
        
        if file_path == "Reset":
            box.setWindowTitle("⚠️ Команда Reset")
            box.setText(
                "Команда Reset не имеет профиля в базе конфигураций\n"
                "Нажмите «Выполнить», чтобы запустить сброс\n"
                "на свой страх и риск"
            )
            btn_text = "Выполнить сброс"
            tag = "RESET RISK"
        else:
            box.setWindowTitle("⚠️ Прошивка не найдена")
            box.setText(
                "Прошивка не найдена в базе\n"
                "Нажмите «Загрузить прошивку», чтобы запустить\n"
                "на свой страх и риск"
            )
            btn_text = "Загрузить прошивку"
            tag = "UNKNOWN RISK"

        box.setStandardButtons(QMessageBox.Cancel)
        btn_load = box.addButton(btn_text, QMessageBox.AcceptRole)
        box.setDefaultButton(btn_load)
        box.exec()
        
        if box.clickedButton() == btn_load:
            on_run(parent, args, tag)

    @staticmethod
    def _run_command(command: str, tag: str) -> None:

        #Выводит команду в консоль (для тестирования)
        print("=" * 60)
        print(f"[{tag}] Запуск команды:")
        print(f"  {command}")
        print("=" * 60)