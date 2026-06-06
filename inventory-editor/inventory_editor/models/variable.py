from dataclasses import dataclass
from enum import Enum


class VariableScope(str, Enum):
    ALL = "all"
    GROUP = "group"
    HOST = "host"


@dataclass
class VariableSource:
    source_path: str
    source_type: str


@dataclass
class Variable:
    key: str
    value: object

    scope: VariableScope

    owner: str

    source: VariableSource
