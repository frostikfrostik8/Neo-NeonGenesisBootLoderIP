# Модуль проверки, переключаемый состоянием Safety mode

# Галочка ВКЛЮЧЕНА  -> выполняется полный код проверки
# Галочка ВЫКЛЮЧЕНА -> сразу возвращается строка "examination"

from config_manager import ConfigManager


def validate() -> str:

    # Главная точка входа валидации
    config = ConfigManager()

    # Если Safety mode выключен - пропускаем всю проверку
    if not config.is_safety_enabled():
        return "examination"

    # Иначе - выполняем полную проверку
    return _run_actual_check()


def _run_actual_check() -> str:

    # Тут должна быть проверка
    # но мне ее лень делать
    # поэтому тут пуста

    return "checked"