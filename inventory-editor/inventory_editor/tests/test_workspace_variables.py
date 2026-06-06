from inventory_editor.io.inventory_loader import load_inventory_file, load_workspace_variables


def test_load_workspace_variables(tmp_path):
    root = tmp_path / "inventory"
    (root / "group_vars" / "web").mkdir(parents=True)
    (root / "host_vars" / "web01").mkdir(parents=True)

    (root / "inventory.yml").write_text(
        """
web:
  hosts:
    web01:
""".strip() + "\n",
        encoding="utf-8",
    )

    (root / "group_vars" / "web" / "main.yml").write_text("http_port: 80\n", encoding="utf-8")
    (root / "group_vars" / "web" / "vault.yml").write_text("secret_token: abc\n", encoding="utf-8")
    (root / "host_vars" / "web01" / "nginx.yml").write_text("http_port: 8080\n", encoding="utf-8")

    project = load_inventory_file(root / "inventory.yml")
    load_workspace_variables(project, root)

    assert any(v.key == "http_port" and v.value == 80 for v in project.groups["web"].variables)
    assert any(v.key == "secret_token" and v.value == "abc" for v in project.groups["web"].variables)
    assert any(v.key == "http_port" and v.value == 8080 for v in project.hosts["web01"].variables)
