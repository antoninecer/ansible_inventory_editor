from __future__ import annotations

from dataclasses import dataclass, field

from inventory_editor.analyzer.cli_suggestions import generate_ansible_command_suggestions
from inventory_editor.analyzer.reporting import explain_variable_for_branch
from inventory_editor.analyzer.tracing import trace_variables_for_branch
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable
from inventory_editor.models.workspace import WorkspaceScanResult


def _value_text(value: object) -> str:
    return str(value)


def _scope_color(scope: str, source_path: str) -> str:
    path = source_path.lower()
    if "vault.yml" in path:
        return "#8e24aa"
    if scope == "host":
        return "#2e7d32"
    if scope == "group":
        if "group_vars/all/" in path:
            return "#546e7a"
        return "#1565c0"
    return "#546e7a"


def _file_color(kind: str) -> str:
    if kind == "vault":
        return "#8e24aa"
    if kind == "host-var":
        return "#2e7d32"
    if kind == "group-var":
        return "#1565c0"
    return "#546e7a"


def _kind_for_path(path: str) -> str:
    lower = path.lower()
    if "vault.yml" in lower:
        return "vault"
    if lower.startswith("host_vars/"):
        return "host-var"
    if lower.startswith("group_vars/"):
        return "group-var"
    if lower.endswith((".yml", ".yaml")):
        return "yaml"
    return "file"


def _add_unique_file(rows: list["ContextFileRow"], seen: set[str], path: str, kind: str) -> None:
    if not path or path in seen:
        return
    seen.add(path)
    rows.append(ContextFileRow(kind=kind, path=path, color=_file_color(kind)))


@dataclass(slots=True)
class ContextVariableRow:
    key: str
    value_text: str
    scope: str
    source_path: str
    source_type: str
    color: str


@dataclass(slots=True)
class ContextFileRow:
    kind: str
    path: str
    color: str


@dataclass(slots=True)
class GroupContextView:
    title: str
    summary_lines: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    variables: list[ContextVariableRow] = field(default_factory=list)
    files: list[ContextFileRow] = field(default_factory=list)


@dataclass(slots=True)
class HostContextView:
    title: str
    summary_lines: list[str] = field(default_factory=list)
    variables: list[ContextVariableRow] = field(default_factory=list)
    files: list[ContextFileRow] = field(default_factory=list)
    trace_map: dict[str, str] = field(default_factory=dict)
    cli_suggestions: list[str] = field(default_factory=list)


def build_group_context_view(project: ProjectModel, scan: WorkspaceScanResult, group_name: str) -> GroupContextView:
    if group_name == "ungrouped":
        hosts = sorted(host_name for host_name, host in project.hosts.items() if not host.groups)
        summary_lines = [
            "Group: ungrouped",
            f"Hosts: {len(hosts)}",
            "This is the fallback branch for hosts with no explicit group membership.",
        ]
        return GroupContextView(title="ungrouped", summary_lines=summary_lines, hosts=hosts)

    group = project.groups.get(group_name)
    if group is None:
        raise KeyError(f"Unknown group: {group_name}")

    summary_lines = [
        f"Group: {group_name}",
        f"Direct hosts: {len(group.hosts)}",
        f"Child groups: {len(group.children)}",
        f"Variables: {len(group.variables)}",
    ]

    variables: list[ContextVariableRow] = []
    files: list[ContextFileRow] = []
    seen_files: set[str] = set()

    for variable in group.variables:
        source_path = variable.source.source_path
        variables.append(
            ContextVariableRow(
                key=variable.key,
                value_text=_value_text(variable.value),
                scope=variable.scope.value,
                source_path=source_path,
                source_type=variable.source.source_type,
                color=_scope_color(variable.scope.value, source_path),
            )
        )
        _add_unique_file(files, seen_files, source_path, _kind_for_path(source_path))

    for path in scan.group_var_paths:
        if path.startswith(f"group_vars/{group_name}/"):
            _add_unique_file(files, seen_files, path, _kind_for_path(path))

    for path in scan.vault_files:
        if path.startswith(f"group_vars/{group_name}/"):
            _add_unique_file(files, seen_files, path, _kind_for_path(path))

    return GroupContextView(
        title=group_name,
        summary_lines=summary_lines,
        hosts=sorted(group.hosts),
        children=sorted(group.children),
        variables=variables,
        files=files,
    )


def build_host_context_view(
    project: ProjectModel,
    scan: WorkspaceScanResult,
    host_name: str,
    branch_group_name: str | None,
) -> HostContextView:
    host = project.hosts.get(host_name)
    if host is None:
        raise KeyError(f"Unknown host: {host_name}")

    branch_label = branch_group_name if branch_group_name not in (None, "", "ungrouped") else "ungrouped"
    branch_groups = project.branch_groups_for_context(branch_group_name)
    effective = project.effective_variables_for_branch(host_name, branch_group_name)
    traces = trace_variables_for_branch(project, host_name, branch_group_name)

    summary_lines = [
        f"Host: {host_name}",
        f"Branch: {branch_label}",
        f"Direct groups: {', '.join(sorted(host.groups)) if host.groups else '-'}",
        f"Context groups: {', '.join(branch_groups) if branch_groups else '-'}",
        f"Effective variables: {len(effective)}",
    ]

    variables: list[ContextVariableRow] = []
    for key, variable in sorted(effective.items(), key=lambda item: item[0].lower()):
        source_path = variable.source.source_path
        variables.append(
            ContextVariableRow(
                key=key,
                value_text=_value_text(variable.value),
                scope=variable.scope.value,
                source_path=source_path,
                source_type=variable.source.source_type,
                color=_scope_color(variable.scope.value, source_path),
            )
        )

    files: list[ContextFileRow] = []
    seen_files: set[str] = set()

    for group_name in branch_groups:
        group = project.groups.get(group_name)
        if group is None:
            continue
        for variable in group.variables:
            _add_unique_file(files, seen_files, variable.source.source_path, _kind_for_path(variable.source.source_path))

    for variable in host.variables:
        _add_unique_file(files, seen_files, variable.source.source_path, _kind_for_path(variable.source.source_path))

    for path in scan.group_var_paths:
        if any(path.startswith(f"group_vars/{group_name}/") for group_name in branch_groups):
            _add_unique_file(files, seen_files, path, _kind_for_path(path))

    for path in scan.host_var_paths:
        if path.startswith(f"host_vars/{host_name}/"):
            _add_unique_file(files, seen_files, path, _kind_for_path(path))

    for path in scan.vault_files:
        if path.startswith("group_vars/all/"):
            _add_unique_file(files, seen_files, path, _kind_for_path(path))
        elif any(path.startswith(f"group_vars/{group_name}/") for group_name in branch_groups if group_name != "all"):
            _add_unique_file(files, seen_files, path, _kind_for_path(path))
        elif path.startswith(f"host_vars/{host_name}/"):
            _add_unique_file(files, seen_files, path, _kind_for_path(path))

    trace_map = {
        item.key: explain_variable_for_branch(project, host_name, branch_group_name, item.key)
        for item in traces
    }

    cli_suggestions = generate_ansible_command_suggestions(project, scan, host_name)

    return HostContextView(
        title=host_name,
        summary_lines=summary_lines,
        variables=variables,
        files=files,
        trace_map=trace_map,
        cli_suggestions=cli_suggestions,
    )
