import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from functools import partial  # Импорт для надежной передачи аргументов

# Импортируем интерфейс из вашего файла UIv1.py
try:
    from UIv1 import Ui_MainWindow
except ImportError as e:
    print(f"Ошибка импорта UIv1.py: {e}")
    print("Убедитесь, что файл UIv1.py находится в той же папке, что и main.py")
    sys.exit(1)

def handle_button_click(button):
    """Функция для отображения сообщения при нажатии кнопки."""
    # Получаем имя объекта кнопки (например, "SelectionButton")
    button_name = button.objectName()
    
    # Словарь для определения текста сообщения
    messages = {
        "SelectionButton": ("Выбрать",),
        "loadBatton": ("Загрузить",),
        "SelectionButton_manual": ("Выбрать",),
        "loadBatton_manual": ("Загрузить",),
        "toolButton_Modify_Config": ("Изменить",),
        "toolButton_Delete_Config": ("Удалить",),
        "toolButton_add_new_config": ("Добавить",)
    }

    # Определяем текст сообщения
    if button_name in messages:
        text = f"{messages[button_name][0]}, ОНО РАБОТАЕТ"
    else:
        text = f"{button_name}, ОНО РАБОТАЕТ"

    # Показываем информационное окно
    QMessageBox.information(button.window(), "Информация", text)

def main():
    # Создаем экземпляр приложения и главного окна
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    
    # Создаем объект интерфейса (это то, что вы получили из UIv1.py)
    ui = Ui_MainWindow()
    ui.setupUi(window)  # Настройка интерфейса в окне
    
    # Список кнопок для подключения событий
    buttons_to_connect = [
        "SelectionButton", 
        "loadBatton", 
        "SelectionButton_manual", 
        "loadBatton_manual", 
        "toolButton_Modify_Config", 
        "toolButton_Delete_Config", 
        "toolButton_add_new_config"
    ]

    # Подключаем сигналы всех кнопок для отображения сообщений
    for btn_name in buttons_to_connect:
        # Ищем кнопку по имени в объекте UI, а не в окне
        button = getattr(ui, btn_name) if hasattr(ui, btn_name) else None
        
        if button is not None:
            # Используем functools.partial для связывания конкретного объекта кнопки с функцией.
            # Это надежнее, чем lambda b=button, так как исключает проблемы с замыканиями в цикле.
            button.clicked.connect(partial(handle_button_click, button))

    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()