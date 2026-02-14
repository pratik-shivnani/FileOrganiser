from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QFrame,
)

from app.core.tag_manager import get_tags_for_file, add_tag, remove_tag, get_all_tags


class TagEditorDialog(QDialog):
    tags_changed = pyqtSignal()

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(f"Edit Tags — {file_path.split('/')[-1].split(chr(92))[-1]}")
        self.setMinimumWidth(400)
        self.setMinimumHeight(350)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Current Tags:</b>"))

        self._tag_list = QListWidget()
        self._refresh_tags()
        layout.addWidget(self._tag_list)

        remove_btn = QPushButton("Remove Selected Tag")
        remove_btn.clicked.connect(self._remove_selected)
        layout.addWidget(remove_btn)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        layout.addWidget(QLabel("<b>Add New Tag:</b>"))

        input_layout = QHBoxLayout()
        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("Enter tag name...")
        self._tag_input.returnPressed.connect(self._add_tag)
        input_layout.addWidget(self._tag_input)

        add_btn = QPushButton("Add")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: white;
                border: none; border-radius: 4px; padding: 6px 16px;
            }
            QPushButton:hover { background: #1976D2; }
        """)
        add_btn.clicked.connect(self._add_tag)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)

        all_tags = get_all_tags()
        if all_tags:
            layout.addWidget(QLabel("Existing tags (click to add):"))
            existing_layout = QHBoxLayout()
            for tag_info in all_tags[:10]:
                btn = QPushButton(f"{tag_info['tag']} ({tag_info['count']})")
                btn.setStyleSheet("""
                    QPushButton {
                        background: #e3f2fd; border: 1px solid #90caf9;
                        border-radius: 10px; padding: 2px 8px; font-size: 11px;
                    }
                    QPushButton:hover { background: #bbdefb; }
                """)
                tag_name = tag_info["tag"]
                btn.clicked.connect(lambda checked, t=tag_name: self._add_specific_tag(t))
                existing_layout.addWidget(btn)
            existing_layout.addStretch()
            layout.addLayout(existing_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _refresh_tags(self):
        self._tag_list.clear()
        tags = get_tags_for_file(self.file_path)
        for tag in tags:
            self._tag_list.addItem(tag)

    def _add_tag(self):
        tag = self._tag_input.text().strip()
        if tag:
            add_tag(self.file_path, tag)
            self._tag_input.clear()
            self._refresh_tags()
            self.tags_changed.emit()

    def _add_specific_tag(self, tag: str):
        add_tag(self.file_path, tag)
        self._refresh_tags()
        self.tags_changed.emit()

    def _remove_selected(self):
        item = self._tag_list.currentItem()
        if item:
            remove_tag(self.file_path, item.text())
            self._refresh_tags()
            self.tags_changed.emit()
