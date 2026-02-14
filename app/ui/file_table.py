import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PyQt6.QtWidgets import (
    QTableView, QVBoxLayout, QWidget, QMenu, QAbstractItemView,
    QHeaderView, QMessageBox, QInputDialog, QFileDialog,
)
from PyQt6.QtGui import QAction, QIcon

from app.config import format_file_size
from app.core.tag_manager import toggle_star, is_starred, add_tag, get_tags_for_file


class FileTableModel(QAbstractTableModel):
    COLUMNS = ["", "Name", "Size", "Type", "Date Modified", "Path"]
    COL_STAR = 0
    COL_NAME = 1
    COL_SIZE = 2
    COL_TYPE = 3
    COL_DATE = 4
    COL_PATH = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: list[dict] = []

    def set_files(self, files: list[dict]):
        self.beginResetModel()
        self._files = files
        self.endResetModel()

    def get_file(self, row: int) -> Optional[dict]:
        if 0 <= row < len(self._files):
            return self._files[row]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self._files)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._files):
            return None

        f = self._files[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_STAR:
                starred = f.get("is_starred", 0)
                return "\u2605" if starred else ""
            elif col == self.COL_NAME:
                return f.get("name", "")
            elif col == self.COL_SIZE:
                if f.get("is_directory"):
                    return ""
                return format_file_size(f.get("size", 0))
            elif col == self.COL_TYPE:
                if f.get("is_directory"):
                    return "Folder"
                ext = f.get("extension", "")
                return ext.lstrip(".").upper() + " File" if ext else "File"
            elif col == self.COL_DATE:
                ts = f.get("modified_at", 0)
                if ts:
                    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                return ""
            elif col == self.COL_PATH:
                return f.get("path", "")

        elif role == Qt.ItemDataRole.UserRole:
            return f

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == self.COL_SIZE:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if col == self.COL_STAR:
                return Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.ToolTipRole:
            return f.get("path", "")

        return None

    def sort(self, column, order=Qt.SortOrder.AscendingOrder):
        self.beginResetModel()
        reverse = order == Qt.SortOrder.DescendingOrder

        key_map = {
            self.COL_NAME: lambda x: x.get("name", "").lower(),
            self.COL_SIZE: lambda x: x.get("size", 0),
            self.COL_TYPE: lambda x: x.get("extension", "") or "",
            self.COL_DATE: lambda x: x.get("modified_at", 0),
            self.COL_PATH: lambda x: x.get("path", "").lower(),
            self.COL_STAR: lambda x: x.get("is_starred", 0),
        }

        key_func = key_map.get(column, key_map[self.COL_NAME])
        dirs = [f for f in self._files if f.get("is_directory")]
        files = [f for f in self._files if not f.get("is_directory")]
        dirs.sort(key=key_func, reverse=reverse)
        files.sort(key=key_func, reverse=reverse)
        self._files = dirs + files

        self.endResetModel()


class FileTable(QWidget):
    file_selected = pyqtSignal(str)
    file_double_clicked = pyqtSignal(str)
    file_starred = pyqtSignal(str, bool)
    file_tagged = pyqtSignal(str, str)
    request_move = pyqtSignal(list, str)
    request_copy = pyqtSignal(list, str)
    request_delete = pyqtSignal(list)
    request_rename = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_dir = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.model = FileTableModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table.setColumnWidth(0, 30)

        self.table.clicked.connect(self._on_clicked)
        self.table.doubleClicked.connect(self._on_double_clicked)
        self.table.customContextMenuRequested.connect(self._on_context_menu)

        layout.addWidget(self.table)

    def set_files(self, files: list[dict], current_dir: str = ""):
        self._current_dir = current_dir
        self.model.set_files(files)

    def _on_clicked(self, index):
        f = self.model.get_file(index.row())
        if f:
            if index.column() == FileTableModel.COL_STAR:
                path = f["path"]
                new_state = toggle_star(path)
                f["is_starred"] = 1 if new_state else 0
                self.model.dataChanged.emit(index, index)
                self.file_starred.emit(path, new_state)
            else:
                self.file_selected.emit(f["path"])

    def _on_double_clicked(self, index):
        f = self.model.get_file(index.row())
        if f:
            self.file_double_clicked.emit(f["path"])

    def _on_context_menu(self, position):
        index = self.table.indexAt(position)
        selected_paths = self._get_selected_paths()

        if not selected_paths:
            menu = QMenu(self)
            new_folder_action = QAction("New Folder", self)
            new_folder_action.triggered.connect(self._create_new_folder)
            menu.addAction(new_folder_action)
            menu.exec(self.table.viewport().mapToGlobal(position))
            return

        menu = QMenu(self)

        if len(selected_paths) == 1:
            path = selected_paths[0]

            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self._open_file(path))
            menu.addAction(open_action)

            open_location_action = QAction("Open File Location", self)
            open_location_action.triggered.connect(lambda: self._open_location(path))
            menu.addAction(open_location_action)

            menu.addSeparator()

            rename_action = QAction("Rename", self)
            rename_action.setShortcut("F2")
            rename_action.triggered.connect(lambda: self._rename_file(path))
            menu.addAction(rename_action)

        menu.addSeparator()

        copy_action = QAction(f"Copy ({len(selected_paths)} items)" if len(selected_paths) > 1 else "Copy", self)
        copy_action.triggered.connect(lambda: self._copy_files(selected_paths))
        menu.addAction(copy_action)

        move_action = QAction(f"Move ({len(selected_paths)} items)" if len(selected_paths) > 1 else "Move to...", self)
        move_action.triggered.connect(lambda: self._move_files(selected_paths))
        menu.addAction(move_action)

        menu.addSeparator()

        delete_action = QAction(f"Delete ({len(selected_paths)} items)" if len(selected_paths) > 1 else "Delete", self)
        delete_action.triggered.connect(lambda: self.request_delete.emit(selected_paths))
        menu.addAction(delete_action)

        menu.addSeparator()

        star_action = QAction("Toggle Star", self)
        star_action.triggered.connect(lambda: self._toggle_stars(selected_paths))
        menu.addAction(star_action)

        tag_action = QAction("Add Tag...", self)
        tag_action.triggered.connect(lambda: self._add_tag(selected_paths))
        menu.addAction(tag_action)

        menu.exec(self.table.viewport().mapToGlobal(position))

    def _get_selected_paths(self) -> list[str]:
        paths = []
        seen = set()
        for index in self.table.selectionModel().selectedRows():
            f = self.model.get_file(index.row())
            if f and f["path"] not in seen:
                paths.append(f["path"])
                seen.add(f["path"])
        return paths

    def _open_file(self, path: str):
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _open_location(self, path: str):
        folder = os.path.dirname(path)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", folder])

    def _rename_file(self, path: str):
        name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=name)
        if ok and new_name and new_name != name:
            self.request_rename.emit(path, new_name)

    def _copy_files(self, paths: list[str]):
        dest = QFileDialog.getExistingDirectory(self, "Copy to...")
        if dest:
            self.request_copy.emit(paths, dest)

    def _move_files(self, paths: list[str]):
        dest = QFileDialog.getExistingDirectory(self, "Move to...")
        if dest:
            self.request_move.emit(paths, dest)

    def _toggle_stars(self, paths: list[str]):
        for path in paths:
            new_state = toggle_star(path)
            self.file_starred.emit(path, new_state)
        self.model.layoutChanged.emit()

    def _add_tag(self, paths: list[str]):
        tag, ok = QInputDialog.getText(self, "Add Tag", "Tag name:")
        if ok and tag:
            for path in paths:
                add_tag(path, tag)
                self.file_tagged.emit(path, tag)

    def _create_new_folder(self):
        if not self._current_dir:
            return
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name:
            try:
                from app.core.operations import create_folder
                create_folder(self._current_dir, name)
                self.file_double_clicked.emit(self._current_dir)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def get_selected_path(self) -> Optional[str]:
        paths = self._get_selected_paths()
        return paths[0] if paths else None

    def get_file_count(self) -> int:
        return self.model.rowCount()
