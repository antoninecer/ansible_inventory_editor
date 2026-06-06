from __future__ import annotations

from dataclasses import dataclass, field

from inventory_editor.analyzer.workspace_quality import WorkspaceQualityReport
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.workspace import WorkspaceScanResult


@dataclass(slots=True)
class GroupCard:
    name: str
    hosts: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HostCard:
    name: str
    groups: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WorkspaceOverview:
    stats: list[tuple[str, str]] = field(default_factory=list)
    groups: list[GroupCard] = field(default_factory=list)
    hosts: list[HostCard] = field(default_factory=list)
    inventory_files: list[str] = field(default_factory=list)
    group_var_files: list[str] = field(default_factory=list)
    host_var_files: list[str] = field(default_factory=list)
    vault_files: list[str] = field(default_factory=list)
    backup_files: list[str] = field(default_factory=list)
    unknown_files: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def build_workspace_overview(
    project: ProjectModel,
    scan: WorkspaceScanResult,
    report: WorkspaceQualityReport,
) -> WorkspaceOverview:
    overview = WorkspaceOverview()

    overview.stats = [
        ("Root", project.root_path),
        ("Inventory file", project.inventory_file),
        ("Groups", str(project.group_count())),
        ("Hosts", str(project.host_count())),
        ("Inventory files", str(len(scan.inventory_files))),
        ("Group var files", str(len(scan.group_var_paths))),
        ("Host var files", str(len(scan.host_var_paths))),
        ("Vault files", str(len(scan.vault_files))),
        ("Backup files", str(len(scan.backup_files))),
        ("Unknown files", str(len(scan.unknown_paths))),
    ]

    for group_name in sorted(project.groups):
        group = project.groups[group_name]
        overview.groups.append(
            GroupCard(
                name=group_name,
                hosts=sorted(group.hosts),
                children=sorted(group.children),
                variables=[f"{variable.key} = {variable.value}" for variable in group.variables],
            )
        )

    for host_name in sorted(project.hosts):
        host = project.hosts[host_name]
        overview.hosts.append(
            HostCard(
                name=host_name,
                groups=sorted(host.groups),
                variables=[f"{variable.key} = {variable.value}" for variable in host.variables],
            )
        )

    overview.inventory_files = list(scan.inventory_files)
    overview.group_var_files = list(scan.group_var_paths)
    overview.host_var_files = list(scan.host_var_paths)
    overview.vault_files = list(scan.vault_files)
    overview.backup_files = list(scan.backup_files)
    overview.unknown_files = list(scan.unknown_paths)
    overview.issues = [f"[{issue.severity.value}] {issue.message}" for issue in report.issues]

    return overview
