from enum import Enum
from pathlib import Path


class FileClassification(str, Enum):
    INVENTORY_FILE = "inventory_file"
    VARIABLE_FILE = "variable_file"
    PLAYBOOK = "playbook"
    VAULT_FILE = "vault_file"
    BACKUP_FILE = "backup_file"
    UNKNOWN = "unknown"


def classify_file(path: str) -> FileClassification:
    p = Path(path)

    name = p.name.lower()

    if name.endswith(".yml") or name.endswith(".yaml"):
        if name == "vault.yml":
            return FileClassification.VAULT_FILE

        if "group_vars" in p.parts or "host_vars" in p.parts:
            return FileClassification.VARIABLE_FILE

        if name == "inventory.yml" or name == "inventory.yaml":
            return FileClassification.INVENTORY_FILE

        return FileClassification.PLAYBOOK

    if ".yml-" in name or ".yaml-" in name:
        return FileClassification.BACKUP_FILE

    return FileClassification.UNKNOWN
