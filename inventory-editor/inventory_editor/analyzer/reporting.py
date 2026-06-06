from __future__ import annotations

from inventory_editor.analyzer.tracing import trace_variables_for_branch, trace_variables_for_host
from inventory_editor.models.project import ProjectModel


def explain_variable_for_host(project: ProjectModel, host_name: str, key: str) -> str:
    traced = trace_variables_for_host(project, host_name)

    for item in traced:
        if item.key != key:
            continue

        lines = [
            f"Host: {host_name}",
            f"Variable: {key}",
            f"Effective value: {item.effective.value}",
            f"Effective source: {item.effective.source.source_path}",
            "Trace:",
        ]

        for variable in item.sources:
            lines.append(f"  - {variable.source.source_path}: {variable.value}")

        if item.overridden_by:
            lines.append("Overridden by:")
            for variable in item.overridden_by:
                lines.append(f"  - {variable.source.source_path}: {variable.value}")

        return "\n".join(lines)

    return f"Variable '{key}' not found for host '{host_name}'"


def explain_variable_for_branch(project: ProjectModel, host_name: str, branch_group_name: str | None, key: str) -> str:
    traced = trace_variables_for_branch(project, host_name, branch_group_name)

    for item in traced:
        if item.key != key:
            continue

        branch_label = branch_group_name if branch_group_name not in (None, "", "ungrouped") else "ungrouped"
        lines = [
            f"Host: {host_name}",
            f"Branch: {branch_label}",
            f"Variable: {key}",
            f"Effective value: {item.effective.value}",
            f"Effective source: {item.effective.source.source_path}",
            "Trace:",
        ]

        for variable in item.sources:
            lines.append(f"  - {variable.source.source_path}: {variable.value}")

        if item.overridden_by:
            lines.append("Overridden by:")
            for variable in item.overridden_by:
                lines.append(f"  - {variable.source.source_path}: {variable.value}")

        return "\n".join(lines)

    return f"Variable '{key}' not found for host '{host_name}' in branch '{branch_group_name}'"
