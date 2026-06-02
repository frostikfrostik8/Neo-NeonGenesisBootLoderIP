
# Менеджер конфигурации для работы с config.ini
# Управляет состоянием Safety mode

import configparser
import configparser
import os
from path_utils import get_resource_path

class ConfigManager:

    # Чтение и запись настроек Safety mode из config.ini
    # Путь к конфигу рядом с главным exe (а не во временной папке)
    CONFIG_FILE = get_resource_path("config.ini")

    SECTION = "Safety"
    KEY_TEMP = "enabled_temp"
    KEY_PERMANENT = "check_disabled_permanently"

    # Для работы с EL

    SECTION_EASYLOADER = "EasyLoader"
    KEY_EXE_NAME = "exe_name"

    def __init__(self):
        self.config = configparser.ConfigParser()
        self._load_or_create()

    def _load_or_create(self):
        if not os.path.exists(self.CONFIG_FILE):
            self.config[self.SECTION] = {
                self.KEY_TEMP: "True",
                self.KEY_PERMANENT: "False"
            }
            self.config[self.SECTION_EASYLOADER] = {
                self.KEY_EXE_NAME: "EasyLoader.exe"
            }
            self._save()
        else:
            self.config.read(self.CONFIG_FILE, encoding="utf-8")
            if self.SECTION not in self.config:
                self.config[self.SECTION] = {}
            if self.SECTION_EASYLOADER not in self.config:
                self.config[self.SECTION_EASYLOADER] = {self.KEY_EXE_NAME: "EasyLoader.exe"}
            self._save()

    # Нужно для EL
    # Возвращает имя исполняемого файла EasyLoader из конфига
    def get_exe_name(self) -> str:
        
        return self.config.get(
            self.SECTION_EASYLOADER,
            self.KEY_EXE_NAME,
            fallback="EasyLoader.exe"
        )

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
    