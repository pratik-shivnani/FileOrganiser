import os
import json
import re
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import (
    DEFAULT_EXCLUDED_DIRS, DEFAULT_EXCLUDED_EXTENSIONS,
    OLLAMA_HOST, OLLAMA_MODEL, format_file_size,
)


class DiskScanThread(QThread):
    progress = pyqtSignal(int)  # files scanned count
    result_ready = pyqtSignal(list)  # list of {path, size, modified_at, extension}
    error = pyqtSignal(str)

    def __init__(self, directory: str, top_n: int = 200, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.top_n = top_n
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            files = []
            scanned = 0

            for dirpath, dirnames, filenames in os.walk(self.directory):
                if self._cancelled:
                    return

                dirnames[:] = [
                    d for d in dirnames
                    if d not in DEFAULT_EXCLUDED_DIRS and not d.startswith(".")
                ]

                for fname in filenames:
                    if self._cancelled:
                        return
                    fpath = os.path.join(dirpath, fname)
                    try:
                        st = os.stat(fpath)
                        ext = Path(fname).suffix.lower()
                        if ext in DEFAULT_EXCLUDED_EXTENSIONS:
                            continue
                        files.append({
                            "path": fpath,
                            "name": fname,
                            "size": st.st_size,
                            "modified_at": st.st_mtime,
                            "extension": ext,
                            "parent": dirpath,
                        })
                    except (OSError, PermissionError):
                        continue

                    scanned += 1
                    if scanned % 500 == 0:
                        self.progress.emit(scanned)

            files.sort(key=lambda x: x["size"], reverse=True)
            self.result_ready.emit(files[:self.top_n])
        except Exception as e:
            self.error.emit(str(e))


class DuplicateScanThread(QThread):
    progress = pyqtSignal(int)
    result_ready = pyqtSignal(dict)  # {size: [list of paths]}
    error = pyqtSignal(str)

    def __init__(self, directory: str, min_size: int = 1048576, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.min_size = min_size
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            size_map = {}
            scanned = 0

            for dirpath, dirnames, filenames in os.walk(self.directory):
                if self._cancelled:
                    return

                dirnames[:] = [
                    d for d in dirnames
                    if d not in DEFAULT_EXCLUDED_DIRS and not d.startswith(".")
                ]

                for fname in filenames:
                    if self._cancelled:
                        return
                    fpath = os.path.join(dirpath, fname)
                    try:
                        st = os.stat(fpath)
                        if st.st_size >= self.min_size:
                            key = (st.st_size, Path(fname).suffix.lower())
                            if key not in size_map:
                                size_map[key] = []
                            size_map[key].append(fpath)
                    except (OSError, PermissionError):
                        continue

                    scanned += 1
                    if scanned % 500 == 0:
                        self.progress.emit(scanned)

            duplicates = {
                f"{k[0]}_{k[1]}": paths
                for k, paths in size_map.items()
                if len(paths) > 1
            }
            self.result_ready.emit(duplicates)
        except Exception as e:
            self.error.emit(str(e))


class CleanupSuggestionThread(QThread):
    result_ready = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, file_list: list[dict], parent=None):
        super().__init__(parent)
        self.file_list = file_list

    def run(self):
        try:
            import ollama

            summary_lines = []
            total_size = 0
            ext_sizes = {}
            dir_sizes = {}

            for f in self.file_list[:50]:
                size_str = format_file_size(f["size"])
                summary_lines.append(f"- {f['name']} ({size_str}) in {f['parent']}")
                total_size += f["size"]

                ext = f.get("extension", "")
                ext_sizes[ext] = ext_sizes.get(ext, 0) + f["size"]

                parent = f.get("parent", "")
                dir_sizes[parent] = dir_sizes.get(parent, 0) + f["size"]

            top_exts = sorted(ext_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
            top_dirs = sorted(dir_sizes.items(), key=lambda x: x[1], reverse=True)[:5]

            prompt = f"""You are a helpful disk cleanup assistant. Analyze these largest files and give practical cleanup advice.

Total size of top files: {format_file_size(total_size)}

Top file types by size:
{chr(10).join(f"  {ext or '(no ext)'}: {format_file_size(s)}" for ext, s in top_exts)}

Top directories by size:
{chr(10).join(f"  {d}: {format_file_size(s)}" for d, s in top_dirs)}

Largest files:
{chr(10).join(summary_lines[:30])}

Please provide:
1. A brief summary of what's taking up the most space
2. Specific files/types that are safe to delete (temp files, caches, old downloads, etc.)
3. Files that should be kept or backed up
4. Actionable cleanup recommendations

Keep it concise and practical. Use markdown formatting."""

            client = ollama.Client(host=OLLAMA_HOST)
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": "You are a disk cleanup assistant. Give concise, practical advice about which files to delete to free up space. Be specific about file types and directories."},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.3},
            )

            self.result_ready.emit(response["message"]["content"])

        except ImportError:
            self.error.emit("Ollama package not installed. Run: pip install ollama")
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                self.error.emit("Cannot connect to Ollama. Make sure 'ollama serve' is running.")
            else:
                self.error.emit(f"AI Error: {error_msg}")
