from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AnsiblePlaybookCommand:
    inventory: str
    playbook: str
    user: str | None = None
    limit: str | None = None
    tags: list[str] = field(default_factory=list)
    skip_tags: list[str] = field(default_factory=list)
    check: bool = False
    diff: bool = False
    become: bool = False
    ask_become_pass: bool = False
    ask_vault_pass: bool = False
    vault_password_file: str | None = None
    extra_vars: list[str] = field(default_factory=list)
    list_hosts: bool = False
    list_tags: bool = False
    list_tasks: bool = False

    def to_argv(self) -> list[str]:
        argv: list[str] = ["ansible-playbook", "-i", self.inventory, self.playbook]

        if self.user:
            argv.extend(["-u", self.user])

        if self.limit:
            argv.extend(["-l", self.limit])

        if self.tags:
            argv.extend(["--tags", ",".join(self.tags)])

        if self.skip_tags:
            argv.extend(["--skip-tags", ",".join(self.skip_tags)])

        if self.check:
            argv.append("--check")

        if self.diff:
            argv.append("--diff")

        if self.become:
            argv.append("--become")

        if self.ask_become_pass:
            argv.append("--ask-become-pass")

        if self.ask_vault_pass:
            argv.append("--ask-vault-pass")

        if self.vault_password_file:
            argv.extend(["--vault-password-file", self.vault_password_file])

        for item in self.extra_vars:
            argv.extend(["--extra-vars", item])

        if self.list_hosts:
            argv.append("--list-hosts")

        if self.list_tags:
            argv.append("--list-tags")

        if self.list_tasks:
            argv.append("--list-tasks")

        return argv

    def to_shell(self) -> str:
        return " ".join(shlex.quote(part) for part in self.to_argv())


def normalize_relative_to_workspace(workspace: str | Path, value: str | Path) -> str:
    workspace_path = Path(workspace).expanduser().resolve()
    path = Path(value).expanduser()

    if path.is_absolute():
        try:
            return str(path.resolve().relative_to(workspace_path))
        except ValueError:
            return str(path)

    return str(path)


def split_csv_values(values: list[str] | None) -> list[str]:
    if not values:
        return []

    result: list[str] = []

    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                result.append(part)

    return result


def build_ansible_playbook_command(
    *,
    workspace: str | Path,
    inventory: str | Path,
    playbook: str | Path,
    user: str | None = None,
    limit: str | None = None,
    tags: list[str] | None = None,
    skip_tags: list[str] | None = None,
    check: bool = False,
    diff: bool = False,
    become: bool = False,
    ask_become_pass: bool = False,
    ask_vault_pass: bool = False,
    vault_password_file: str | None = None,
    extra_vars: list[str] | None = None,
    list_hosts: bool = False,
    list_tags: bool = False,
    list_tasks: bool = False,
) -> AnsiblePlaybookCommand:
    return AnsiblePlaybookCommand(
        inventory=normalize_relative_to_workspace(workspace, inventory),
        playbook=normalize_relative_to_workspace(workspace, playbook),
        user=user,
        limit=limit,
        tags=tags or [],
        skip_tags=skip_tags or [],
        check=check,
        diff=diff,
        become=become,
        ask_become_pass=ask_become_pass,
        ask_vault_pass=ask_vault_pass,
        vault_password_file=vault_password_file,
        extra_vars=extra_vars or [],
        list_hosts=list_hosts,
        list_tags=list_tags,
        list_tasks=list_tasks,
    )
