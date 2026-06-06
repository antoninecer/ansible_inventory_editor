from inventory_editor.models.variable import (
    Variable,
    VariableScope,
    VariableSource,
)


def test_variable_creation():
    variable = Variable(
        key="http_port",
        value=8080,
        scope=VariableScope.HOST,
        owner="web01",
        source=VariableSource(
            source_path="host_vars/web01/main.yml",
            source_type="host_vars",
        ),
    )

    assert variable.key == "http_port"
    assert variable.owner == "web01"
    assert variable.scope == VariableScope.HOST
