from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource


def test_effective_variables_host_over_group_over_all():
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
        "web",
        Variable(
            key="http_port",
            value=8080,
            scope=VariableScope.GROUP,
            owner="web",
            source=VariableSource(
                source_path="group_vars/web/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    model.assign_host_to_group("web01", "web")

    model.add_variable_to_host(
        "web01",
        Variable(
            key="http_port",
            value=9090,
            scope=VariableScope.HOST,
            owner="web01",
            source=VariableSource(
                source_path="host_vars/web01/main.yml",
                source_type="host_vars",
            ),
        ),
    )

    effective = model.effective_variables_for_host("web01")

    assert effective["http_port"].value == 9090
    assert effective["http_port"].source.source_path == "host_vars/web01/main.yml"
