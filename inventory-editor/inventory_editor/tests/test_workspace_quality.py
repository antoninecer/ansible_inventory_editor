from inventory_editor.analyzer.workspace_quality import analyze_workspace_scan
from inventory_editor.models.workspace import WorkspaceScanResult


def test_workspace_quality_flags_unknown_files():
    scan = WorkspaceScanResult(
        root_path="/tmp/inventory",
        inventory_files=["inventory.yml"],
        group_var_paths=["group_vars/all/main.yml"],
        host_var_paths=["host_vars/web01/main.yml"],
        unknown_paths=["notes.txt"],
    )

    report = analyze_workspace_scan(scan)

    assert len(report.issues) == 1
    assert report.issues[0].severity.value == "C"
    assert report.issues[0].source_path == "notes.txt"
