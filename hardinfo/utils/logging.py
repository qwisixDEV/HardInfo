"""Thread-safe Qt signal logger and application logging setup.
"""

import sys
import logging
from PySide6.QtCore import QObject, Signal


class QtLogSignaller(QObject):
    log_signal = Signal(str)


class QtLoggingHandler(logging.Handler):
    def __init__(self, signaller: QtLogSignaller):
        super().__init__()
        self.signaller = signaller

    def emit(self, record):
        msg = self.format(record)
        self.signaller.log_signal.emit(msg)


def setup_logging(log_filename: str = "hardinfo.log") -> None:
    """Configures global logging to write to both stdout and a log file."""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
