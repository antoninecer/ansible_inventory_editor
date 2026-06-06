from inventory_editor.analyzer.reporting import explain_variable_for_host
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource


def test_explain_variable_for_host():
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

    report = explain_variable_for_host(model, "web01", "http_port")

    assert "Effective value: 9090" in report
    assert "group_vars/all/main.yml" in report
    assert "host_vars/web01/main.yml" in report
