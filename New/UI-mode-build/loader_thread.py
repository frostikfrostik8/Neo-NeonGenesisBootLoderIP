
# Модуль запуска EasyLoader в отдельном потоке
# Читает stdout в реальном времени, парсит Progress, очищает мусор

import os
import sys
import re
import subprocess
from PySide6.QtCore import QThread, Signal
from path_utils import get_base_dir


class LoaderThread(QThread):

    # Сигналы
    log_received = Signal(str)       # новая строка лога
    progress_received = Signal(int)  # новое значение прогресса 0 - 100
    process_finished = Signal()      # процесс завершился
    error_occurred = Signal(str)     # ошибка запуска

    def __init__(self, exe_name: str, args: list, parent=None):
        super().__init__(parent)
        self.exe_name = exe_name
        self.args = args  # список аргументов без самого exe

    def run(self):
        script_dir = get_base_dir()
        program = os.path.join(script_dir, self.exe_name)

        if not os.path.isfile(program):
            self.error_occurred.emit(f"Исполняемый файл не найден:\n{program}")
            self.process_finished.emit()
            return

        full_args = [program] + self.args

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
                kwargs['creationflags'] = 0x08000000  # CREATE_NO_WINDOW

            process = subprocess.Popen(full_args, **kwargs)

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
                    buffer_bytes = buffer_bytes[idx + 1:]

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
                            if text.startswith(current_line) or current_line.startswith(text):
                                current_line = text
                            else:
                                self._process_line(current_line)
                                current_line = text
                    else:
                        if not current_line:
                            if text:
                                self._process_line(text)
                        else:
                            if not text:
                                self._process_line(current_line)
                            else:
                                if text.startswith(current_line) or current_line.startswith(text):
                                    self._process_line(text)
                                else:
                                    self._process_line(current_line)
                                    self._process_line(text)
                        current_line = ""

            if current_line:
                self._process_line(current_line)
            if buffer_bytes:
                try:
                    text = buffer_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    text = buffer_bytes.decode('cp866', errors='replace')
                if text:
                    self._process_line(text)

            process.wait()

        except Exception as e:
            self.error_occurred.emit(f"Ошибка запуска: {e}")
        finally:
            self.process_finished.emit()

    def _process_line(self, line: str):

        # Очистка + поиск прогресса + отправка сигнала
        # Удаляет невидимые символы
        line = line.replace('\x08', '').replace('\x07', '').replace('\x00', '')

        # ANSI escape
        line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)

        # Прогресс бар
        progress_match = re.search(r"Progress:\s*(\d+)%", line)
        if progress_match:
            self.progress_received.emit(int(progress_match.group(1)))
            return

        # Очистка от мусора: ¯¯ | █ ¯ _ |
        cleaned = re.sub(r"[\s▒|_¯█\u2500-\u259F]", " ", line)
        if not cleaned.strip():
            return

        # Отправляет оригинальную строку для читаемости, но можно и cleaned
        self.log_received.emit(line.strip())