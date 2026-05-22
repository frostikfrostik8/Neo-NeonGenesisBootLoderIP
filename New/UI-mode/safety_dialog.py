# Диалог подтверждения снятия Safety mode
# Требует точного ввода фразы капсом: "Я УВЕРЕН В СЕБЕ"

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


REQUIRED_PHRASE = "Я УВЕРЕН В СЕБЕ"


class SafetyConfirmDialog(QDialog):

    # Большое окно с запросом подтверждения снятия Safety mode
    def __init__(self, parent=None):
        
        super().__init__(parent)
        self.setWindowTitle("⚠️ Подтверждение ⚠️")
        self.setFixedSize(620, 380)

        # Убираем кнопку справки
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Поверх всех окон
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout()
        
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        # Большой заголовок
        title = QLabel("ТЫ УВЕРЕН В СЕБЕ?")
        
        title_font = QFont()
        title_font.setPointSize(30)
        title_font.setBold(True)
        
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title)

        # Подсказка
        hint = QLabel(f"Чтобы снять защиту, введите точную фразу:\n«{REQUIRED_PHRASE}»")
        
        hint_font = QFont()
        hint_font.setPointSize(12)
        
        hint.setFont(hint_font)
        hint.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(hint)

        # Поле ввода
        self.input_field = QLineEdit()
        
        self.input_field.setPlaceholderText(REQUIRED_PHRASE)
        
        input_font = QFont()
        input_font.setPointSize(14)
        
        self.input_field.setFont(input_font)
        self.input_field.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.input_field)
        layout.addStretch()

        # Кнопки
        buttons_layout = QHBoxLayout()
        
        btn_font = QFont()
        btn_font.setPointSize(12)

        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.setFixedSize(160, 50)
        self.btn_cancel.setFont(btn_font)
        
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton("ОК")
        self.btn_ok.setFixedSize(160, 50)
        self.btn_ok.setFont(btn_font)
        
        self.btn_ok.clicked.connect(self._on_ok)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_ok)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)

        # Энтер в поле = нажатие ОК
        self.input_field.returnPressed.connect(self._on_ok)
        self.input_field.setFocus()

    def _on_ok(self):

        # Проверяем точное совпадение фразы (с учётом регистра)
        text = self.input_field.text().strip()
        if text == REQUIRED_PHRASE:
            self.accept()

        else:

            # Просто закрываем как "не подтверждено", а уведомление "Ты не уверен в себе" покажет main.py
            self.reject()