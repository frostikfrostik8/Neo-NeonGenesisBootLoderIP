from esptool.logger import log, TemplateLogger
from output import logger
import sys

class CustomLogger(TemplateLogger):
    output = logger()

    def print(self, message="", *args, **kwargs):
        # Print to console
        self.output.log(f"[Log from ESP32]: {message}")

    def note(self, message):
        self.print(f"NOTE: {message}")

    def warning(self, message):
        self.print(f"WARNING: {message}")

    def error(self, message):
        self.print(f"ERROR: {message}", file=sys.stderr)

    def progress_bar(
        self,
        cur_iter,
        total_iters,
    ):
        if cur_iter != 0: print("\r\b\r\b\r\b\r\b\r\b")
        self.output.progressBar(cur_iter / float(total_iters))

# Replace the default logger with the custom logger
# log.set_logger(CustomLogger())