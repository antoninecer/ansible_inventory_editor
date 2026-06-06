from __future__ import annotations
import shutil
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ruamel.yaml import YAML

from inventory_editor.analyzer.workspace_quality import analyze_workspace_scan
from inventory_editor.gui.context import build_group_context_view, build_host_context_view
from inventory_editor.gui.presenter import build_workspace_overview
from inventory_editor.io.workspace_exporter import export_workspace
from inventory_editor.io.workspace_loader import load_inventory_workspace
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource

_yaml_loader = YAML(typ="safe")


from inventory_editor.gui.settings import settings

class HostDialog(QDialog):
    def __init__(self, parent: QWidget, groups: list[str], initial_group: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Host")
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Host Name:", self.name_edit)

        self.group_list = QTreeWidget()
        self.group_list.setHeaderLabels(["Groups"])
        self.group_list.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        
        for g in sorted(groups):
            item = QTreeWidgetItem([g])
            self.group_list.addTopLevelItem(item)
            if g == initial_group:
                item.setSelected(True)
        
        layout.addLayout(form)
        layout.addWidget(QLabel("Select Groups:"))
        layout.addWidget(self.group_list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, list[str]]:
        groups = [item.text(0) for item in self.group_list.selectedItems()]
        return self.name_edit.text().strip(), groups

from inventory_editor.io.vault_handler import VaultHandler

class CodeEditorDialog(QDialog):
    def __init__(self, parent: QWidget, file_path: Path, content: str, is_vault: bool = False) -> None:
        super().__init__(parent)
        self.file_path = file_path
        self.is_vault = is_vault
        self.setWindowTitle(f"Editing: {file_path.name}" + (" (VAULT)" if is_vault else ""))
        self.resize(1000, 800)

        layout = QVBoxLayout(self)
        self.editor = QTextEdit()
        self.editor.setFontFamily("Menlo")  # Good for macOS
        self.editor.setPlainText(content)
        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        content = self.editor.toPlainText()
        try:
            if self.is_vault:
                VaultHandler.encrypt(content, self.file_path)
            else:
                self.file_path.write_text(content)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ws_edit = QLineEdit(settings.default_workspace)
        self.vault_pass_edit = QLineEdit(settings.vault_password)
        self.vault_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.vault_file_edit = QLineEdit(settings.vault_password_file)
        self.editor_edit = QLineEdit(settings.external_editor)

        browse_ws = QPushButton("...")
        browse_ws.setFixedWidth(30)
        browse_ws.clicked.connect(self._browse_ws)
        ws_layout = QHBoxLayout()
        ws_layout.addWidget(self.ws_edit)
        ws_layout.addWidget(browse_ws)

        browse_vf = QPushButton("...")
        browse_vf.setFixedWidth(30)
        browse_vf.clicked.connect(self._browse_vf)
        vf_layout = QHBoxLayout()
        vf_layout.addWidget(self.vault_file_edit)
        vf_layout.addWidget(browse_vf)

        browse_editor = QPushButton("...")
        browse_editor.setFixedWidth(30)
        browse_editor.clicked.connect(self._browse_editor)
        editor_layout = QHBoxLayout()
        editor_layout.addWidget(self.editor_edit)
        editor_layout.addWidget(browse_editor)

        form.addRow("Default Workspace:", ws_layout)
        form.addRow("Vault Password:", self.vault_pass_edit)
        form.addRow("Vault Password File:", vf_layout)
        form.addRow("External Editor Command:", editor_layout)
        form.addRow(QLabel("(Leave editor empty for internal editor)"))

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_ws(self):
        selected = QFileDialog.getExistingDirectory(self, "Select default workspace", self.ws_edit.text())
        if selected: self.ws_edit.setText(selected)

    def _browse_vf(self):
        selected, _ = QFileDialog.getOpenFileName(self, "Select Vault password file")
        if selected: self.vault_file_edit.setText(selected)

    def _browse_editor(self):
        selected, _ = QFileDialog.getOpenFileName(self, "Select Editor executable")
        if selected: self.editor_edit.setText(selected)

    def _save(self):
        settings.default_workspace = self.ws_edit.text().strip()
        settings.vault_password = self.vault_pass_edit.text()
        settings.vault_password_file = self.vault_file_edit.text().strip()
        settings.external_editor = self.editor_edit.text().strip()
        settings.save()
        self.accept()

from PySide6.QtWidgets import QCheckBox

class VariableDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, default_file: str = "main.yml") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(640, 480)

        self._value = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.key_edit = QLineEdit()
        self.file_edit = QLineEdit(default_file)
        self.encrypt_cb = QCheckBox("Encrypt as Vault")
        self.value_edit = QTextEdit()
        self.value_edit.setPlaceholderText("YAML value, for example: 42, true, [a, b], or a multiline mapping")

        form.addRow("Key:", self.key_edit)
        form.addRow("File name:", self.file_edit)
        form.addRow("", self.encrypt_cb)
        form.addRow("Value:", self.value_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "Missing key", "Variable key cannot be empty.")
            return

        file_name = self.file_edit.text().strip() or "main.yml"
        encrypt = self.encrypt_cb.isChecked()

        if encrypt and "vault" not in file_name.lower():
            answer = QMessageBox.question(
                self,
                "Encrypting plain file?",
                f"You are about to encrypt '{file_name}'. This will make the ENTIRE file unreadable without a password.\n\n"
                "Usually, it is better to use a file like 'vault.yml' for secrets.\n\n"
                "Do you want to change the filename to 'vault.yml' instead?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if answer == QMessageBox.StandardButton.Yes:
                file_name = "vault.yml"
                self.file_edit.setText(file_name)
                return # Let user check again
            elif answer == QMessageBox.StandardButton.Cancel:
                return

        raw_value = self.value_edit.toPlainText().strip()
        try:
            value = _yaml_loader.load(raw_value) if raw_value else None
        except Exception as exc:
            QMessageBox.warning(self, "Invalid value", f"YAML parsing failed: {exc}")
            return

        self._value = (key, value, file_name, encrypt)
        self.accept()

    @property
    def result_data(self) -> tuple[str, object, str, bool] | None:
        return self._value


class MainWindow(QMainWindow):
    def __init__(self, workspace: str | Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Inventory Editor")
        self.resize(1600, 980)
        self.statusBar().showMessage("Ready")

        self._workspace_path: Path | None = None
        self._project: ProjectModel | None = None
        self._scan = None
        self._report = None
        self._overview = None
        self._dirty = False

        self._current_mode: str | None = None
        self._current_group: str | None = None
        self._current_host: str | None = None
        self._current_branch_group: str | None = None
        self._current_file_path: str | None = None
        self._current_file_kind: str | None = None

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Workspace path")

        browse_button = QPushButton("Browse")
        load_button = QPushButton("Load")
        reload_button = QPushButton("Reload")
        find_button = QPushButton("Find")
        add_group_button = QPushButton("Add group")
        add_host_button = QPushButton("Add host")
        add_variable_button = QPushButton("Add variable")
        export_button = QPushButton("Export")
        settings_button = QPushButton("Settings")

        browse_button.clicked.connect(self._browse_workspace)
        load_button.clicked.connect(self._load_workspace)
        reload_button.clicked.connect(self._reload_workspace)
        find_button.clicked.connect(self._find_entry)
        add_group_button.clicked.connect(self._add_group)
        add_host_button.clicked.connect(self._add_host)
        add_variable_button.clicked.connect(self._add_variable)
        export_button.clicked.connect(self._export_workspace)
        settings_button.clicked.connect(self._open_settings)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Workspace:"))
        top_row.addWidget(self.path_edit, 1)
        top_row.addWidget(browse_button)
        top_row.addWidget(load_button)
        top_row.addWidget(reload_button)
        top_row.addWidget(find_button)
        top_row.addWidget(export_button)
        top_row.addWidget(settings_button)
        top_row.addWidget(add_group_button)
        top_row.addWidget(add_host_button)
        top_row.addWidget(add_variable_button)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type"])
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree.setMinimumWidth(420)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        self.tabs = QTabWidget()

        self.overview_text = QTextEdit()
        self.overview_text.setReadOnly(True)

        self.variables_tree = QTreeWidget()
        self.variables_tree.setHeaderLabels(["Key", "Value", "Scope", "Source"])
        self.variables_tree.itemSelectionChanged.connect(self._on_variable_selection_changed)
        self.variables_tree.itemDoubleClicked.connect(self._on_variable_double_clicked)
        self.variables_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.variables_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.variables_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.variables_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        self.trace_text = QTextEdit()
        self.trace_text.setReadOnly(True)

        self.variables_splitter = QSplitter(Qt.Orientation.Vertical)
        self.variables_splitter.addWidget(self.variables_tree)
        self.variables_splitter.addWidget(self.trace_text)
        self.variables_splitter.setStretchFactor(0, 3)
        self.variables_splitter.setStretchFactor(1, 2)

        self.files_tree = QTreeWidget()
        self.files_tree.setHeaderLabels(["Kind", "Path"])
        self.files_tree.itemSelectionChanged.connect(self._on_file_selection_changed)
        self.files_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.files_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.file_preview = QTextEdit()
        self.file_preview.setReadOnly(True)

        file_buttons = QHBoxLayout()
        self.open_source_button = QPushButton("Open source")
        self.open_source_button.clicked.connect(self._open_source)
        file_buttons.addWidget(self.open_source_button)
        file_buttons.addStretch(1)

        self.files_container = QWidget()
        files_layout = QVBoxLayout(self.files_container)
        files_layout.addWidget(self.files_tree, 1)
        files_layout.addLayout(file_buttons)
        files_layout.addWidget(self.file_preview)

        self.issues_text = QTextEdit()
        self.issues_text.setReadOnly(True)

        self.tabs.addTab(self.overview_text, "Overview")
        self.tabs.addTab(self.variables_splitter, "Variables")
        self.tabs.addTab(self.files_container, "Files")
        self.tabs.addTab(self.issues_text, "Issues")

        splitter = QSplitter()
        splitter.addWidget(self.tree)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        splitter.setSizes([560, 1040])

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top_row)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        if workspace is not None:
            self.path_edit.setText(str(Path(workspace).expanduser().resolve()))
            self._load_workspace()
        elif settings.default_workspace:
            self.path_edit.setText(settings.default_workspace)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

    def _browse_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select inventory workspace", self.path_edit.text())
        if selected:
            self.path_edit.setText(selected)
            self._load_workspace()

    def _load_workspace(self) -> None:
        raw_path = self.path_edit.text().strip()
        if not raw_path:
            QMessageBox.warning(self, "Missing workspace", "Enter a workspace path first.")
            return

        try:
            project, scan = load_inventory_workspace(
                raw_path, 
                vault_password=settings.vault_password, 
                vault_password_file=settings.vault_password_file
            )
            report = analyze_workspace_scan(scan)
            overview = build_workspace_overview(project, scan, report)
        except Exception as exc:  # pragma: no cover - UI error path
            QMessageBox.critical(self, "Load failed", str(exc))
            self.file_preview.setPlainText(str(exc))
            return

        self._workspace_path = Path(raw_path).expanduser().resolve()
        self._project = project
        self._scan = scan
        self._report = report
        self._overview = overview
        self._dirty = False

        self._current_mode = None
        self._current_group = None
        self._current_host = None
        self._current_branch_group = None
        self._current_file_path = None
        self._current_file_kind = None

        self._rebuild_tree()
        self._show_overview()
        self.statusBar().showMessage(f"Loaded: {self._workspace_path}")

    def _group_parent_map(self) -> dict[str, set[str]]:
        parent_map: dict[str, set[str]] = {}
        if self._project is None:
            return parent_map

        for group_name, group in self._project.groups.items():
            for child_name in group.children:
                parent_map.setdefault(child_name, set()).add(group_name)
        return parent_map

    def _is_root_group(self, group_name: str) -> bool:
        if self._project is None:
            return False
        if group_name == "all":
            return False
        parent_map = self._group_parent_map()
        return group_name not in parent_map

    def _rebuild_tree(self) -> None:
        self.tree.clear()
        if self._project is None:
            return

        root = QTreeWidgetItem(["Inventory", "root"])
        root.setData(0, Qt.ItemDataRole.UserRole, ("root", None))
        self.tree.addTopLevelItem(root)
        root.setExpanded(True)

        all_item = self._build_group_item("all")
        root.addChild(all_item)

        ungrouped_item = QTreeWidgetItem(["ungrouped", "special"])
        ungrouped_item.setData(0, Qt.ItemDataRole.UserRole, ("group", "ungrouped"))
        self._style_item(ungrouped_item, "#757575", bold=True)
        for host_name in sorted(
            host_name for host_name, host in self._project.hosts.items() if not host.groups
        ):
            ungrouped_item.addChild(self._build_host_item(host_name, "ungrouped"))
        root.addChild(ungrouped_item)

        for group_name in sorted(
            group_name for group_name in self._project.groups if self._is_root_group(group_name)
        ):
            if group_name == "all":
                continue
            root.addChild(self._build_group_item(group_name))

        self.tree.expandAll()

    def _build_group_item(self, group_name: str) -> QTreeWidgetItem:
        if self._project is None:
            return QTreeWidgetItem()

        group = self._project.groups.get(group_name)
        if group is None:
            item = QTreeWidgetItem([group_name, "group"])
            item.setData(0, Qt.ItemDataRole.UserRole, ("group", group_name))
            return item

        item = QTreeWidgetItem([group_name, f"vars={len(group.variables)} hosts={len(group.hosts)}"])
        item.setData(0, Qt.ItemDataRole.UserRole, ("group", group_name))
        self._style_item(item, "#1565c0", bold=True)

        for child_name in sorted(group.children):
            if child_name in self._project.groups:
                item.addChild(self._build_group_item(child_name))

        for host_name in sorted(group.hosts):
            item.addChild(self._build_host_item(host_name, group_name))

        return item

    def _build_host_item(self, host_name: str, branch_group: str) -> QTreeWidgetItem:
        if self._project is None:
            return QTreeWidgetItem()

        host = self._project.hosts.get(host_name)
        var_count = len(host.variables) if host is not None else 0
        item = QTreeWidgetItem([host_name, f"branch={branch_group} vars={var_count}"])
        item.setData(0, Qt.ItemDataRole.UserRole, ("host", host_name, branch_group))
        self._style_item(item, "#2e7d32", bold=False)
        return item

    def _style_item(self, item: QTreeWidgetItem, color: str, bold: bool = False) -> None:
        brush = QBrush(QColor(color))
        for column in range(2):
            item.setForeground(column, brush)
        if bold:
            font = QFont()
            font.setBold(True)
            item.setFont(0, font)

    def _show_overview(self) -> None:
        if self._overview is None:
            self.overview_text.setPlainText("No workspace loaded.")
            self.issues_text.setPlainText("No workspace loaded.")
            return

        lines = ["Workspace overview", ""]
        for label, value in self._overview.stats:
            lines.append(f"{label}: {value}")
        self.overview_text.setPlainText("\n".join(lines))
        self.issues_text.setPlainText("\n".join(self._overview.issues) if self._overview.issues else "No issues found.")

        self.variables_tree.clear()
        self.trace_text.clear()
        self.files_tree.clear()
        self.file_preview.clear()

    def _on_tree_selection_changed(self) -> None:
        if self._project is None or self._scan is None:
            return

        items = self.tree.selectedItems()
        if not items:
            return

        item = items[0]
        payload = item.data(0, Qt.ItemDataRole.UserRole)
        if not payload:
            return

        kind = payload[0]
        if kind == "root":
            self._show_overview()
            self._current_mode = None
            self._current_group = None
            self._current_host = None
            self._current_branch_group = None
            return

        if kind == "group":
            group_name = payload[1]
            self._current_mode = "group"
            self._current_group = group_name
            self._current_host = None
            self._current_branch_group = None
            self._show_group_context(group_name)
            return

        if kind == "host":
            host_name = payload[1]
            branch_group = payload[2]
            self._current_mode = "host"
            self._current_group = branch_group
            self._current_host = host_name
            self._current_branch_group = branch_group
            self._show_host_context(host_name, branch_group)
            return

    def _populate_variables_tree(self, rows: list[object]) -> None:
        self.variables_tree.clear()
        for row in sorted(rows, key=self._variable_sort_key):
            # Mask value if it's from a vault file
            is_vault = "vault" in row.source_path.lower()
            display_value = "********" if is_vault else row.value_text

            item = QTreeWidgetItem([row.key, display_value, row.scope, row.source_path])
            item.setData(0, Qt.ItemDataRole.UserRole, row.key)
            # Store real value for double-click reveal
            item.setData(1, Qt.ItemDataRole.UserRole, row.value_text)
            self._style_item(item, row.color)
            self.variables_tree.addTopLevelItem(item)
        self.variables_tree.resizeColumnToContents(0)
        self.variables_tree.resizeColumnToContents(2)

    def _on_variable_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if column == 1: # Value column
            real_value = item.data(1, Qt.ItemDataRole.UserRole)
            if real_value:
                item.setText(1, real_value)
                # Auto-hide after 10 seconds
                from PySide6.QtCore import QTimer
                QTimer.singleShot(10000, lambda: item.setText(1, "********"))

    def _populate_files_tree(self, rows: list[object]) -> None:
        self.files_tree.clear()
        for row in rows:
            item = QTreeWidgetItem([row.kind, row.path])
            item.setData(0, Qt.ItemDataRole.UserRole, (row.kind, row.path))
            self._style_item(item, row.color)
            self.files_tree.addTopLevelItem(item)
        self.files_tree.resizeColumnToContents(0)

    def _show_group_context(self, group_name: str) -> None:
        if self._project is None or self._scan is None:
            return

        view = build_group_context_view(self._project, self._scan, group_name)
        self.overview_text.setPlainText("\n".join(view.summary_lines))
        self._populate_variables_tree(view.variables)
        if hasattr(self, "_populate_files_tree"):
            self._populate_files_tree(view.files)
        else:
            self.statusBar().showMessage("Warning: _populate_files_tree missing!")
        self.trace_text.setPlainText(
            "Group context\n\n"
            f"Hosts: {', '.join(view.hosts) if view.hosts else '-'}\n"
            f"Child groups: {', '.join(view.children) if view.children else '-'}\n"
            "Select a variable to see its source path."
        )
        self.file_preview.setPlainText("")
        self.issues_text.setPlainText(
            "\n".join(self._overview.issues) if self._overview and self._overview.issues else "No issues found."
        )

    def _show_host_context(self, host_name: str, branch_group: str | None) -> None:
        if self._project is None or self._scan is None:
            return

        view = build_host_context_view(self._project, self._scan, host_name, branch_group)
        content = "\n".join(view.summary_lines)
        if view.cli_suggestions:
            content += "\n\nCLI Suggestions:\n" + "\n".join(view.cli_suggestions)

        self.overview_text.setPlainText(content)
        self._populate_variables_tree(view.variables)
        if hasattr(self, "_populate_files_tree"):
            self._populate_files_tree(view.files)
        else:
            self.statusBar().showMessage("Warning: _populate_files_tree missing!")
        self.trace_text.setPlainText("Select a variable to see its trace.")
        self.file_preview.setPlainText("")
        self.issues_text.setPlainText(
            "\n".join(self._overview.issues) if self._overview and self._overview.issues else "No issues found."
        )


    def _variable_sort_key(self, row: object) -> tuple[int, str, str]:
        source_path = str(getattr(row, "source_path", ""))
        key = str(getattr(row, "key", ""))
        if source_path.startswith("group_vars/all/"):
            priority = 0
        elif source_path.startswith("group_vars/"):
            priority = 1
        elif source_path.startswith("host_vars/"):
            priority = 2
        else:
            priority = 3
        return priority, source_path, key

    def _find_entry(self) -> None:
        text, ok = QInputDialog.getText(self, "Find", "Search text:")
        if not ok:
            return

        needle = text.strip().lower()
        if not needle:
            return

        search_order = [
            (self.tree, None),
            (self.variables_tree, self.tabs.indexOf(self.variables_splitter)),
            (self.files_tree, self.tabs.indexOf(self.files_container)),
        ]

        for widget, tab_index in search_order:
            item = self._find_in_tree(widget, needle)
            if item is not None:
                if tab_index is not None:
                    self.tabs.setCurrentIndex(tab_index)
                widget.setCurrentItem(item)
                widget.scrollToItem(item)
                self.statusBar().showMessage(f"Found: {text}")
                return

        QMessageBox.information(self, "Find", f"No match for '{text}'.")

    def _find_in_tree(self, tree: QTreeWidget, needle: str) -> QTreeWidgetItem | None:
        def matches(item: QTreeWidgetItem) -> bool:
            for column in range(item.columnCount()):
                value = item.text(column).strip().lower()
                if needle in value:
                    return True
            return False

        def walk(parent: QTreeWidgetItem | None = None) -> QTreeWidgetItem | None:
            count = tree.topLevelItemCount() if parent is None else parent.childCount()
            for index in range(count):
                item = tree.topLevelItem(index) if parent is None else parent.child(index)
                if item is None:
                    continue
                if matches(item):
                    self._expand_item_path(item)
                    return item
                found = walk(item)
                if found is not None:
                    return found
            return None

        return walk()

    def _expand_item_path(self, item: QTreeWidgetItem) -> None:
        current = item.parent()
        while current is not None:
            current.setExpanded(True)
            current = current.parent()

    def _reload_workspace(self) -> None:
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Reload workspace",
                "Discard unsaved changes and reload the current workspace?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._load_workspace()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self._dirty:
            event.accept()
            return

        answer = QMessageBox.question(
            self,
            "Exit",
            "You have unsaved changes. Export before exit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self._export_workspace()
            except Exception:
                event.ignore()
                return
            event.accept()
            return
        if answer == QMessageBox.StandardButton.No:
            event.accept()
            return

        event.ignore()

    def _open_external(self, file_path: Path) -> None:
        resolved = str(file_path.resolve())
        import sys

        cmds = []
        if sys.platform == "darwin":
            cmds.append(["open", resolved])
        elif sys.platform == "win32":
            cmds.append(["start", resolved])
        
        cmds.extend([
            ["xdg-open", resolved],
            ["gio", "open", resolved],
            ["kde-open5", resolved],
        ])

        for cmd in cmds:
            if shutil.which(cmd[0]):
                try:
                    result = subprocess.run(cmd, check=False)
                    if result.returncode == 0:
                        return
                except Exception:
                    continue

        QMessageBox.critical(
            self,
            "Open failed",
            f"Cannot open file: {resolved}\n\nMake sure the file exists and you have permission to open it.",
        )

    def _current_variable_key(self) -> str | None:
        items = self.variables_tree.selectedItems()
        if not items:
            return None
        return str(items[0].data(0, Qt.ItemDataRole.UserRole) or "").strip() or None

    def _on_variable_selection_changed(self) -> None:
        if self._project is None or self._scan is None:
            return

        key = self._current_variable_key()
        if not key:
            return

        if self._current_mode == "host" and self._current_host is not None:
            branch_group = self._current_branch_group
            from inventory_editor.analyzer.reporting import explain_variable_for_branch
            self.trace_text.setPlainText(explain_variable_for_branch(self._project, self._current_host, branch_group, key))
        elif self._current_mode == "group" and self._current_group is not None:
            group = self._project.groups.get(self._current_group)
            if group is None:
                return
            for variable in group.variables:
                if variable.key == key:
                    self.trace_text.setPlainText(
                        "\n".join(
                            [
                                f"Group: {self._current_group}",
                                f"Variable: {key}",
                                f"Value: {variable.value}",
                                f"Source: {variable.source.source_path}",
                                f"Source type: {variable.source.source_type}",
                            ]
                        )
                    )
                    return

    def _selected_file_info(self) -> tuple[str, str] | None:
        items = self.files_tree.selectedItems()
        if not items:
            return None
        payload = items[0].data(0, Qt.ItemDataRole.UserRole)
        if not payload:
            return None
        return str(payload[0]), str(payload[1])

    def _on_file_selection_changed(self) -> None:
        info = self._selected_file_info()
        if info is None:
            self._current_file_kind = None
            self._current_file_path = None
            self.file_preview.clear()
            return

        kind, path = info
        self._current_file_kind = kind
        self._current_file_path = path
        self.file_preview.setPlainText(f"{kind}\n{path}")

    def _open_source(self) -> None:
        info = self._selected_file_info()
        if info is None:
            QMessageBox.information(self, "Open source", "Select a file first.")
            return

        kind, path = info
        file_path = Path(path)
        if not file_path.exists() and self._workspace_path is not None:
            file_path = self._workspace_path / path

        is_vault = (kind == "vault")
        content = ""
        
        # 1. Handle Decryption if needed
        if is_vault:
            if not settings.vault_password and not settings.vault_password_file:
                answer = QMessageBox.question(
                    self,
                    "Vault Credentials Required",
                    "This is an encrypted Vault file, but no Vault password is configured.\n\nOpen Settings to configure it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if answer == QMessageBox.StandardButton.Yes:
                    self._open_settings()
                
                # Check again after settings dialog
                if not settings.vault_password and not settings.vault_password_file:
                    return

            try:
                content = VaultHandler.decrypt(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Decryption failed", f"Could not decrypt vault file.\n\nError: {e}\n\nCheck your Vault password in Settings.")
                return
        else:
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception as e:
                QMessageBox.critical(self, "Read failed", str(e))
                return

        # 2. Open in Editor
        if settings.external_editor:
            # Use configured external editor
            # For Vault files, we'd need to write to a temp file, open it, then re-encrypt.
            # For now, let's keep it simple: external editor is for non-vault or raw vault content.
            if is_vault:
                QMessageBox.information(self, "Vault & External Editor", "Vault files are currently only supported in the internal editor for safety. Opening raw encrypted content.")
            
            cmd = [settings.external_editor, str(file_path.resolve())]
            try:
                subprocess.Popen(cmd)
            except Exception as e:
                QMessageBox.critical(self, "External editor failed", str(e))
        else:
            # Use internal editor
            dialog = CodeEditorDialog(self, file_path, content, is_vault=is_vault)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.statusBar().showMessage(f"Saved: {file_path.name}")
                self._reload_workspace()


    def _add_group(self) -> None:
        if self._project is None:
            return

        group_name, ok = QInputDialog.getText(self, "Add group", "Group name:")
        if not ok or not group_name.strip():
            return

        group_name = group_name.strip()
        self._project.add_group(group_name)
        self._dirty = True
        self._rebuild_tree()
        self.statusBar().showMessage(f"Added group: {group_name}")

    def _add_host(self) -> None:
        if self._project is None:
            return

        target_group: str | None = None
        if self._current_mode == "group" and self._current_group not in (None, "ungrouped"):
            target_group = self._current_group
        elif self._current_mode == "host" and self._current_branch_group not in (None, "ungrouped"):
            target_group = self._current_branch_group

        dialog = HostDialog(self, list(self._project.groups.keys()), initial_group=target_group)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        host_name, target_groups = dialog.get_data()
        if not host_name:
            return

        self._project.add_host(host_name)
        for g in target_groups:
            self._project.assign_host_to_group(host_name, g)

        self._dirty = True
        self._rebuild_tree()
        self.statusBar().showMessage(
            f"Added host: {host_name} to {', '.join(target_groups) if target_groups else 'no groups'}"
        )

    def _prompt_existing_variable_action(self, key: str, existing_values: list[str]) -> str | None:
        box = QMessageBox(self)
        box.setWindowTitle("Variable exists")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(f"Variable '{key}' already exists in this context.")
        box.setInformativeText(
            "Choose how to proceed.\n\n"
            f"Existing values: {', '.join(existing_values) if existing_values else '-'}"
        )
        replace_button = box.addButton("Replace", QMessageBox.ButtonRole.AcceptRole)
        append_button = box.addButton("Append", QMessageBox.ButtonRole.ActionRole)
        cancel_button = box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()

        clicked = box.clickedButton()
        if clicked == replace_button:
            return "replace"
        if clicked == append_button:
            return "append"
        if clicked == cancel_button:
            return None
        return None

    def _add_variable(self) -> None:
        if self._project is None:
            return

        if self._current_mode not in {"group", "host"}:
            QMessageBox.information(self, "Add variable", "Select a group or host first.")
            return

        dialog_title = "Add group variable" if self._current_mode == "group" else "Add host variable"
        dialog = VariableDialog(self, dialog_title)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        result = dialog.result_data
        if result is None:
            return

        key, value, file_name, encrypt = result
        file_name = file_name.strip() or "main.yml"
        if not file_name.endswith((".yml", ".yaml")):
            file_name += ".yml"

        if self._current_mode == "group":
            group_name = self._current_group
            if not group_name:
                return
            source_path = f"group_vars/{group_name}/{file_name}"
            
            if encrypt:
                if not hasattr(self._project, "vault_files"): self._project.vault_files = set()
                self._project.vault_files.add(source_path)

            existing = [
                variable.value
                for variable in self._project.groups.get(group_name, None).variables
                if variable.key == key
            ] if self._project.groups.get(group_name) is not None else []
            action = None
            if existing:
                existing_text = [str(item) for item in existing]
                if all(str(item) == str(value) for item in existing):
                    QMessageBox.information(
                        self,
                        "Already exists",
                        "The same key/value already exists in this group context. Nothing changed.",
                    )
                    return
                action = self._prompt_existing_variable_action(key, existing_text)
                if action is None:
                    return

            variable = Variable(
                key=key,
                value=value,
                scope=VariableScope.GROUP,
                owner=group_name,
                source=VariableSource(source_path=source_path, source_type="group_vars"),
            )

            if action == "replace":
                self._project.replace_variable_in_group(group_name, variable)
            else:
                self._project.add_variable_to_group(group_name, variable)

            self._dirty = True
            self._rebuild_tree()
            self.statusBar().showMessage(f"Added group variable {key} to {group_name}")
            return

        host_name = self._current_host
        branch_group = self._current_branch_group
        if not host_name:
            return

        source_path = f"host_vars/{host_name}/{file_name}"
        
        if encrypt:
            if not hasattr(self._project, "vault_files"): self._project.vault_files = set()
            self._project.vault_files.add(source_path)

        existing = [
            variable.value
            for variable in self._project.hosts.get(host_name, None).variables
            if variable.key == key
        ] if self._project.hosts.get(host_name) is not None else []
        action = None
        if existing:
            existing_text = [str(item) for item in existing]
            if all(str(item) == str(value) for item in existing):
                QMessageBox.information(
                    self,
                    "Already exists",
                    "The same key/value already exists on this host. Nothing changed.",
                )
                return
            action = self._prompt_existing_variable_action(key, existing_text)
            if action is None:
                return

        variable = Variable(
            key=key,
            value=value,
            scope=VariableScope.HOST,
            owner=host_name,
            source=VariableSource(source_path=source_path, source_type="host_vars"),
        )

        if action == "replace":
            self._project.replace_variable_in_host(host_name, variable)
        else:
            self._project.add_variable_to_host(host_name, variable)

        self._dirty = True
        self._rebuild_tree()
        self.statusBar().showMessage(f"Added host variable {key} to {host_name} ({branch_group})")
    def _export_workspace(self) -> None:
        if self._project is None or self._workspace_path is None:
            QMessageBox.warning(self, "Export", "Load a workspace first.")
            return

        # Check if we have vault files but no credentials
        vault_files = getattr(self._project, "vault_files", set())
        if vault_files and not VaultHandler.has_credentials():
            answer = QMessageBox.question(
                self,
                "Vault Credentials Required",
                f"Your project contains {len(vault_files)} Vault-encrypted file(s), but no Vault password is configured.\n\n"
                "Exporting now will fail or hang when trying to encrypt these files.\n\n"
                "Open Settings to configure a password?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._open_settings()
            
            # Re-check after settings
            if not VaultHandler.has_credentials():
                return

        if self._dirty:
            proceed = QMessageBox.question(
                self,
                "Export workspace",
                "Export changes back to the loaded workspace?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        try:
            export_workspace(self._project, self._workspace_path)
            self._dirty = False
            self.statusBar().showMessage(f"Exported to {self._workspace_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))


