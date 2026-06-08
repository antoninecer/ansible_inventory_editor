from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from heapq import heappop, heappush

from inventory_editor.models.group import Group
from inventory_editor.models.host import Host
from inventory_editor.models.variable import Variable, VariableScope


@dataclass
class ProjectModel:
    root_path: str
    inventory_file: str = "inventory.yml"

    groups: dict[str, Group] = field(default_factory=dict)
    hosts: dict[str, Host] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if "all" not in self.groups:
            self.groups["all"] = Group(name="all")

    def add_group(self, group_name: str) -> Group:
        if group_name in self.groups:
            return self.groups[group_name]

        group = Group(name=group_name)
        self.groups[group_name] = group
        return group

    def add_host(self, host_name: str) -> Host:
        if host_name in self.hosts:
            return self.hosts[host_name]

        host = Host(name=host_name)
        self.hosts[host_name] = host
        return host

    def assign_host_to_group(self, host_name: str, group_name: str) -> None:
        host = self.add_host(host_name)
        group = self.add_group(group_name)

        host.add_group(group_name)
        group.add_host(host_name)

    def add_variable_to_group(self, group_name: str, variable: Variable) -> None:
        group = self.add_group(group_name)
        if variable.scope != VariableScope.GROUP:
            raise ValueError("Variable scope must be GROUP for group variables")
        group.add_variable(variable)

    def add_variable_to_host(self, host_name: str, variable: Variable) -> None:
        host = self.add_host(host_name)
        if variable.scope != VariableScope.HOST:
            raise ValueError("Variable scope must be HOST for host variables")
        host.add_variable(variable)

    def replace_variable_in_group(self, group_name: str, variable: Variable) -> None:
        group = self.add_group(group_name)
        if variable.scope != VariableScope.GROUP:
            raise ValueError("Variable scope must be GROUP for group variables")
        group.variables = [item for item in group.variables if item.key != variable.key]
        group.add_variable(variable)

    def replace_variable_in_host(self, host_name: str, variable: Variable) -> None:
        host = self.add_host(host_name)
        if variable.scope != VariableScope.HOST:
            raise ValueError("Variable scope must be HOST for host variables")
        host.variables = [item for item in host.variables if item.key != variable.key]
        host.add_variable(variable)

    def parent_groups_for_group(self, group_name: str) -> list[str]:
        parents: list[str] = []
        for candidate_name, candidate_group in self.groups.items():
            if group_name in candidate_group.children:
                parents.append(candidate_name)
        return sorted(parents)

    def ancestor_chain_for_group(self, group_name: str) -> list[str]:
        if group_name not in self.groups:
            return []

        ordered: list[str] = []
        seen: set[str] = set()

        def visit(name: str) -> None:
            for parent in self.parent_groups_for_group(name):
                if parent in seen:
                    continue
                visit(parent)
                if parent not in seen:
                    seen.add(parent)
                    ordered.append(parent)

        visit(group_name)
        return ordered

    def branch_groups_for_context(self, branch_group_name: str | None) -> list[str]:
        if branch_group_name in (None, "", "ungrouped"):
            return ["all"] if "all" in self.groups else []

        if branch_group_name == "all":
            return ["all"]

        ordered: list[str] = []
        if "all" in self.groups:
            ordered.append("all")

        for ancestor in self.ancestor_chain_for_group(branch_group_name):
            if ancestor not in ordered:
                ordered.append(ancestor)

        if branch_group_name not in ordered:
            ordered.append(branch_group_name)

        return ordered

    def ordered_groups_for_host(self, host_name: str) -> list[Group]:
        if host_name not in self.hosts:
            raise KeyError(f"Unknown host: {host_name}")

        host = self.hosts[host_name]
        applicable: set[str] = set()

        if "all" in self.groups:
            applicable.add("all")

        for direct_group in host.groups:
            applicable.add(direct_group)
            applicable.update(self.ancestor_chain_for_group(direct_group))

        indegree: dict[str, int] = {name: 0 for name in applicable}
        children_map: dict[str, set[str]] = defaultdict(set)

        for parent_name, parent_group in self.groups.items():
            if parent_name not in applicable:
                continue

            for child_name in parent_group.children:
                if child_name in applicable and child_name != parent_name:
                    if child_name not in children_map[parent_name]:
                        children_map[parent_name].add(child_name)
                        indegree[child_name] += 1

        heap: list[str] = []
        for name, degree in indegree.items():
            if degree == 0:
                heappush(heap, name)

        ordered_names: list[str] = []
        seen: set[str] = set()

        while heap:
            name = heappop(heap)
            if name in seen:
                continue
            seen.add(name)
            ordered_names.append(name)

            for child_name in sorted(children_map.get(name, set())):
                indegree[child_name] -= 1
                if indegree[child_name] == 0:
                    heappush(heap, child_name)

        for name in sorted(applicable):
            if name not in seen and name in self.groups:
                ordered_names.append(name)

        return [self.groups[name] for name in ordered_names if name in self.groups]

    def effective_variables_for_host(self, host_name: str) -> dict[str, Variable]:
        if host_name not in self.hosts:
            raise KeyError(f"Unknown host: {host_name}")

        host = self.hosts[host_name]
        merged: dict[str, Variable] = {}

        for group in self.ordered_groups_for_host(host_name):
            for variable in group.variables:
                merged[variable.key] = variable

        for variable in host.variables:
            merged[variable.key] = variable

        return merged

    def effective_variables_for_branch(self, host_name: str, branch_group_name: str | None) -> dict[str, Variable]:
        if host_name not in self.hosts:
            raise KeyError(f"Unknown host: {host_name}")

        host = self.hosts[host_name]
        merged: dict[str, Variable] = {}

        for group_name in self.branch_groups_for_context(branch_group_name):
            group = self.groups.get(group_name)
            if group is None:
                continue
            for variable in group.variables:
                merged[variable.key] = variable

        for variable in host.variables:
            merged[variable.key] = variable

        return merged

    def group_count(self) -> int:
        return len(self.groups)

    def host_count(self) -> int:
        return len(self.hosts)
