import sys
import re
import os
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QProgressBar)
from PyQt6.QtCore import QThread, pyqtSignal

class LoaderThread(QThread):
    output_received = pyqtSignal(str)
    process_finished = pyqtSignal()

    def run(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        program = os.path.join(script_dir, "EasyLoader.exe")
        
        args = [
            program,
            "3", 
            "COM3", 
            r"c:\work\Neo-NeonGenesisBootLoderIP\Old\Firmware\ChS-RA-04.v2_DChub_CCS_P5_400kWt_no2CAN_noCcsBoard_2.0.0_7.10.2025_release.bin", 
            ""
        ]
        
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"

            kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.STDOUT,
                'cwd': script_dir,
                'env': env
            }
            if sys.platform == 'win32':
                kwargs['creationflags'] = 0x08000000
                
            process = subprocess.Popen(args, **kwargs)
            
            buffer_bytes = b""
            current_line = ""
            
            while True:
                chunk = process.stdout.read(128)
                if not chunk:
                    break
                
                buffer_bytes += chunk
                
                while True:
                    cr_idx = buffer_bytes.find(b'\r')
                    lf_idx = buffer_bytes.find(b'\n')
                    
                    if cr_idx == -1 and lf_idx == -1:
                        break
                        
                    if cr_idx != -1 and (lf_idx == -1 or cr_idx < lf_idx):
                        idx = cr_idx
                        is_cr = True
                    else:
                        idx = lf_idx
                        is_cr = False
                        
                    line_bytes = buffer_bytes[:idx]
                    buffer_bytes = buffer_bytes[idx+1:]
                    
                    try:
                        text = line_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        text = line_bytes.decode('cp866', errors='replace')

                    if is_cr:
                        if not text:
                            continue
                        
                        if not current_line:
                            current_line = text
                        else:

                            # Умная проверка, если строка просто "растет" (спиннер U -> Ud -> Udp), 
                            # то это одна и та же строка и мы её обновляем (схлопываем)
                            # Если это совершенно другой текст, значит программа вывела два разных
                            # сообщения подряд через \r должно сохранить оба
                            if text.startswith(current_line) or current_line.startswith(text):
                                current_line = text
                            else:
                                self.output_received.emit(current_line)
                                current_line = text
                        
                        # Прогресс эмитим всегда, чтобы бар обновлялся мгновенно
                        if "Progress:" in text:
                            self.output_received.emit(text)
                            
                    else: # Пришел \n (конец строки)
                        if not current_line:
                            if text:
                                self.output_received.emit(text)
                        else:
                            if not text:
                                self.output_received.emit(current_line)
                            else:
                                if text.startswith(current_line) or current_line.startswith(text):
                                    self.output_received.emit(text)
                                else:

                                    # Две разные строки завершены переносом, выводит обе
                                    self.output_received.emit(current_line)
                                    self.output_received.emit(text)
                        current_line = ""
                            
            if current_line:
                self.output_received.emit(current_line)
            if buffer_bytes:
                try:
                    text = buffer_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    text = buffer_bytes.decode('cp866', errors='replace')
                if text:
                    self.output_received.emit(text)
                
            process.wait()
        except Exception as e:
            self.output_received.emit(f"Ошибка запуска: {e}")
        finally:
            self.process_finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EasyLoader Tester")
        self.resize(600, 500)

        self.max_progress = 0
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.btn_start = QPushButton("Запустить EasyLoader")
        self.btn_start.clicked.connect(self.start_process)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white; padding: 12px;
                font-size: 16px; font-weight: bold; border: none; border-radius: 5px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 5px;
                text-align: center;
                background-color: #2c2c2c;
                color: white;
                font-weight: bold;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, 'Courier New', monospace; 
                background-color: #1e1e1e; color: #dcdcdc;
                border: 1px solid #333; padding: 5px;
            }
        """)

        layout.addWidget(self.btn_start)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.text_edit)

    def start_process(self):
        self.text_edit.clear()
        self.max_progress = 0
        self.progress_bar.setValue(0)
        self.btn_start.setEnabled(False)
        
        self.thread = LoaderThread()
        self.thread.output_received.connect(self.process_line)
        self.thread.process_finished.connect(self.process_finished)
        self.thread.start()
        self.text_edit.append("[INFO] Запуск процесса...")

    def process_line(self, line):
        line = line.replace('\x08', '').replace('\x07', '').replace('\x00', '')
        line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)

        progress_match = re.search(r"Progress:\s*(\d+)%", line)
        if progress_match:
            prog = int(progress_match.group(1))
            if prog > self.max_progress:
                self.max_progress = prog
                self.progress_bar.setValue(self.max_progress)
            return

        cleaned = re.sub(r"[\s▒|_¯█\u2500-\u259F]", "", line)
        if not cleaned:
            return

        self.text_edit.append(line)
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def process_finished(self):
        self.text_edit.append("[INFO] Процесс завершен")
        self.btn_start.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())