import os
import sys
from pathlib import Path


APP_NAME = "File Organiser"
APP_VERSION = "1.0.0"

if sys.platform == "win32":
    APP_DATA_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
else:
    APP_DATA_DIR = Path.home() / ".file_organiser"

DB_PATH = APP_DATA_DIR / "file_organiser.db"

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"

DEFAULT_EXCLUDED_DIRS = {
    "$Recycle.Bin",
    "System Volume Information",
    "Windows",
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
}

DEFAULT_EXCLUDED_EXTENSIONS = {
    ".sys",
    ".dll",
    ".tmp",
}

WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 600
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 800

TREE_PANEL_WIDTH = 250
DETAIL_PANEL_WIDTH = 300

FILE_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]


def ensure_app_data_dir():
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def format_file_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(FILE_SIZE_UNITS) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {FILE_SIZE_UNITS[unit_index]}"
