from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource


def test_add_group_variable():
    model = ProjectModel(root_path=".")

    variable = Variable(
        key="web_port",
        value=80,
        scope=VariableScope.GROUP,
        owner="web",
        source=VariableSource(
            source_path="group_vars/web/main.yml",
            source_type="group_vars",
        ),
    )

    model.add_variable_to_group("web", variable)

    assert "web" in model.groups
    assert len(model.groups["web"].variables) == 1


def test_add_host_variable():
    model = ProjectModel(root_path=".")

    variable = Variable(
        key="nginx_port",
        value=8080,
        scope=VariableScope.HOST,
        owner="web01",
        source=VariableSource(
            source_path="host_vars/web01/main.yml",
            source_type="host_vars",
        ),
    )

    model.add_variable_to_host("web01", variable)

    assert "web01" in model.hosts
    assert len(model.hosts["web01"].variables) == 1
