from dataclasses import dataclass

from inventory_editor.models.project import ProjectModel


@dataclass(slots=True)
class HostSearchResult:
    host_name: str
    groups: list[str]
    host_vars: list[str]
    group_vars: list[str]


def find_hosts(project: ProjectModel, query: str) -> list[HostSearchResult]:
    term = query.strip().lower()
    if not term:
        return []

    results: list[HostSearchResult] = []

    for host_name in sorted(project.hosts):
        if term not in host_name.lower():
            continue

        host = project.hosts[host_name]
        groups = sorted(host.groups)

        group_vars: list[str] = []
        for group_name in groups:
            group = project.groups.get(group_name)
            if group is None:
                continue
            for variable in group.variables:
                group_vars.append(f"{group_name}:{variable.key}")

        host_vars = [variable.key for variable in host.variables]

        results.append(
            HostSearchResult(
                host_name=host_name,
                groups=groups,
                host_vars=host_vars,
                group_vars=group_vars,
            )
        )

    return results


def describe_host(project: ProjectModel, host_name: str) -> str:
    if host_name not in project.hosts:
        return f"Host '{host_name}' not found"

    host = project.hosts[host_name]
    lines = [
        f"Host: {host_name}",
        f"Groups: {', '.join(sorted(host.groups)) if host.groups else '-'}",
        f"Host variables: {', '.join(variable.key for variable in host.variables) if host.variables else '-'}",
    ]

    if host.groups:
        lines.append("Group variables:")
        for group_name in sorted(host.groups):
            group = project.groups.get(group_name)
            if group is None:
                continue
            if not group.variables:
                lines.append(f"  - {group_name}: -")
                continue
            for variable in group.variables:
                lines.append(f"  - {group_name}: {variable.key}")

    return "\n".join(lines)
