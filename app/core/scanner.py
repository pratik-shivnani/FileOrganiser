import mimetypes
import os
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import DEFAULT_EXCLUDED_DIRS, DEFAULT_EXCLUDED_EXTENSIONS
from app.db.database import get_connection


class ScannerThread(QThread):
    progress = pyqtSignal(int, int)  # current, total
    finished_scanning = pyqtSignal(str, int)  # directory, file_count
    error = pyqtSignal(str)

    def __init__(self, directory: str, parent=None):
        super().__init__(parent)
        self.directory = directory
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            file_count = self._scan_directory(self.directory)
            if not self._cancelled:
                self._update_indexed_dir(self.directory, file_count)
                self.finished_scanning.emit(self.directory, file_count)
        except Exception as e:
            self.error.emit(str(e))

    def _scan_directory(self, root_dir: str) -> int:
        conn = get_connection()
        cursor = conn.cursor()

        entries_to_insert = []
        file_count = 0

        for dirpath, dirnames, filenames in os.walk(root_dir):
            if self._cancelled:
                break

            dirnames[:] = [
                d for d in dirnames
                if d not in DEFAULT_EXCLUDED_DIRS and not d.startswith(".")
            ]

            for name in dirnames:
                if self._cancelled:
                    break
                full_path = os.path.join(dirpath, name)
                try:
                    st = os.stat(full_path)
                    entries_to_insert.append((
                        full_path, name, None, 0,
                        st.st_ctime, st.st_mtime,
                        True, dirpath, None, time.time()
                    ))
                except (OSError, PermissionError):
                    continue

            for name in filenames:
                if self._cancelled:
                    break
                full_path = os.path.join(dirpath, name)
                ext = Path(name).suffix.lower()

                if ext in DEFAULT_EXCLUDED_EXTENSIONS:
                    continue

                try:
                    st = os.stat(full_path)
                    mime, _ = mimetypes.guess_type(full_path)
                    entries_to_insert.append((
                        full_path, name, ext, st.st_size,
                        st.st_ctime, st.st_mtime,
                        False, dirpath, mime, time.time()
                    ))
                    file_count += 1
                except (OSError, PermissionError):
                    continue

            if len(entries_to_insert) >= 500:
                self._batch_insert(cursor, entries_to_insert)
                conn.commit()
                self.progress.emit(file_count, 0)
                entries_to_insert.clear()

        if entries_to_insert and not self._cancelled:
            self._batch_insert(cursor, entries_to_insert)
            conn.commit()

        return file_count

    def _batch_insert(self, cursor, entries):
        cursor.executemany("""
            INSERT OR REPLACE INTO file_index
            (path, name, extension, size, created_at, modified_at,
             is_directory, parent_path, mime_type, indexed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, entries)

    def _update_indexed_dir(self, directory: str, file_count: int):
        conn = get_connection()
        conn.execute("""
            INSERT OR REPLACE INTO indexed_dirs (path, last_indexed, file_count)
            VALUES (?, ?, ?)
        """, (directory, time.time(), file_count))
        conn.commit()


def is_directory_indexed(directory: str) -> Optional[float]:
    conn = get_connection()
    row = conn.execute(
        "SELECT last_indexed FROM indexed_dirs WHERE path = ?",
        (directory,)
    ).fetchone()
    return row["last_indexed"] if row else None


def get_indexed_directories() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT path, last_indexed, file_count FROM indexed_dirs ORDER BY path"
    ).fetchall()
    return [dict(row) for row in rows]
