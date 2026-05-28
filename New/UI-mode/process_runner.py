# Асинхронный запуск внешнего EasyLoader через QProcess.

import os
import re
from PySide6.QtCore import QObject, Signal, QProcess, QProcessEnvironment


class EasyLoaderRunner(QObject):
    line_received = Signal(str)
    progress_updated = Signal(int)
    finished = Signal(int, str)        # (exit_code, "success" | "error" | "crash")
    error_occurred = Signal(str)

    _PROGRESS_RE = re.compile(r"Progress:\s*(\d+)\s*%")
    _BAR_GARBAGE_RE = re.compile(r"^[\s█▒_¯\-]+$")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._max_progress = 0
        self._last_state_ok = False
        self._buffer = ""

    # - Публичные методы -

    def start(self, exe_path: str, args: list[str]) -> None:
        if self.is_running():
            self.error_occurred.emit("Предыдущий запуск ещё не завершён.")
            return

        if not os.path.isfile(exe_path):
            self.error_occurred.emit(f"Исполняемый файл не найден:\n{exe_path}")
            return

        self._reset_state()

        # Нормализует пути
        normalized_args = [os.path.normpath(a) if os.path.sep in a or "/" in a else a for a in args]
        if len(normalized_args) >= 3:
            normalized_args[2] = os.path.normpath(normalized_args[2])

        # Рабочая директория = корень проекта (2 уровня выше exe)
        exe_dir = os.path.dirname(os.path.abspath(exe_path))
        working_dir = os.path.abspath(os.path.join(exe_dir, "..", ".."))
        if not os.path.isdir(working_dir):
            working_dir = exe_dir

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ForwardedChannels)
        self._process.setWorkingDirectory(working_dir)

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self._process.setProcessEnvironment(env)

        self._process.readyReadStandardOutput.connect(self._on_ready_read)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_process_error)

        print("=" * 60)
        print(f"[RUN] {exe_path}")
        print(f"[ARGS] {normalized_args}")
        print(f"[CWD]  {working_dir}")
        print(f"[EXE_DIR] {exe_dir}")
        print(f"[FULL] {exe_path} {' '.join(normalized_args)}")
        print("=" * 60)

        self._process.start(exe_path, normalized_args)

    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.NotRunning

    def terminate(self) -> None:
        if self.is_running():
            self._process.terminate()
            if not self._process.waitForFinished(2000):
                self._process.kill()

    # - Обработчики -

    def _on_ready_read(self) -> None:
        raw = bytes(self._process.readAllStandardOutput())
        text = self._decode(raw)
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip("\r")
            self._process_line(line)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:

        # Догоняет хвост буфера
        if self._buffer.strip():
            self._process_line(self._buffer.rstrip("\r\n"))
            self._buffer = ""

        # Дополнительная диагностика при ошибке
        if exit_code != 0 or exit_status == QProcess.CrashExit:
            print(f"[FINISH] exit_code={exit_code}, status={exit_status}")
            print(f"[STDERR/OUT tail] {self._buffer!r}")

        if exit_status == QProcess.CrashExit:
            self.finished.emit(exit_code, "crash")
        elif exit_code == 0:
            self.finished.emit(exit_code, "success")
        else:
            self.finished.emit(exit_code, "error")

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        msgs = {
            QProcess.FailedToStart: "Не удалось запустить EasyLoader",
            QProcess.Crashed: "EasyLoader аварийно завершился",
            QProcess.Timedout: "Тайм-аут выполнения",
            QProcess.WriteError: "Ошибка записи в процесс",
            QProcess.ReadError: "Ошибка чтения из процесса",
            QProcess.UnknownError: "Неизвестная ошибка процесса",
        }
        self.error_occurred.emit(msgs.get(error, f"Ошибка QProcess: {error}"))

    # - Парсинг -

    def _process_line(self, line: str) -> None:
        m = self._PROGRESS_RE.search(line)
        if m:
            value = int(m.group(1))
            if value > self._max_progress:
                self._max_progress = value
                self.progress_updated.emit(self._max_progress)
            return

        if "State" in line and "✅" in line:
            self._last_state_ok = True

        if self._BAR_GARBAGE_RE.match(line):
            return
        if not line.strip():
            return

        self.line_received.emit(line)

    # - Вспомогательное -

    def _reset_state(self) -> None:
        self._max_progress = 0
        self._last_state_ok = False
        self._buffer = ""
        self.progress_updated.emit(0)

    @staticmethod
    def _decode(raw: bytes) -> str:
        for enc in ("utf-8", "cp866", "cp1251", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")