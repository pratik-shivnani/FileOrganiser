from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame, QMessageBox,
)

from app.config import APP_VERSION
from app.core.updater import (
    UpdateCheckThread, DownloadUpdateThread, apply_update, is_frozen,
)


class UpdateDialog(QDialog):
    def __init__(self, version: str = "", download_url: str = "", release_notes: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Software Update")
        self.setMinimumWidth(480)
        self.setMinimumHeight(320)
        self._version = version
        self._download_url = download_url
        self._release_notes = release_notes
        self._download_thread = None
        self._downloaded_path = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel(f"<h3>Update Available: v{self._version}</h3>")
        layout.addWidget(header)

        current_label = QLabel(f"Current version: <b>v{APP_VERSION}</b>")
        layout.addWidget(current_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        if self._release_notes:
            notes_label = QLabel("Release notes:")
            layout.addWidget(notes_label)
            notes = QTextEdit()
            notes.setReadOnly(True)
            notes.setMarkdown(self._release_notes)
            notes.setMaximumHeight(150)
            layout.addWidget(notes)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #666;")
        layout.addWidget(self._status_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self._skip_btn = QPushButton("Skip")
        self._skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._skip_btn)

        self._download_btn = QPushButton("Download && Install")
        self._download_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: white;
                border: none; border-radius: 4px; padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:disabled { background: #90CAF9; }
        """)
        self._download_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(self._download_btn)

        layout.addLayout(btn_layout)

    def _start_download(self):
        self._download_btn.setEnabled(False)
        self._skip_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 100)
        self._status_label.setText("Downloading...")

        self._download_thread = DownloadUpdateThread(self._download_url)
        self._download_thread.progress.connect(self._on_progress)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.error.connect(self._on_download_error)
        self._download_thread.start()

    def _on_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self._progress_bar.setValue(pct)
            self._status_label.setText(
                f"Downloading... {downloaded // 1048576} MB / {total // 1048576} MB"
            )
        else:
            self._progress_bar.setRange(0, 0)
            self._status_label.setText(f"Downloading... {downloaded // 1048576} MB")

    def _on_download_finished(self, path: str):
        self._downloaded_path = path
        self._progress_bar.setValue(100)

        if is_frozen():
            self._status_label.setText("Download complete. Restarting to apply update...")
            apply_update(path)
        else:
            self._status_label.setText(
                f"Download complete: {path}\n"
                "Running from source — update downloaded but cannot auto-apply.\n"
                "Replace the exe manually or run from the new exe."
            )
            self._skip_btn.setEnabled(True)
            self._skip_btn.setText("Close")

    def _on_download_error(self, error: str):
        self._progress_bar.setVisible(False)
        self._status_label.setText(f"Download failed: {error}")
        self._status_label.setStyleSheet("color: #d32f2f;")
        self._download_btn.setEnabled(True)
        self._skip_btn.setEnabled(True)
