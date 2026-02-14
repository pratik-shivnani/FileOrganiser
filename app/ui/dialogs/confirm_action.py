from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QFrame,
)
from PyQt6.QtCore import Qt


class ConfirmActionDialog(QDialog):
    def __init__(self, action: str, files: list[str], target: str = "",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Confirm {action.title()}")
        self.setMinimumWidth(450)
        self._setup_ui(action, files, target)

    def _setup_ui(self, action: str, files: list[str], target: str):
        layout = QVBoxLayout(self)

        action_label = QLabel(f"<b>{action.title()}</b> the following {len(files)} item(s)?")
        action_label.setStyleSheet("font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(action_label)

        file_list = QListWidget()
        file_list.setMaximumHeight(200)
        for f in files[:50]:
            file_list.addItem(f)
        if len(files) > 50:
            file_list.addItem(f"... and {len(files) - 50} more")
        layout.addWidget(file_list)

        if target:
            target_label = QLabel(f"<b>To:</b> {target}")
            target_label.setStyleSheet("margin-top: 8px;")
            layout.addWidget(target_label)

        if action.lower() == "delete":
            warning = QLabel("This action cannot be undone if files are permanently deleted.")
            warning.setStyleSheet("color: #d32f2f; margin-top: 8px;")
            layout.addWidget(warning)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(f"{action.title()}")
        if action.lower() == "delete":
            confirm_btn.setStyleSheet("""
                QPushButton {
                    background: #d32f2f; color: white;
                    border: none; border-radius: 4px; padding: 6px 16px;
                }
                QPushButton:hover { background: #b71c1c; }
            """)
        else:
            confirm_btn.setStyleSheet("""
                QPushButton {
                    background: #2196F3; color: white;
                    border: none; border-radius: 4px; padding: 6px 16px;
                }
                QPushButton:hover { background: #1976D2; }
            """)
        confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)
