from dataclasses import dataclass, field

from inventory_editor.models.variable import Variable


@dataclass
class Host:
    name: str

    groups: set[str] = field(default_factory=set)

    variables: list[Variable] = field(default_factory=list)

    def add_group(self, group_name: str) -> None:
        self.groups.add(group_name)

    def add_variable(self, variable: Variable) -> None:
        self.variables.append(variable)
