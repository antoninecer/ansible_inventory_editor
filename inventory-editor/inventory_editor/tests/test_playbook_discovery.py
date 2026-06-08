from inventory_editor.analyzer.playbook_discovery import analyze_playbook, discover_tags_in_playbook


def test_analyze_playbook_extracts_tags_roles_and_tasks(tmp_path):
    playbook = tmp_path / "site.yml"
    playbook.write_text(
        """
- name: Repair
  hosts: all
  become: true
  gather_facts: false
  tags:
    - repair
  roles:
    - role: zabbix_agent
      tags:
        - zabbix
  tasks:
    - name: Check uptime
      ansible.builtin.command: uptime
      tags:
        - uptime
    - name: Block test
      block:
        - name: Restart service
          ansible.builtin.service:
            name: zabbix-agent
            state: restarted
          tags:
            - restart
""".strip()
        + "\n",
        encoding="utf-8",
    )

    summary = analyze_playbook(playbook)

    assert len(summary.plays) == 1
    assert summary.plays[0].name == "Repair"
    assert summary.plays[0].hosts == "all"
    assert summary.plays[0].become is True
    assert summary.plays[0].gather_facts is False
    assert "zabbix_agent" in summary.roles
    assert "repair" in summary.tags
    assert "zabbix" in summary.tags
    assert "uptime" in summary.tags
    assert "restart" in summary.tags

    task_names = [task.name for task in summary.plays[0].tasks]
    assert "Check uptime" in task_names
    assert "Restart service" in task_names


def test_discover_tags_in_playbook_keeps_old_api(tmp_path):
    playbook = tmp_path / "site.yml"
    playbook.write_text(
        """
- hosts: all
  tasks:
    - name: Task
      debug:
        msg: hi
      tags:
        - hello
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert discover_tags_in_playbook(playbook) == ["hello"]
