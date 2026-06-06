from dataclasses import dataclass, field

from inventory_editor.models.variable import Variable


@dataclass
class Group:
    name: str

    hosts: set[str] = field(default_factory=set)
    children: set[str] = field(default_factory=set)

    variables: list[Variable] = field(default_factory=list)

    def add_host(self, host_name: str) -> None:
        self.hosts.add(host_name)

    def add_child(self, group_name: str) -> None:
        self.children.add(group_name)

    def add_variable(self, variable: Variable) -> None:
        self.variables.append(variable)
