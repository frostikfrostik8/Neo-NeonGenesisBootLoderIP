
# Универсальное определение базовой директории приложения
# Работает корректно с Nuitka в режиме --onefile

import os
import sys


def get_base_dir() -> str:

    # Возвращает папку, где лежит оригинальный .exe (или .py при разработке)
    # Ключевое отличие для Nuitka --onefile:
    # sys.executable -> временная папка (%TEMP%\onefile_xxx)
    # sys.argv[0] -> оригинальный .exe рядом с пользователем

    # Nuitka скомпилированное приложение
    if "__compiled__" in globals():
        # sys.argv[0] содержит путь к ОРИГИНАЛЬНОМУ exe
        exe_path = os.path.abspath(sys.argv[0])
        return os.path.dirname(exe_path)
    
    # PyInstaller (для совместимости)
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    
    # Обычный запуск из Python
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(filename: str) -> str:

    # Полный путь к файлу рядом с приложением
    base_dir = get_base_dir()
    return os.path.join(base_dir, filename)


#  ОТЛАДКА 
# print("=" * 60)
# print(f"[PATH_UTILS] __compiled__: {'__compiled__' in globals()}")
# print(f"[PATH_UTILS] sys.argv[0]: {sys.argv[0]}")
# print(f"[PATH_UTILS] sys.executable: {sys.executable}")
# print(f"[PATH_UTILS] Base dir: {get_base_dir()}")
# print(f"[PATH_UTILS] config.ini: {get_resource_path('config.ini')}")
# print("=" * 60)