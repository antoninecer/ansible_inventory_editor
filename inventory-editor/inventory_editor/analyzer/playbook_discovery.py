from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


yaml = YAML(typ="safe")


@dataclass
class TaskSummary:
    name: str
    module: str
    tags: list[str] = field(default_factory=list)
    source_path: str = ""


@dataclass
class PlaySummary:
    name: str
    hosts: str
    become: bool | None = None
    gather_facts: bool | None = None
    tags: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    tasks: list[TaskSummary] = field(default_factory=list)


@dataclass
class PlaybookSummary:
    path: str
    plays: list[PlaySummary] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _as_list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(value, list):
        return [str(item) for item in value if item is not None]

    return [str(value)]


def _extract_role_name(role_item: Any) -> str | None:
    if isinstance(role_item, str):
        return role_item

    if isinstance(role_item, dict):
        role = role_item.get("role")
        if role:
            return str(role)

    return None


def _guess_task_module(task: dict[str, Any]) -> str:
    control_keys = {
        "name",
        "tags",
        "when",
        "register",
        "vars",
        "become",
        "become_user",
        "delegate_to",
        "ignore_errors",
        "changed_when",
        "failed_when",
        "loop",
        "with_items",
        "notify",
        "block",
        "rescue",
        "always",
    }

    for key in task:
        if key not in control_keys:
            return str(key)

    if "block" in task:
        return "block"

    return "-"


def _collect_tags_from_task_tree(item: Any, tags: set[str], tasks: list[TaskSummary], source_path: str) -> None:
    if not isinstance(item, dict):
        return

    item_tags = _as_list_of_strings(item.get("tags"))
    tags.update(item_tags)

    if "block" in item or "rescue" in item or "always" in item:
        for key in ("block", "rescue", "always"):
            value = item.get(key)
            if isinstance(value, list):
                for child in value:
                    _collect_tags_from_task_tree(child, tags, tasks, source_path)
        return

    task_name = str(item.get("name", ""))
    module = _guess_task_module(item)

    tasks.append(
        TaskSummary(
            name=task_name,
            module=module,
            tags=item_tags,
            source_path=source_path,
        )
    )


def analyze_playbook(playbook_path: str | Path) -> PlaybookSummary:
    path = Path(playbook_path).expanduser()
    summary = PlaybookSummary(path=str(path))

    try:
        data = yaml.load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        summary.warnings.append(f"Failed to read playbook: {exc}")
        return summary

    if not isinstance(data, list):
        summary.warnings.append("Playbook root is not a YAML list.")
        return summary

    all_tags: set[str] = set()
    all_roles: set[str] = set()

    for play in data:
        if not isinstance(play, dict):
            continue

        play_tags = _as_list_of_strings(play.get("tags"))
        all_tags.update(play_tags)

        roles: list[str] = []
        role_items = play.get("roles", [])

        if isinstance(role_items, list):
            for role_item in role_items:
                role_name = _extract_role_name(role_item)

                if role_name:
                    roles.append(role_name)
                    all_roles.add(role_name)

                if isinstance(role_item, dict):
                    role_tags = _as_list_of_strings(role_item.get("tags"))
                    all_tags.update(role_tags)

        tasks: list[TaskSummary] = []

        for section in ("pre_tasks", "tasks", "post_tasks"):
            section_items = play.get(section, [])

            if isinstance(section_items, list):
                for task in section_items:
                    _collect_tags_from_task_tree(task, all_tags, tasks, str(path))

        hosts = play.get("hosts", "-")

        summary.plays.append(
            PlaySummary(
                name=str(play.get("name", "")),
                hosts=str(hosts),
                become=play.get("become") if isinstance(play.get("become"), bool) else None,
                gather_facts=play.get("gather_facts") if isinstance(play.get("gather_facts"), bool) else None,
                tags=play_tags,
                roles=roles,
                tasks=tasks,
            )
        )

    summary.tags = sorted(all_tags)
    summary.roles = sorted(all_roles)

    return summary


def discover_tags_in_playbook(playbook_path: Path) -> list[str]:
    return analyze_playbook(playbook_path).tags
