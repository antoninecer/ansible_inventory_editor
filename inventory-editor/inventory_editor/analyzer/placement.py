from dataclasses import dataclass
from enum import Enum

from inventory_editor.models.project import ProjectModel


class PlacementScope(str, Enum):
    ALL = "all"
    GROUP = "group"
    HOST = "host"


class ConflictAction(str, Enum):
    KEEP = "keep"
    OVERWRITE = "overwrite"
    MOVE = "move"
    NONE = "none"


@dataclass(slots=True)
class PlacementCandidate:
    scope: PlacementScope
    owner: str
    target_file: str


@dataclass(slots=True)
class VariableConflict:
    key: str
    existing_value: object
    owner: str
    source_path: str


def suggest_placements(
    project: ProjectModel,
    host_name: str,
) -> list[PlacementCandidate]:

    if host_name not in project.hosts:
        return []

    host = project.hosts[host_name]

    candidates = [
        PlacementCandidate(
            scope=PlacementScope.ALL,
            owner="all",
            target_file="group_vars/all/main.yml",
        )
    ]

    for group_name in sorted(host.groups):
        candidates.append(
            PlacementCandidate(
                scope=PlacementScope.GROUP,
                owner=group_name,
                target_file=f"group_vars/{group_name}/main.yml",
            )
        )

    candidates.append(
        PlacementCandidate(
            scope=PlacementScope.HOST,
            owner=host_name,
            target_file=f"host_vars/{host_name}/main.yml",
        )
    )

    return candidates


def find_variable_conflicts(
    project: ProjectModel,
    host_name: str,
    key: str,
) -> list[VariableConflict]:

    conflicts: list[VariableConflict] = []

    if host_name not in project.hosts:
        return conflicts

    host = project.hosts[host_name]

    for variable in host.variables:
        if variable.key == key:
            conflicts.append(
                VariableConflict(
                    key=key,
                    existing_value=variable.value,
                    owner=host_name,
                    source_path=variable.source.source_path,
                )
            )

    for group_name in host.groups:
        group = project.groups.get(group_name)
        if group is None:
            continue

        for variable in group.variables:
            if variable.key == key:
                conflicts.append(
                    VariableConflict(
                        key=key,
                        existing_value=variable.value,
                        owner=group_name,
                        source_path=variable.source.source_path,
                    )
                )

    return conflicts
