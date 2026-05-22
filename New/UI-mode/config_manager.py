# Менеджер конфигурации для работы с config.ini
# Управляет состоянием Safety mode

import configparser
import os


class ConfigManager:

    # Чтение и запись настроек Safety mode из config.ini
    # Путь к конфигу рядом с main.py (а не в рабочей директории)
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

    SECTION = "Safety"
    KEY_TEMP = "enabled_temp"
    KEY_PERMANENT = "check_disabled_permanently"

    def __init__(self):
        self.config = configparser.ConfigParser()
        self._load_or_create()

    def _load_or_create(self):
        
        #Загружает config.ini или создаёт со значениями по умолчанию
        if not os.path.exists(self.CONFIG_FILE):
            self.config[self.SECTION] = {
                self.KEY_TEMP: "True",
                self.KEY_PERMANENT: "False"
            }
            self._save()
        else:
            self.config.read(self.CONFIG_FILE, encoding="utf-8")

            # Гарантирует наличие секции
            if self.SECTION not in self.config:
                self.config[self.SECTION] = {}
                self._save()

    def _save(self):
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            self.config.write(f)

    # - Чтение -
    def is_safety_check_permanently_disabled(self) -> bool:
        return self.config.getboolean(self.SECTION, self.KEY_PERMANENT, fallback=False)

    def is_safety_enabled(self) -> bool:

        # Текущее состояние Safety mode (учитывает permanent disable)
        if self.is_safety_check_permanently_disabled():
            return False
        
        return self.config.getboolean(self.SECTION, self.KEY_TEMP, fallback=True)

    # - Запись -
    def reset_temp_on_startup(self):

        # При запуске если permanent=False, temp всегда сбрасывается в True
        if not self.is_safety_check_permanently_disabled():
            self.config[self.SECTION][self.KEY_TEMP] = "True"
            self._save()

        else:

            # Если проверка отключена навсегда - temp тоже False
            self.config[self.SECTION][self.KEY_TEMP] = "False"
            self._save()

    def set_safety_temp(self, value: bool):

        if self.SECTION not in self.config:
            self.config[self.SECTION] = {}

        self.config[self.SECTION][self.KEY_TEMP] = str(value)
        self._save()

    def set_safety_permanent_disable(self, value: bool):

        # Позволяет программно включить/выключить permanent disable
        if self.SECTION not in self.config:
            self.config[self.SECTION] = {}
        self.config[self.SECTION][self.KEY_PERMANENT] = str(value)
        
        if value:
            self.config[self.SECTION][self.KEY_TEMP] = "False"
        self._save()