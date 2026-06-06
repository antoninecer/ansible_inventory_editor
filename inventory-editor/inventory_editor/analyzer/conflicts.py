from collections import defaultdict

from inventory_editor.analyzer.issues import Issue, IssueSeverity
from inventory_editor.models.project import ProjectModel


def find_conflicts(project: ProjectModel) -> list[Issue]:
    issues: list[Issue] = []

    for group_name, group in project.groups.items():
        seen: dict[str, int] = defaultdict(int)
        for variable in group.variables:
            seen[variable.key] += 1
        for key, count in seen.items():
            if count > 1:
                issues.append(
                    Issue(
                        severity=IssueSeverity.B,
                        message=f"Duplicate group variable '{key}' in group '{group_name}'",
                    )
                )

    for host_name, host in project.hosts.items():
        seen: dict[str, int] = defaultdict(int)
        for variable in host.variables:
            seen[variable.key] += 1
        for key, count in seen.items():
            if count > 1:
                issues.append(
                    Issue(
                        severity=IssueSeverity.B,
                        message=f"Duplicate host variable '{key}' on host '{host_name}'",
                    )
                )

    return issues
