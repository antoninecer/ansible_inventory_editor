from inventory_editor.analyzer.placement import (
    PlacementScope,
    find_variable_conflicts,
    suggest_placements,
)
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import (
    Variable,
    VariableScope,
    VariableSource,
)


def test_suggest_placements():
    model = ProjectModel(root_path=".")

    model.assign_host_to_group(
        "web01",
        "web",
    )

    placements = suggest_placements(
        model,
        "web01",
    )

    assert len(placements) == 3

    assert placements[0].scope == PlacementScope.ALL
    assert placements[1].scope == PlacementScope.GROUP
    assert placements[2].scope == PlacementScope.HOST


def test_find_variable_conflicts():
    model = ProjectModel(root_path=".")

    model.assign_host_to_group(
        "web01",
        "web",
    )

    model.add_variable_to_group(
        "web",
        Variable(
            key="http_port",
            value=80,
            scope=VariableScope.GROUP,
            owner="web",
            source=VariableSource(
                source_path="group_vars/web/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    conflicts = find_variable_conflicts(
        model,
        "web01",
        "http_port",
    )

    assert len(conflicts) == 1
    assert conflicts[0].owner == "web"
