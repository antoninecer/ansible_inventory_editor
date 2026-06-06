from __future__ import annotations

from dataclasses import dataclass

from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable


@dataclass(slots=True)
class TracedVariable:
    key: str
    effective: Variable
    sources: list[Variable]
    overridden_by: list[Variable]


def trace_variables_for_host(project: ProjectModel, host_name: str) -> list[TracedVariable]:
    if host_name not in project.hosts:
        raise KeyError(f"Unknown host: {host_name}")

    host = project.hosts[host_name]
    traced: dict[str, TracedVariable] = {}

    for group in project.ordered_groups_for_host(host_name):
        for variable in group.variables:
            if variable.key in traced:
                traced[variable.key].overridden_by.append(variable)
                traced[variable.key].effective = variable
                traced[variable.key].sources.append(variable)
            else:
                traced[variable.key] = TracedVariable(
                    key=variable.key,
                    effective=variable,
                    sources=[variable],
                    overridden_by=[],
                )

    for variable in host.variables:
        if variable.key in traced:
            traced[variable.key].overridden_by.append(variable)
            traced[variable.key].effective = variable
            traced[variable.key].sources.append(variable)
        else:
            traced[variable.key] = TracedVariable(
                key=variable.key,
                effective=variable,
                sources=[variable],
                overridden_by=[],
            )

    return list(traced.values())


def trace_variables_for_branch(project: ProjectModel, host_name: str, branch_group_name: str | None) -> list[TracedVariable]:
    if host_name not in project.hosts:
        raise KeyError(f"Unknown host: {host_name}")

    host = project.hosts[host_name]
    traced: dict[str, TracedVariable] = {}

    for group_name in project.branch_groups_for_context(branch_group_name):
        group = project.groups.get(group_name)
        if group is None:
            continue

        for variable in group.variables:
            if variable.key in traced:
                traced[variable.key].overridden_by.append(variable)
                traced[variable.key].effective = variable
                traced[variable.key].sources.append(variable)
            else:
                traced[variable.key] = TracedVariable(
                    key=variable.key,
                    effective=variable,
                    sources=[variable],
                    overridden_by=[],
                )

    for variable in host.variables:
        if variable.key in traced:
            traced[variable.key].overridden_by.append(variable)
            traced[variable.key].effective = variable
            traced[variable.key].sources.append(variable)
        else:
            traced[variable.key] = TracedVariable(
                key=variable.key,
                effective=variable,
                sources=[variable],
                overridden_by=[],
            )

    return list(traced.values())
