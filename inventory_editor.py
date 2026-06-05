#!/usr/bin/env python3
"""Inventory editor GUI for Ansible YAML inventories.

This version preserves comments and blank lines by editing the original
text instead of dumping the full YAML tree on save.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"Tkinter is required: {exc}")

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"PyYAML is required: {exc}")


DEFAULT_INVENTORY_FILE = Path("../ansible/inventory/inventory.yml")

TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+:\s*$")
SECTION_KEY_RE = re.compile(r"^  [A-Za-z0-9_.-]+:\s*$")
ACTIVE_HOST_LINE_RE = re.compile(r"^    (?!#)(.+?):(?:\s*#.*)?\s*$")
COMMENTED_HOST_LINE_RE = re.compile(r"^    #(.+?):(?:\s*#.*)?\s*$")


def is_mapping(value: Any) -> bool:
    return isinstance(value, dict)


class HostEntry:
    def __init__(self, name: str, vars: Dict[str, Any]):
        self.name = name
        self.vars = vars


class InventoryModel:
    def __init__(self) -> None:
        self.path: Optional[Path] = None
        self.data: Dict[str, Any] = {}
        self.text: str = ""
        self.original_text: str = ""

    def _reload_data(self) -> None:
        loaded = yaml.safe_load(self.text)
        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            raise ValueError("Inventory root must be a mapping")
        self.data = loaded

    def _set_text(self, text: str) -> None:
        self.text = text
        self._reload_data()

    def load(self, path: os.PathLike[str] | str) -> None:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(p)
        self.path = p
        self.text = p.read_text(encoding="utf-8")
        self.original_text = self.text
        self._reload_data()

    def save(self, path: Optional[os.PathLike[str] | str] = None) -> Path:
        target = Path(path).expanduser().resolve() if path else self.path
        if target is None:
            raise ValueError("No inventory file loaded")

        target.parent.mkdir(parents=True, exist_ok=True)
        backup_path = self.backup(target)
        target.write_text(self.text, encoding="utf-8")
        self.path = target
        self.original_text = self.text
        return backup_path

    def backup(self, path: Optional[os.PathLike[str] | str] = None) -> Path:
        src = Path(path).expanduser().resolve() if path else self.path
        if src is None:
            raise ValueError("No inventory file loaded")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = src.with_name(f"{src.name}.{ts}.bak")
        shutil.copy2(src, backup)
        return backup

    def _lines(self) -> List[str]:
        return self.text.splitlines(keepends=True)

    def _group_span(self, group: str) -> Tuple[List[str], int, int]:
        lines = self._lines()
        start = None
        for i, line in enumerate(lines):
            if TOP_LEVEL_KEY_RE.match(line):
                key = line.strip()[:-1]
                if key == group:
                    start = i
                    break
        if start is None:
            raise KeyError(f"Group '{group}' not found")

        end = len(lines)
        for j in range(start + 1, len(lines)):
            if TOP_LEVEL_KEY_RE.match(lines[j]):
                end = j
                break
        return lines, start, end

    def _hosts_span(self, group: str) -> Tuple[List[str], int, int]:
        lines, start, end = self._group_span(group)
        hosts_line = None
        for i in range(start + 1, end):
            if lines[i].rstrip("\n").rstrip("\n") == "  hosts:":
                hosts_line = i
                break
        if hosts_line is None:
            raise ValueError(f"Group '{group}' has no hosts section")

        body_start = hosts_line + 1
        section_end = end
        for j in range(body_start, end):
            line = lines[j]
            stripped = line.strip()
            if stripped and (len(line) - len(line.lstrip(" "))) <= 2:
                section_end = j
                break

        block_lines = lines[body_start:section_end]
        blocks, consumed = self._host_blocks_for_sort(block_lines)
        if not blocks:
            return lines, body_start, section_end
        return lines, body_start, body_start + consumed

    def _format_host_entry(self, host: str, host_vars: Optional[Dict[str, Any]] = None) -> List[str]:
        out = [f"    {host}:\n"]
        if host_vars:
            dumped = yaml.safe_dump(
                host_vars,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
                width=120,
            ).splitlines()
            for line in dumped:
                out.append(f"      {line}\n")
        return out

    def _remove_host_entries_from_block(self, block_lines: List[str], host: str) -> Tuple[List[str], bool]:
        entries = self._host_entries(block_lines)
        remove_starts = {start for name, start, _end, _block in entries if name == host}
        remove_ends = {start: end for name, start, end, _block in entries if name == host}
        if not remove_starts:
            return block_lines, False

        out: List[str] = []
        i = 0
        while i < len(block_lines):
            if i in remove_ends:
                i = remove_ends[i]
                continue
            out.append(block_lines[i])
            i += 1
        return out, True

    def _insert_host_entry_into_block(
        self,
        block_lines: List[str],
        host: str,
        host_vars: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        new_entry = self._format_host_entry(host, host_vars)
        entries = self._host_entries(block_lines)
        if not entries:
            return new_entry + block_lines

        insert_at = entries[-1][2]
        for name, start, _end, _block in entries:
            if name.lower() > host.lower():
                insert_at = start
                break

        out: List[str] = []
        inserted = False
        i = 0
        while i < len(block_lines):
            if not inserted and i == insert_at:
                out.extend(new_entry)
                inserted = True
            out.append(block_lines[i])
            i += 1

        if not inserted:
            out.extend(new_entry)
        return out

    def _replace_hosts_block(self, group: str, transform) -> None:
        lines, body_start, body_end = self._hosts_span(group)
        block = lines[body_start:body_end]
        new_block = transform(block)
        new_lines = lines[:body_start] + new_block + lines[body_end:]
        self._set_text("".join(new_lines))

    def _clean_block_lines(self, lines: List[str]) -> List[str]:
        return [line for line in lines if line.strip() != ""]

    def _host_blocks_for_sort(self, block_lines: List[str]) -> Tuple[List[Tuple[str, List[str]]], int]:
        """Return host blocks and the number of consumed lines.

        A block starts at either an active host line (`    host:`) or a commented host
        line (`    #host:`). Comment lines directly before a host stay attached to that
        host. Comments and indented lines after a host remain in the same block until
        the next host line. Blank lines inside the hosts section are discarded.
        """
        blocks: List[Tuple[str, List[str]]] = []
        pending_prefix: List[str] = []
        i = 0
        consumed = 0

        while i < len(block_lines):
            line = block_lines[i]
            if line.strip() == "":
                i += 1
                continue

            consumed = i + 1
            match = ACTIVE_HOST_LINE_RE.match(line) or COMMENTED_HOST_LINE_RE.match(line)
            if not match:
                pending_prefix.append(line)
                i += 1
                continue

            current_name = match.group(1).strip()
            current_lines: List[str] = pending_prefix[:] + [line]
            pending_prefix = []
            i += 1

            while i < len(block_lines):
                nxt = block_lines[i]
                if nxt.strip() == "":
                    i += 1
                    continue
                if ACTIVE_HOST_LINE_RE.match(nxt) or COMMENTED_HOST_LINE_RE.match(nxt):
                    break
                current_lines.append(nxt)
                consumed = i + 1
                i += 1

            blocks.append((current_name, current_lines))

        if pending_prefix and blocks:
            blocks[-1] = (blocks[-1][0], blocks[-1][1] + pending_prefix)
            consumed = max(consumed, len(block_lines))
        elif pending_prefix and not blocks:
            blocks.append(("", pending_prefix))
            consumed = len(block_lines)

        return blocks, consumed

    def _top_level_sections(self) -> List[Tuple[List[str], List[Tuple[str, List[str]]]]]:
        """Split the file into top-level sections.

        Top-level comment lines (column 0) act as section separators. Groups within a
        section can be sorted without moving the comment header to a different area.
        """
        lines = self._lines()
        sections: List[Tuple[List[str], List[Tuple[str, List[str]]]]] = []
        current_prefix: List[str] = []
        current_blocks: List[Tuple[str, List[str]]] = []
        pending_prefix: List[str] = []
        current_name: Optional[str] = None
        current_lines: List[str] = []

        def flush_block() -> None:
            nonlocal current_name, current_lines
            if current_name is not None:
                current_blocks.append((current_name, current_lines))
                current_name = None
                current_lines = []

        def flush_section() -> None:
            nonlocal current_prefix, current_blocks
            if current_prefix or current_blocks:
                sections.append((current_prefix, current_blocks))
            current_prefix = []
            current_blocks = []

        for line in lines:
            if TOP_LEVEL_KEY_RE.match(line):
                if current_name is not None:
                    flush_block()
                if not current_blocks and not current_prefix:
                    current_prefix = pending_prefix
                pending_prefix = []
                current_name = line.strip()[:-1]
                current_lines = [line]
                continue

            if line.startswith("#") and not line.startswith(" "):
                if current_name is not None:
                    flush_block()
                if current_blocks or current_prefix:
                    flush_section()
                pending_prefix.append(line)
                continue

            if current_name is not None:
                current_lines.append(line)
            else:
                pending_prefix.append(line)

        if current_name is not None:
            flush_block()
        if current_blocks or current_prefix or pending_prefix:
            if not current_prefix:
                current_prefix = pending_prefix
            elif pending_prefix:
                current_prefix.extend(pending_prefix)
            sections.append((current_prefix, current_blocks))
        return sections

    def _write_top_level_sections(self, sections: List[Tuple[List[str], List[Tuple[str, List[str]]]]]) -> None:
        out: List[str] = []
        first_section = True
        for prefix, blocks in sections:
            if not first_section and out and out[-1].strip() != "":
                out.append("\n")
            first_section = False
            out.extend(prefix)
            for idx, (_name, block) in enumerate(blocks):
                if idx > 0:
                    out.append("\n")
                trimmed = block[:]
                while trimmed and trimmed[0].strip() == "":
                    trimmed.pop(0)
                while trimmed and trimmed[-1].strip() == "":
                    trimmed.pop()
                out.extend(trimmed)
        self._set_text("".join(out))

    def top_groups(self) -> List[str]:
        return list(self.data.keys())

    def group_node(self, group: str) -> Dict[str, Any]:
        node = self.data.get(group)
        if not isinstance(node, dict):
            node = {}
            self.data[group] = node
        return node

    def group_hosts(self, group: str) -> Dict[str, Any]:
        node = self.group_node(group)
        hosts = node.get("hosts")
        if hosts is None:
            hosts = {}
            node["hosts"] = hosts
        if not isinstance(hosts, dict):
            raise ValueError(f"Group '{group}' has a non-mapping hosts section")
        return hosts

    def group_vars(self, group: str) -> Dict[str, Any]:
        node = self.group_node(group)
        vars_node = node.get("vars")
        if vars_node is None:
            vars_node = {}
            node["vars"] = vars_node
        if not isinstance(vars_node, dict):
            raise ValueError(f"Group '{group}' has a non-mapping vars section")
        return vars_node

    def group_children(self, group: str) -> Dict[str, Any]:
        node = self.group_node(group)
        children = node.get("children")
        if children is None:
            children = {}
            node["children"] = children
        if not isinstance(children, dict):
            raise ValueError(f"Group '{group}' has a non-mapping children section")
        return children

    def leaf_groups(self) -> List[str]:
        out: List[str] = []
        for group in self.top_groups():
            node = self.data.get(group, {})
            if isinstance(node, dict) and isinstance(node.get("hosts"), dict):
                out.append(group)
        return out

    def iter_hosts(self, group: str) -> List[HostEntry]:
        hosts = self.group_hosts(group)
        entries: List[HostEntry] = []
        for name, value in hosts.items():
            if value is None:
                entries.append(HostEntry(name=name, vars={}))
            elif isinstance(value, dict):
                entries.append(HostEntry(name=name, vars=value))
            else:
                entries.append(HostEntry(name=name, vars={"value": value}))
        return entries

    def sort_group_hosts(self, group: str) -> None:
        def transform(block: List[str]) -> List[str]:
            blocks, _ = self._host_blocks_for_sort(block)
            if not blocks:
                return block
            blocks = sorted(blocks, key=lambda item: item[0].lower())
            return [line for _name, lines in blocks for line in lines]

        self._replace_hosts_block(group, transform)

    def sort_all_hosts(self) -> None:
        for group in self.leaf_groups():
            self.sort_group_hosts(group)

    def sort_top_level_groups(self) -> None:
        sections = self._top_level_sections()
        if not sections:
            return
        sorted_sections: List[Tuple[List[str], List[Tuple[str, List[str]]]]] = []
        for prefix, blocks in sections:
            if blocks:
                blocks = sorted(blocks, key=lambda item: item[0].lower())
            sorted_sections.append((prefix, blocks))
        self._write_top_level_sections(sorted_sections)

    def sort_entire_inventory(self) -> None:
        # Full-file sorting is disabled in this build.
        # Top-level comments in this inventory carry meaning and should not be moved automatically.
        self.sort_all_hosts()

    def host_groups(self, host: str) -> List[str]:
        groups: List[str] = []
        for group in self.leaf_groups():
            hosts = self.group_hosts(group)
            if host in hosts:
                groups.append(group)
        return groups

    def add_host(self, host: str, groups: List[str], host_vars: Optional[Dict[str, Any]] = None) -> List[str]:
        if not host.strip():
            raise ValueError("Host name is empty")
        if not groups:
            raise ValueError("No target groups selected")
        changed: List[str] = []
        for group in groups:
            def transform(block: List[str]) -> List[str]:
                blocks, _ = self._host_blocks_for_sort(block)
                blocks = [item for item in blocks if item[0] != host]
                new_entry = self._format_host_entry(host, host_vars)
                insert_at = len(blocks)
                for idx, (name, _lines) in enumerate(blocks):
                    if name.lower() > host.lower():
                        insert_at = idx
                        break
                blocks = blocks[:insert_at] + [(host, new_entry)] + blocks[insert_at:]
                return [line for _name, lines in blocks for line in lines]

            self._replace_hosts_block(group, transform)
            changed.append(group)
        return changed

    def remove_host_from_group(self, host: str, group: str) -> bool:
        removed = False

        def transform(block: List[str]) -> List[str]:
            nonlocal removed
            block2, did_remove = self._remove_host_entries_from_block(block, host)
            removed = did_remove
            return block2

        self._replace_hosts_block(group, transform)
        return removed

    def remove_host_everywhere(self, host: str) -> List[str]:
        changed: List[str] = []
        for group in self.leaf_groups():
            if self.remove_host_from_group(host, group):
                changed.append(group)
        return changed

    def add_group(self, group: str) -> None:
        if group in self.data:
            return
        sep = "" if self.text.endswith("\n") else "\n"
        addition = f"{sep}{group}:\n  hosts:\n"
        self._set_text(self.text + addition)


class AddHostDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, groups: List[str]):
        super().__init__(parent)
        self.title("Add host")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.result: Optional[Tuple[str, List[str], Dict[str, Any]]] = None
        self.groups = groups

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        frm = ttk.Frame(self, padding=12)
        frm.grid(sticky="nsew")
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(2, weight=1)

        ttk.Label(frm, text="Host name:").grid(row=0, column=0, sticky="w")
        self.host_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.host_var, width=40).grid(row=0, column=1, sticky="ew", padx=(8, 0))

        ttk.Label(frm, text="Groups:").grid(row=1, column=0, sticky="nw", pady=(10, 0))
        self.group_list = tk.Listbox(frm, selectmode=tk.EXTENDED, height=min(14, max(6, len(groups))))
        for g in groups:
            self.group_list.insert(tk.END, g)
        self.group_list.grid(row=1, column=1, sticky="nsew", padx=(8, 0), pady=(10, 0))

        ttk.Label(frm, text="Vars (key=value per line):").grid(row=2, column=0, sticky="nw", pady=(10, 0))
        self.vars_text = tk.Text(frm, height=10, width=40)
        self.vars_text.grid(row=2, column=1, sticky="nsew", padx=(8, 0), pady=(10, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btns, text="Add", command=self._ok).pack(side=tk.RIGHT)

        if groups:
            self.group_list.selection_set(0)
        self.host_var.set("")
        self.vars_text.insert("1.0", "")
        self.bind("<Return>", lambda _e: self._ok())
        self.bind("<Escape>", lambda _e: self._cancel())

    def _parse_vars(self) -> Dict[str, Any]:
        raw = self.vars_text.get("1.0", tk.END).strip()
        if not raw:
            return {}
        out: Dict[str, Any] = {}
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"Invalid var line: '{line}'")
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
        return out

    def _selected_groups(self) -> List[str]:
        idxs = self.group_list.curselection()
        return [self.groups[i] for i in idxs]

    def _ok(self) -> None:
        host = self.host_var.get().strip()
        groups = self._selected_groups()
        try:
            vars_dict = self._parse_vars()
        except Exception as exc:
            messagebox.showerror("Invalid vars", str(exc), parent=self)
            return
        if not host:
            messagebox.showerror("Invalid host", "Host name cannot be empty.", parent=self)
            return
        if not groups:
            messagebox.showerror("Invalid groups", "Select at least one target group.", parent=self)
            return
        self.result = (host, groups, vars_dict)
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class InventoryEditorApp(tk.Tk):
    def __init__(self, default_path: Path = DEFAULT_INVENTORY_FILE) -> None:
        super().__init__()
        self.title("Ansible Inventory Editor")
        self.geometry("1200x760")
        self.minsize(960, 640)

        self.model = InventoryModel()
        self.current_group: Optional[str] = None
        self.current_host: Optional[str] = None
        self.auto_sort_var = tk.BooleanVar(value=True)
        self.search_var = tk.StringVar()
        self.path_var = tk.StringVar(value=str(default_path))
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self._bind_shortcuts()

        try:
            self.load_path(default_path)
        except Exception as exc:
            self.status_var.set(f"Load failed: {exc}")

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=(10, 10, 10, 6))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Inventory file:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.path_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(top, text="Load", command=self.load_from_entry).grid(row=0, column=3, padx=(0, 6))
        ttk.Checkbutton(top, text="Auto-sort after edits", variable=self.auto_sort_var).grid(row=0, column=4, padx=(8, 0))

        main = ttk.Frame(self, padding=(10, 0, 10, 10))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Labelframe(main, text="Inventory tree")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        search_bar = ttk.Frame(left, padding=8)
        search_bar.grid(row=0, column=0, sticky="ew")
        search_bar.columnconfigure(1, weight=1)
        ttk.Label(search_bar, text="Search host:").grid(row=0, column=0, sticky="w")
        ttk.Entry(search_bar, textvariable=self.search_var).grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ttk.Button(search_bar, text="Find", command=self.find_host).grid(row=0, column=2)
        ttk.Button(search_bar, text="Clear", command=self.clear_search).grid(row=0, column=3, padx=(6, 0))

        self.tree = ttk.Treeview(left, columns=("kind",), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Name")
        self.tree.heading("kind", text="Type")
        self.tree.column("#0", width=280, anchor="w")
        self.tree.column("kind", width=110, anchor="w")
        yscroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        yscroll.grid(row=1, column=1, sticky="ns", pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        right = ttk.Labelframe(main, text="Group details")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        info = ttk.Frame(right, padding=8)
        info.grid(row=0, column=0, sticky="ew")
        info.columnconfigure(1, weight=1)
        ttk.Label(info, text="Selected group:").grid(row=0, column=0, sticky="w")
        self.group_label = ttk.Label(info, text="-", font=("TkDefaultFont", 10, "bold"))
        self.group_label.grid(row=0, column=1, sticky="w")
        ttk.Label(info, text="Hosts:").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.count_label = ttk.Label(info, text="0")
        self.count_label.grid(row=1, column=1, sticky="w", pady=(4, 0))

        list_frame = ttk.Frame(right, padding=(8, 0, 8, 8))
        list_frame.grid(row=1, column=0, sticky="ew")
        list_frame.columnconfigure(0, weight=1)
        self.hosts_list = tk.Listbox(list_frame, height=18, exportselection=False)
        host_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.hosts_list.yview)
        self.hosts_list.configure(yscrollcommand=host_scroll.set)
        self.hosts_list.grid(row=0, column=0, sticky="nsew")
        host_scroll.grid(row=0, column=1, sticky="ns")
        self.hosts_list.bind("<<ListboxSelect>>", self.on_host_select)

        self.host_detail = tk.Text(right, height=10, wrap="word")
        self.host_detail.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.host_detail.configure(state="disabled")

        buttons = ttk.Frame(right, padding=8)
        buttons.grid(row=3, column=0, sticky="ew")
        for i in range(3):
            buttons.columnconfigure(i, weight=1)
        ttk.Button(buttons, text="Add host", command=self.add_host).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Remove selected host", command=self.remove_selected_host).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(buttons, text="Remove host everywhere", command=self.remove_host_everywhere).grid(row=0, column=2, sticky="ew", padx=(4, 0))
        ttk.Button(buttons, text="Sort current group", command=self.sort_current_group).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(6, 0))
        ttk.Button(buttons, text="Sort all groups", command=self.sort_all_groups).grid(row=1, column=1, sticky="ew", padx=4, pady=(6, 0))
        ttk.Button(buttons, text="Save", command=self.save_inventory).grid(row=1, column=2, sticky="ew", padx=(4, 0), pady=(6, 0))

        bottom = ttk.Frame(self, padding=(10, 0, 10, 8))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        ttk.Label(bottom, textvariable=self.status_var).grid(row=0, column=0, sticky="w")

    def _bind_shortcuts(self) -> None:
        self.bind("<Control-s>", lambda _e: self.save_inventory())
        self.bind("<Control-o>", lambda _e: self.load_from_entry())
        self.bind("<F5>", lambda _e: self.reload_current())
        self.bind("<Control-a>", lambda _e: self.add_host())
        self.bind("<Delete>", lambda _e: self.remove_selected_host())

    def browse_file(self) -> None:
        initial = str(Path(self.path_var.get()).expanduser())
        path = filedialog.askopenfilename(
            title="Open inventory YAML",
            initialdir=str(Path(initial).parent if initial else Path.cwd()),
            filetypes=[("YAML files", "*.yml *.yaml"), ("All files", "*.*")],
        )
        if path:
            self.path_var.set(path)
            self.load_from_entry()

    def load_from_entry(self) -> None:
        self.load_path(self.path_var.get())

    def load_path(self, path: os.PathLike[str] | str) -> None:
        self.model.load(path)
        self.refresh_all()
        self.status_var.set(f"Loaded: {self.model.path}")

    def reload_current(self) -> None:
        if self.model.path is None:
            return
        self.load_path(self.model.path)

    def refresh_all(self) -> None:
        self.refresh_tree()
        groups = self.model.leaf_groups()
        if self.current_group not in groups:
            self.current_group = groups[0] if groups else None
        self.refresh_group_panel()

    def refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for group in self.model.top_groups():
            node = self.model.data.get(group, {})
            if not isinstance(node, dict):
                continue
            counts = []
            if isinstance(node.get("hosts"), dict):
                counts.append(f"hosts={len(node['hosts'])}")
            if isinstance(node.get("children"), dict):
                counts.append(f"children={len(node['children'])}")
            if isinstance(node.get("vars"), dict):
                counts.append(f"vars={len(node['vars'])}")
            group_id = self.tree.insert("", tk.END, text=group, values=(", ".join(counts) if counts else "group",))

            if isinstance(node.get("vars"), dict):
                vars_id = self.tree.insert(group_id, tk.END, text="vars", values=(f"{len(node['vars'])} items",))
                for key, value in node["vars"].items():
                    self.tree.insert(vars_id, tk.END, text=str(key), values=(str(value),))

            if isinstance(node.get("hosts"), dict):
                hosts_id = self.tree.insert(group_id, tk.END, text="hosts", values=(f"{len(node['hosts'])} items",))
                for host, attrs in sorted(node["hosts"].items(), key=lambda item: item[0].lower()):
                    if attrs is None:
                        val = ""
                    elif isinstance(attrs, dict):
                        val = ", ".join(f"{k}={v}" for k, v in attrs.items())
                    else:
                        val = str(attrs)
                    self.tree.insert(hosts_id, tk.END, text=host, values=(val,))

            if isinstance(node.get("children"), dict):
                children_id = self.tree.insert(group_id, tk.END, text="children", values=(f"{len(node['children'])} items",))
                for child, attrs in node["children"].items():
                    if attrs is None:
                        val = ""
                    elif isinstance(attrs, dict):
                        val = ", ".join(f"{k}={v}" for k, v in attrs.items())
                    else:
                        val = str(attrs)
                    self.tree.insert(children_id, tk.END, text=child, values=(val,))

        for item in self.tree.get_children(""):
            self.tree.item(item, open=True)

    def refresh_group_panel(self) -> None:
        self.hosts_list.delete(0, tk.END)
        if not self.current_group:
            self.group_label.config(text="-")
            self.count_label.config(text="0")
            self._set_host_detail("")
            return

        self.group_label.config(text=self.current_group)
        try:
            hosts = self.model.iter_hosts(self.current_group)
        except Exception as exc:
            self.count_label.config(text="error")
            self._set_host_detail(str(exc))
            return
        self.count_label.config(text=str(len(hosts)))
        filter_term = self.search_var.get().strip().lower()
        shown = 0
        for entry in hosts:
            if filter_term and filter_term not in entry.name.lower():
                continue
            label = entry.name
            if entry.vars:
                label += "  *"
            self.hosts_list.insert(tk.END, label)
            shown += 1
        self.status_var.set(f"Group {self.current_group}: {shown} shown, {len(hosts)} total")
        self._set_host_detail("")

    def _set_host_detail(self, text: str) -> None:
        self.host_detail.configure(state="normal")
        self.host_detail.delete("1.0", tk.END)
        self.host_detail.insert("1.0", text)
        self.host_detail.configure(state="disabled")

    def on_tree_select(self, _event: tk.Event) -> None:
        item = self.tree.focus()
        if not item:
            return
        parent = self.tree.parent(item)
        grand = self.tree.parent(parent)
        if parent == "":
            self.current_group = self.tree.item(item, "text")
            self.refresh_group_panel()
        elif grand == "":
            self.current_group = self.tree.item(parent, "text")
            self.refresh_group_panel()

    def on_tree_double_click(self, _event: tk.Event) -> None:
        item = self.tree.focus()
        if not item:
            return
        parent = self.tree.parent(item)
        if parent == "":
            self.current_group = self.tree.item(item, "text")
            self.refresh_group_panel()

    def on_host_select(self, _event: tk.Event) -> None:
        if not self.current_group:
            return
        idxs = self.hosts_list.curselection()
        if not idxs:
            return
        displayed = self._filtered_hosts_for_current_group()
        if idxs[0] >= len(displayed):
            return
        host = displayed[idxs[0]]
        self.current_host = host.name
        text = [f"Host: {host.name}"]
        groups = self.model.host_groups(host.name)
        text.append(f"Groups: {', '.join(groups) if groups else '-'}")
        if host.vars:
            text.append("Vars:")
            for key, value in host.vars.items():
                text.append(f"  {key}: {value}")
        else:
            text.append("Vars: -")
        self._set_host_detail("\n".join(text))

    def _filtered_hosts_for_current_group(self) -> List[HostEntry]:
        if not self.current_group:
            return []
        hosts = self.model.iter_hosts(self.current_group)
        filter_term = self.search_var.get().strip().lower()
        if not filter_term:
            return hosts
        return [h for h in hosts if filter_term in h.name.lower()]

    def clear_search(self) -> None:
        self.search_var.set("")
        self.refresh_group_panel()

    def find_host(self) -> None:
        term = self.search_var.get().strip().lower()
        if not term:
            self.refresh_group_panel()
            return

        matches: List[Tuple[str, str]] = []
        for group in self.model.top_groups():
            node = self.model.data.get(group, {})
            if not isinstance(node, dict) or not isinstance(node.get("hosts"), dict):
                continue
            for host in node["hosts"].keys():
                if term in host.lower():
                    matches.append((group, host))

        if not matches:
            messagebox.showinfo("Search", f"No host found for '{term}'.", parent=self)
            return

        group, host = matches[0]
        self.current_group = group
        self.refresh_group_panel()
        hosts = self._filtered_hosts_for_current_group()
        for idx, entry in enumerate(hosts):
            if entry.name == host:
                self.hosts_list.selection_clear(0, tk.END)
                self.hosts_list.selection_set(idx)
                self.hosts_list.see(idx)
                self.current_host = host
                self.on_host_select(None)  # type: ignore[arg-type]
                break

        if len(matches) > 1:
            self.status_var.set(f"Found {len(matches)} matches for '{term}'. Showing first result.")
        else:
            self.status_var.set(f"Found '{host}' in group '{group}'.")

    def sort_current_group(self) -> None:
        if not self.current_group:
            return
        try:
            self.model.sort_group_hosts(self.current_group)
        except Exception as exc:
            messagebox.showerror("Sort failed", str(exc), parent=self)
            return
        self.refresh_all()
        self.status_var.set(f"Sorted group '{self.current_group}'.")

    def sort_all_groups(self) -> None:
        proceed = messagebox.askyesno(
            "Confirm sort all groups",
            (
                "This will sort hosts inside every group.\n\n"
                "It will keep the existing top-level group layout as-is and will not\n"
                "reorder the section headers. Continue?"
            ),
            parent=self,
        )
        if not proceed:
            return
        try:
            self.model.sort_all_hosts()
        except Exception as exc:
            messagebox.showerror("Sort failed", str(exc), parent=self)
            return
        self.refresh_all()
        self.status_var.set("Sorted all host groups.")

    def add_host(self) -> None:
        groups = self.model.leaf_groups()
        if not groups:
            messagebox.showerror("Add host", "No host groups available.", parent=self)
            return
        dlg = AddHostDialog(self, groups)
        self.wait_window(dlg)
        if dlg.result is None:
            return

        host, target_groups, vars_dict = dlg.result
        try:
            changed = self.model.add_host(host, target_groups, vars_dict)
            if self.auto_sort_var.get():
                for group in changed:
                    self.model.sort_group_hosts(group)
            self.refresh_all()
            self.status_var.set(f"Added '{host}' to: {', '.join(changed)}")
        except Exception as exc:
            messagebox.showerror("Add host failed", str(exc), parent=self)

    def _selected_host_from_list(self) -> Optional[str]:
        if not self.current_group:
            return None
        idxs = self.hosts_list.curselection()
        if not idxs:
            return None
        displayed = self._filtered_hosts_for_current_group()
        if idxs[0] >= len(displayed):
            return None
        return displayed[idxs[0]].name

    def remove_selected_host(self) -> None:
        if not self.current_group:
            return
        host = self._selected_host_from_list()
        if not host:
            messagebox.showinfo("Remove host", "Select a host first.", parent=self)
            return
        if not messagebox.askyesno("Confirm", f"Remove '{host}' from group '{self.current_group}'?", parent=self):
            return
        try:
            removed = self.model.remove_host_from_group(host, self.current_group)
            if removed and self.auto_sort_var.get():
                self.model.sort_group_hosts(self.current_group)
            self.refresh_all()
            self.status_var.set(f"Removed '{host}' from '{self.current_group}'.")
        except Exception as exc:
            messagebox.showerror("Remove failed", str(exc), parent=self)

    def remove_host_everywhere(self) -> None:
        host = self._selected_host_from_list()
        if not host:
            host = simpledialog.askstring("Remove everywhere", "Host name:", parent=self)
        if not host:
            return
        if not messagebox.askyesno("Confirm", f"Remove '{host}' from all groups?", parent=self):
            return
        try:
            changed = self.model.remove_host_everywhere(host)
            if self.auto_sort_var.get():
                for group in changed:
                    self.model.sort_group_hosts(group)
            self.refresh_all()
            self.status_var.set(f"Removed '{host}' from: {', '.join(changed) if changed else 'nothing'}")
        except Exception as exc:
            messagebox.showerror("Remove failed", str(exc), parent=self)


    def save_inventory(self) -> None:
        if self.model.path is None:
            messagebox.showerror("Save", "No inventory file loaded.", parent=self)
            return
        try:
            backup = self.model.save()
            self.refresh_all()
            self.status_var.set(f"Saved. Backup: {backup.name}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)


def main() -> int:
    default_path = DEFAULT_INVENTORY_FILE
    if len(sys.argv) > 1:
        default_path = Path(sys.argv[1])
    app = InventoryEditorApp(default_path=default_path)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

