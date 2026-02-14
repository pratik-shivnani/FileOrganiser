import os
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame,
    QHBoxLayout, QPushButton, QLineEdit,
)
from PyQt6.QtGui import QFont

from app.config import format_file_size
from app.core.metadata import get_file_metadata, FileMetadata
from app.core.tag_manager import get_tags_for_file, is_starred, toggle_star, add_tag, remove_tag


class TagChip(QFrame):
    removed = pyqtSignal(str)

    def __init__(self, tag: str, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            TagChip {
                background-color: #e3f2fd;
                border: 1px solid #90caf9;
                border-radius: 10px;
                padding: 2px 6px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 2, 2)
        layout.setSpacing(4)

        label = QLabel(tag)
        label.setStyleSheet("color: #1565c0; font-size: 11px;")
        layout.addWidget(label)

        remove_btn = QPushButton("\u00d7")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #1565c0;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { color: #d32f2f; }
        """)
        remove_btn.clicked.connect(lambda: self.removed.emit(self.tag))
        layout.addWidget(remove_btn)


class DetailPanel(QWidget):
    star_toggled = pyqtSignal(str, bool)
    tag_added = pyqtSignal(str, str)
    tag_removed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._layout.setSpacing(8)

        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self._title_label = QLabel("No file selected")
        self._title_label.setFont(title_font)
        self._title_label.setWordWrap(True)
        self._layout.addWidget(self._title_label)

        self._star_btn = QPushButton("\u2606 Star")
        self._star_btn.setCheckable(True)
        self._star_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background: white;
            }
            QPushButton:checked {
                background: #fff3e0;
                border-color: #ffb74d;
                color: #e65100;
            }
        """)
        self._star_btn.clicked.connect(self._on_star_clicked)
        self._layout.addWidget(self._star_btn)

        self._add_separator()

        self._info_section = QLabel("Details")
        self._info_section.setStyleSheet("font-weight: bold; color: #555; margin-top: 4px;")
        self._layout.addWidget(self._info_section)

        self._details_label = QLabel("")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._details_label.setStyleSheet("font-size: 12px; line-height: 1.6;")
        self._layout.addWidget(self._details_label)

        self._add_separator()

        self._tags_header = QLabel("Tags")
        self._tags_header.setStyleSheet("font-weight: bold; color: #555; margin-top: 4px;")
        self._layout.addWidget(self._tags_header)

        self._tags_container = QWidget()
        self._tags_layout = QVBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(4)
        self._layout.addWidget(self._tags_container)

        tag_input_layout = QHBoxLayout()
        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("Add tag...")
        self._tag_input.returnPressed.connect(self._on_add_tag)
        tag_input_layout.addWidget(self._tag_input)

        add_tag_btn = QPushButton("+")
        add_tag_btn.setFixedWidth(30)
        add_tag_btn.clicked.connect(self._on_add_tag)
        tag_input_layout.addWidget(add_tag_btn)
        self._layout.addLayout(tag_input_layout)

        self._layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _add_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self._layout.addWidget(line)

    def show_file(self, filepath: str):
        self._current_path = filepath
        meta = get_file_metadata(filepath)
        if not meta:
            self._title_label.setText("Cannot read file")
            self._details_label.setText("")
            return

        self._title_label.setText(meta.name)

        starred = is_starred(filepath)
        self._star_btn.setChecked(starred)
        self._star_btn.setText("\u2605 Starred" if starred else "\u2606 Star")

        details = []
        details.append(f"<b>Path:</b> {meta.path}")
        details.append(f"<b>Type:</b> {'Folder' if meta.is_directory else (meta.extension or 'File')}")
        if not meta.is_directory:
            details.append(f"<b>Size:</b> {format_file_size(meta.size)}")
        if meta.mime_type:
            details.append(f"<b>MIME:</b> {meta.mime_type}")
        details.append(f"<b>Created:</b> {meta.created_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        details.append(f"<b>Modified:</b> {meta.modified_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        details.append(f"<b>Accessed:</b> {meta.accessed_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        details.append(f"<b>Permissions:</b> {meta.permissions}")
        if meta.is_hidden:
            details.append("<b>Hidden:</b> Yes")
        if meta.is_readonly:
            details.append("<b>Read-only:</b> Yes")
        if meta.is_symlink:
            details.append("<b>Symlink:</b> Yes")

        self._details_label.setText("<br>".join(details))

        self._refresh_tags()

    def _refresh_tags(self):
        while self._tags_layout.count():
            item = self._tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._current_path:
            return

        tags = get_tags_for_file(self._current_path)
        if not tags:
            no_tags = QLabel("No tags")
            no_tags.setStyleSheet("color: #999; font-style: italic;")
            self._tags_layout.addWidget(no_tags)
        else:
            for tag in tags:
                chip = TagChip(tag)
                chip.removed.connect(self._on_remove_tag)
                self._tags_layout.addWidget(chip)

    def _on_star_clicked(self):
        if self._current_path:
            new_state = toggle_star(self._current_path)
            self._star_btn.setChecked(new_state)
            self._star_btn.setText("\u2605 Starred" if new_state else "\u2606 Star")
            self.star_toggled.emit(self._current_path, new_state)

    def _on_add_tag(self):
        tag = self._tag_input.text().strip()
        if tag and self._current_path:
            add_tag(self._current_path, tag)
            self._tag_input.clear()
            self._refresh_tags()
            self.tag_added.emit(self._current_path, tag)

    def _on_remove_tag(self, tag: str):
        if self._current_path:
            remove_tag(self._current_path, tag)
            self._refresh_tags()
            self.tag_removed.emit(self._current_path, tag)

    def clear(self):
        self._current_path = None
        self._title_label.setText("No file selected")
        self._details_label.setText("")
        self._star_btn.setChecked(False)
        self._star_btn.setText("\u2606 Star")
        while self._tags_layout.count():
            item = self._tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
