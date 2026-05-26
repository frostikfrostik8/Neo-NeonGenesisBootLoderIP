# Модуль отправки прошивки через внешний EasyLoader.
# С проверкой конфигурации и 3 режимами уведомлений.

import os
# import subprocess  # Раскомментировать для реального запуска
from PySide6.QtWidgets import QMessageBox
from firmware_config_manager import FirmwareConfigManager


class FirmwareSender:
    EXE_NAME = "EasyLoader"

    def __init__(self):
        self.fw_config = FirmwareConfigManager()

    def build_command(self, file_path: str, dev_id: str, port: str, ip: str | None) -> str:

        # Собирает строку: EasyLoader [ID] [PORT] [FILE] [IP]
        exe_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            self.EXE_NAME
        )

        parts = [exe_path, str(dev_id), str(port), file_path]

        if ip and ip.strip().lower() != "none":
            parts.append(ip.strip())

        quoted = [f'"{p}"' if " " in p else p for p in parts]
        return " ".join(quoted)

    def _validate_manual_fields(self, dev_id: str, port: str, ip: str | None, ip_required: bool) -> str | None:
        if not dev_id or not dev_id.strip():
            return "Не указан ID устройства"
        if not port or not port.strip():
            return "Не указан порт"
        if ip_required and (not ip or not ip.strip()):
            return "Выбран IP=YES, но адрес не введён"
        return None

    def send_auto(self, parent, file_path: str, ui_fields: dict) -> bool:
        # Auto mode - ищет конфиг и заполняет поля UI.
        # Returns True если можно загружать, False если нет

        if not file_path or not os.path.isfile(file_path):
            QMessageBox.critical(parent, "Ошибка", "Файл прошивки не выбран")
            return False

        firmware, match_type = self.fw_config.find_firmware_for_file(file_path)

        if match_type == "full":
            # Полное совпадение - заполняем поля
            ui_fields["name"].setPlainText(firmware.get("name", ""))
            ui_fields["specifier"].setPlainText(firmware.get("specifier", ""))
            ui_fields["id"].setPlainText(firmware.get("id", ""))
            ui_fields["port"].setPlainText(firmware.get("port", ""))
            
            ip_value = firmware.get("ip", "none")
            ui_fields["ip"].setPlainText("" if ip_value.lower() == "none" else ip_value)
            
            QMessageBox.information(parent, "✅ Конфиг найден", "Прошивка найдена в базе. Загрузка разрешена")
            return True

        elif match_type == "partial":
            QMessageBox.warning(
                parent,
                "⚠️ Неполное совпадение",
                "Найдено частичное совпадение конфигурации\n"
                "Загрузка в Auto Mode запрещена"
            )
            return False

        else:
            QMessageBox.critical(
                parent,
                "❌ Не найдено",
                "Файл конфигурации прошивки не найден\n"
                "Загрузка в Auto Mode запрещена"
            )
            return False

    def send_manual(
        self,
        parent,
        file_path: str,
        dev_id: str,
        port: str,
        ip: str | None,
        ip_required: bool,
        safety_enabled: bool,
    ) -> None:
        
        # Manual mode с проверкой конфига
        # Проверка файла
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.critical(parent, "Ошибка", "Файл прошивки не выбран или не существует")
            return

        # Валидация полей
        err = self._validate_manual_fields(dev_id, port, ip, ip_required)
        if err:
            QMessageBox.warning(parent, "Неполные данные", err)
            return

        # Safety OFF - загрузка без проверок
        if not safety_enabled:
            command = self.build_command(file_path, dev_id, port, ip if ip_required else None)
            self._show_unsafe_dialog(parent, command)
            return

        # Safety ON - ищем конфиг
        firmware, match_type = self.fw_config.find_firmware_for_file(file_path)

        if match_type == "full":

            # Проверяем совпадение параметров
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
                QMessageBox.warning(
                    parent,
                    "⚠️ Параметры не совпадают",
                    f"Конфиг найден, но параметры отличаются:\n\n{error_text}"
                )
                return

            # Всё совпало - запускаем
            command = self.build_command(file_path, dev_id, port, ip if ip_required else None)
            self._show_ok_dialog(parent, command, firmware)

        elif match_type == "partial":
            QMessageBox.warning(
                parent,
                "⚠️ Неполное совпадение",
                "Найдено частичное совпадение конфигурации\n"
                "Загрузка запрещена в защищённом режиме"
            )

        else:
            command = self.build_command(file_path, dev_id, port, ip if ip_required else None)
            self._show_unknown_dialog(parent, command)

    def _show_ok_dialog(self, parent, command: str, firmware: dict) -> None:
        QMessageBox.information(
            parent,
            "✅ Всё готово",
            f"Конфиг найден: {firmware.get('name', '?')}\n"
            f"Проверка параметров пройдена\n\n"
            f"Запускаю загрузку ..."
        )
        self._run_command(command, tag="SAFE MATCHED")

    def _show_unsafe_dialog(self, parent, command: str) -> None:
        QMessageBox.warning(
            parent,
            "⚠️ Внимание",
            "Safety mode отключен!\n"
            "Загрузка выполняется без проверки"
        )
        self._run_command(command, tag="UNSAFE")

    def _show_unknown_dialog(self, parent, command: str) -> None:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("⚠️ Прошивка не найдена")
        box.setText(
            "Прошивка не найдена в базе конфигураций.\n"
            "Нажмите «Загрузить прошивку», чтобы запустить\n"
            "её на свой страх и риск"
        )
        box.setStandardButtons(QMessageBox.Cancel)
        btn_load = box.addButton("Загрузить прошивку", QMessageBox.AcceptRole)
        box.setDefaultButton(btn_load)

        box.exec()

        if box.clickedButton() == btn_load:
            self._run_command(command, tag="UNKNOWN RISK")

    @staticmethod
    def _run_command(command: str, tag: str) -> None:

        #Выводит команду в консоль (для тестирования)
        print("=" * 60)
        print(f"[{tag}] Запуск команды:")
        print(f"  {command}")
        print("=" * 60)
        
        # subprocess.run(command, shell=True)