from __future__ import annotations

from pathlib import Path

from inventory_editor.io.inventory_loader import load_inventory_file, load_workspace_variables
from inventory_editor.io.scanner import scan_inventory_workspace
from inventory_editor.models.project import ProjectModel


def load_inventory_workspace(root_path: str | Path, vault_password: str | None = None, vault_password_file: str | None = None) -> tuple[ProjectModel, object]:
    scan = scan_inventory_workspace(root_path)

    root = Path(root_path).expanduser().resolve()
    inventory_file = None
    if "inventory.yml" in scan.inventory_files:
        inventory_file = root / "inventory.yml"
    elif scan.inventory_files:
        inventory_file = root / scan.inventory_files[0]

    if inventory_file is None:
        raise FileNotFoundError("No inventory YAML file found in workspace")

    project = load_inventory_file(inventory_file)
    load_workspace_variables(project, root, vault_password=vault_password, vault_password_file=vault_password_file)

    return project, scan
