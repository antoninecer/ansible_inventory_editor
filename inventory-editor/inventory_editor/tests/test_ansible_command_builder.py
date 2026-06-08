from inventory_editor.analyzer.ansible_command_builder import (
    build_ansible_playbook_command,
    split_csv_values,
)


def test_split_csv_values():
    assert split_csv_values(["uptime,repair", "zabbix"]) == ["uptime", "repair", "zabbix"]


def test_build_ansible_playbook_command_basic(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    cmd = build_ansible_playbook_command(
        workspace=workspace,
        inventory="inventory.yml",
        playbook="playbooks/repair/uptime.yml",
        user="ansible",
        limit="pinda:&db_servers",
        tags=["uptime"],
        check=True,
    )

    assert cmd.to_argv() == [
        "ansible-playbook",
        "-i",
        "inventory.yml",
        "playbooks/repair/uptime.yml",
        "-u",
        "ansible",
        "-l",
        "pinda:&db_servers",
        "--tags",
        "uptime",
        "--check",
    ]

    assert cmd.to_shell() == (
        "ansible-playbook -i inventory.yml playbooks/repair/uptime.yml "
        "-u ansible -l 'pinda:&db_servers' --tags uptime --check"
    )
