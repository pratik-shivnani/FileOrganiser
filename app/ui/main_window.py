import os
import sys
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout, QMessageBox,
    QInputDialog, QApplication,
)
from PyQt6.QtGui import QAction, QKeySequence, QShortcut

from app.config import (
    APP_NAME, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    TREE_PANEL_WIDTH, DETAIL_PANEL_WIDTH, format_file_size,
)
from app.core.scanner import ScannerThread, get_indexed_directories
from app.core.search import search_files
from app.core.operations import (
    move_file, copy_file, rename_file, delete_file, create_folder,
    undo_last_operation,
)
from app.core.metadata import get_file_metadata
from app.core.tag_manager import get_starred_files, is_starred
from app.nlp.parser import OllamaParserThread, parse_size_string, parse_time_string, check_ollama_connection
from app.nlp.models import ParsedCommand
from app.ui.toolbar import NavigationToolbar
from app.ui.chat_panel import ChatPanel
from app.ui.folder_tree import FolderTree
from app.ui.file_table import FileTable
from app.ui.detail_panel import DetailPanel
from app.ui.status_bar import StatusBar
from app.ui.dialogs.confirm_action import ConfirmActionDialog
from app.ui.dialogs.new_folder import NewFolderDialog
from app.ui.dialogs.settings import SettingsDialog
from app.ui.dialogs.operation_log import OperationLogDialog
from app.ui.dialogs.disk_cleanup import DiskCleanupDialog
from app.core.updater import UpdateCheckThread, is_frozen
from app.core.folder_size import FolderSizeThread
from app.config import APP_VERSION


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._current_dir = ""
        self._scanner_thread: Optional[ScannerThread] = None
        self._parser_thread: Optional[OllamaParserThread] = None
        self._folder_size_thread: Optional[FolderSizeThread] = None
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_menu()
        self._check_ollama()
        self._navigate_to_home()
        self._check_for_updates(silent=True)

    def _setup_ui(self):
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._toolbar = NavigationToolbar()
        self._toolbar.path_entered.connect(self._on_path_entered)
        self._toolbar.navigate_up.connect(self._navigate_up)
        self._toolbar.index_current.connect(self._index_current_folder)
        self._toolbar.index_all.connect(self._index_all_folders)
        self._toolbar.new_folder.connect(self._create_new_folder)
        self._toolbar.open_settings.connect(self._open_settings)
        self._toolbar.show_starred.connect(self._show_starred)
        self._toolbar.view_mode_changed.connect(self._on_view_mode_changed)
        self._toolbar.disk_cleanup.connect(self._open_disk_cleanup)
        main_layout.addWidget(self._toolbar)

        outer_splitter = QSplitter(Qt.Orientation.Horizontal)

        left_section = QWidget()
        left_layout = QVBoxLayout(left_section)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        file_splitter = QSplitter(Qt.Orientation.Horizontal)

        self._folder_tree = FolderTree()
        self._folder_tree.directory_selected.connect(self._navigate_to)
        self._folder_tree.directory_double_clicked.connect(self._navigate_to)
        file_splitter.addWidget(self._folder_tree)

        self._file_table = FileTable()
        self._file_table.file_selected.connect(self._on_file_selected)
        self._file_table.file_double_clicked.connect(self._on_file_double_clicked)
        self._file_table.request_move.connect(self._do_move)
        self._file_table.request_copy.connect(self._do_copy)
        self._file_table.request_delete.connect(self._do_delete)
        self._file_table.request_rename.connect(self._do_rename)
        self._file_table.file_starred.connect(self._on_file_starred)
        file_splitter.addWidget(self._file_table)

        self._detail_panel = DetailPanel()
        self._detail_panel.star_toggled.connect(self._on_file_starred)
        file_splitter.addWidget(self._detail_panel)

        file_splitter.setSizes([TREE_PANEL_WIDTH, 600, DETAIL_PANEL_WIDTH])
        left_layout.addWidget(file_splitter)

        outer_splitter.addWidget(left_section)

        self._chat_panel = ChatPanel()
        self._chat_panel.query_submitted.connect(self._on_nlp_query)
        self._chat_panel.setMinimumWidth(280)
        outer_splitter.addWidget(self._chat_panel)

        outer_splitter.setSizes([1050, 350])
        main_layout.addWidget(outer_splitter)

        self._status_bar = StatusBar()
        self.setStatusBar(self._status_bar)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+L"), self, self._chat_panel.focus_input)
        QShortcut(QKeySequence("Ctrl+N"), self, self._create_new_folder)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_operation)
        QShortcut(QKeySequence("F5"), self, self._refresh_current)
        QShortcut(QKeySequence("Alt+Up"), self, self._navigate_up)
        QShortcut(QKeySequence("Delete"), self, self._delete_selected)
        QShortcut(QKeySequence("F2"), self, self._rename_selected)
        QShortcut(QKeySequence("Ctrl+H"), self, self._show_operation_log)
        QShortcut(QKeySequence("Ctrl+Shift+D"), self, self._open_disk_cleanup)

    def _add_menu_action(self, menu, text, slot, shortcut=None):
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        menu.addAction(action)
        return action

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        self._add_menu_action(file_menu, "New Folder", self._create_new_folder, "Ctrl+N")
        file_menu.addSeparator()
        self._add_menu_action(file_menu, "Settings", self._open_settings)
        file_menu.addSeparator()
        self._add_menu_action(file_menu, "Exit", self.close, "Alt+F4")

        edit_menu = menubar.addMenu("&Edit")
        self._add_menu_action(edit_menu, "Undo", self._undo_operation, "Ctrl+Z")
        edit_menu.addSeparator()
        self._add_menu_action(edit_menu, "Rename", self._rename_selected, "F2")
        self._add_menu_action(edit_menu, "Delete", self._delete_selected, "Delete")

        view_menu = menubar.addMenu("&View")
        self._add_menu_action(view_menu, "Refresh", self._refresh_current, "F5")
        self._add_menu_action(view_menu, "Starred Files", self._show_starred)
        self._add_menu_action(view_menu, "Operation History", self._show_operation_log, "Ctrl+H")

        tools_menu = menubar.addMenu("&Tools")
        self._add_menu_action(tools_menu, "Index Current Folder", self._index_current_folder)
        self._add_menu_action(tools_menu, "Index All Folders", self._index_all_folders)
        tools_menu.addSeparator()
        self._add_menu_action(tools_menu, "Disk Cleanup...", self._open_disk_cleanup, "Ctrl+Shift+D")
        tools_menu.addSeparator()
        self._add_menu_action(tools_menu, "Focus Chat", self._chat_panel.focus_input, "Ctrl+L")

        help_menu = menubar.addMenu("&Help")
        self._add_menu_action(help_menu, "Check for Updates...", lambda: self._check_for_updates(silent=False))
        help_menu.addSeparator()
        self._add_menu_action(help_menu, f"About (v{APP_VERSION})", self._show_about)

    def _navigate_to_home(self):
        home = str(Path.home())
        self._navigate_to(home)

    def _navigate_to(self, path: str):
        if not os.path.isdir(path):
            return
        self._current_dir = path
        self._toolbar.set_path(path)
        self._folder_tree.navigate_to(path)
        self._load_directory_files(path)

    def _on_path_entered(self, path: str):
        if os.path.isdir(path):
            self._navigate_to(path)
        else:
            QMessageBox.warning(self, "Invalid Path", f"'{path}' is not a valid directory.")

    def _navigate_up(self):
        if self._current_dir:
            parent = os.path.dirname(self._current_dir)
            if parent and parent != self._current_dir:
                self._navigate_to(parent)

    def _load_directory_files(self, directory: str):
        files = []
        try:
            for entry in os.scandir(directory):
                try:
                    st = entry.stat()
                    ext = Path(entry.name).suffix.lower() if entry.is_file() else None
                    files.append({
                        "path": entry.path,
                        "name": entry.name,
                        "extension": ext,
                        "size": st.st_size if entry.is_file() else 0,
                        "created_at": st.st_ctime,
                        "modified_at": st.st_mtime,
                        "is_directory": entry.is_dir(),
                        "parent_path": directory,
                        "mime_type": None,
                        "is_starred": 1 if is_starred(entry.path) else 0,
                        "tags": None,
                    })
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError) as e:
            QMessageBox.warning(self, "Error", f"Cannot read directory: {e}")
            return

        dirs = sorted([f for f in files if f["is_directory"]], key=lambda x: x["name"].lower())
        regular = sorted([f for f in files if not f["is_directory"]], key=lambda x: x["name"].lower())
        files = dirs + regular

        self._file_table.set_files(files, directory)
        total_size = sum(f["size"] for f in files if not f["is_directory"])
        self._status_bar.set_file_info(len(files), total_size)

        folder_paths = [f["path"] for f in files if f["is_directory"]]
        if folder_paths:
            if self._folder_size_thread and self._folder_size_thread.isRunning():
                self._folder_size_thread.cancel()
                self._folder_size_thread.wait(500)
            self._folder_size_thread = FolderSizeThread(folder_paths)
            self._folder_size_thread.size_ready.connect(self._on_folder_size_ready)
            self._folder_size_thread.start()

    def _on_folder_size_ready(self, path: str, size: int):
        self._file_table.update_folder_size(path, size)

    def _on_file_selected(self, path: str):
        self._detail_panel.show_file(path)

    def _on_file_double_clicked(self, path: str):
        if os.path.isdir(path):
            self._navigate_to(path)
        else:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])

    def _on_view_mode_changed(self, mode: str):
        self._file_table.set_view_mode(mode)

    def _on_file_starred(self, path: str, starred: bool):
        self._refresh_current()

    def _refresh_current(self):
        if self._current_dir:
            self._load_directory_files(self._current_dir)

    # --- File Operations ---

    def _do_move(self, paths: list[str], dest: str):
        dialog = ConfirmActionDialog("move", paths, dest, self)
        if dialog.exec():
            errors = []
            for p in paths:
                try:
                    move_file(p, dest)
                except Exception as e:
                    errors.append(f"{p}: {e}")
            if errors:
                QMessageBox.warning(self, "Errors", "\n".join(errors))
            self._refresh_current()

    def _do_copy(self, paths: list[str], dest: str):
        dialog = ConfirmActionDialog("copy", paths, dest, self)
        if dialog.exec():
            errors = []
            for p in paths:
                try:
                    copy_file(p, dest)
                except Exception as e:
                    errors.append(f"{p}: {e}")
            if errors:
                QMessageBox.warning(self, "Errors", "\n".join(errors))
            self._refresh_current()

    def _do_delete(self, paths: list[str]):
        dialog = ConfirmActionDialog("delete", paths, parent=self)
        if dialog.exec():
            errors = []
            for p in paths:
                try:
                    delete_file(p, use_trash=True)
                except Exception as e:
                    errors.append(f"{p}: {e}")
            if errors:
                QMessageBox.warning(self, "Errors", "\n".join(errors))
            self._refresh_current()

    def _do_rename(self, path: str, new_name: str):
        try:
            rename_file(path, new_name)
            self._refresh_current()
        except Exception as e:
            QMessageBox.warning(self, "Rename Error", str(e))

    def _delete_selected(self):
        path = self._file_table.get_selected_path()
        if path:
            self._do_delete([path])

    def _rename_selected(self):
        path = self._file_table.get_selected_path()
        if path:
            name = os.path.basename(path)
            new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=name)
            if ok and new_name and new_name != name:
                self._do_rename(path, new_name)

    def _create_new_folder(self):
        if not self._current_dir:
            return
        dialog = NewFolderDialog(self._current_dir, self)
        if dialog.exec():
            name = dialog.get_folder_name()
            try:
                create_folder(self._current_dir, name)
                self._refresh_current()
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))

    def _undo_operation(self):
        result = undo_last_operation()
        if result:
            self._status_bar.set_message(f"Undone: {result['action']}")
            self._refresh_current()
        else:
            self._status_bar.set_message("Nothing to undo")

    def _show_operation_log(self):
        dialog = OperationLogDialog(self)
        dialog.undo_performed.connect(self._refresh_current)
        dialog.exec()

    # --- Indexing ---

    def _index_current_folder(self):
        if not self._current_dir:
            return
        self._start_indexing(self._current_dir)

    def _index_all_folders(self):
        indexed = get_indexed_directories()
        if not indexed:
            QMessageBox.information(
                self, "Index All",
                "No folders have been indexed yet. Navigate to a folder and click 'Index Folder' first."
            )
            return
        for d in indexed:
            self._start_indexing(d["path"])

    def _start_indexing(self, directory: str):
        if self._scanner_thread and self._scanner_thread.isRunning():
            QMessageBox.information(self, "Indexing", "Already indexing. Please wait.")
            return

        self._toolbar.set_indexing(True)
        self._status_bar.set_indexing(True)

        self._scanner_thread = ScannerThread(directory)
        self._scanner_thread.progress.connect(self._on_scan_progress)
        self._scanner_thread.finished_scanning.connect(self._on_scan_finished)
        self._scanner_thread.error.connect(self._on_scan_error)
        self._scanner_thread.start()

    def _on_scan_progress(self, current, total):
        self._status_bar.set_indexing(True, current)

    def _on_scan_finished(self, directory, file_count):
        self._toolbar.set_indexing(False)
        self._status_bar.set_indexing(False)
        self._status_bar.set_message(f"Indexed {file_count} files in {directory}")

    def _on_scan_error(self, error):
        self._toolbar.set_indexing(False)
        self._status_bar.set_indexing(False)
        QMessageBox.warning(self, "Indexing Error", error)

    # --- NLP ---

    def _check_ollama(self):
        def _check():
            connected, msg = check_ollama_connection()
            self._status_bar.set_ollama_status(connected, msg)
        QTimer.singleShot(1000, _check)

    def _on_nlp_query(self, query: str):
        self._chat_panel.set_loading(True)
        self._status_bar.set_message(f"Processing: {query}")

        self._parser_thread = OllamaParserThread(query)
        self._parser_thread.result_ready.connect(self._on_nlp_result)
        self._parser_thread.error.connect(self._on_nlp_error)
        self._parser_thread.start()

    def _on_nlp_result(self, cmd: ParsedCommand):
        self._chat_panel.set_loading(False)
        if cmd.response:
            self._chat_panel.add_assistant_message(cmd.response)
        self._execute_parsed_command(cmd)

    def _on_nlp_error(self, error: str):
        self._chat_panel.set_loading(False)
        self._chat_panel.add_assistant_message(f"<span style='color:#d32f2f;'>Error: {error}</span>")
        self._status_bar.set_message(f"NLP Error: {error}")

    def _execute_parsed_command(self, cmd: ParsedCommand):
        action = cmd.action
        filters = cmd.filters

        if action == "navigate":
            self._execute_navigate(cmd)
        elif action == "search":
            self._execute_search(filters)
        elif action in ("move", "copy"):
            self._execute_file_action(cmd)
        elif action == "delete":
            self._execute_delete(cmd)
        elif action == "rename":
            self._execute_rename_nlp(cmd)
        elif action == "tag":
            self._execute_tag(cmd)
        elif action in ("star", "unstar"):
            self._execute_star(cmd)
        elif action == "create_folder":
            self._execute_create_folder(cmd)
        else:
            self._status_bar.set_message(f"Unknown action: {action}")

    def _execute_navigate(self, cmd: ParsedCommand):
        target = cmd.target or ""
        if not target:
            self._chat_panel.add_assistant_message("I need a folder path to navigate to.")
            return
        if not os.path.isabs(target):
            target = os.path.join(str(Path.home()), target)
        if os.path.isdir(target):
            self._navigate_to(target)
            if not cmd.response:
                self._chat_panel.add_assistant_message(f"Navigated to <b>{target}</b>")
        else:
            self._chat_panel.add_assistant_message(
                f"Folder not found: <b>{target}</b>. Please check the path."
            )

    def _execute_search(self, filters: dict):
        kwargs = {}

        if "directory" in filters:
            d = filters["directory"]
            if not os.path.isabs(d):
                d = os.path.join(str(Path.home()), d)
            kwargs["directory"] = d

        if "extension" in filters:
            kwargs["extension"] = filters["extension"]

        if "name_pattern" in filters:
            kwargs["name_pattern"] = filters["name_pattern"]

        if "min_size" in filters:
            size = parse_size_string(filters["min_size"])
            if size:
                kwargs["min_size"] = size

        if "max_size" in filters:
            size = parse_size_string(filters["max_size"])
            if size:
                kwargs["max_size"] = size

        if "modified_after" in filters:
            ts = parse_time_string(filters["modified_after"])
            if ts:
                kwargs["modified_after"] = ts

        if "modified_before" in filters:
            ts = parse_time_string(filters["modified_before"])
            if ts:
                kwargs["modified_before"] = ts

        if "is_directory" in filters:
            kwargs["is_directory"] = filters["is_directory"]

        if "starred" in filters:
            kwargs["starred"] = filters["starred"]

        if "sort" in filters:
            kwargs["sort_by"] = filters["sort"]

        if "sort_desc" in filters:
            kwargs["sort_desc"] = filters["sort_desc"]

        if "limit" in filters:
            kwargs["limit"] = int(filters["limit"])

        results = search_files(**kwargs)
        if results:
            self._file_table.set_files(results, "Search Results")
            self._status_bar.set_message(f"Found {len(results)} files")
            self._toolbar.set_path("Search Results", add_to_history=False)
            self._chat_panel.add_assistant_message(f"Found <b>{len(results)}</b> matching files.")
        else:
            self._status_bar.set_message("No files found. Try indexing the folder first.")
            self._chat_panel.add_assistant_message(
                "No files matched your query. Make sure the folder is indexed first "
                "(click <b>Index Folder</b> in the toolbar)."
            )

    def _execute_file_action(self, cmd: ParsedCommand):
        results = search_files(**self._build_search_kwargs(cmd.filters))
        if not results:
            self._chat_panel.add_assistant_message("No matching files found for this operation.")
            return

        paths = [r["path"] for r in results]
        target = cmd.target or ""
        if target and not os.path.isabs(target):
            target = os.path.join(str(Path.home()), target)

        if not target or not os.path.isdir(target):
            from PyQt6.QtWidgets import QFileDialog
            target = QFileDialog.getExistingDirectory(
                self, f"{cmd.action.title()} to...", target
            )
            if not target:
                return

        if cmd.action == "move":
            self._do_move(paths, target)
        else:
            self._do_copy(paths, target)

    def _execute_delete(self, cmd: ParsedCommand):
        results = search_files(**self._build_search_kwargs(cmd.filters))
        if not results:
            self._chat_panel.add_assistant_message("No matching files found to delete.")
            return
        paths = [r["path"] for r in results]
        self._do_delete(paths)

    def _execute_rename_nlp(self, cmd: ParsedCommand):
        results = search_files(**self._build_search_kwargs(cmd.filters))
        if not results:
            self._chat_panel.add_assistant_message("No matching files found to rename.")
            return
        if len(results) > 1:
            self._chat_panel.add_assistant_message("Multiple files matched. Rename works on a single file — please be more specific.")
            return
        new_name = cmd.target
        if not new_name:
            new_name, ok = QInputDialog.getText(self, "Rename", "New name:")
            if not ok or not new_name:
                return
        self._do_rename(results[0]["path"], new_name)

    def _execute_tag(self, cmd: ParsedCommand):
        results = search_files(**self._build_search_kwargs(cmd.filters))
        if not results:
            self._chat_panel.add_assistant_message("No matching files found to tag.")
            return
        tag = cmd.tag
        if not tag:
            tag, ok = QInputDialog.getText(self, "Tag", "Tag name:")
            if not ok or not tag:
                return
        from app.core.tag_manager import bulk_tag
        count = bulk_tag([r["path"] for r in results], tag)
        self._chat_panel.add_assistant_message(f"Tagged <b>{count}</b> files as <b>{tag}</b>.")
        self._status_bar.set_message(f"Tagged {count} files as '{tag}'")
        self._refresh_current()

    def _execute_star(self, cmd: ParsedCommand):
        results = search_files(**self._build_search_kwargs(cmd.filters))
        if not results:
            self._chat_panel.add_assistant_message("No matching files found to star.")
            return
        from app.core.tag_manager import bulk_star
        count = bulk_star([r["path"] for r in results])
        self._chat_panel.add_assistant_message(f"Starred <b>{count}</b> files.")
        self._status_bar.set_message(f"Starred {count} files")
        self._refresh_current()

    def _execute_create_folder(self, cmd: ParsedCommand):
        target = cmd.target or self._current_dir
        if target and not os.path.isabs(target):
            target = os.path.join(str(Path.home()), target)
        name = cmd.filters.get("name_pattern", "")
        if not name:
            name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
            if not ok or not name:
                return
        try:
            create_folder(target, name)
            self._status_bar.set_message(f"Created folder '{name}' in {target}")
            if target == self._current_dir:
                self._refresh_current()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def _build_search_kwargs(self, filters: dict) -> dict:
        kwargs = {}
        if "directory" in filters:
            d = filters["directory"]
            if not os.path.isabs(d):
                d = os.path.join(str(Path.home()), d)
            kwargs["directory"] = d
        if "extension" in filters:
            kwargs["extension"] = filters["extension"]
        if "name_pattern" in filters:
            kwargs["name_pattern"] = filters["name_pattern"]
        if "min_size" in filters:
            s = parse_size_string(filters["min_size"])
            if s:
                kwargs["min_size"] = s
        if "max_size" in filters:
            s = parse_size_string(filters["max_size"])
            if s:
                kwargs["max_size"] = s
        if "modified_after" in filters:
            t = parse_time_string(filters["modified_after"])
            if t:
                kwargs["modified_after"] = t
        if "modified_before" in filters:
            t = parse_time_string(filters["modified_before"])
            if t:
                kwargs["modified_before"] = t
        if "starred" in filters:
            kwargs["starred"] = filters["starred"]
        return kwargs

    # --- Starred ---

    def _show_starred(self):
        starred_paths = get_starred_files()
        if not starred_paths:
            QMessageBox.information(self, "Starred Files", "No starred files yet.")
            return

        files = []
        for path in starred_paths:
            if os.path.exists(path):
                try:
                    st = os.stat(path)
                    is_dir = os.path.isdir(path)
                    files.append({
                        "path": path,
                        "name": os.path.basename(path),
                        "extension": Path(path).suffix.lower() if not is_dir else None,
                        "size": st.st_size if not is_dir else 0,
                        "created_at": st.st_ctime,
                        "modified_at": st.st_mtime,
                        "is_directory": is_dir,
                        "parent_path": os.path.dirname(path),
                        "mime_type": None,
                        "is_starred": 1,
                        "tags": None,
                    })
                except (OSError, PermissionError):
                    continue

        self._file_table.set_files(files, "Starred")
        self._toolbar.set_path("Starred Files", add_to_history=False)
        self._status_bar.set_message(f"{len(files)} starred files")

    # --- Disk Cleanup ---

    def _open_disk_cleanup(self):
        dialog = DiskCleanupDialog(self._current_dir, self)
        dialog.files_deleted.connect(self._refresh_current)
        dialog.exec()

    # --- Updates ---

    def _check_for_updates(self, silent: bool = True):
        self._update_check_silent = silent
        self._update_thread = UpdateCheckThread()
        self._update_thread.update_available.connect(self._on_update_available)
        self._update_thread.no_update.connect(self._on_no_update)
        self._update_thread.error.connect(self._on_update_error)
        self._update_thread.start()

    def _on_update_available(self, version: str, download_url: str, release_notes: str):
        from app.ui.dialogs.update_dialog import UpdateDialog
        dialog = UpdateDialog(version, download_url, release_notes, self)
        dialog.exec()

    def _on_no_update(self):
        if not self._update_check_silent:
            QMessageBox.information(self, "Updates", f"You're running the latest version (v{APP_VERSION}).")

    def _on_update_error(self, error: str):
        if not self._update_check_silent:
            QMessageBox.warning(self, "Update Error", f"Could not check for updates:\n{error}")

    def _show_about(self):
        QMessageBox.about(
            self, "About File Organiser",
            f"<h3>File Organiser v{APP_VERSION}</h3>"
            "<p>A desktop file manager with NLP-powered search and AI chat.</p>"
            "<p>Built with PyQt6 + Ollama.</p>"
        )

    # --- Settings ---

    def _open_settings(self):
        indexed = get_indexed_directories()
        current = {
            "indexed_dirs": [d["path"] for d in indexed],
        }
        dialog = SettingsDialog(current, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self, settings: dict):
        import app.config as config
        if settings.get("ollama_host"):
            config.OLLAMA_HOST = settings["ollama_host"]
        if settings.get("ollama_model"):
            config.OLLAMA_MODEL = settings["ollama_model"]
        self._check_ollama()
        self._status_bar.set_message("Settings saved")
