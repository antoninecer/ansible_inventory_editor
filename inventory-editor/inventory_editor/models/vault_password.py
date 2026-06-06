from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class VaultPasswordSource:
    source_path: str

    @classmethod
    def from_path(cls, path: str | Path) -> "VaultPasswordSource":
        return cls(source_path=str(Path(path).expanduser().resolve()))
