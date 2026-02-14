from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel,
)
from PyQt6.QtGui import QFont


class CommandBar(QWidget):
    query_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        icon_label = QLabel("\U0001f50d")
        icon_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(icon_label)

        self._input = QLineEdit()
        self._input.setPlaceholderText(
            "Ask in natural language... e.g. 'find all PDFs larger than 10MB' or 'move screenshots to Pictures'"
        )
        self._input.setMinimumHeight(32)
        font = QFont()
        font.setPointSize(11)
        self._input.setFont(font)
        self._input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #bbb;
                border-radius: 6px;
                padding: 4px 10px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        self._input.returnPressed.connect(self._on_submit)
        layout.addWidget(self._input)

        self._submit_btn = QPushButton("Ask")
        self._submit_btn.setMinimumHeight(32)
        self._submit_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:pressed { background: #0D47A1; }
            QPushButton:disabled { background: #bbb; }
        """)
        self._submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._submit_btn)

    def _on_submit(self):
        text = self._input.text().strip()
        if text:
            self.query_submitted.emit(text)

    def set_loading(self, loading: bool):
        self._input.setEnabled(not loading)
        self._submit_btn.setEnabled(not loading)
        if loading:
            self._submit_btn.setText("Thinking...")
        else:
            self._submit_btn.setText("Ask")

    def clear(self):
        self._input.clear()

    def focus_input(self):
        self._input.setFocus()
        self._input.selectAll()
