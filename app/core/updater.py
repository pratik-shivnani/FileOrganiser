import json
import os
import sys
import tempfile
import subprocess
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.config import APP_VERSION

GITHUB_REPO = "pratik-shivnani/FileOrganiser"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ASSET_NAME = "FileOrganiser.exe"


def is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def get_current_exe_path() -> str:
    if is_frozen():
        return sys.executable
    return ""


def parse_version(version_str: str) -> tuple:
    clean = version_str.lstrip("v").strip()
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer_version(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


class UpdateCheckThread(QThread):
    update_available = pyqtSignal(str, str, str)  # version, download_url, release_notes
    no_update = pyqtSignal()
    error = pyqtSignal(str)

    def run(self):
        try:
            import urllib.request
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "FileOrganiser"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            tag = data.get("tag_name", "")
            remote_version = tag.lstrip("v")
            body = data.get("body", "")

            download_url = ""
            for asset in data.get("assets", []):
                if asset.get("name", "") == ASSET_NAME:
                    download_url = asset.get("browser_download_url", "")
                    break

            if not download_url:
                self.no_update.emit()
                return

            if is_newer_version(remote_version, APP_VERSION):
                self.update_available.emit(remote_version, download_url, body)
            else:
                self.no_update.emit()

        except Exception as e:
            self.error.emit(str(e))


class DownloadUpdateThread(QThread):
    progress = pyqtSignal(int, int)  # downloaded, total
    finished = pyqtSignal(str)  # path to downloaded file
    error = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            import urllib.request
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "FileOrganiser"}
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=".exe", prefix="FileOrganiser_update_"
                )
                downloaded = 0
                chunk_size = 65536
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    downloaded += len(chunk)
                    self.progress.emit(downloaded, total)
                tmp.close()
                self.finished.emit(tmp.name)

        except Exception as e:
            self.error.emit(str(e))


def apply_update(downloaded_exe: str):
    current_exe = get_current_exe_path()
    if not current_exe:
        return

    bat_path = os.path.join(tempfile.gettempdir(), "file_organiser_update.bat")
    bat_content = f"""@echo off
timeout /t 2 /nobreak >nul
del "{current_exe}"
move "{downloaded_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
    with open(bat_path, "w") as f:
        f.write(bat_content)

    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0x08000000
    )
    sys.exit(0)
