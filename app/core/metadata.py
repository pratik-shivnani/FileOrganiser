import mimetypes
import os
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FileMetadata:
    path: str
    name: str
    extension: Optional[str]
    size: int
    created_at: float
    modified_at: float
    accessed_at: float
    is_directory: bool
    is_hidden: bool
    is_readonly: bool
    is_symlink: bool
    mime_type: Optional[str]
    permissions: str
    parent_path: str

    @property
    def created_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.created_at)

    @property
    def modified_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.modified_at)

    @property
    def accessed_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.accessed_at)


def get_file_metadata(filepath: str) -> Optional[FileMetadata]:
    try:
        p = Path(filepath)
        st = p.stat()
        is_dir = p.is_dir()
        ext = p.suffix.lower() if not is_dir else None
        mime = None
        if not is_dir:
            mime, _ = mimetypes.guess_type(filepath)

        is_hidden = p.name.startswith(".")
        if os.name == "nt":
            try:
                attrs = os.stat(filepath).st_file_attributes
                is_hidden = bool(attrs & stat.FILE_ATTRIBUTE_HIDDEN)
            except (AttributeError, OSError):
                pass

        is_readonly = not os.access(filepath, os.W_OK)

        mode = st.st_mode
        permissions = stat.filemode(mode)

        return FileMetadata(
            path=str(p.resolve()),
            name=p.name,
            extension=ext,
            size=st.st_size if not is_dir else 0,
            created_at=st.st_ctime,
            modified_at=st.st_mtime,
            accessed_at=st.st_atime,
            is_directory=is_dir,
            is_hidden=is_hidden,
            is_readonly=is_readonly,
            is_symlink=p.is_symlink(),
            mime_type=mime,
            permissions=permissions,
            parent_path=str(p.parent),
        )
    except (OSError, PermissionError):
        return None


def get_directory_size(dirpath: str) -> int:
    total = 0
    try:
        for entry in os.scandir(dirpath):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += get_directory_size(entry.path)
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    return total
