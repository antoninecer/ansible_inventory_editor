from __future__ import annotations

from pathlib import Path
from ruamel.yaml import YAML

from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource

# Use typ="rt" for round-trip (preserves comments and formatting)
yaml_rt = YAML(typ="rt")
yaml_rt.preserve_quotes = True
yaml_rt.indent(mapping=2, sequence=4, offset=2)

IGNORED_FILE_SUFFIXES = {".bak", ".tmp", ".swp", ".swo"}

def _is_ansible_vault(path: Path) -> bool:
    try:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
    except Exception:
        return False
    return first_line.startswith("$ANSIBLE_VAULT;")

def _load_yaml_rt(path: Path) -> any:
    # ruamel.yaml.load returns a CommentedMap/CommentedSeq which preserves comments
    return yaml_rt.load(path)

def load_inventory_file(path: str | Path) -> ProjectModel:
    inventory_path = Path(path).expanduser().resolve()
    if not inventory_path.exists():
        raise FileNotFoundError(inventory_path)

    data = _load_yaml_rt(inventory_path) or {}

    project = ProjectModel(root_path=str(inventory_path.parent), inventory_file=inventory_path.name)
    # Store the raw data to preserve structure during export
    project.raw_inventory_data = data

    # Ansible inventory YAML structure can vary, but we support the standard 'all' or flat groups
    root_groups = data
    if "all" in data and len(data) == 1:
        # If it's the standard nested structure
        # We still want to process it but ProjectModel always has 'all'
        pass

    def process_group_data(g_name, g_data):
        if not isinstance(g_data, dict):
            return
        
        project.add_group(g_name)
        
        # Process hosts
        hosts = g_data.get("hosts", {})
        if isinstance(hosts, dict):
            for h_name in hosts.keys():
                project.assign_host_to_group(h_name, g_name)
        
        # Process children
        children = g_data.get("children", {})
        if isinstance(children, dict):
            for c_name, c_data in children.items():
                project.add_group(c_name)
                project.groups[g_name].add_child(c_name)
                # Recursively process children if they are defined inline
                if isinstance(c_data, dict):
                    process_group_data(c_name, c_data)

    for name, content in root_groups.items():
        if name == "all":
            # Handle 'all' hosts/children/vars
            if isinstance(content, dict):
                hosts = content.get("hosts", {})
                if isinstance(hosts, dict):
                    for h_name in hosts.keys():
                        project.assign_host_to_group(h_name, "all")

                children = content.get("children", {})
                if isinstance(children, dict):
                    for child_name, child_data in children.items():
                        process_group_data(child_name, child_data)
                
                # Inline vars in inventory.yml
                vars_data = content.get("vars", {})
                if isinstance(vars_data, dict):
                    for k, v in vars_data.items():
                        project.add_variable_to_group("all", Variable(
                            key=k, value=v, scope=VariableScope.GROUP, owner="all",
                            source=VariableSource(source_path=inventory_path.name, source_type="inventory")
                        ))
        else:
            process_group_data(name, content)

    return project

def _iter_var_files(scope_root: Path) -> list[Path]:
    if not scope_root.exists():
        return []

    files: list[Path] = []
    for path in sorted(scope_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix in IGNORED_FILE_SUFFIXES:
            continue
        if path.name.startswith("."):
            continue
        files.append(path)
    return files

from inventory_editor.io.vault_handler import VaultHandler

def load_workspace_variables(project: ProjectModel, workspace_root: str | Path, vault_password: str | None = None, vault_password_file: str | None = None) -> None:
    root = Path(workspace_root).expanduser().resolve()
    
    # Update settings temporarily for VaultHandler if credentials provided
    from inventory_editor.gui.settings import settings
    if vault_password: settings.vault_password = vault_password
    if vault_password_file: settings.vault_password_file = vault_password_file

    if not hasattr(project, "raw_var_data"):
        project.raw_var_data = {} 
    
    if not hasattr(project, "vault_files"):
        project.vault_files = set() # Set of relative paths that should be encrypted

    def load_vars(dir_root, scope_type):
        if not dir_root.exists():
            return
        for entry_dir in dir_root.iterdir():
            if not entry_dir.is_dir():
                continue
            entry_name = entry_dir.name
            for file_path in _iter_var_files(entry_dir):
                is_vault = _is_ansible_vault(file_path)
                rel_path = str(file_path.relative_to(root))
                
                if is_vault:
                    project.vault_files.add(rel_path)
                
                try:
                    if is_vault:
                        # Try to decrypt to load keys
                        try:
                            decrypted_content = VaultHandler.decrypt(file_path)
                            data = yaml_rt.load(decrypted_content) or {}
                        except Exception:
                            # If decryption fails, load as raw (will stay encrypted in UI)
                            data = _load_yaml_rt(file_path) or {}
                    else:
                        data = _load_yaml_rt(file_path) or {}
                except Exception:
                    continue
                
                project.raw_var_data[(scope_type, entry_name, file_path.name)] = data
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        variable = Variable(
                            key=key,
                            value=value,
                            scope=VariableScope.GROUP if scope_type == "group_vars" else VariableScope.HOST,
                            owner=entry_name,
                            source=VariableSource(
                                source_path=rel_path,
                                source_type=scope_type,
                            ),
                        )
                        if scope_type == "group_vars":
                            project.add_variable_to_group(entry_name, variable)
                        else:
                            project.add_variable_to_host(entry_name, variable)

    load_vars(root / "group_vars", "group_vars")
    load_vars(root / "host_vars", "host_vars")
