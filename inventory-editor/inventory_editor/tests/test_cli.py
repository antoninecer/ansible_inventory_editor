from inventory_editor.cli import main


def test_cli_prints_summary(tmp_path, capsys):
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
    (root / "notes.txt").write_text("ignore me\n", encoding="utf-8")

    rc = main([str(root), "--vault-password-file", "~/.ansible/vault-pass.txt"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Workspace:" in captured.out
    assert "Groups:" in captured.out
    assert "Vault password file:" in captured.out
    assert "Unknown files: 1" in captured.out
