from inventory_editor.models.project import ProjectModel


def test_project_contains_all_group():
    model = ProjectModel(root_path=".")

    assert "all" in model.groups
    assert model.group_count() == 1


def test_add_host():
    model = ProjectModel(root_path=".")

    model.add_host("server01")

    assert model.host_count() == 1


def test_assign_host_to_group():
    model = ProjectModel(root_path=".")

    model.assign_host_to_group(
        host_name="web01",
        group_name="web",
    )

    assert "web01" in model.hosts

    assert "web" in model.groups

    assert "web" in model.hosts["web01"].groups

    assert "web01" in model.groups["web"].hosts
