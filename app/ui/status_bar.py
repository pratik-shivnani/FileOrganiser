from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QStatusBar, QLabel, QProgressBar

from app.config import format_file_size


class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self._file_count_label = QLabel("Ready")
        self.addWidget(self._file_count_label, 1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setMaximumHeight(16)
        self._progress_bar.setVisible(False)
        self.addWidget(self._progress_bar)

        self._ollama_label = QLabel("")
        self._ollama_label.setStyleSheet("color: #999;")
        self.addPermanentWidget(self._ollama_label)

    def set_file_info(self, count: int, total_size: int = 0):
        size_str = format_file_size(total_size) if total_size > 0 else ""
        if size_str:
            self._file_count_label.setText(f"{count} items | {size_str}")
        else:
            self._file_count_label.setText(f"{count} items")

    def set_message(self, message: str):
        self._file_count_label.setText(message)

    def set_indexing(self, active: bool, current: int = 0):
        self._progress_bar.setVisible(active)
        if active:
            self._progress_bar.setRange(0, 0)
            self._file_count_label.setText(f"Indexing... {current} files scanned")
        else:
            self._file_count_label.setText("Ready")

    def set_ollama_status(self, connected: bool, message: str = ""):
        if connected:
            self._ollama_label.setText("\u2713 Ollama")
            self._ollama_label.setStyleSheet("color: #4CAF50;")
        else:
            self._ollama_label.setText("\u2717 Ollama")
            self._ollama_label.setStyleSheet("color: #f44336;")
        if message:
            self._ollama_label.setToolTip(message)
