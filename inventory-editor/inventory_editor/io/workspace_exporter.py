from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from inventory_editor.models.project import ProjectModel

# Use typ="rt" for round-trip (preserves comments and formatting)
yaml_rt = YAML(typ="rt")
yaml_rt.preserve_quotes = True
yaml_rt.indent(mapping=2, sequence=4, offset=2)

from io import StringIO
from inventory_editor.io.vault_handler import VaultHandler

def _write_yaml_rt(path: Path, data: any, project: ProjectModel = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if this path should be encrypted
    # We need the relative path to match project.vault_files
    is_vault = False
    if project and hasattr(project, "root_path") and hasattr(project, "vault_files"):
        root = Path(project.root_path).expanduser().resolve()
        try:
            rel_path = str(path.relative_to(root))
            if rel_path in project.vault_files:
                is_vault = True
        except ValueError:
            pass

    if is_vault:
        # Dump to string first, then encrypt
        stream = StringIO()
        yaml_rt.dump(data, stream)
        VaultHandler.encrypt(stream.getvalue(), path)
    else:
        with path.open("w", encoding="utf-8") as fh:
            yaml_rt.dump(data, fh)

def export_workspace(project: ProjectModel, target_root: str | Path) -> None:
    root = Path(target_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    # 1. Export inventory.yml
    # If we have raw data, we update it instead of recreating to preserve comments
    inventory_data = getattr(project, "raw_inventory_data", CommentedMap())
    
    # Ensure standard 'all' structure if it's preferred
    if "all" not in inventory_data:
        inventory_data["all"] = CommentedMap()
    
    if "children" not in inventory_data["all"]:
        inventory_data["all"]["children"] = CommentedMap()

    # Sync groups and hosts to inventory_data
    # This is a bit complex for round-trip because we need to find where to put things
    # For now, we update the existing children structure
    all_children = inventory_data["all"]["children"]
    for group_name, group in project.groups.items():
        if group_name == "all": continue
        
        if group_name not in all_children:
            all_children[group_name] = CommentedMap()
        
        g_block = all_children[group_name]
        
        if group.hosts:
            if "hosts" not in g_block: g_block["hosts"] = CommentedMap()
            # Add missing hosts
            for h_name in sorted(group.hosts):
                if h_name not in g_block["hosts"]:
                    g_block["hosts"][h_name] = None
        
        if group.children:
            if "children" not in g_block: g_block["children"] = CommentedMap()
            for c_name in sorted(group.children):
                if c_name not in g_block["children"]:
                    g_block["children"][c_name] = CommentedMap()

    _write_yaml_rt(root / project.inventory_file, inventory_data, project=project)

    # 2. Export variables (group_vars & host_vars)
    raw_var_data = getattr(project, "raw_var_data", {})

    def sync_vars(items, owner_name, scope_type):
        # items is a list of Variable objects
        # grouped by file_name
        files = {}
        for var in items:
            source_path = var.source.source_path
            file_name = Path(source_path).name if source_path else "main.yml"
            if file_name in {"", "."}: file_name = "main.yml"
            if file_name not in files: files[file_name] = []
            files[file_name].append(var)

        for file_name, vars_in_file in files.items():
            key = (scope_type, owner_name, file_name)
            data = raw_var_data.get(key, CommentedMap())
            
            # Update data with current variable values
            for var in vars_in_file:
                data[var.key] = var.value
            
            _write_yaml_rt(root / scope_type / owner_name / file_name, data, project=project)

    for group_name, group in project.groups.items():
        if group.variables:
            sync_vars(group.variables, group_name, "group_vars")

    for host_name, host in project.hosts.items():
        if host.variables:
            sync_vars(host.variables, host_name, "host_vars")
