import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from functools import partial

try:
    from UIv1 import Ui_MainWindow
    
    from file_selector import FileSelector
    from config_manager import ConfigManager
    from safety_dialog import SafetyConfirmDialog
    from validating import validate
    from sender import FirmwareSender
    
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

        # Инициализация логики выбора IP
        self._init_ip_checkboxes() 

        # Подключения сигналов
        self.ui.SelectionButton_Auto.clicked.connect(self.select_file_auto)
        self.ui.SelectionButton_Manual.clicked.connect(self.select_file_manual)
        self.ui.checkBox_Safety_Mode_Manual.stateChanged.connect(self._on_safety_checkbox_changed)
        self.ui.loadBatton_Manual.clicked.connect(self._on_manual_load_clicked)
        self.ui.loadBatton_Auto.clicked.connect(self._on_auto_load_clicked)

    # - IP Manual Mode -

    def _init_ip_checkboxes(self):

        # Инициализация чекбоксов IP, при запуске всегда активно NO

        # Блокируем сигналы на время начальной настройки, чтобы не сработали обработчики

        self.ui.checkBox_NO_IP.blockSignals(True)
        self.ui.checkBox_Yes_IP.blockSignals(True)
        
        # По умолчанию всегда NO
        self.ui.checkBox_NO_IP.setChecked(True)
        self.ui.checkBox_Yes_IP.setChecked(False)
        
        self.ui.checkBox_NO_IP.blockSignals(False)
        self.ui.checkBox_Yes_IP.blockSignals(False)
        
        # Флаг состояния: True = YES (IP нужен), False = NO (IP не нужен)
        self.manual_ip_enabled = False
        
        # Поле ввода IP неактивно, так как выбрано NO
        self.ui.plainTextIP_Manual.setEnabled(False)
        
        # Подключаем обработчики
        self.ui.checkBox_Yes_IP.toggled.connect(self._on_yes_ip_toggled)
        self.ui.checkBox_NO_IP.toggled.connect(self._on_no_ip_toggled)

    def _on_yes_ip_toggled(self, checked: bool):

        # Обработчик нажатия на YES
        if checked:

            # Снимаем NO
            self.ui.checkBox_NO_IP.blockSignals(True)
            self.ui.checkBox_NO_IP.setChecked(False)
            self.ui.checkBox_NO_IP.blockSignals(False)
            
            self.manual_ip_enabled = True
            self.ui.plainTextIP_Manual.setEnabled(True)
        else:

            # Если YES выключили (пользователь кликнул по нему повторно),
            # NO должен включиться принудительно
            self.ui.checkBox_NO_IP.blockSignals(True)
            self.ui.checkBox_NO_IP.setChecked(True)
            self.ui.checkBox_NO_IP.blockSignals(False)

    def _on_no_ip_toggled(self, checked: bool):

        # Обработчик нажатия на NO
        if checked:

            # Снимаем YES
            self.ui.checkBox_Yes_IP.blockSignals(True)
            self.ui.checkBox_Yes_IP.setChecked(False)
            self.ui.checkBox_Yes_IP.blockSignals(False)
            
            self.manual_ip_enabled = False
            self.ui.plainTextIP_Manual.setEnabled(False)
            self.ui.plainTextIP_Manual.setPlainText("") # Очищстка при отказе от IP
        else:

            # Заприщает снимать NO, если YES не активен (возвращает галочку)
            if not self.ui.checkBox_Yes_IP.isChecked():
                self.ui.checkBox_NO_IP.blockSignals(True)
                self.ui.checkBox_NO_IP.setChecked(True)
                self.ui.checkBox_NO_IP.blockSignals(False)

    @property
    def is_manual_ip_required(self) -> bool:

        # Свойство-флаг для удобной проверки в других частях кода
        # Возвращает True, если в Manual Mode выбран YES (IP используется)
        return self.manual_ip_enabled

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

    # Загрузка в Manual Mode с учётом Safety mode и наличия конфига
        FirmwareSender.send_manual(
            parent=self,
            file_path=self.manual_file_path,
            dev_id=self.ui.plainTextID_Manual.toPlainText().strip(),
            port=self.ui.plainTextPort_Manual.toPlainText().strip(),
            ip=self.ui.plainTextIP_Manual.toPlainText().strip(),
            ip_required=self.is_manual_ip_required,   
            safety_enabled=self.ui.checkBox_Safety_Mode_Manual.isChecked(),
        )

    def _on_auto_load_clicked(self):

    # Загрузка в Auto Mode (пока пустышка)
        FirmwareSender.send_auto(self, self.auto_file_path)

    def select_file_auto(self):
        
        # Обработчик выбора файла для Auto Mode
        full_path, display_path = FileSelector.select_firmware_file( self, "Выберите файл прошивки (Auto Mode)")

        if full_path:
            self.auto_file_path = full_path
            self.ui.path_Auto.setPlainText(display_path)


    def select_file_manual(self):

        # Обработчик выбора файла для Manual Mode
        full_path, display_path = FileSelector.select_firmware_file( self, "Выберите файл прошивки (Manual Mode)")
        
        if full_path:
            self.manual_file_path = full_path
            self.ui.path_Manual.setPlainText(display_path)


def main():

    # Создание приложения и главного окна
    app = QApplication(sys.argv)
    
    window = EasyLoaderWindow()
    window.setWindowTitle("UI-mode for EasyLoader")
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()