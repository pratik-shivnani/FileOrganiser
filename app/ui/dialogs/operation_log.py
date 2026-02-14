import json
from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
)

from app.core.operations import get_operation_history, undo_last_operation


class OperationLogDialog(QDialog):
    undo_performed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Operation History")
        self.setMinimumWidth(700)
        self.setMinimumHeight(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<b>Recent File Operations</b>"))

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Action", "Source", "Destination", "Time", "Undone"
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._load_history()

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        btn_layout = QHBoxLayout()

        undo_btn = QPushButton("Undo Last Operation")
        undo_btn.setStyleSheet("""
            QPushButton {
                background: #ff9800; color: white;
                border: none; border-radius: 4px; padding: 6px 16px;
            }
            QPushButton:hover { background: #f57c00; }
        """)
        undo_btn.clicked.connect(self._undo_last)
        btn_layout.addWidget(undo_btn)

        btn_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_history)
        btn_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _load_history(self):
        history = get_operation_history(100)
        self._table.setRowCount(len(history))

        for row, entry in enumerate(history):
            self._table.setItem(row, 0, QTableWidgetItem(entry["action"]))
            self._table.setItem(row, 1, QTableWidgetItem(entry.get("source_path", "") or ""))
            self._table.setItem(row, 2, QTableWidgetItem(entry.get("dest_path", "") or ""))

            ts = entry.get("performed_at", 0)
            if ts:
                time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = ""
            self._table.setItem(row, 3, QTableWidgetItem(time_str))

            undone = "Yes" if entry.get("undone") else "No"
            self._table.setItem(row, 4, QTableWidgetItem(undone))

    def _undo_last(self):
        result = undo_last_operation()
        if result:
            self._load_history()
            self.undo_performed.emit()
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Undo", "Nothing to undo or operation cannot be reversed.")
