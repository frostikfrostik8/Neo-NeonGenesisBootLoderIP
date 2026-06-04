# Модуль для работы с выбором файлов прошивки
# Содержит логику открытия диалога выбора файла и форматирования пути

import os
from PySide6.QtWidgets import QFileDialog


class FileSelector:

    # Класс-утилита для выбора файлов прошивки (.bin)
    
    # Фильтр файлов для диалога
    FILE_FILTER = "Binary Files (*.bin);;All Files (*)"
    
    # Префикс для отображения сокращённого пути
    DISPLAY_PREFIX = ".../"
    
    @classmethod
    def select_firmware_file(cls, parent, title: str = "Выберите файл прошивки"):

        # Открывает диалог выбора файла прошивки
        full_path, _ = QFileDialog.getOpenFileName(parent, title, "", cls.FILE_FILTER)
        
        if not full_path:
            return "", ""
        
        display_path = cls.format_display_path(full_path)

        return full_path, display_path
    
    @classmethod
    def format_display_path(cls, full_path: str) -> str:

        # Форматирует полный путь в сокращённый вид ".../имя_файла.bin"
        if not full_path:
            return ""
        filename = os.path.basename(full_path)

        return f"{cls.DISPLAY_PREFIX}{filename}"
    
    @classmethod
    def is_valid_firmware(cls, file_path: str) -> bool:

        # Проверяет, что файл существует и имеет расширение .bin
        if not file_path:
            return False
        
        if not os.path.isfile(file_path):
            return False
        
        return file_path.lower().endswith(".bin")