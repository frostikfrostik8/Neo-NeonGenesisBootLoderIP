import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from functools import partial

try:
    from UIv1 import Ui_MainWindow
    
    from file_selector import FileSelector
    from config_manager import ConfigManager
    from safety_dialog import SafetyConfirmDialog
    
    from validating import validate
    
except ImportError as e:
    print(f"Ошибка импорта UI: {e}")
    sys.exit(1)

class EasyLoaderWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        
        # Инициализация UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Переменные для хранения полных путей (раздельно для каждого режима)
        self.auto_file_path = ""
        self.manual_file_path = ""

        # Менеджер конфигурации
        self.config = ConfigManager()

        # Инициализация состояния Safety mode из config.ini
        self._init_safety_checkbox()

        # Подключения сигналов
        self.ui.SelectionButton_Auto.clicked.connect(self.select_file_auto)
        self.ui.SelectionButton_Manual.clicked.connect(self.select_file_manual)
        self.ui.checkBox_Safety_Mode_Manual.stateChanged.connect(self._on_safety_checkbox_changed)
        self.ui.loadBatton_Manual.clicked.connect(self._on_manual_load_clicked)

# - Safety mode -
    def _init_safety_checkbox(self):

        # Устанавливает начальное состояние чекбокса при запуске
        # permanent disable = True -> галочка снята, окно не показывается
        # permanent disable = False -> галочка установлена (temp сброшен в True)
        
        self.config.reset_temp_on_startup()

        self.ui.checkBox_Safety_Mode_Manual.blockSignals(True)
        self.ui.checkBox_Safety_Mode_Manual.setChecked(self.config.is_safety_enabled())
        self.ui.checkBox_Safety_Mode_Manual.blockSignals(False)

    def _on_safety_checkbox_changed(self, state):

        # state == 0 -> пользователь пытается СНЯТЬ галочку (показать диалог)
        # state == 2 -> пользователь поставил галочку обратно

        if state == 0:

            # Если проверка отключена навсегда - просто обновляем temp, диалог показывать не нужно
            if self.config.is_safety_check_permanently_disabled():
                self.config.set_safety_temp(False)
                return

            dialog = SafetyConfirmDialog(self)
            
            confirmed = dialog.exec() == SafetyConfirmDialog.Accepted

            if confirmed:

                # Успех - фиксируем в конфиге
                self.config.set_safety_temp(False)

            else:

                # Возвращаем галочку и показываем "Ты не уверен в себе"
                self.ui.checkBox_Safety_Mode_Manual.blockSignals(True)
                self.ui.checkBox_Safety_Mode_Manual.setChecked(True)
                self.ui.checkBox_Safety_Mode_Manual.blockSignals(False)
                
                QMessageBox.information(self, "Результат", "Ты не уверен в себе")

        else:

            # Галочку вернули вручную - обновляем temp в TrueА
            self.config.set_safety_temp(True)

    # - Загрузка -
    def _on_manual_load_clicked(self):

        # Загрузка в Manual Mode с учётом Safety mode
        result = validate()
        if result == "examination":

            # Safety mode выключен - предупреждаем пользователя
            QMessageBox.warning(self, "Внимание", "Safety mode отключен. Загрузка выполняется без проверки!")

        else:
            QMessageBox.information(self, "Информация", f"Проверка пройдена: {result}\nЗагрузка началась.")

            # Сюда реальную загрузку потом прикорячить

    def select_file_auto(self):
        
        # Обработчик выбора файла для Auto Mode
        full_path, display_path = FileSelector.select_firmware_file( self, "Выберите файл прошивки (Auto Mode)")

        if full_path:
            self.auto_file_path = full_path
            self.ui.path_auto.setPlainText(display_path)

    def select_file_manual(self):

        # Обработчик выбора файла для Manual Mode
        full_path, display_path = FileSelector.select_firmware_file( self, "Выберите файл прошивки (Manual Mode)")
        
        if full_path:
            self.manual_file_path = full_path
            self.ui.path_manual.setPlainText(display_path)


def main():

    # Создание приложения и главного окна
    app = QApplication(sys.argv)
    
    window = EasyLoaderWindow()
    window.setWindowTitle("UI-mode for EasyLoader")
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()