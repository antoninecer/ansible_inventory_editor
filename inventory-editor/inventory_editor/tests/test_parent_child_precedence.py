from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource


def test_parent_group_overridden_by_child_group():
    model = ProjectModel(root_path=".")

    model.add_variable_to_group(
        "all",
        Variable(
            key="http_port",
            value=80,
            scope=VariableScope.GROUP,
            owner="all",
            source=VariableSource(
                source_path="group_vars/all/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    model.add_variable_to_group(
        "parent",
        Variable(
            key="http_port",
            value=81,
            scope=VariableScope.GROUP,
            owner="parent",
            source=VariableSource(
                source_path="group_vars/parent/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    model.add_variable_to_group(
        "child",
        Variable(
            key="http_port",
            value=82,
            scope=VariableScope.GROUP,
            owner="child",
            source=VariableSource(
                source_path="group_vars/child/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    model.groups["parent"].add_child("child")
    model.assign_host_to_group("web01", "child")

    effective = model.effective_variables_for_host("web01")

    assert effective["http_port"].value == 82
    assert effective["http_port"].source.source_path == "group_vars/child/main.yml"
