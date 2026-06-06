from inventory_editor.analyzer.host_search import describe_host, find_hosts
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource


def test_find_hosts_by_partial_name():
    model = ProjectModel(root_path=".")
    model.add_host("web01")
    model.add_host("db01")

    results = find_hosts(model, "web")

    assert len(results) == 1
    assert results[0].host_name == "web01"


def test_describe_host():
    model = ProjectModel(root_path=".")
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
    model.assign_host_to_group("web01", "web")
    model.add_variable_to_host(
        "web01",
        Variable(
            key="nginx_port",
            value=8080,
            scope=VariableScope.HOST,
            owner="web01",
            source=VariableSource(
                source_path="host_vars/web01/main.yml",
                source_type="host_vars",
            ),
        ),
    )

    text = describe_host(model, "web01")

    assert "Host: web01" in text
    assert "Groups: web" in text
    assert "http_port" in text
    assert "nginx_port" in text
