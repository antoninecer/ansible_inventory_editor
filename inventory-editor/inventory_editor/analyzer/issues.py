from dataclasses import dataclass
from enum import Enum


class IssueSeverity(str, Enum):
    A = "A"
    B = "B"
    C = "C"


@dataclass(slots=True)
class Issue:
    severity: IssueSeverity
    message: str
    source_path: str | None = None
