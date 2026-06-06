from dataclasses import dataclass, field

from inventory_editor.models.vault import VaultFile


@dataclass(slots=True)
class WorkspaceScanResult:
    root_path: str

    inventory_files: list[str] = field(default_factory=list)
    group_var_paths: list[str] = field(default_factory=list)
    host_var_paths: list[str] = field(default_factory=list)
    playbook_files: list[str] = field(default_factory=list)
    backup_files: list[str] = field(default_factory=list)
    vault_files: list[str] = field(default_factory=list)
    vault_metadata: list[VaultFile] = field(default_factory=list)
    unknown_paths: list[str] = field(default_factory=list)
