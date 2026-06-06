from inventory_editor.io.workspace_loader import load_inventory_workspace


def test_load_inventory_workspace(tmp_path):
    root = tmp_path / "inventory"
    (root / "group_vars" / "all").mkdir(parents=True)
    (root / "host_vars" / "web01").mkdir(parents=True)

    (root / "inventory.yml").write_text(
        """
all:
  hosts:
    localhost:
web:
  hosts:
    web01:
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (root / "group_vars" / "all" / "main.yml").write_text("debug: true\n", encoding="utf-8")
    (root / "host_vars" / "web01" / "main.yml").write_text("http_port: 8080\n", encoding="utf-8")

    project, scan = load_inventory_workspace(root)

    assert "inventory.yml" in scan.inventory_files
    assert project.groups["all"].variables[0].key == "debug"
    assert project.hosts["web01"].variables[0].key == "http_port"
