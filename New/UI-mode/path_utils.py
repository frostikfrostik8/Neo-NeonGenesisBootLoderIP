
# Универсальное определение базовой директории приложения
# Работает одинаково (наверное) и при запуске из исходников, и после компиляции Nuitka/PyInstaller

import os
import sys


def get_base_dir() -> str:

    # Возвращает папку где лежит главное приложение
    # При запуске из .py папка со скриптом
    # При запуске из скомпилированного .exe папка где лежит сам .exe
    
    # PyInstaller
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    
    # Nuitka
    if "__compiled__" in globals():
        return os.path.dirname(sys.executable)
    
    # Обычный запуск из Python
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(filename: str) -> str:
    
    # Полный путь к файлу рядом с приложением (конфиги, exe и т.д.)
    return os.path.join(get_base_dir(), filename)