from inventory_editor.io.inventory_loader import load_inventory_file


def test_load_simple_inventory(tmp_path):
    inventory_file = tmp_path / "inventory.yml"
    inventory_file.write_text(
        """
all:
  hosts:
    localhost:
web:
  hosts:
    web01:
  children:
    all:
""".strip()
        + "\n",
        encoding="utf-8",
    )

    project = load_inventory_file(inventory_file)

    assert "all" in project.groups
    assert "web" in project.groups
    assert "localhost" in project.hosts
    assert "web01" in project.hosts
    assert "web" in project.hosts["web01"].groups
    assert "localhost" in project.groups["all"].hosts
