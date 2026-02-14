import json
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from app.db.database import get_connection


def move_file(source: str, dest_dir: str) -> str:
    dest_path = os.path.join(dest_dir, os.path.basename(source))
    dest_path = _get_unique_path(dest_path)
    shutil.move(source, dest_path)
    _log_operation("move", source, dest_path)
    _update_index_after_move(source, dest_path)
    return dest_path


def copy_file(source: str, dest_dir: str) -> str:
    dest_path = os.path.join(dest_dir, os.path.basename(source))
    dest_path = _get_unique_path(dest_path)
    if os.path.isdir(source):
        shutil.copytree(source, dest_path)
    else:
        shutil.copy2(source, dest_path)
    _log_operation("copy", source, dest_path)
    return dest_path


def rename_file(filepath: str, new_name: str) -> str:
    parent = os.path.dirname(filepath)
    new_path = os.path.join(parent, new_name)
    if os.path.exists(new_path) and new_path != filepath:
        raise FileExistsError(f"A file named '{new_name}' already exists")
    os.rename(filepath, new_path)
    _log_operation("rename", filepath, new_path)
    _update_index_after_move(filepath, new_path)
    return new_path


def delete_file(filepath: str, use_trash: bool = True) -> bool:
    if use_trash:
        try:
            _move_to_trash(filepath)
        except Exception:
            if os.path.isdir(filepath):
                shutil.rmtree(filepath)
            else:
                os.remove(filepath)
    else:
        if os.path.isdir(filepath):
            shutil.rmtree(filepath)
        else:
            os.remove(filepath)

    _log_operation("delete", filepath, None, {"use_trash": use_trash})
    _remove_from_index(filepath)
    return True


def create_folder(parent_dir: str, folder_name: str) -> str:
    new_path = os.path.join(parent_dir, folder_name)
    os.makedirs(new_path, exist_ok=False)
    _log_operation("create_folder", None, new_path)
    return new_path


def undo_last_operation() -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM operation_log
        WHERE undone = 0
        ORDER BY performed_at DESC
        LIMIT 1
    """).fetchone()

    if not row:
        return None

    entry = dict(row)
    action = entry["action"]
    source = entry["source_path"]
    dest = entry["dest_path"]

    try:
        if action == "move" and source and dest and os.path.exists(dest):
            original_dir = os.path.dirname(source)
            os.makedirs(original_dir, exist_ok=True)
            shutil.move(dest, source)
        elif action == "rename" and source and dest and os.path.exists(dest):
            os.rename(dest, source)
        elif action == "create_folder" and dest and os.path.exists(dest):
            os.rmdir(dest)
        else:
            return None

        conn.execute(
            "UPDATE operation_log SET undone = 1 WHERE id = ?",
            (entry["id"],)
        )
        conn.commit()
        return entry
    except (OSError, shutil.Error):
        return None


def get_operation_history(limit: int = 50) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM operation_log
        ORDER BY performed_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def _move_to_trash(filepath: str):
    if os.name == "nt":
        try:
            from ctypes import windll, pointer, Structure, c_uint, c_wchar_p
            from ctypes.wintypes import HWND

            class SHFILEOPSTRUCT(Structure):
                _fields_ = [
                    ("hwnd", HWND),
                    ("wFunc", c_uint),
                    ("pFrom", c_wchar_p),
                    ("pTo", c_wchar_p),
                    ("fFlags", c_uint),
                ]

            FO_DELETE = 3
            FOF_ALLOWUNDO = 0x40
            FOF_NOCONFIRMATION = 0x10
            FOF_SILENT = 0x4

            op = SHFILEOPSTRUCT()
            op.hwnd = None
            op.wFunc = FO_DELETE
            op.pFrom = filepath + "\0\0"
            op.pTo = None
            op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT

            result = windll.shell32.SHFileOperationW(pointer(op))
            if result != 0:
                raise OSError(f"SHFileOperation failed with code {result}")
        except ImportError:
            raise OSError("Cannot access Windows trash API")
    else:
        trash_dir = Path.home() / ".Trash"
        if not trash_dir.exists():
            trash_dir = Path.home() / ".local" / "share" / "Trash" / "files"
            trash_dir.mkdir(parents=True, exist_ok=True)
        dest = trash_dir / os.path.basename(filepath)
        dest = Path(_get_unique_path(str(dest)))
        shutil.move(filepath, str(dest))


def _get_unique_path(filepath: str) -> str:
    if not os.path.exists(filepath):
        return filepath
    base, ext = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(f"{base} ({counter}){ext}"):
        counter += 1
    return f"{base} ({counter}){ext}"


def _log_operation(action: str, source: Optional[str], dest: Optional[str],
                   metadata: Optional[dict] = None):
    conn = get_connection()
    meta_json = json.dumps(metadata) if metadata else None
    conn.execute("""
        INSERT INTO operation_log (action, source_path, dest_path, metadata, performed_at)
        VALUES (?, ?, ?, ?, ?)
    """, (action, source, dest, meta_json, time.time()))
    conn.commit()


def _update_index_after_move(old_path: str, new_path: str):
    conn = get_connection()
    conn.execute(
        "UPDATE file_index SET path = ?, name = ?, parent_path = ?, modified_at = ? WHERE path = ?",
        (new_path, os.path.basename(new_path), os.path.dirname(new_path), time.time(), old_path)
    )
    conn.execute("UPDATE tags SET file_path = ? WHERE file_path = ?", (new_path, old_path))
    conn.execute("UPDATE stars SET file_path = ? WHERE file_path = ?", (new_path, old_path))
    conn.commit()


def _remove_from_index(filepath: str):
    conn = get_connection()
    conn.execute("DELETE FROM file_index WHERE path = ? OR path LIKE ?",
                 (filepath, filepath + os.sep + "%"))
    conn.execute("DELETE FROM tags WHERE file_path = ? OR file_path LIKE ?",
                 (filepath, filepath + os.sep + "%"))
    conn.execute("DELETE FROM stars WHERE file_path = ? OR file_path LIKE ?",
                 (filepath, filepath + os.sep + "%"))
    conn.commit()
