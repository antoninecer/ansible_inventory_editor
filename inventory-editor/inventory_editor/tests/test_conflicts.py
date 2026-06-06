from inventory_editor.analyzer.conflicts import find_conflicts
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource


def test_duplicate_host_variable_conflict():
    model = ProjectModel(root_path=".")

    var1 = Variable(
        key="app_env",
        value="prod",
        scope=VariableScope.HOST,
        owner="web01",
        source=VariableSource(
            source_path="host_vars/web01/main.yml",
            source_type="host_vars",
        ),
    )

    var2 = Variable(
        key="app_env",
        value="stage",
        scope=VariableScope.HOST,
        owner="web01",
        source=VariableSource(
            source_path="host_vars/web01/nginx.yml",
            source_type="host_vars",
        ),
    )

    model.add_variable_to_host("web01", var1)
    model.add_variable_to_host("web01", var2)

    issues = find_conflicts(model)

    assert len(issues) == 1
    assert issues[0].severity.value == "B"
