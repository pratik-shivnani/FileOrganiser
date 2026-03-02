import os

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import DEFAULT_EXCLUDED_DIRS


class FolderSizeThread(QThread):
    size_ready = pyqtSignal(str, int)  # path, size
    all_done = pyqtSignal()

    def __init__(self, folders: list[str], parent=None):
        super().__init__(parent)
        self._folders = folders
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        for folder_path in self._folders:
            if self._cancelled:
                return
            size = self._calc_size(folder_path)
            if not self._cancelled:
                self.size_ready.emit(folder_path, size)
        if not self._cancelled:
            self.all_done.emit()

    def _calc_size(self, dirpath: str) -> int:
        total = 0
        try:
            for entry in os.scandir(dirpath):
                if self._cancelled:
                    return total
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False):
                        if entry.name not in DEFAULT_EXCLUDED_DIRS:
                            total += self._calc_size(entry.path)
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            pass
        return total
