from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
)


class NewFolderDialog(QDialog):
    def __init__(self, parent_dir: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Folder")
        self.setMinimumWidth(350)
        self._folder_name = ""
        self._setup_ui(parent_dir)

    def _setup_ui(self, parent_dir: str):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"Create new folder in:\n{parent_dir}"))

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Folder name")
        self._name_input.returnPressed.connect(self._on_create)
        layout.addWidget(self._name_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("Create")
        create_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: white;
                border: none; border-radius: 4px; padding: 6px 16px;
            }
            QPushButton:hover { background: #1976D2; }
        """)
        create_btn.clicked.connect(self._on_create)
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)

    def _on_create(self):
        name = self._name_input.text().strip()
        if name:
            self._folder_name = name
            self.accept()

    def get_folder_name(self) -> str:
        return self._folder_name
