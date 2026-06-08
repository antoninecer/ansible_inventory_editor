from __future__ import annotations

from pathlib import Path

from inventory_editor.io.inventory_loader import load_inventory_file, load_workspace_variables
from inventory_editor.io.scanner import scan_inventory_workspace
from inventory_editor.models.project import ProjectModel


def load_inventory_workspace(
    root_path: str | Path,
    vault_password: str | None = None,
    vault_password_file: str | None = None,
    inventory_file: str | Path | None = None,
) -> tuple[ProjectModel, object]:
    scan = scan_inventory_workspace(root_path)

    root = Path(root_path).expanduser().resolve()

    if inventory_file is not None:
        selected_inventory = Path(inventory_file)
        if not selected_inventory.is_absolute():
            selected_inventory = root / selected_inventory
    else:
        selected_inventory = None
        if "inventory.yml" in scan.inventory_files:
            selected_inventory = root / "inventory.yml"
        elif scan.inventory_files:
            selected_inventory = root / scan.inventory_files[0]

    if selected_inventory is None:
        raise FileNotFoundError("No inventory YAML file found in workspace")

    if not selected_inventory.exists():
        raise FileNotFoundError(f"Selected inventory file does not exist: {selected_inventory}")

    project = load_inventory_file(selected_inventory)

    try:
        project.inventory_file = str(selected_inventory.relative_to(root))
    except ValueError:
        project.inventory_file = str(selected_inventory)

    load_workspace_variables(
        project,
        root,
        vault_password=vault_password,
        vault_password_file=vault_password_file,
    )

    return project, scan
