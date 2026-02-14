import sqlite3
import threading
from pathlib import Path

from app.config import DB_PATH, ensure_app_data_dir


_local = threading.local()


def get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "connection") or _local.connection is None:
        ensure_app_data_dir()
        _local.connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
        _local.connection.execute("PRAGMA journal_mode=WAL")
        _local.connection.execute("PRAGMA foreign_keys=ON")
    return _local.connection


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            extension TEXT,
            size INTEGER,
            created_at REAL,
            modified_at REAL,
            is_directory BOOLEAN,
            parent_path TEXT,
            mime_type TEXT,
            indexed_at REAL DEFAULT (julianday('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            tag TEXT NOT NULL,
            created_at REAL DEFAULT (julianday('now')),
            UNIQUE(file_path, tag)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            starred_at REAL DEFAULT (julianday('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            source_path TEXT,
            dest_path TEXT,
            metadata TEXT,
            performed_at REAL DEFAULT (julianday('now')),
            undone BOOLEAN DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS indexed_dirs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            last_indexed REAL,
            file_count INTEGER DEFAULT 0
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_index_path ON file_index(path)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_index_parent ON file_index(parent_path)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_index_ext ON file_index(extension)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_index_name ON file_index(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_file ON tags(file_path)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stars_file ON stars(file_path)")

    conn.commit()


def close_db():
    if hasattr(_local, "connection") and _local.connection is not None:
        _local.connection.close()
        _local.connection = None
