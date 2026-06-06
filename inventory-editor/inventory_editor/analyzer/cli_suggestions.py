from __future__ import annotations

from pathlib import Path

from inventory_editor.analyzer.playbook_discovery import discover_tags_in_playbook
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.workspace import WorkspaceScanResult


def generate_ansible_command_suggestions(
    project: ProjectModel,
    scan_result: WorkspaceScanResult,
    host_name: str,
) -> list[str]:
    suggestions: list[str] = []

    if not scan_result.inventory_files:
        return suggestions

    inventory_file = scan_result.inventory_files[0]
    root = Path(scan_result.root_path)

    for playbook_rel in scan_result.playbook_files:
        playbook_path = root / playbook_rel
        tags = discover_tags_in_playbook(playbook_path)

        cmd = f"ansible-playbook -i {inventory_file} {playbook_rel} --limit {host_name}"

        if tags:
            # Suggest the first few tags or just show they exist
            # For the suggestion, we might just want to show the common ones or a placeholder
            # For now, let's just show them all comma-separated
            tag_str = ",".join(tags[:5])
            if len(tags) > 5:
                tag_str += ",..."
            cmd += f" --tags {tag_str}"

        if scan_result.vault_files:
            cmd += " --ask-vault-pass"

        suggestions.append(cmd)

    return suggestions
