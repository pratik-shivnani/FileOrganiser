import os
import time
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QTextEdit, QSplitter, QFrame,
    QComboBox, QGroupBox, QCheckBox, QWidget, QTabWidget,
)

from app.config import format_file_size
from app.core.disk_analyzer import DiskScanThread, DuplicateScanThread, CleanupSuggestionThread
from app.core.operations import delete_file


class DiskCleanupDialog(QDialog):
    files_deleted = pyqtSignal()

    def __init__(self, initial_dir: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disk Cleanup & Large File Finder")
        self.setMinimumWidth(900)
        self.setMinimumHeight(650)
        self._scan_thread = None
        self._dup_thread = None
        self._ai_thread = None
        self._files = []
        self._duplicates = {}
        self._initial_dir = initial_dir or str(Path.home())
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # --- Directory picker ---
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Scan directory:"))
        self._dir_label = QLabel(self._initial_dir)
        self._dir_label.setStyleSheet("font-weight: bold;")
        dir_layout.addWidget(self._dir_label, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        dir_layout.addWidget(browse_btn)

        self._scan_btn = QPushButton("Scan")
        self._scan_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: white;
                border: none; border-radius: 4px; padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:disabled { background: #90CAF9; }
        """)
        self._scan_btn.clicked.connect(self._start_scan)
        dir_layout.addWidget(self._scan_btn)

        layout.addLayout(dir_layout)

        # --- Progress ---
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumHeight(16)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("Click 'Scan' to find large files.")
        self._status_label.setStyleSheet("color: #666;")
        layout.addWidget(self._status_label)

        # --- Tabs ---
        self._tabs = QTabWidget()

        # Tab 1: Large Files
        large_files_widget = QWidget()
        lf_layout = QVBoxLayout(large_files_widget)
        lf_layout.setContentsMargins(0, 4, 0, 0)

        # Summary bar
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("font-size: 13px; padding: 4px;")
        lf_layout.addWidget(self._summary_label)

        # Extension filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by type:"))
        self._ext_filter = QComboBox()
        self._ext_filter.addItem("All types")
        self._ext_filter.currentTextChanged.connect(self._apply_filter)
        self._ext_filter.setMinimumWidth(120)
        filter_layout.addWidget(self._ext_filter)
        filter_layout.addStretch()

        self._select_all_cb = QCheckBox("Select all visible")
        self._select_all_cb.stateChanged.connect(self._toggle_select_all)
        filter_layout.addWidget(self._select_all_cb)

        lf_layout.addLayout(filter_layout)

        # File tree
        self._file_tree = QTreeWidget()
        self._file_tree.setHeaderLabels(["", "Name", "Size", "Type", "Location", "Modified"])
        self._file_tree.setRootIsDecorated(False)
        self._file_tree.setAlternatingRowColors(True)
        self._file_tree.setSortingEnabled(True)
        header = self._file_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._file_tree.setColumnWidth(0, 30)
        lf_layout.addWidget(self._file_tree)

        # Action buttons
        action_layout = QHBoxLayout()
        self._selected_size_label = QLabel("")
        action_layout.addWidget(self._selected_size_label)
        action_layout.addStretch()

        open_loc_btn = QPushButton("Open Location")
        open_loc_btn.clicked.connect(self._open_selected_location)
        action_layout.addWidget(open_loc_btn)

        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setStyleSheet("""
            QPushButton {
                background: #d32f2f; color: white;
                border: none; border-radius: 4px; padding: 6px 16px;
            }
            QPushButton:hover { background: #b71c1c; }
            QPushButton:disabled { background: #ef9a9a; }
        """)
        self._delete_btn.clicked.connect(self._delete_selected)
        self._delete_btn.setEnabled(False)
        action_layout.addWidget(self._delete_btn)

        lf_layout.addLayout(action_layout)
        self._tabs.addTab(large_files_widget, "Large Files")

        # Tab 2: Duplicates
        dup_widget = QWidget()
        dup_layout = QVBoxLayout(dup_widget)
        dup_layout.setContentsMargins(0, 4, 0, 0)

        self._dup_tree = QTreeWidget()
        self._dup_tree.setHeaderLabels(["", "Name", "Size", "Location"])
        self._dup_tree.setAlternatingRowColors(True)
        dup_header = self._dup_tree.header()
        dup_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        dup_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        dup_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        dup_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._dup_tree.setColumnWidth(0, 30)
        dup_layout.addWidget(self._dup_tree)

        dup_action_layout = QHBoxLayout()
        dup_action_layout.addStretch()
        self._delete_dup_btn = QPushButton("Delete Selected Duplicates")
        self._delete_dup_btn.setStyleSheet("""
            QPushButton {
                background: #d32f2f; color: white;
                border: none; border-radius: 4px; padding: 6px 16px;
            }
            QPushButton:hover { background: #b71c1c; }
            QPushButton:disabled { background: #ef9a9a; }
        """)
        self._delete_dup_btn.clicked.connect(self._delete_selected_duplicates)
        self._delete_dup_btn.setEnabled(False)
        dup_action_layout.addWidget(self._delete_dup_btn)
        dup_layout.addLayout(dup_action_layout)

        self._tabs.addTab(dup_widget, "Potential Duplicates")

        # Tab 3: AI Suggestions
        ai_widget = QWidget()
        ai_layout = QVBoxLayout(ai_widget)
        ai_layout.setContentsMargins(0, 4, 0, 0)

        ai_header_layout = QHBoxLayout()
        ai_header_layout.addWidget(QLabel("Get AI-powered cleanup suggestions from your Ollama model:"))
        ai_header_layout.addStretch()
        self._ai_btn = QPushButton("Ask AI for Suggestions")
        self._ai_btn.setStyleSheet("""
            QPushButton {
                background: #7C4DFF; color: white;
                border: none; border-radius: 4px; padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background: #651FFF; }
            QPushButton:disabled { background: #B39DDB; }
        """)
        self._ai_btn.clicked.connect(self._ask_ai)
        self._ai_btn.setEnabled(False)
        ai_header_layout.addWidget(self._ai_btn)
        ai_layout.addLayout(ai_header_layout)

        self._ai_output = QTextEdit()
        self._ai_output.setReadOnly(True)
        self._ai_output.setPlaceholderText(
            "Scan a directory first, then click 'Ask AI for Suggestions' to get cleanup advice.\n\n"
            "The AI will analyze your largest files and recommend:\n"
            "- Safe files to delete (temp, cache, old downloads)\n"
            "- Files to keep or back up\n"
            "- Space-saving strategies"
        )
        ai_layout.addWidget(self._ai_output)
        self._tabs.addTab(ai_widget, "AI Suggestions")

        layout.addWidget(self._tabs)

        # File tree checkbox change tracking
        self._file_tree.itemChanged.connect(self._on_item_checked)
        self._dup_tree.itemChanged.connect(self._on_dup_item_checked)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Directory to Scan", self._initial_dir)
        if d:
            self._initial_dir = d
            self._dir_label.setText(d)

    def _start_scan(self):
        directory = self._dir_label.text()
        if not os.path.isdir(directory):
            QMessageBox.warning(self, "Error", "Invalid directory.")
            return

        self._scan_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)
        self._status_label.setText("Scanning for large files...")
        self._file_tree.clear()
        self._dup_tree.clear()
        self._files = []
        self._duplicates = {}

        self._scan_thread = DiskScanThread(directory, top_n=200)
        self._scan_thread.progress.connect(self._on_scan_progress)
        self._scan_thread.result_ready.connect(self._on_scan_done)
        self._scan_thread.error.connect(self._on_scan_error)
        self._scan_thread.start()

        self._dup_thread = DuplicateScanThread(directory)
        self._dup_thread.result_ready.connect(self._on_dup_done)
        self._dup_thread.error.connect(self._on_scan_error)
        self._dup_thread.start()

    def _on_scan_progress(self, count: int):
        self._status_label.setText(f"Scanning... {count} files checked")

    def _on_scan_done(self, files: list):
        self._files = files
        self._progress_bar.setVisible(False)
        self._scan_btn.setEnabled(True)

        if not files:
            self._status_label.setText("No files found.")
            return

        total_size = sum(f["size"] for f in files)
        self._status_label.setText(
            f"Found {len(files)} largest files — total: {format_file_size(total_size)}"
        )

        # Populate extension filter
        exts = sorted(set(f.get("extension", "") for f in files if f.get("extension")))
        self._ext_filter.clear()
        self._ext_filter.addItem("All types")
        for ext in exts:
            self._ext_filter.addItem(ext)

        self._populate_file_tree(files)
        self._update_summary(files)
        self._ai_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)

    def _on_dup_done(self, duplicates: dict):
        self._duplicates = duplicates
        if not duplicates:
            return

        self._dup_tree.clear()
        group_count = 0
        for key, paths in sorted(duplicates.items(), key=lambda x: -len(x[1])):
            if len(paths) < 2:
                continue
            group_count += 1
            try:
                size = os.path.getsize(paths[0])
            except OSError:
                size = 0

            group_item = QTreeWidgetItem(self._dup_tree)
            group_item.setText(1, f"Group {group_count} ({len(paths)} files)")
            group_item.setText(2, format_file_size(size))
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

            for p in paths:
                child = QTreeWidgetItem(group_item)
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
                child.setText(1, os.path.basename(p))
                child.setText(2, format_file_size(size))
                child.setText(3, os.path.dirname(p))
                child.setData(0, Qt.ItemDataRole.UserRole, p)

        self._dup_tree.expandAll()
        dup_tab_idx = self._tabs.indexOf(self._tabs.widget(1))
        self._tabs.setTabText(dup_tab_idx, f"Potential Duplicates ({group_count})")
        self._delete_dup_btn.setEnabled(group_count > 0)

    def _on_scan_error(self, error: str):
        self._progress_bar.setVisible(False)
        self._scan_btn.setEnabled(True)
        self._status_label.setText(f"Error: {error}")
        QMessageBox.warning(self, "Scan Error", error)

    def _populate_file_tree(self, files: list):
        self._file_tree.clear()
        self._file_tree.setSortingEnabled(False)

        for f in files:
            item = QTreeWidgetItem()
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setText(1, f["name"])
            item.setText(2, format_file_size(f["size"]))
            item.setData(2, Qt.ItemDataRole.UserRole, f["size"])
            item.setText(3, f.get("extension", ""))
            item.setText(4, f.get("parent", ""))
            mod_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(f.get("modified_at", 0)))
            item.setText(5, mod_time)
            item.setData(0, Qt.ItemDataRole.UserRole, f["path"])
            self._file_tree.addTopLevelItem(item)

        self._file_tree.setSortingEnabled(True)
        self._file_tree.sortByColumn(2, Qt.SortOrder.DescendingOrder)

    def _update_summary(self, files: list):
        if not files:
            self._summary_label.setText("")
            return

        total = sum(f["size"] for f in files)
        ext_sizes = {}
        for f in files:
            ext = f.get("extension", "") or "(no ext)"
            ext_sizes[ext] = ext_sizes.get(ext, 0) + f["size"]
        top_exts = sorted(ext_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
        ext_summary = " | ".join(f"{ext}: {format_file_size(s)}" for ext, s in top_exts)
        self._summary_label.setText(
            f"<b>Total: {format_file_size(total)}</b> — Top types: {ext_summary}"
        )

    def _apply_filter(self, ext_filter: str):
        if ext_filter == "All types" or not ext_filter:
            filtered = self._files
        else:
            filtered = [f for f in self._files if f.get("extension", "") == ext_filter]
        self._populate_file_tree(filtered)
        self._update_summary(filtered)

    def _toggle_select_all(self, state: int):
        check = Qt.CheckState.Checked if state == Qt.CheckState.Checked.value else Qt.CheckState.Unchecked
        for i in range(self._file_tree.topLevelItemCount()):
            self._file_tree.topLevelItem(i).setCheckState(0, check)

    def _on_item_checked(self, item, column):
        self._update_selected_size()

    def _on_dup_item_checked(self, item, column):
        pass

    def _update_selected_size(self):
        total = 0
        count = 0
        for i in range(self._file_tree.topLevelItemCount()):
            item = self._file_tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                size = item.data(2, Qt.ItemDataRole.UserRole)
                if size:
                    total += size
                    count += 1
        if count > 0:
            self._selected_size_label.setText(
                f"<b>{count} selected — {format_file_size(total)} to free</b>"
            )
        else:
            self._selected_size_label.setText("")

    def _get_checked_paths(self, tree: QTreeWidget) -> list[str]:
        paths = []
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            path = item.data(0, Qt.ItemDataRole.UserRole)
            if item.checkState(0) == Qt.CheckState.Checked and path:
                paths.append(path)
            # Check children (for duplicate groups)
            for j in range(item.childCount()):
                child = item.child(j)
                child_path = child.data(0, Qt.ItemDataRole.UserRole)
                if child.checkState(0) == Qt.CheckState.Checked and child_path:
                    paths.append(child_path)
        return paths

    def _delete_selected(self):
        paths = self._get_checked_paths(self._file_tree)
        if not paths:
            QMessageBox.information(self, "Delete", "No files selected.")
            return

        total_size = 0
        for p in paths:
            try:
                total_size += os.path.getsize(p)
            except OSError:
                pass

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(paths)} file(s) ({format_file_size(total_size)}) to recycle bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        errors = []
        deleted = 0
        for p in paths:
            try:
                delete_file(p, use_trash=True)
                deleted += 1
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")

        if errors:
            QMessageBox.warning(self, "Errors", f"Deleted {deleted}, errors:\n" + "\n".join(errors[:10]))
        else:
            QMessageBox.information(self, "Done", f"Deleted {deleted} files ({format_file_size(total_size)})")

        self._start_scan()
        self.files_deleted.emit()

    def _delete_selected_duplicates(self):
        paths = self._get_checked_paths(self._dup_tree)
        if not paths:
            QMessageBox.information(self, "Delete", "No duplicates selected.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(paths)} duplicate file(s) to recycle bin?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        errors = []
        deleted = 0
        for p in paths:
            try:
                delete_file(p, use_trash=True)
                deleted += 1
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")

        if errors:
            QMessageBox.warning(self, "Errors", f"Deleted {deleted}, errors:\n" + "\n".join(errors[:10]))
        else:
            QMessageBox.information(self, "Done", f"Deleted {deleted} duplicate files.")

        self._start_scan()
        self.files_deleted.emit()

    def _open_selected_location(self):
        item = self._file_tree.currentItem()
        if not item:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            import sys
            import subprocess
            parent = os.path.dirname(path)
            if sys.platform == "win32":
                subprocess.Popen(["explorer", "/select,", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", parent])

    def _ask_ai(self):
        if not self._files:
            QMessageBox.information(self, "AI", "Scan a directory first.")
            return

        self._ai_btn.setEnabled(False)
        self._ai_output.setPlainText("Analyzing files with AI...\nThis may take a moment.")

        self._ai_thread = CleanupSuggestionThread(self._files)
        self._ai_thread.result_ready.connect(self._on_ai_result)
        self._ai_thread.error.connect(self._on_ai_error)
        self._ai_thread.start()

    def _on_ai_result(self, text: str):
        self._ai_btn.setEnabled(True)
        self._ai_output.setMarkdown(text)

    def _on_ai_error(self, error: str):
        self._ai_btn.setEnabled(True)
        self._ai_output.setPlainText(f"Error: {error}")

    def closeEvent(self, event):
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.cancel()
            self._scan_thread.wait(2000)
        if self._dup_thread and self._dup_thread.isRunning():
            self._dup_thread.cancel()
            self._dup_thread.wait(2000)
        super().closeEvent(event)
