from dataclasses import dataclass

from inventory_editor.analyzer.issues import Issue, IssueSeverity
from inventory_editor.models.workspace import WorkspaceScanResult


@dataclass(slots=True)
class WorkspaceQualityReport:
    issues: list[Issue]


def analyze_workspace_scan(scan: WorkspaceScanResult) -> WorkspaceQualityReport:
    issues: list[Issue] = []

    for path in scan.unknown_paths:
        issues.append(
            Issue(
                severity=IssueSeverity.C,
                message=f"Unknown file in inventory workspace: {path}",
                source_path=path,
            )
        )

    return WorkspaceQualityReport(issues=issues)
