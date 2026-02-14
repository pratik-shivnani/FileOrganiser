import time
from typing import Optional

from app.db.database import get_connection


def add_tag(file_path: str, tag: str) -> bool:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO tags (file_path, tag, created_at) VALUES (?, ?, ?)",
            (file_path, tag.strip().lower(), time.time())
        )
        conn.commit()
        return True
    except Exception:
        return False


def remove_tag(file_path: str, tag: str) -> bool:
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM tags WHERE file_path = ? AND tag = ?",
        (file_path, tag.strip().lower())
    )
    conn.commit()
    return cursor.rowcount > 0


def get_tags_for_file(file_path: str) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT tag FROM tags WHERE file_path = ? ORDER BY tag",
        (file_path,)
    ).fetchall()
    return [row["tag"] for row in rows]


def get_files_with_tag(tag: str) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT file_path FROM tags WHERE tag = ?",
        (tag.strip().lower(),)
    ).fetchall()
    return [row["file_path"] for row in rows]


def get_all_tags() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT tag, COUNT(*) as count FROM tags
        GROUP BY tag ORDER BY tag
    """).fetchall()
    return [{"tag": row["tag"], "count": row["count"]} for row in rows]


def toggle_star(file_path: str) -> bool:
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM stars WHERE file_path = ?", (file_path,)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM stars WHERE file_path = ?", (file_path,))
        conn.commit()
        return False
    else:
        conn.execute(
            "INSERT INTO stars (file_path, starred_at) VALUES (?, ?)",
            (file_path, time.time())
        )
        conn.commit()
        return True


def is_starred(file_path: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM stars WHERE file_path = ?", (file_path,)
    ).fetchone()
    return row is not None


def get_starred_files() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT file_path FROM stars ORDER BY starred_at DESC"
    ).fetchall()
    return [row["file_path"] for row in rows]


def bulk_tag(file_paths: list[str], tag: str) -> int:
    conn = get_connection()
    tag = tag.strip().lower()
    count = 0
    for fp in file_paths:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO tags (file_path, tag, created_at) VALUES (?, ?, ?)",
                (fp, tag, time.time())
            )
            count += 1
        except Exception:
            continue
    conn.commit()
    return count


def bulk_star(file_paths: list[str]) -> int:
    conn = get_connection()
    count = 0
    for fp in file_paths:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO stars (file_path, starred_at) VALUES (?, ?)",
                (fp, time.time())
            )
            count += 1
        except Exception:
            continue
    conn.commit()
    return count
