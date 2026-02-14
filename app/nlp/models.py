from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedCommand:
    action: str  # search, move, copy, rename, delete, tag, star, create_folder
    filters: dict = field(default_factory=dict)
    target: Optional[str] = None  # destination directory or new name
    tag: Optional[str] = None  # tag name for tag operations
    raw_query: str = ""

    @property
    def is_search(self) -> bool:
        return self.action == "search"

    @property
    def is_destructive(self) -> bool:
        return self.action in ("move", "delete", "rename")

    @property
    def needs_confirmation(self) -> bool:
        return self.action in ("move", "copy", "delete", "rename")
