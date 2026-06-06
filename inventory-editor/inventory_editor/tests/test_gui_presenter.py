from inventory_editor.analyzer.issues import Issue, IssueSeverity
from inventory_editor.analyzer.workspace_quality import WorkspaceQualityReport
from inventory_editor.gui.presenter import build_workspace_overview
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource
from inventory_editor.models.workspace import WorkspaceScanResult


def test_build_workspace_overview():
    project = ProjectModel(root_path=".")
    project.add_variable_to_group(
        "all",
        Variable(
            key="debug",
            value=True,
            scope=VariableScope.GROUP,
            owner="all",
            source=VariableSource(
                source_path="group_vars/all/main.yml",
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
                source_path="host_vars/web01/main.yml",
                source_type="host_vars",
            ),
        ),
    )

    scan = WorkspaceScanResult(
        root_path="/tmp/inventory",
        inventory_files=["inventory.yml"],
        group_var_paths=["group_vars/all/main.yml"],
        host_var_paths=["host_vars/web01/main.yml"],
        vault_files=["group_vars/web/vault.yml"],
        backup_files=["inventory.yml-20240522"],
        unknown_paths=["notes.txt"],
    )
    report = WorkspaceQualityReport(
        issues=[Issue(severity=IssueSeverity.C, message="Unknown file", source_path="notes.txt")]
    )

    overview = build_workspace_overview(project, scan, report)

    assert ("Groups", "2") in overview.stats
    assert ("Hosts", "1") in overview.stats
    assert overview.groups[0].name == "all"
    assert "debug = True" in overview.groups[0].variables
    assert "http_port = 8080" in overview.hosts[0].variables
    assert "[C] Unknown file" in overview.issues[0]
