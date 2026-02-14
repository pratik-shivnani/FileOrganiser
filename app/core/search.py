from typing import Optional

from app.db.database import get_connection


def search_files(
    directory: Optional[str] = None,
    name_pattern: Optional[str] = None,
    extension: Optional[str] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    modified_after: Optional[float] = None,
    modified_before: Optional[float] = None,
    is_directory: Optional[bool] = None,
    tag: Optional[str] = None,
    starred: Optional[bool] = None,
    sort_by: str = "name",
    sort_desc: bool = False,
    limit: int = 1000,
) -> list[dict]:
    conn = get_connection()

    conditions = []
    params = []

    if directory:
        conditions.append("(f.parent_path = ? OR f.path LIKE ?)")
        params.extend([directory, directory + "%"])

    if name_pattern:
        like_pattern = name_pattern.replace("*", "%").replace("?", "_")
        conditions.append("f.name LIKE ?")
        params.append(like_pattern)

    if extension:
        ext = extension if extension.startswith(".") else f".{extension}"
        conditions.append("f.extension = ?")
        params.append(ext.lower())

    if min_size is not None:
        conditions.append("f.size >= ?")
        params.append(min_size)

    if max_size is not None:
        conditions.append("f.size <= ?")
        params.append(max_size)

    if modified_after is not None:
        conditions.append("f.modified_at >= ?")
        params.append(modified_after)

    if modified_before is not None:
        conditions.append("f.modified_at <= ?")
        params.append(modified_before)

    if is_directory is not None:
        conditions.append("f.is_directory = ?")
        params.append(1 if is_directory else 0)

    joins = ""
    if tag:
        joins += " INNER JOIN tags t ON f.path = t.file_path"
        conditions.append("t.tag = ?")
        params.append(tag)

    if starred:
        joins += " INNER JOIN stars s ON f.path = s.file_path"

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sort_column_map = {
        "name": "f.name",
        "size": "f.size",
        "modified": "f.modified_at",
        "created": "f.created_at",
        "extension": "f.extension",
        "path": "f.path",
    }
    sort_col = sort_column_map.get(sort_by, "f.name")
    sort_dir = "DESC" if sort_desc else "ASC"

    query = f"""
        SELECT f.*, 
               GROUP_CONCAT(DISTINCT tg.tag) as tags,
               CASE WHEN st.file_path IS NOT NULL THEN 1 ELSE 0 END as is_starred
        FROM file_index f
        {joins}
        LEFT JOIN tags tg ON f.path = tg.file_path
        LEFT JOIN stars st ON f.path = st.file_path
        WHERE {where_clause}
        GROUP BY f.path
        ORDER BY {sort_col} {sort_dir}
        LIMIT ?
    """
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def get_all_tags() -> list[str]:
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT tag FROM tags ORDER BY tag").fetchall()
    return [row["tag"] for row in rows]
