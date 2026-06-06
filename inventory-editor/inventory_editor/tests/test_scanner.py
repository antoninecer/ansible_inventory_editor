from inventory_editor.io.scanner import scan_inventory_workspace


def test_scan_inventory_workspace(tmp_path):
    root = tmp_path / "inventory"
    (root / "group_vars" / "all").mkdir(parents=True)
    (root / "group_vars" / "web").mkdir(parents=True)
    (root / "host_vars" / "web01").mkdir(parents=True)

    (root / "inventory.yml").write_text("---\n", encoding="utf-8")
    (root / "group_vars" / "all" / "main.yml").write_text("x: 1\n", encoding="utf-8")
    (root / "group_vars" / "web" / "main.yml").write_text("y: 2\n", encoding="utf-8")
    (root / "host_vars" / "web01" / "main.yml").write_text("z: 3\n", encoding="utf-8")
    (root / "inventory.yml-20240522").write_text("backup\n", encoding="utf-8")
    (root / "notes.txt").write_text("ignore me\n", encoding="utf-8")

    result = scan_inventory_workspace(root)

    assert "inventory.yml" in result.inventory_files
    assert "group_vars/all/main.yml" in result.group_var_paths
    assert "group_vars/web/main.yml" in result.group_var_paths
    assert "host_vars/web01/main.yml" in result.host_var_paths
    assert "inventory.yml-20240522" in result.backup_files
    assert "notes.txt" in result.unknown_paths
