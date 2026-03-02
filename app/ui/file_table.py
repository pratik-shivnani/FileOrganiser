import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QAbstractTableModel, QAbstractListModel, QModelIndex, QSize
from PyQt6.QtWidgets import (
    QTableView, QListView, QVBoxLayout, QWidget, QMenu, QAbstractItemView,
    QHeaderView, QMessageBox, QInputDialog, QFileDialog, QStackedWidget,
    QStyledItemDelegate, QStyle, QApplication,
)
from PyQt6.QtGui import QAction, QIcon, QFont, QPainter, QColor, QPen

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
                size = f.get("size", 0)
                if f.get("is_directory"):
                    return format_file_size(size) if size > 0 else "..."
                return format_file_size(size)
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

    def update_folder_size(self, path: str, size: int):
        for i, f in enumerate(self._files):
            if f.get("path") == path and f.get("is_directory"):
                f["size"] = size
                idx = self.index(i, self.COL_SIZE)
                self.dataChanged.emit(idx, idx)
                return

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


class GridItemDelegate(QStyledItemDelegate):
    def __init__(self, icon_size: int = 48, parent=None):
        super().__init__(parent)
        self._icon_size = icon_size

    def paint(self, painter: QPainter, option, index):
        painter.save()
        rect = option.rect

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, QColor("#e3f2fd"))
            painter.setPen(QPen(QColor("#90caf9"), 1))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, QColor("#f5f5f5"))

        f = index.data(Qt.ItemDataRole.UserRole)
        if not f:
            painter.restore()
            return

        is_dir = f.get("is_directory", False)
        is_star = f.get("is_starred", 0)
        name = f.get("name", "")
        ext = f.get("extension", "") or ""

        icon_rect_y = rect.top() + 8
        icon_rect_x = rect.center().x() - self._icon_size // 2

        icon_text = "\U0001f4c1" if is_dir else self._get_file_icon(ext)
        icon_font = QFont()
        icon_font.setPointSize(self._icon_size // 2)
        painter.setFont(icon_font)
        painter.setPen(QColor("#333"))
        painter.drawText(
            icon_rect_x, icon_rect_y, self._icon_size, self._icon_size,
            Qt.AlignmentFlag.AlignCenter, icon_text
        )

        if is_star:
            star_font = QFont()
            star_font.setPointSize(10)
            painter.setFont(star_font)
            painter.setPen(QColor("#FF9800"))
            painter.drawText(rect.right() - 18, rect.top() + 2, 16, 16,
                             Qt.AlignmentFlag.AlignCenter, "\u2605")

        name_font = QFont()
        name_font.setPointSize(9)
        painter.setFont(name_font)
        painter.setPen(QColor("#1a1a1a"))
        name_rect_top = icon_rect_y + self._icon_size + 4
        metrics = painter.fontMetrics()
        elided = metrics.elidedText(name, Qt.TextElideMode.ElideMiddle, rect.width() - 8)
        painter.drawText(
            rect.left() + 4, name_rect_top, rect.width() - 8, 20,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, elided
        )

        if not is_dir and self._icon_size >= 64:
            size_str = format_file_size(f.get("size", 0))
            size_font = QFont()
            size_font.setPointSize(8)
            painter.setFont(size_font)
            painter.setPen(QColor("#888"))
            painter.drawText(
                rect.left() + 4, name_rect_top + 16, rect.width() - 8, 16,
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, size_str
            )

        painter.restore()

    def sizeHint(self, option, index):
        if self._icon_size >= 64:
            return QSize(140, 120)
        return QSize(100, 90)

    def _get_file_icon(self, ext: str) -> str:
        icon_map = {
            ".pdf": "\U0001f4d1", ".doc": "\U0001f4dd", ".docx": "\U0001f4dd",
            ".xls": "\U0001f4ca", ".xlsx": "\U0001f4ca", ".csv": "\U0001f4ca",
            ".ppt": "\U0001f4ca", ".pptx": "\U0001f4ca",
            ".txt": "\U0001f4c4", ".md": "\U0001f4c4", ".log": "\U0001f4c4",
            ".py": "\U0001f40d", ".js": "\U0001f4dc", ".ts": "\U0001f4dc",
            ".html": "\U0001f310", ".css": "\U0001f3a8",
            ".jpg": "\U0001f5bc", ".jpeg": "\U0001f5bc", ".png": "\U0001f5bc",
            ".gif": "\U0001f5bc", ".svg": "\U0001f5bc", ".webp": "\U0001f5bc",
            ".mp4": "\U0001f3ac", ".avi": "\U0001f3ac", ".mkv": "\U0001f3ac", ".mov": "\U0001f3ac",
            ".mp3": "\U0001f3b5", ".wav": "\U0001f3b5", ".flac": "\U0001f3b5",
            ".zip": "\U0001f4e6", ".rar": "\U0001f4e6", ".7z": "\U0001f4e6", ".tar": "\U0001f4e6",
            ".gz": "\U0001f4e6",
            ".exe": "\u2699", ".msi": "\u2699",
            ".json": "\U0001f4cb", ".xml": "\U0001f4cb", ".yaml": "\U0001f4cb",
            ".yml": "\U0001f4cb",
        }
        return icon_map.get(ext.lower(), "\U0001f4c4")


class FileListModel(QAbstractListModel):
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

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._files):
            return None
        f = self._files[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return f.get("name", "")
        elif role == Qt.ItemDataRole.UserRole:
            return f
        elif role == Qt.ItemDataRole.ToolTipRole:
            return f.get("path", "")
        return None


class FileTable(QWidget):
    file_selected = pyqtSignal(str)
    file_double_clicked = pyqtSignal(str)
    file_starred = pyqtSignal(str, bool)
    file_tagged = pyqtSignal(str, str)
    request_move = pyqtSignal(list, str)
    request_copy = pyqtSignal(list, str)
    request_delete = pyqtSignal(list)
    request_rename = pyqtSignal(str, str)

    VIEW_LIST = "list"
    VIEW_GRID = "grid"
    VIEW_GALLERY = "gallery"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_dir = ""
        self._current_view = self.VIEW_LIST
        self._files: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()

        # --- List view (table) ---
        self.model = FileTableModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(False)
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
        self.table.selectionModel().currentRowChanged.connect(self._on_current_row_changed)
        self._stack.addWidget(self.table)

        # --- Grid view ---
        self._grid_model = FileListModel()
        self._grid_view = QListView()
        self._grid_view.setModel(self._grid_model)
        self._grid_view.setViewMode(QListView.ViewMode.IconMode)
        self._grid_view.setResizeMode(QListView.ResizeMode.Adjust)
        self._grid_view.setMovement(QListView.Movement.Static)
        self._grid_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._grid_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._grid_view.setSpacing(6)
        self._grid_view.setUniformItemSizes(True)
        self._grid_delegate = GridItemDelegate(icon_size=48)
        self._grid_view.setItemDelegate(self._grid_delegate)
        self._grid_view.setGridSize(QSize(106, 96))

        self._grid_view.clicked.connect(self._on_grid_clicked)
        self._grid_view.doubleClicked.connect(self._on_grid_double_clicked)
        self._grid_view.customContextMenuRequested.connect(self._on_grid_context_menu)
        self._grid_view.selectionModel().currentChanged.connect(self._on_grid_current_changed)
        self._stack.addWidget(self._grid_view)

        # --- Gallery view ---
        self._gallery_model = FileListModel()
        self._gallery_view = QListView()
        self._gallery_view.setModel(self._gallery_model)
        self._gallery_view.setViewMode(QListView.ViewMode.IconMode)
        self._gallery_view.setResizeMode(QListView.ResizeMode.Adjust)
        self._gallery_view.setMovement(QListView.Movement.Static)
        self._gallery_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._gallery_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._gallery_view.setSpacing(10)
        self._gallery_view.setUniformItemSizes(True)
        self._gallery_delegate = GridItemDelegate(icon_size=72)
        self._gallery_view.setItemDelegate(self._gallery_delegate)
        self._gallery_view.setGridSize(QSize(146, 126))

        self._gallery_view.clicked.connect(self._on_grid_clicked)
        self._gallery_view.doubleClicked.connect(self._on_grid_double_clicked)
        self._gallery_view.customContextMenuRequested.connect(self._on_gallery_context_menu)
        self._gallery_view.selectionModel().currentChanged.connect(self._on_grid_current_changed)
        self._stack.addWidget(self._gallery_view)

        layout.addWidget(self._stack)

    def set_view_mode(self, mode: str):
        self._current_view = mode
        if mode == self.VIEW_LIST:
            self._stack.setCurrentWidget(self.table)
        elif mode == self.VIEW_GRID:
            self._stack.setCurrentWidget(self._grid_view)
        elif mode == self.VIEW_GALLERY:
            self._stack.setCurrentWidget(self._gallery_view)

    def set_files(self, files: list[dict], current_dir: str = ""):
        self._current_dir = current_dir
        self._files = files
        self.model.set_files(files)
        self._grid_model.set_files(files)
        self._gallery_model.set_files(files)

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

    def _on_current_row_changed(self, current, previous):
        if current.isValid():
            f = self.model.get_file(current.row())
            if f:
                self.file_selected.emit(f["path"])

    def _on_double_clicked(self, index):
        f = self.model.get_file(index.row())
        if f:
            self.file_double_clicked.emit(f["path"])

    # --- Grid/Gallery handlers ---

    def _on_grid_clicked(self, index):
        model = index.model()
        f = model.get_file(index.row()) if model else None
        if f:
            self.file_selected.emit(f["path"])

    def _on_grid_double_clicked(self, index):
        model = index.model()
        f = model.get_file(index.row()) if model else None
        if f:
            self.file_double_clicked.emit(f["path"])

    def _on_grid_current_changed(self, current, previous):
        if current.isValid():
            model = current.model()
            f = model.get_file(current.row()) if model else None
            if f:
                self.file_selected.emit(f["path"])

    def _on_grid_context_menu(self, position):
        self._show_context_menu(self._grid_view, self._grid_model, position)

    def _on_gallery_context_menu(self, position):
        self._show_context_menu(self._gallery_view, self._gallery_model, position)

    def _show_context_menu(self, view, model, position):
        selected_paths = self._get_selected_paths_from_view(view, model)
        if not selected_paths:
            menu = QMenu(self)
            new_folder_action = QAction("New Folder", self)
            new_folder_action.triggered.connect(self._create_new_folder)
            menu.addAction(new_folder_action)
            menu.exec(view.viewport().mapToGlobal(position))
            return
        self._build_file_context_menu(selected_paths, view.viewport().mapToGlobal(position))

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

    def _build_file_context_menu(self, selected_paths: list[str], global_pos):
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

        menu.exec(global_pos)

    def _get_selected_paths_from_view(self, view, model) -> list[str]:
        paths = []
        seen = set()
        for index in view.selectionModel().selectedIndexes():
            f = model.get_file(index.row())
            if f and f["path"] not in seen:
                paths.append(f["path"])
                seen.add(f["path"])
        return paths

    def _get_selected_paths(self) -> list[str]:
        if self._current_view == self.VIEW_GRID:
            return self._get_selected_paths_from_view(self._grid_view, self._grid_model)
        elif self._current_view == self.VIEW_GALLERY:
            return self._get_selected_paths_from_view(self._gallery_view, self._gallery_model)
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

    def update_folder_size(self, path: str, size: int):
        self.model.update_folder_size(path, size)

    def get_file_count(self) -> int:
        return self.model.rowCount()
