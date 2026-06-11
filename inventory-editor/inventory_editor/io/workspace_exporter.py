from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from inventory_editor.models.project import ProjectModel

COMMENT_CONTEXT_WARNING = (
    "Block/comment context detected in inventory membership section. "
    "AIS preserved existing order and used minimal-diff export instead of aggressive sorting. "
    "Review Git diff after saving."
)

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

def _mapping_has_comment_context(mapping: object) -> bool:
    ca = getattr(mapping, "ca", None)
    if not ca:
        return False

    if getattr(ca, "comment", None):
        return True

    items = getattr(ca, "items", None)
    if items:
        return True

    for attr in ("_items", "_pre", "_post"):
        value = getattr(ca, attr, None)
        if value:
            return True

    return False


def _sync_membership_map(
    old_map: object,
    desired_keys: set[str],
    *,
    default_value_factory,
    warning_bucket: list[str],
) -> CommentedMap:
    if not isinstance(old_map, CommentedMap):
        old_map = CommentedMap(old_map or {})

    has_comment_context = _mapping_has_comment_context(old_map)

    if has_comment_context and COMMENT_CONTEXT_WARNING not in warning_bucket:
        warning_bucket.append(COMMENT_CONTEXT_WARNING)

    if has_comment_context:
        # Conservative mode:
        # - update the existing CommentedMap in-place
        # - keep existing order
        # - keep ruamel comment associations untouched
        # - remove stale keys
        # - append new keys at the end
        for key in list(old_map.keys()):
            if str(key) not in desired_keys:
                del old_map[key]

        existing_key_set = {str(key) for key in old_map.keys()}

        for key in sorted(desired_keys - existing_key_set):
            old_map[key] = default_value_factory()

        return old_map

    # Clean map without comment context: deterministic alphabetical order.
    new_map = CommentedMap()

    for key in sorted(desired_keys):
        if key in old_map:
            new_map[key] = old_map[key]
        else:
            new_map[key] = default_value_factory()

    return new_map


def export_workspace(project: ProjectModel, target_root: str | Path, *, write_vars: bool = True, var_sources_to_write: set[str] | None = None) -> None:
    root = Path(target_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    export_warnings: list[str] = []
    project.export_warnings = export_warnings

    # 1. Export inventory.yml
    # If we have raw data, we update it instead of recreating to preserve comments
    inventory_data = getattr(project, "raw_inventory_data", CommentedMap())
    
    # Ensure standard 'all' structure if it's preferred
    if "all" not in inventory_data:
        inventory_data["all"] = CommentedMap()
    
    if "children" not in inventory_data["all"]:
        inventory_data["all"]["children"] = CommentedMap()

    # Sync groups and hosts to inventory_data.
    # Keep round-trip data where possible, but remove stale hosts/groups too.
    all_children = inventory_data["all"]["children"]

    for old_group_name in list(all_children.keys()):
        if old_group_name not in project.groups:
            del all_children[old_group_name]

    for group_name, group in project.groups.items():
        if group_name == "all":
            continue

        if group_name not in all_children:
            all_children[group_name] = CommentedMap()

        g_block = all_children[group_name]

        if group.hosts:
            old_hosts = g_block.get("hosts", CommentedMap())
            g_block["hosts"] = _sync_membership_map(
                old_hosts,
                {str(host_name) for host_name in group.hosts},
                default_value_factory=lambda: None,
                warning_bucket=export_warnings,
            )
        else:
            g_block.pop("hosts", None)

        if group.children:
            old_children = g_block.get("children", CommentedMap())
            g_block["children"] = _sync_membership_map(
                old_children,
                {str(child_name) for child_name in group.children},
                default_value_factory=CommentedMap,
                warning_bucket=export_warnings,
            )
        else:
            g_block.pop("children", None)

    _write_yaml_rt(root / project.inventory_file, inventory_data, project=project)

    if not write_vars:
        return

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
            
            target_path = root / scope_type / owner_name / file_name
            rel_target = str(target_path.relative_to(root))

            if var_sources_to_write is not None and rel_target not in var_sources_to_write:
                continue

            _write_yaml_rt(target_path, data, project=project)

    for group_name, group in project.groups.items():
        if group.variables:
            sync_vars(group.variables, group_name, "group_vars")

    for host_name, host in project.hosts.items():
        if host.variables:
            sync_vars(host.variables, host_name, "host_vars")
