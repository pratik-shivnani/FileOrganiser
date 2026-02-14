from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QFrame, QComboBox, QGroupBox,
    QFormLayout, QFileDialog, QMessageBox,
)

from app.config import OLLAMA_HOST, OLLAMA_MODEL
from app.nlp.parser import check_ollama_connection


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)

    def __init__(self, current_settings: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self._settings = current_settings or {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        ollama_group = QGroupBox("Ollama Configuration")
        ollama_layout = QFormLayout()

        self._host_input = QLineEdit(self._settings.get("ollama_host", OLLAMA_HOST))
        ollama_layout.addRow("Host:", self._host_input)

        self._model_input = QComboBox()
        self._model_input.setEditable(True)
        self._model_input.addItems([
            "llama3.2:3b", "llama3.2:1b", "llama3.1:8b",
            "mistral:7b", "phi3:mini",
        ])
        current_model = self._settings.get("ollama_model", OLLAMA_MODEL)
        self._model_input.setCurrentText(current_model)
        ollama_layout.addRow("Model:", self._model_input)

        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        ollama_layout.addRow("", test_btn)

        self._connection_status = QLabel("")
        ollama_layout.addRow("Status:", self._connection_status)

        ollama_group.setLayout(ollama_layout)
        layout.addWidget(ollama_group)

        dirs_group = QGroupBox("Indexed Directories")
        dirs_layout = QVBoxLayout()

        self._dirs_list = QListWidget()
        for d in self._settings.get("indexed_dirs", []):
            self._dirs_list.addItem(d)
        dirs_layout.addWidget(self._dirs_list)

        dirs_btn_layout = QHBoxLayout()
        add_dir_btn = QPushButton("Add Directory")
        add_dir_btn.clicked.connect(self._add_directory)
        dirs_btn_layout.addWidget(add_dir_btn)

        remove_dir_btn = QPushButton("Remove Selected")
        remove_dir_btn.clicked.connect(self._remove_directory)
        dirs_btn_layout.addWidget(remove_dir_btn)
        dirs_layout.addLayout(dirs_btn_layout)

        dirs_group.setLayout(dirs_layout)
        layout.addWidget(dirs_group)

        exclude_group = QGroupBox("Excluded Folders")
        exclude_layout = QVBoxLayout()

        self._exclude_input = QLineEdit(
            ", ".join(self._settings.get("excluded_dirs", []))
        )
        self._exclude_input.setPlaceholderText("Comma-separated folder names to skip")
        exclude_layout.addWidget(self._exclude_input)

        exclude_group.setLayout(exclude_layout)
        layout.addWidget(exclude_group)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: white;
                border: none; border-radius: 4px; padding: 6px 16px;
            }
            QPushButton:hover { background: #1976D2; }
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _test_connection(self):
        self._connection_status.setText("Testing...")
        connected, message = check_ollama_connection()
        if connected:
            self._connection_status.setText(f"\u2713 {message}")
            self._connection_status.setStyleSheet("color: #4CAF50;")
        else:
            self._connection_status.setText(f"\u2717 {message}")
            self._connection_status.setStyleSheet("color: #d32f2f;")

    def _add_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory to Index")
        if directory:
            self._dirs_list.addItem(directory)

    def _remove_directory(self):
        item = self._dirs_list.currentItem()
        if item:
            row = self._dirs_list.row(item)
            self._dirs_list.takeItem(row)

    def _save(self):
        dirs = []
        for i in range(self._dirs_list.count()):
            dirs.append(self._dirs_list.item(i).text())

        excluded = [
            d.strip() for d in self._exclude_input.text().split(",") if d.strip()
        ]

        settings = {
            "ollama_host": self._host_input.text().strip(),
            "ollama_model": self._model_input.currentText().strip(),
            "indexed_dirs": dirs,
            "excluded_dirs": excluded,
        }
        self.settings_changed.emit(settings)
        self.accept()
