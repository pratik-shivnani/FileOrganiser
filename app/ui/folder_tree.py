import os
import sys

from PyQt6.QtCore import Qt, pyqtSignal, QDir
from PyQt6.QtWidgets import (
    QTreeView, QVBoxLayout, QWidget,
    QMenu, QAbstractItemView,
)
from PyQt6.QtGui import QAction, QFileSystemModel


class FolderTree(QWidget):
    directory_selected = pyqtSignal(str)
    directory_double_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot | QDir.Filter.Drives
        )

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(""))
        self.tree.setAnimated(True)
        self.tree.setIndentation(16)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.tree.hideColumn(1)  # Size
        self.tree.hideColumn(2)  # Type
        self.tree.hideColumn(3)  # Date Modified

        self.tree.setHeaderHidden(True)

        self.tree.clicked.connect(self._on_clicked)
        self.tree.doubleClicked.connect(self._on_double_clicked)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

        layout.addWidget(self.tree)

        if sys.platform == "win32":
            self.tree.setRootIndex(self.model.index(""))
        else:
            home = os.path.expanduser("~")
            home_index = self.model.index(home)
            self.tree.setCurrentIndex(home_index)
            self.tree.scrollTo(home_index)

    def _on_clicked(self, index):
        path = self.model.filePath(index)
        if path and os.path.isdir(path):
            self.directory_selected.emit(path)

    def _on_double_clicked(self, index):
        path = self.model.filePath(index)
        if path and os.path.isdir(path):
            self.directory_double_clicked.emit(path)

    def _on_context_menu(self, position):
        index = self.tree.indexAt(position)
        if not index.isValid():
            return

        path = self.model.filePath(index)
        menu = QMenu(self)

        open_action = QAction("Open in File Table", self)
        open_action.triggered.connect(lambda: self.directory_selected.emit(path))
        menu.addAction(open_action)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def navigate_to(self, path: str):
        index = self.model.index(path)
        if index.isValid():
            self.tree.setCurrentIndex(index)
            self.tree.scrollTo(index)
            self.tree.expand(index)

    def get_selected_path(self) -> str:
        indexes = self.tree.selectedIndexes()
        if indexes:
            return self.model.filePath(indexes[0])
        return ""
