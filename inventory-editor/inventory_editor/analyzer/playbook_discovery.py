from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML


yaml = YAML(typ="safe")


def discover_tags_in_playbook(playbook_path: Path) -> list[str]:
    try:
        data = yaml.load(playbook_path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    tags: set[str] = set()

    def _extract_tags(item: object) -> None:
        if isinstance(item, dict):
            t = item.get("tags")
            if isinstance(t, str):
                tags.add(t)
            elif isinstance(t, list):
                for tag in t:
                    if isinstance(tag, str):
                        tags.add(tag)

            # Recurse into common task containers
            for key in ("tasks", "pre_tasks", "post_tasks", "block", "rescue", "always"):
                val = item.get(key)
                if isinstance(val, list):
                    for subitem in val:
                        _extract_tags(subitem)

    for play in data:
        _extract_tags(play)

    return sorted(list(tags))
