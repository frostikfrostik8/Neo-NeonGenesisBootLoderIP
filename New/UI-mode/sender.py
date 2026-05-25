#Модуль отправки прошивки через внешний EasyLoader

#Режимы работы:
#   1) Auto mode - заглушка
#   2) Manual + Safety ON  + конфиг найден       -> окно "Всё ок" + print
#   3) Manual + Safety OFF                       -> окно "Защита отключена" + print
#   4) Manual + Safety ON  + конфиг НЕ найден    -> окно "На свой страх и риск" + print

# РЕАЛЬНЫЙ ЗАПУСК EXE ЗАКОММЕНТИРОВАН
# Для активации раскомментировать строки с subprocess.run


import os
import configparser
# import subprocess  # Раскомментировать для реального запуска
from PySide6.QtWidgets import QMessageBox


class FirmwareSender:
    EXE_NAME = "EasyLoader"
    CONFIG_FIRMWARE_FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "config-firmware.ini"
    )

    # --- Поиск конфига ---

    @classmethod
    def find_config_for_file(cls, file_path: str) -> dict | None:

        # Ищет запись в config-firmware.ini по вхождению "specifier"
        # (или "specifier_2") в имя файла без учёта регистра

        if not file_path or not os.path.isfile(file_path):
            return None
        if not os.path.isfile(cls.CONFIG_FIRMWARE_FILE):
            return None

        filename_lower = os.path.basename(file_path).lower()

        parser = configparser.ConfigParser()
        parser.read(cls.CONFIG_FIRMWARE_FILE, encoding="utf-8")

        for section in parser.sections():
            specifier = parser.get(section, "specifier", fallback="").strip().lower()
            specifier_2 = parser.get(section, "specifier_2", fallback="").strip().lower()

            if specifier and specifier in filename_lower:
                return cls._section_to_dict(parser, section)
            if specifier_2 and specifier_2 in filename_lower:
                return cls._section_to_dict(parser, section)

        return None

    @staticmethod
    def _section_to_dict(parser: configparser.ConfigParser, section: str) -> dict:
        return {k: v.strip() for k, v in parser.items(section)}

    # --- Построение команды ---

    @classmethod
    def build_command(cls, file_path: str, dev_id: str, port: str, ip: str | None) -> str:

        # Собирает строку:  EasyLoader [ID] [PORT] [FILE] [IP]
        # IP добавляется, только если он задан и не равен "none"

        exe_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            cls.EXE_NAME
        )

        parts = [exe_path, str(dev_id), str(port), file_path]

        if ip and ip.strip().lower() != "none":
            parts.append(ip.strip())

        # Обрамляем кавычками пути с пробелами
        quoted = [f'"{p}"' if " " in p else p for p in parts]
        return " ".join(quoted)

    # --- Валидация полей ---

    @staticmethod
    def _validate_manual_fields(dev_id: str, port: str, ip: str | None, ip_required: bool) -> str | None:
        if not dev_id or not dev_id.strip():
            return "Не указан ID устройства."
        if not port or not port.strip():
            return "Не указан порт."
        if ip_required and (not ip or not ip.strip()):
            return "Выбран IP=YES, но адрес не введён"
        return None

    # -- Режим 1: Auto (заглушка) --

    @classmethod
    def send_auto(cls, parent, file_path: str) -> None:
        QMessageBox.information(
            parent,
            "Auto Mode",
            "Auto Mode пока находится в разработке\n"
            "Скоро здесь появится автоматическая загрузка"
        )

    # -- Режимы 2/3/4: Manual --

    @classmethod
    def send_manual(
        cls,
        parent,
        file_path: str,
        dev_id: str,
        port: str,
        ip: str | None,
        ip_required: bool,
        safety_enabled: bool,
    ) -> None:
        
        # Проверка файла
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.critical(parent, "Ошибка", "Файл прошивки не выбран или не существует")
            return

        # Валидация полей
        err = cls._validate_manual_fields(dev_id, port, ip, ip_required)
        if err:
            QMessageBox.warning(parent, "Неполные данные", err)
            return

        # Строим команду
        command = cls.build_command(file_path, dev_id, port, ip if ip_required else None)

        # -- Режим 3: Safety OFF --
        if not safety_enabled:
            cls._show_unsafe_dialog(parent, command)
            return

        # Ищем конфиг
        config = cls.find_config_for_file(file_path)

        if config is not None:

            # -- Режим 2: Safety ON + конфиг найден --
            cls._show_ok_dialog(parent, command, config)
        else:

            # -- Режим 4: Safety ON + конфига нет --
            cls._show_unknown_dialog(parent, command)

    # - Окно 1: "Всё ок" -
    @classmethod
    def _show_ok_dialog(cls, parent, command: str, config: dict) -> None:
        QMessageBox.information(
            parent,
            "✅ Всё готово",
            f"Конфиг найден: {config.get('specifier', '?')}\n"
            f"Проверка параметров пройдена.\n\n"
            f"Запускаю загрузку..."
        )
        cls._run_command(command, tag="SAFE MATCHED")

    # - Окно 2: "Защита отключена" -
    @classmethod
    def _show_unsafe_dialog(cls, parent, command: str) -> None:
        QMessageBox.warning(
            parent,
            "⚠️ Внимание",
            "Safety mode отключен!\n"
            "Загрузка выполняется без проверки"
        )
        cls._run_command(command, tag="UNSAFE")

    # - Окно 3: "Конфиг не найден - на свой страх и риск" -
    @classmethod
    def _show_unknown_dialog(cls, parent, command: str) -> None:
        box = QMessageBox(parent)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("⚠️ Прошивка не найдена")
        box.setText(
            "Прошивка не найдена в базе конфигураций\n"
            "Нажмите «Загрузить прошивку», чтобы запустить\n"
            "её на свой страх и риск"
        )
        box.setStandardButtons(QMessageBox.Cancel)
        btn_load = box.addButton("Загрузить прошивку", QMessageBox.AcceptRole)
        box.setDefaultButton(btn_load)

        box.exec()

        if box.clickedButton() == btn_load:

            # Без дополнительного окна - сразу запуск
            cls._run_command(command, tag="UNKNOWN RISK")

    # --- Единая точка запуска ---

    @staticmethod
    def _run_command(command: str, tag: str) -> None:
        
        # Выводит команду в консоль (для тестирования)
        # Для реального запуска раскомментируй subprocess.run

        print("=" * 60)
        print(f"[{tag}] Запуск команды:")
        print(f"  {command}")
        print("=" * 60)

        # subprocess.run(command, shell=True)