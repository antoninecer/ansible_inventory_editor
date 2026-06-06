from inventory_editor.io.workspace_exporter import export_workspace
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource


def test_export_workspace_preserves_source_file_names(tmp_path):
    project = ProjectModel(root_path=str(tmp_path))

    project.add_variable_to_group(
        "web",
        Variable(
            key="web_port",
            value=80,
            scope=VariableScope.GROUP,
            owner="web",
            source=VariableSource(
                source_path="group_vars/web/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    project.add_variable_to_group(
        "web",
        Variable(
            key="secret_token",
            value="abc",
            scope=VariableScope.GROUP,
            owner="web",
            source=VariableSource(
                source_path="group_vars/web/vault.yml",
                source_type="group_vars",
            ),
        ),
    )

    project.assign_host_to_group("web01", "web")

    project.add_variable_to_host(
        "web01",
        Variable(
            key="http_port",
            value=8080,
            scope=VariableScope.HOST,
            owner="web01",
            source=VariableSource(
                source_path="host_vars/web01/nginx.yml",
                source_type="host_vars",
            ),
        ),
    )

    export_workspace(project, tmp_path / "out")

    assert (tmp_path / "out" / "group_vars" / "web" / "main.yml").exists()
    assert (tmp_path / "out" / "group_vars" / "web" / "vault.yml").exists()
    assert (tmp_path / "out" / "host_vars" / "web01" / "nginx.yml").exists()
