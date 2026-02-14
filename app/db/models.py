from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class FileEntry:
    path: str
    name: str
    extension: Optional[str] = None
    size: int = 0
    created_at: float = 0.0
    modified_at: float = 0.0
    is_directory: bool = False
    parent_path: Optional[str] = None
    mime_type: Optional[str] = None
    indexed_at: float = field(default_factory=time.time)
    id: Optional[int] = None

    @classmethod
    def from_row(cls, row) -> "FileEntry":
        return cls(
            id=row["id"],
            path=row["path"],
            name=row["name"],
            extension=row["extension"],
            size=row["size"] or 0,
            created_at=row["created_at"] or 0.0,
            modified_at=row["modified_at"] or 0.0,
            is_directory=bool(row["is_directory"]),
            parent_path=row["parent_path"],
            mime_type=row["mime_type"],
            indexed_at=row["indexed_at"] or 0.0,
        )


@dataclass
class Tag:
    file_path: str
    tag: str
    created_at: float = field(default_factory=time.time)
    id: Optional[int] = None


@dataclass
class Star:
    file_path: str
    starred_at: float = field(default_factory=time.time)
    id: Optional[int] = None


@dataclass
class OperationLogEntry:
    action: str
    source_path: Optional[str] = None
    dest_path: Optional[str] = None
    metadata: Optional[str] = None
    performed_at: float = field(default_factory=time.time)
    undone: bool = False
    id: Optional[int] = None


@dataclass
class IndexedDir:
    path: str
    last_indexed: Optional[float] = None
    file_count: int = 0
    id: Optional[int] = None
