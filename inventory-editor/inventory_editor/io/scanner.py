from __future__ import annotations

from pathlib import Path

from inventory_editor.analyzer.file_classifier import FileClassification, classify_file
from inventory_editor.analyzer.vault import detect_vault_file
from inventory_editor.models.workspace import WorkspaceScanResult


def scan_inventory_workspace(root_path: str | Path) -> WorkspaceScanResult:
    root = Path(root_path).expanduser().resolve()
    result = WorkspaceScanResult(root_path=str(root))

    if not root.exists():
        raise FileNotFoundError(root)

    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue

        rel = path.relative_to(root).as_posix()
        classification = classify_file(rel)

        if classification == FileClassification.INVENTORY_FILE:
            result.inventory_files.append(rel)
        elif classification == FileClassification.VARIABLE_FILE:
            if rel.startswith("group_vars/"):
                result.group_var_paths.append(rel)
            elif rel.startswith("host_vars/"):
                result.host_var_paths.append(rel)
            else:
                result.unknown_paths.append(rel)
        elif classification == FileClassification.PLAYBOOK:
            result.playbook_files.append(rel)
        elif classification == FileClassification.VAULT_FILE:
            result.vault_files.append(rel)
            vault = detect_vault_file(path)
            if vault is not None:
                result.vault_metadata.append(vault)
        elif classification == FileClassification.BACKUP_FILE:
            result.backup_files.append(rel)
        else:
            result.unknown_paths.append(rel)

    return result
