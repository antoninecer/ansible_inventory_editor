from __future__ import annotations

import argparse
from pathlib import Path

from inventory_editor.analyzer.workspace_quality import analyze_workspace_scan
from inventory_editor.io.workspace_loader import load_inventory_workspace
from inventory_editor.models.vault_password import VaultPasswordSource


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inventory-editor")
    parser.add_argument("workspace", help="Inventory workspace path")
    parser.add_argument("--vault-password-file", dest="vault_password_file")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()

    project, scan = load_inventory_workspace(workspace)
    report = analyze_workspace_scan(scan)

    print(f"Workspace: {workspace}")
    print(f"Groups: {project.group_count()}")
    print(f"Hosts: {project.host_count()}")
    print(f"Inventory files: {len(scan.inventory_files)}")
    print(f"Group var files: {len(scan.group_var_paths)}")
    print(f"Host var files: {len(scan.host_var_paths)}")
    print(f"Vault files: {len(scan.vault_files)}")
    print(f"Backup files: {len(scan.backup_files)}")
    print(f"Unknown files: {len(scan.unknown_paths)}")

    if args.vault_password_file:
        vault_source = VaultPasswordSource.from_path(args.vault_password_file)
        print(f"Vault password file: {vault_source.source_path}")

    if scan.vault_metadata:
        print("Vault metadata:")
        for vault in scan.vault_metadata:
            print(
                f"- {vault.source_path} "
                f"(version={vault.vault_version}, cipher={vault.cipher})"
            )

    if report.issues:
        print("Issues:")
        for issue in report.issues:
            print(f"- [{issue.severity.value}] {issue.message}")

    return 0
