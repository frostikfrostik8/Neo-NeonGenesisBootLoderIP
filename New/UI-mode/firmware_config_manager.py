# Менеджер конфигурации прошивок для работы с config-firmware.ini

import configparser
import os
from typing import Optional, Tuple, Dict, List


class FirmwareConfigManager:
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"config-firmware.ini")

    def __init__(self):
        self.config = configparser.ConfigParser()
        self._load_or_create()

    def _load_or_create(self):

        # Загружает config-firmware.ini или создаёт пустой
        if not os.path.exists(self.CONFIG_FILE):
            self._save()
        else:
            self.config.read(self.CONFIG_FILE, encoding="utf-8")

    def _save(self):

        # Сохраняет конфигурацию в файл
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            self.config.write(f)

    def _normalize_string(self, text: str) -> str:
        
        # Нормализует строку, нижний регистр, замена "_" и пробелов на "-"
        if not text:
            return ""
        return text.lower().replace("_", "-").replace(" ", "-")

    def get_all_firmwares(self) -> List[Dict[str, str]]:

        # Возвращает список всех прошивок из конфига
        firmwares = []
        for section in self.config.sections():
            if section.startswith("firmware_"):
                firmware = {
                    "section": section,
                    "name": self.config.get(section, "name", fallback=""),
                    "specifier": self.config.get(section, "specifier", fallback=""),
                    "id": self.config.get(section, "id", fallback=""),
                    "port": self.config.get(section, "port", fallback=""),
                    "specifier_2": self.config.get(section, "specifier_2", fallback="none"),
                    "ip": self.config.get(section, "ip", fallback="none"),
                }
                firmwares.append(firmware)
        return firmwares

    def get_firmware_by_section(self, section: str) -> Optional[Dict[str, str]]:

        # Получить прошивку по имени секции
        if section not in self.config:
            return None
        
        return {
            "section": section,
            "name": self.config.get(section, "name", fallback=""),
            "specifier": self.config.get(section, "specifier", fallback=""),
            "id": self.config.get(section, "id", fallback=""),
            "port": self.config.get(section, "port", fallback=""),
            "specifier_2": self.config.get(section, "specifier_2", fallback="none"),
            "ip": self.config.get(section, "ip", fallback="none"),
        }

    def add_firmware(self, name: str, specifier: str, dev_id: str, port: str, 
                     specifier_2: str = "none", ip: str = "none") -> str:
        
        # Добавляет новую прошивку и возвращает имя секции
        # Находим следующий свободный номер
        max_num = 0
        for section in self.config.sections():
            if section.startswith("firmware_"):
                try:
                    num = int(section.split("_")[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    pass
        
        new_section = f"firmware_{max_num + 1}"
        
        self.config[new_section] = {
            "name": name,
            "specifier": self._normalize_string(specifier),
            "id": dev_id,
            "port": port,
            "specifier_2": self._normalize_string(specifier_2) if specifier_2 and specifier_2.lower() != "none" else "none",
            "ip": ip if ip and ip.lower() != "none" else "none",
        }
        
        self._save()
        return new_section

    def update_firmware(self, section: str, name: str, specifier: str, dev_id: str, 
                       port: str, specifier_2: str = "none", ip: str = "none"):
        
        # Обновляет существующую прошивку
        if section not in self.config:
            return
        
        self.config[section] = {
            "name": name,
            "specifier": self._normalize_string(specifier),
            "id": dev_id,
            "port": port,
            "specifier_2": self._normalize_string(specifier_2) if specifier_2 and specifier_2.lower() != "none" else "none",
            "ip": ip if ip and ip.lower() != "none" else "none",
        }
        
        self._save()

    def delete_firmware(self, section: str):

        # Удаляет прошивку по имени секции
        if section in self.config:
            self.config.remove_section(section)
            self._save()

    def find_firmware_for_file(self, file_path: str) -> Tuple[Optional[Dict[str, str]], str]:

        # Ищет конфиг для файла прошивки
        if not file_path or not os.path.isfile(file_path):
            return None, "none"

        filename = os.path.basename(file_path)
        filename_normalized = self._normalize_string(filename)

        best_match = None
        best_score = 0
        match_type = "none"

        for section in self.config.sections():
            if not section.startswith("firmware_"):
                continue

            specifier = self._normalize_string(
                self.config.get(section, "specifier", fallback="")
            )
            specifier_2 = self._normalize_string(
                self.config.get(section, "specifier_2", fallback="none")
            )

            if not specifier:
                continue

            # Проверяем совпадение specifier
            if specifier not in filename_normalized:
                continue

            # Specifier совпал
            score = 1
            
            # Проверяем specifier_2
            if specifier_2 and specifier_2 != "none":
                
                if specifier_2 in filename_normalized:

                    # Полное совпадение
                    score = 2
                else:
                    
                    # Specifier совпал, но specifier_2 не совпал
                    score = 1
            else:

                # В конфиге нет specifier_2, это тоже полное совпадение
                score = 2

            if score > best_score:
                best_score = score
                best_match = self.get_firmware_by_section(section)
                
                if score == 2:
                    match_type = "full"
                else:
                    match_type = "partial"

        return best_match, match_type