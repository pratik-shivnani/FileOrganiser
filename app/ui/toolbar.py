import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QToolBar, QWidget, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QSizePolicy,
)
from PyQt6.QtGui import QAction


class NavigationToolbar(QToolBar):
    navigate_back = pyqtSignal()
    navigate_forward = pyqtSignal()
    navigate_up = pyqtSignal()
    path_entered = pyqtSignal(str)
    index_current = pyqtSignal()
    index_all = pyqtSignal()
    new_folder = pyqtSignal()
    open_settings = pyqtSignal()
    show_starred = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)
        self.setFloatable(False)
        self._history: list[str] = []
        self._history_index: int = -1
        self._setup_ui()

    def _setup_ui(self):
        self._back_btn = QPushButton("\u2190")
        self._back_btn.setToolTip("Back")
        self._back_btn.setFixedSize(30, 28)
        self._back_btn.setEnabled(False)
        self._back_btn.clicked.connect(self._on_back)
        self.addWidget(self._back_btn)

        self._forward_btn = QPushButton("\u2192")
        self._forward_btn.setToolTip("Forward")
        self._forward_btn.setFixedSize(30, 28)
        self._forward_btn.setEnabled(False)
        self._forward_btn.clicked.connect(self._on_forward)
        self.addWidget(self._forward_btn)

        self._up_btn = QPushButton("\u2191")
        self._up_btn.setToolTip("Up one level")
        self._up_btn.setFixedSize(30, 28)
        self._up_btn.clicked.connect(self.navigate_up.emit)
        self.addWidget(self._up_btn)

        self.addSeparator()

        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("Enter path...")
        self._path_input.setMinimumHeight(26)
        self._path_input.returnPressed.connect(
            lambda: self.path_entered.emit(self._path_input.text())
        )
        self.addWidget(self._path_input)

        self.addSeparator()

        self._new_folder_btn = QPushButton("New Folder")
        self._new_folder_btn.setToolTip("Create new folder (Ctrl+N)")
        self._new_folder_btn.clicked.connect(self.new_folder.emit)
        self.addWidget(self._new_folder_btn)

        self._starred_btn = QPushButton("\u2605 Starred")
        self._starred_btn.setToolTip("Show starred files")
        self._starred_btn.clicked.connect(self.show_starred.emit)
        self.addWidget(self._starred_btn)

        self.addSeparator()

        self._index_btn = QPushButton("Index Folder")
        self._index_btn.setToolTip("Index current folder for NLP search")
        self._index_btn.clicked.connect(self.index_current.emit)
        self.addWidget(self._index_btn)

        self._index_all_btn = QPushButton("Index All")
        self._index_all_btn.setToolTip("Re-index all registered folders")
        self._index_all_btn.clicked.connect(self.index_all.emit)
        self.addWidget(self._index_all_btn)

        self.addSeparator()

        self._settings_btn = QPushButton("\u2699")
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.setFixedSize(30, 28)
        self._settings_btn.clicked.connect(self.open_settings.emit)
        self.addWidget(self._settings_btn)

    def set_path(self, path: str, add_to_history: bool = True):
        self._path_input.setText(path)
        if add_to_history and (not self._history or self._history[self._history_index] != path):
            if self._history_index < len(self._history) - 1:
                self._history = self._history[:self._history_index + 1]
            self._history.append(path)
            self._history_index = len(self._history) - 1
        self._update_nav_buttons()

    def _on_back(self):
        if self._history_index > 0:
            self._history_index -= 1
            path = self._history[self._history_index]
            self._path_input.setText(path)
            self._update_nav_buttons()
            self.navigate_back.emit()
            self.path_entered.emit(path)

    def _on_forward(self):
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            path = self._history[self._history_index]
            self._path_input.setText(path)
            self._update_nav_buttons()
            self.navigate_forward.emit()
            self.path_entered.emit(path)

    def _update_nav_buttons(self):
        self._back_btn.setEnabled(self._history_index > 0)
        self._forward_btn.setEnabled(self._history_index < len(self._history) - 1)

    def get_current_path(self) -> str:
        return self._path_input.text()

    def set_indexing(self, active: bool):
        self._index_btn.setEnabled(not active)
        self._index_all_btn.setEnabled(not active)
        if active:
            self._index_btn.setText("Indexing...")
        else:
            self._index_btn.setText("Index Folder")
