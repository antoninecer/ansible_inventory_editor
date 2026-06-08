from __future__ import annotations

import argparse
from pathlib import Path

from inventory_editor.analyzer.ansible_command_builder import (
    build_ansible_playbook_command,
    split_csv_values,
)
from inventory_editor.analyzer.playbook_discovery import analyze_playbook
from inventory_editor.analyzer.workspace_quality import analyze_workspace_scan
from inventory_editor.io.workspace_loader import load_inventory_workspace
from inventory_editor.models.vault_password import VaultPasswordSource


def _run_summary(argv: list[str] | None = None) -> int:
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


def _run_playbook_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="inventory-editor playbook-command",
        description="Build an ansible-playbook command from AIS workspace context.",
    )

    parser.add_argument("--workspace", required=True, help="AIS / Ansible inventory workspace path")
    parser.add_argument("--inventory", required=True, help="Inventory file, relative to workspace or absolute")
    parser.add_argument("--playbook", required=True, help="Playbook file, relative to workspace or absolute")
    parser.add_argument("--user", "-u")
    parser.add_argument("--limit", "-l")
    parser.add_argument("--tags", action="append", help="Tag or comma-separated tag list. Can be used more than once.")
    parser.add_argument("--skip-tags", action="append", help="Skip tag or comma-separated skip-tag list.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--become", action="store_true")
    parser.add_argument("--ask-become-pass", action="store_true")
    parser.add_argument("--ask-vault-pass", action="store_true")
    parser.add_argument("--vault-password-file")
    parser.add_argument("--extra-vars", action="append", default=[])
    parser.add_argument("--list-hosts", action="store_true")
    parser.add_argument("--list-tags", action="store_true")
    parser.add_argument("--list-tasks", action="store_true")
    parser.add_argument("--show-playbook-info", action="store_true")

    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()

    command = build_ansible_playbook_command(
        workspace=workspace,
        inventory=args.inventory,
        playbook=args.playbook,
        user=args.user,
        limit=args.limit,
        tags=split_csv_values(args.tags),
        skip_tags=split_csv_values(args.skip_tags),
        check=args.check,
        diff=args.diff,
        become=args.become,
        ask_become_pass=args.ask_become_pass,
        ask_vault_pass=args.ask_vault_pass,
        vault_password_file=args.vault_password_file,
        extra_vars=args.extra_vars,
        list_hosts=args.list_hosts,
        list_tags=args.list_tags,
        list_tasks=args.list_tasks,
    )

    if args.show_playbook_info:
        playbook_path = Path(args.playbook)
        if not playbook_path.is_absolute():
            playbook_path = workspace / playbook_path

        summary = analyze_playbook(playbook_path)

        print("Playbook summary")
        print("-" * 80)
        print(f"Path: {summary.path}")
        print(f"Plays: {len(summary.plays)}")
        print(f"Tags: {', '.join(summary.tags) if summary.tags else '-'}")
        print(f"Roles: {', '.join(summary.roles) if summary.roles else '-'}")

        if summary.warnings:
            print("Warnings:")
            for warning in summary.warnings:
                print(f"- {warning}")

        print("")

    print(command.to_shell())
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or [])

    if argv and argv[0] == "playbook-command":
        return _run_playbook_command(argv[1:])

    return _run_summary(argv)
