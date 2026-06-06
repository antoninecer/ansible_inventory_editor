from inventory_editor.analyzer.reporting import explain_variable_for_branch
from inventory_editor.analyzer.tracing import trace_variables_for_branch
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource


def test_branch_specific_effective_variables():
    model = ProjectModel(root_path=".")

    model.add_variable_to_group(
        "all",
        Variable(
            key="http_port",
            value=80,
            scope=VariableScope.GROUP,
            owner="all",
            source=VariableSource(
                source_path="group_vars/all/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    model.add_variable_to_group(
        "group_a",
        Variable(
            key="http_port",
            value=81,
            scope=VariableScope.GROUP,
            owner="group_a",
            source=VariableSource(
                source_path="group_vars/group_a/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    model.add_variable_to_group(
        "group_b",
        Variable(
            key="http_port",
            value=82,
            scope=VariableScope.GROUP,
            owner="group_b",
            source=VariableSource(
                source_path="group_vars/group_b/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    model.assign_host_to_group("web01", "group_a")
    model.assign_host_to_group("web01", "group_b")

    effective_a = model.effective_variables_for_branch("web01", "group_a")
    effective_b = model.effective_variables_for_branch("web01", "group_b")

    assert effective_a["http_port"].value == 81
    assert effective_b["http_port"].value == 82


def test_trace_and_explain_branch():
    model = ProjectModel(root_path=".")

    model.add_variable_to_group(
        "all",
        Variable(
            key="debug",
            value=False,
            scope=VariableScope.GROUP,
            owner="all",
            source=VariableSource(
                source_path="group_vars/all/main.yml",
                source_type="group_vars",
            ),
        ),
    )

    model.assign_host_to_group("web01", "web")

    model.add_variable_to_host(
        "web01",
        Variable(
            key="debug",
            value=True,
            scope=VariableScope.HOST,
            owner="web01",
            source=VariableSource(
                source_path="host_vars/web01/main.yml",
                source_type="host_vars",
            ),
        ),
    )

    trace = trace_variables_for_branch(model, "web01", "web")
    assert len(trace) == 1
    assert trace[0].effective.value is True

    report = explain_variable_for_branch(model, "web01", "web", "debug")
    assert "Effective value: True" in report
    assert "group_vars/all/main.yml" in report
    assert "host_vars/web01/main.yml" in report
