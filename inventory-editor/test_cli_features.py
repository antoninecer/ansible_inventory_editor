from pathlib import Path
from inventory_editor.io.scanner import scan_inventory_workspace
from inventory_editor.models.project import ProjectModel
from inventory_editor.analyzer.cli_suggestions import generate_ansible_command_suggestions

def test_cli_features():
    # Create a dummy workspace
    root = Path("test_workspace")
    root.mkdir(exist_ok=True)
    (root / "inventory.yml").write_text("all:\n  hosts:\n    localhost:\n")
    (root / "playbooks").mkdir(exist_ok=True)
    
    # A dummy playbook with tags
    playbook_content = """
- name: Test Play
  hosts: all
  tags: [setup, common]
  tasks:
    - name: Task 1
      debug: msg="hello"
      tags: install
"""
    (root / "playbooks" / "site.yml").write_text(playbook_content)
    
    # Scan
    scan = scan_inventory_workspace(root)
    print(f"Inventory files: {scan.inventory_files}")
    print(f"Playbook files: {scan.playbook_files}")
    
    # Project
    project = ProjectModel(root_path=str(root))
    project.add_host("localhost")
    
    # Suggestions
    suggestions = generate_ansible_command_suggestions(project, scan, "localhost")
    print("Suggestions:")
    for s in suggestions:
        print(f"  {s}")

    # Cleanup
    import shutil
    shutil.rmtree(root)

if __name__ == "__main__":
    test_cli_features()
