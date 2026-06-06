from __future__ import annotations
import shutil
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QBrush, QColor, QFont, QAction, QIcon
from PySide6.QtWidgets import (
    QApplication,
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
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QSizePolicy
)

from ruamel.yaml import YAML

from inventory_editor.analyzer.workspace_quality import analyze_workspace_scan
from inventory_editor.gui.context import build_group_context_view, build_host_context_view
from inventory_editor.gui.presenter import build_workspace_overview
from inventory_editor.io.workspace_exporter import export_workspace
from inventory_editor.io.workspace_loader import load_inventory_workspace
from inventory_editor.models.project import ProjectModel
from inventory_editor.models.variable import Variable, VariableScope, VariableSource
from inventory_editor.gui.settings import settings
from inventory_editor.io.vault_handler import VaultHandler

_yaml_loader = YAML(typ="safe")

class AboutDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Inventory Editor")
        self.resize(500, 350)
        layout = QVBoxLayout(self)
        
        title = QLabel("Ansible Inventory Editor")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        author = QLabel("Author: Antonín Ečer, DiS.")
        author.setFont(QFont("Arial", 12))
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        github = QLabel('<a href="https://github.com/antoninecer/ansible_inventory_editor">GitHub Repository</a>')
        github.setOpenExternalLinks(True)
        github.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        desc = QTextEdit()
        desc.setReadOnly(True)
        desc.setPlainText(
            "A professional tool for managing complex Ansible inventories.\n\n"
            "Key Features:\n"
            "- Round-trip YAML: Preserves your comments and formatting.\n"
            "- Ansible Vault: Integrated encryption/decryption and secure editing.\n"
            "- Visibility: Automatic masking of secrets with 10s reveal timer.\n"
            "- Analysis: Intelligent variable precedence and provenance tracking.\n"
            "- Organization: Visual management of hosts and hierarchical groups."
        )
        
        layout.addWidget(title)
        layout.addSpacing(5)
        layout.addWidget(author)
        layout.addWidget(github)
        layout.addSpacing(10)
        layout.addWidget(desc)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

class HostDialog(QDialog):
    def __init__(self, parent: QWidget, groups: list[str], initial_group: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Host")
        self.resize(400, 500)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Host Name:", self.name_edit)

        self.group_list = QTreeWidget()
        self.group_list.setHeaderLabels(["Available Groups"])
        self.group_list.setSelectionMode(QTreeWidget.SelectionMode.MultiSelection)
        
        for g in sorted(groups):
            item = QTreeWidgetItem([g])
            self.group_list.addTopLevelItem(item)
            if g == initial_group:
                item.setSelected(True)
        
        layout.addLayout(form)
        layout.addWidget(QLabel("Assign to Groups:"))
        layout.addWidget(self.group_list)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, list[str]]:
        groups = [item.text(0) for item in self.group_list.selectedItems()]
        return self.name_edit.text().strip(), groups

class CodeEditorDialog(QDialog):
    def __init__(self, parent: QWidget, file_path: Path, content: str, is_vault: bool = False) -> None:
        super().__init__(parent)
        self.file_path = file_path
        self.is_vault = is_vault
        self.setWindowTitle(f"Editing: {file_path.name}" + (" (VAULTED)" if is_vault else ""))
        self.resize(1000, 800)

        layout = QVBoxLayout(self)
        self.editor = QTextEdit()
        # Use a proper monospaced font
        font = QFont("Menlo", 12) if os.name != 'nt' else QFont("Consolas", 12)
        self.editor.setFont(font)
        self.editor.setPlainText(content)
        self.editor.setAcceptRichText(False)
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
                self.file_path.write_text(content, encoding="utf-8")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Application Settings")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.ws_edit = QLineEdit(settings.default_workspace)
        self.vault_pass_edit = QLineEdit(settings.vault_password)
        self.vault_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.vault_file_edit = QLineEdit(settings.vault_password_file)
        self.editor_edit = QLineEdit(settings.external_editor)

        browse_ws = QPushButton("...")
        browse_ws.setFixedWidth(35)
        browse_ws.clicked.connect(self._browse_ws)
        ws_layout = QHBoxLayout()
        ws_layout.addWidget(self.ws_edit)
        ws_layout.addWidget(browse_ws)

        browse_vf = QPushButton("...")
        browse_vf.setFixedWidth(35)
        browse_vf.clicked.connect(self._browse_vf)
        vf_layout = QHBoxLayout()
        vf_layout.addWidget(self.vault_file_edit)
        vf_layout.addWidget(browse_vf)

        browse_editor = QPushButton("...")
        browse_editor.setFixedWidth(35)
        browse_editor.clicked.connect(self._browse_editor)
        editor_layout = QHBoxLayout()
        editor_layout.addWidget(self.editor_edit)
        editor_layout.addWidget(browse_editor)

        form.addRow("Default Workspace:", ws_layout)
        form.addRow("Vault Password:", self.vault_pass_edit)
        form.addRow("Vault Password File:", vf_layout)
        form.addRow("External Editor Command:", editor_layout)
        form.addRow("", QLabel("<i>(Leave empty to use built-in editor)</i>"))

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

class VariableDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, default_file: str = "main.yml") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(640, 500)

        self._value = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.key_edit = QLineEdit()
        self.file_edit = QLineEdit(default_file)
        self.encrypt_cb = QCheckBox("Encrypt as Vault")
        self.value_edit = QTextEdit()
        font = QFont("Menlo", 11) if os.name != 'nt' else QFont("Consolas", 11)
        self.value_edit.setFont(font)
        self.value_edit.setPlaceholderText("YAML value (e.g. 42, true, [a, b], or object)")

        form.addRow("Key:", self.key_edit)
        form.addRow("Target File:", self.file_edit)
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
            QMessageBox.warning(self, "Validation Error", "Variable key cannot be empty.")
            return

        file_name = self.file_edit.text().strip() or "main.yml"
        encrypt = self.encrypt_cb.isChecked()

        if encrypt and "vault" not in file_name.lower():
            answer = QMessageBox.question(
                self,
                "Security Recommendation",
                f"You are about to encrypt '{file_name}'. This will secure the ENTIRE file.\n\n"
                "Standard practice is to use 'vault.yml' for secrets.\n\n"
                "Switch to 'vault.yml'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            if answer == QMessageBox.StandardButton.Yes:
                file_name = "vault.yml"
                self.file_edit.setText(file_name)
                return 
            elif answer == QMessageBox.StandardButton.Cancel:
                return

        raw_value = self.value_edit.toPlainText().strip()
        try:
            value = _yaml_loader.load(raw_value) if raw_value else None
        except Exception as exc:
            QMessageBox.warning(self, "YAML Error", f"Failed to parse value: {exc}")
            return

        self._value = (key, value, file_name, encrypt)
        self.accept()

    @property
    def result_data(self) -> tuple[str, object, str, bool] | None:
        return self._value


class MainWindow(QMainWindow):
    def __init__(self, workspace: str | Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Ansible Inventory Editor")
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

        self._setup_ui()
        self._setup_menu()
        self._update_action_states()

        if workspace is not None:
            self.path_edit.setText(str(Path(workspace).expanduser().resolve()))
            self._load_workspace()
        elif settings.default_workspace:
            self.path_edit.setText(settings.default_workspace)

    def _setup_ui(self) -> None:
        # --- Toolbar ---
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        toolbar.addWidget(QLabel("  Workspace: "))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Path to Ansible inventory directory...")
        self.path_edit.setMinimumWidth(400)
        toolbar.addWidget(self.path_edit)
        
        self.browse_action = QAction("Browse", self)
        self.browse_action.setToolTip("Browse for workspace directory")
        self.browse_action.triggered.connect(self._browse_workspace)
        toolbar.addAction(self.browse_action)
        
        toolbar.addSeparator()
        
        self.save_action = QAction("Save", self)
        self.save_action.setToolTip("Save changes (Ctrl+S)")
        self.save_action.triggered.connect(self._export_workspace)
        toolbar.addAction(self.save_action)
        
        self.settings_action = QAction("Settings", self)
        self.settings_action.setToolTip("Configure application settings")
        self.settings_action.triggered.connect(self._open_settings)
        toolbar.addAction(self.settings_action)
        
        toolbar.addSeparator()
        
        self.find_action = QAction("Find", self)
        self.find_action.setToolTip("Search in inventory (Ctrl+F)")
        self.find_action.triggered.connect(self._find_entry)
        toolbar.addAction(self.find_action)

        toolbar.addSeparator()
        
        # Action-icons for Inventory management
        self.add_group_action = QAction("+ Group", self)
        self.add_group_action.setToolTip("Add new group (to selected node)")
        self.add_group_action.triggered.connect(self._add_group)
        toolbar.addAction(self.add_group_action)
        
        self.add_host_action = QAction("+ Host", self)
        self.add_host_action.setToolTip("Add new host to selected group")
        self.add_host_action.triggered.connect(self._add_host)
        toolbar.addAction(self.add_host_action)
        
        self.add_var_action = QAction("+ Var", self)
        self.add_var_action.setToolTip("Add variable to selected node")
        self.add_var_action.triggered.connect(self._add_variable)
        toolbar.addAction(self.add_var_action)

        # --- Central Area ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Inventory Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Status"])
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree.setMinimumWidth(350)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.tree)

        # Right: Tabs
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        splitter.setSizes([450, 1150])

        # Tab: Overview
        self.overview_text = QTextEdit()
        self.overview_text.setReadOnly(True)
        self.tabs.addTab(self.overview_text, "Overview")

        # Tab: Variables (Vertical Splitter)
        self.variables_tree = QTreeWidget()
        self.variables_tree.setHeaderLabels(["Key", "Value", "Scope", "Source"])
        self.variables_tree.itemSelectionChanged.connect(self._on_variable_selection_changed)
        self.variables_tree.itemDoubleClicked.connect(self._on_variable_double_clicked)
        self.variables_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.variables_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.trace_text = QTextEdit()
        self.trace_text.setReadOnly(True)

        var_split = QSplitter(Qt.Orientation.Vertical)
        var_split.addWidget(self.variables_tree)
        var_split.addWidget(self.trace_text)
        var_split.setStretchFactor(0, 3)
        var_split.setStretchFactor(1, 1)
        self.tabs.addTab(var_split, "Variables")

        # Tab: Files
        self.files_tree = QTreeWidget()
        self.files_tree.setHeaderLabels(["Kind", "Path"])
        self.files_tree.itemSelectionChanged.connect(self._on_file_selection_changed)
        self.files_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.files_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.file_preview = QTextEdit()
        self.file_preview.setReadOnly(True)
        self.file_preview.setFont(QFont("Menlo", 10) if os.name != 'nt' else QFont("Consolas", 10))
        
        self.edit_file_btn = QPushButton("Open in Internal Editor")
        self.edit_file_btn.clicked.connect(self._open_source)

        file_cont = QWidget()
        file_lay = QVBoxLayout(file_cont)
        file_lay.addWidget(self.files_tree, 2)
        file_lay.addWidget(self.edit_file_btn)
        file_lay.addWidget(self.file_preview, 1)
        self.tabs.addTab(file_cont, "Files")

        # Tab: Issues
        self.issues_text = QTextEdit()
        self.issues_text.setReadOnly(True)
        self.tabs.addTab(self.issues_text, "Issues")

        self.setCentralWidget(splitter)

    def _setup_menu(self) -> None:
        mb = self.menuBar()
        
        # File
        file_m = mb.addMenu("&File")
        
        new_act = QAction("&New Project...", self)
        new_act.triggered.connect(self._new_project)
        file_m.addAction(new_act)
        
        file_m.addSeparator()
        
        load_act = QAction("&Load Workspace", self)
        load_act.triggered.connect(self._load_workspace)
        file_m.addAction(load_act)
        
        reload_act = QAction("&Reload", self)
        reload_act.setShortcut("Ctrl+R")
        reload_act.triggered.connect(self._reload_workspace)
        file_m.addAction(reload_act)
        
        file_m.addSeparator()
        
        save_act = QAction("&Save", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self._export_workspace)
        file_m.addAction(save_act)
        
        file_m.addSeparator()
        
        exit_act = QAction("E&xit", self)
        exit_act.triggered.connect(self.close)
        file_m.addAction(exit_act)
        
        # Inventory
        inv_m = mb.addMenu("&Inventory")
        inv_m.addAction(self.add_group_action)
        inv_m.addAction(self.add_host_action)
        inv_m.addSeparator()
        inv_m.addAction(self.add_var_action)
        
        # Tools
        tools_m = mb.addMenu("&Tools")
        tools_m.addAction(self.find_action)
        
        set_act = QAction("&Settings", self)
        set_act.triggered.connect(self._open_settings)
        tools_m.addAction(set_act)
        
        # Help
        help_m = mb.addMenu("&Help")
        about_act = QAction("&About", self)
        about_act.triggered.connect(self._open_about)
        help_m.addAction(about_act)

    def _update_action_states(self) -> None:
        """Dynamically enable/disable buttons based on selection."""
        has_proj = self._project is not None
        
        # Add Group: Root or Group selected
        self.add_group_action.setEnabled(has_proj)
        
        # Add Host: Only if a Group is selected
        self.add_host_action.setEnabled(has_proj and self._current_mode == "group")
        
        # Add Var: Group or Host selected
        self.add_var_action.setEnabled(has_proj and self._current_mode in ("group", "host"))
        
        self.save_action.setEnabled(has_proj)
        self.find_action.setEnabled(has_proj)

    def _open_about(self) -> None:
        AboutDialog(self).exec()

    def _open_settings(self) -> None:
        if SettingsDialog(self).exec() == QDialog.DialogCode.Accepted:
            if self._workspace_path:
                self._reload_workspace()

    def _new_project(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select directory for NEW project")
        if not path: return
        
        root = Path(path)
        if any(root.iterdir()):
            ans = QMessageBox.warning(self, "Directory not empty", 
                                     "The directory is not empty. Initialize anyway?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans != QMessageBox.StandardButton.Yes: return
            
        try:
            # 1. Base files
            (root / "group_vars" / "all").mkdir(parents=True, exist_ok=True)
            (root / "host_vars").mkdir(parents=True, exist_ok=True)
            
            inv_file = root / "inventory.yml"
            if not inv_file.exists():
                inv_file.write_text("# Created by Ansible Inventory Editor\nall:\n  hosts:\n    localhost:\n      ansible_connection: local\n", encoding="utf-8")
            
            all_file = root / "group_vars" / "all" / "main.yml"
            if not all_file.exists():
                all_file.write_text("# Global variables\nansible_python_interpreter: auto_silent\n", encoding="utf-8")
                
            self.path_edit.setText(str(root))
            self._load_workspace()
            QMessageBox.information(self, "Success", f"Project initialized at {root}")
        except Exception as e:
            QMessageBox.critical(self, "Init Failed", str(e))

    def _browse_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select inventory workspace", self.path_edit.text())
        if selected:
            self.path_edit.setText(selected)
            self._load_workspace()

    def _load_workspace(self) -> None:
        raw_path = self.path_edit.text().strip()
        if not raw_path: return

        try:
            project, scan = load_inventory_workspace(
                raw_path, 
                vault_password=settings.vault_password, 
                vault_password_file=settings.vault_password_file
            )
            report = analyze_workspace_scan(scan)
            overview = build_workspace_overview(project, scan, report)
        except Exception as exc: 
            QMessageBox.critical(self, "Load failed", str(exc))
            return

        self._workspace_path = Path(raw_path).expanduser().resolve()
        self._project = project
        self._scan = scan
        self._report = report
        self._overview = overview
        self._dirty = False

        self._rebuild_tree()
        self._show_overview()
        self._update_action_states()
        self.statusBar().showMessage(f"Loaded: {self._workspace_path}")

    def _reload_workspace(self) -> None:
        # Capture current selection
        mode = self._current_mode
        group = self._current_group
        host = self._current_host

        if self._dirty:
            ans = QMessageBox.question(self, "Unsaved changes", "Discard changes and reload?", 
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans != QMessageBox.StandardButton.Yes: return
        
        self._load_workspace()
        
        # Restore selection
        if mode == "group":
            self._select_in_tree("group", group)
        elif mode == "host":
            self._select_in_tree("host", host, group)

    def _select_in_tree(self, kind: str, name: str, branch: str | None = None) -> None:
        def walk(parent: QTreeWidgetItem | None = None):
            count = self.tree.topLevelItemCount() if parent is None else parent.childCount()
            for i in range(count):
                item = self.tree.topLevelItem(i) if parent is None else parent.child(i)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data[0] == kind and data[1] == name:
                    if kind != "host" or data[2] == branch:
                        self.tree.setCurrentItem(item)
                        item.setSelected(True)
                        self._expand_item_path(item)
                        return True
                if walk(item): return True
            return False
        walk()

    def _rebuild_tree(self) -> None:
        self.tree.clear()
        if self._project is None: return

        root_item = QTreeWidgetItem(["Inventory", "root"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, ("root", None))
        self.tree.addTopLevelItem(root_item)

        # Build groups starting from 'all'
        all_item = self._build_group_item("all")
        root_item.addChild(all_item)

        # Ungrouped
        ungrouped = QTreeWidgetItem(["ungrouped", "special"])
        ungrouped.setData(0, Qt.ItemDataRole.UserRole, ("group", "ungrouped"))
        self._style_item(ungrouped, "#757575", bold=True)
        for h_name in sorted(h for h, host in self._project.hosts.items() if not host.groups):
            ungrouped.addChild(self._build_host_item(h_name, "ungrouped"))
        root_item.addChild(ungrouped)

        # Other top-level groups
        parents = self._group_parent_map()
        for g_name in sorted(self._project.groups):
            if g_name != "all" and g_name not in parents:
                root_item.addChild(self._build_group_item(g_name))

        self.tree.expandToDepth(1)

    def _build_group_item(self, group_name: str) -> QTreeWidgetItem:
        group = self._project.groups.get(group_name)
        if not group: return QTreeWidgetItem([group_name, "error"])

        item = QTreeWidgetItem([group_name, f"vars:{len(group.variables)}"])
        item.setData(0, Qt.ItemDataRole.UserRole, ("group", group_name))
        self._style_item(item, "#1565c0", bold=True)

        for child in sorted(group.children):
            item.addChild(self._build_group_item(child))
        for host in sorted(group.hosts):
            item.addChild(self._build_host_item(host, group_name))
        return item

    def _build_host_item(self, host_name: str, branch: str) -> QTreeWidgetItem:
        host = self._project.hosts.get(host_name)
        v_count = len(host.variables) if host else 0
        item = QTreeWidgetItem([host_name, f"vars:{v_count}"])
        item.setData(0, Qt.ItemDataRole.UserRole, ("host", host_name, branch))
        self._style_item(item, "#2e7d32")
        return item

    def _style_item(self, item: QTreeWidgetItem, color: str, bold: bool = False) -> None:
        brush = QBrush(QColor(color))
        item.setForeground(0, brush)
        if bold:
            f = item.font(0)
            f.setBold(True)
            item.setFont(0, f)

    def _on_tree_selection_changed(self) -> None:
        items = self.tree.selectedItems()
        if not items: return
        
        payload = items[0].data(0, Qt.ItemDataRole.UserRole)
        if not payload: return

        kind = payload[0]
        if kind == "root":
            self._current_mode, self._current_group, self._current_host = "root", None, None
            self._show_overview()
        elif kind == "group":
            self._current_mode, self._current_group, self._current_host = "group", payload[1], None
            self._show_group_context(payload[1])
        elif kind == "host":
            self._current_mode, self._current_host, self._current_group = "host", payload[1], payload[2]
            self._show_host_context(payload[1], payload[2])
            
        self._update_action_states()

    def _show_overview(self) -> None:
        if not self._overview: return
        lines = ["Project Overview", ""] + [f"{l}: {v}" for l, v in self._overview.stats]
        self.overview_text.setPlainText("\n".join(lines))
        self.issues_text.setPlainText("\n".join(self._overview.issues) or "No issues.")
        self.variables_tree.clear()
        self.files_tree.clear()

    def _show_group_context(self, name: str) -> None:
        view = build_group_context_view(self._project, self._scan, name)
        self.overview_text.setPlainText("\n".join(view.summary_lines))
        self._populate_variables_tree(view.variables)
        self._populate_files_tree(view.files)
        self.trace_text.setPlainText(f"Group: {name}\nHosts: {', '.join(view.hosts) or '-'}")

    def _show_host_context(self, name: str, branch: str) -> None:
        view = build_host_context_view(self._project, self._scan, name, branch)
        self.overview_text.setPlainText("\n".join(view.summary_lines))
        self._populate_variables_tree(view.variables)
        self._populate_files_tree(view.files)
        self.trace_text.setPlainText("Double-click a masked value to reveal for 10s.")

    def _populate_variables_tree(self, rows: list[object]) -> None:
        self.variables_tree.clear()
        for row in sorted(rows, key=self._variable_sort_key):
            is_vault = "vault" in row.source_path.lower()
            val = "********" if is_vault else row.value_text
            item = QTreeWidgetItem([row.key, val, row.scope, row.source_path])
            item.setData(0, Qt.ItemDataRole.UserRole, row.key)
            item.setData(1, Qt.ItemDataRole.UserRole, row.value_text) # Store real val
            self._style_item(item, row.color)
            self.variables_tree.addTopLevelItem(item)

    def _on_variable_double_clicked(self, item: QTreeWidgetItem, col: int) -> None:
        if col == 1:
            real = item.data(1, Qt.ItemDataRole.UserRole)
            if real and item.text(1) == "********":
                item.setText(1, real)
                QTimer.singleShot(10000, lambda: item.setText(1, "********"))

    def _on_variable_selection_changed(self) -> None:
        items = self.variables_tree.selectedItems()
        if not items:
            self.trace_text.clear()
            return

        item = items[0]
        key = item.text(0)
        value = item.text(1)
        scope = item.text(2)
        source = item.text(3)

        self.trace_text.setPlainText(
            f"Variable: {key}\n"
            f"Value: {value}\n"
            f"Scope: {scope}\n"
            f"Source: {source}"
        )

    def _populate_files_tree(self, rows: list[object]) -> None:
        self.files_tree.clear()
        for row in rows:
            item = QTreeWidgetItem([row.kind, row.path])
            item.setData(0, Qt.ItemDataRole.UserRole, (row.kind, row.path))
            self._style_item(item, row.color)
            self.files_tree.addTopLevelItem(item)

    def _on_file_selection_changed(self) -> None:
        items = self.files_tree.selectedItems()
        if not items: 
            self.file_preview.clear()
            return
        kind, path = items[0].data(0, Qt.ItemDataRole.UserRole)
        self.file_preview.setPlainText(f"File: {path}\nKind: {kind}")

    def _open_source(self) -> None:
        items = self.files_tree.selectedItems()
        if not items: return
        kind, path = items[0].data(0, Qt.ItemDataRole.UserRole)
        file_path = Path(self._workspace_path) / path
        
        is_vault = (kind == "vault")
        try:
            if is_vault:
                if not VaultHandler.has_credentials():
                    if QMessageBox.question(self, "Vault", "No password set. Open Settings?", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                        self._open_settings()
                    if not VaultHandler.has_credentials(): return
                content = VaultHandler.decrypt(file_path)
            else:
                content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
            return

        if settings.external_editor and not is_vault:
            subprocess.Popen([settings.external_editor, str(file_path.resolve())])
        else:
            if CodeEditorDialog(self, file_path, content, is_vault).exec() == QDialog.DialogCode.Accepted:
                self._reload_workspace()

    def _add_group(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Group", "Group Name:")
        if ok and name.strip():
            self._project.add_group(name.strip())
            self._dirty = True
            self._rebuild_tree()

    def _add_host(self) -> None:
        dialog = HostDialog(self, list(self._project.groups.keys()), self._current_group)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, gs = dialog.get_data()
            if name:
                self._project.add_host(name)
                for g in gs: self._project.assign_host_to_group(name, g)
                self._dirty = True
                self._rebuild_tree()

    def _add_variable(self) -> None:
        dialog = VariableDialog(self, f"Add variable to {self._current_host or self._current_group}")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            key, val, f_name, encrypt = dialog.result_data
            if not f_name.endswith((".yml", ".yaml")): f_name += ".yml"
            
            target = self._current_host or self._current_group
            is_host = self._current_host is not None
            scope = VariableScope.HOST if is_host else VariableScope.GROUP
            s_type = "host_vars" if is_host else "group_vars"
            path = f"{s_type}/{target}/{f_name}"
            
            if encrypt:
                if not hasattr(self._project, "vault_files"): self._project.vault_files = set()
                self._project.vault_files.add(path)
            
            v = Variable(key=key, value=val, scope=scope, owner=target, 
                         source=VariableSource(source_path=path, source_type=s_type))
            
            if is_host: self._project.add_variable_to_host(target, v)
            else: self._project.add_variable_to_group(target, v)
            
            self._dirty = True
            self._rebuild_tree()

            if is_host:
                self._select_in_tree("host", target, self._current_group)
            else:
                self._select_in_tree("group", target)

            self.statusBar().showMessage(
                f"Variable '{key}' added to {path}. Press Save to write changes."
            )

    def _export_workspace(self) -> None:
        if not self._project: return
        # Check vault credentials first
        v_files = getattr(self._project, "vault_files", set())
        if v_files and not VaultHandler.has_credentials():
            if QMessageBox.question(self, "Vault", "Vault files detected but no password set. Open Settings?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                self._open_settings()
            if not VaultHandler.has_credentials(): return

        try:
            export_workspace(self._project, self._workspace_path)
            self._dirty = False
            self.statusBar().showMessage(f"Successfully saved to {self._workspace_path}")
            self._reload_workspace()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _find_entry(self) -> None:
        text, ok = QInputDialog.getText(self, "Find", "Search text:")
        if ok and text.strip():
            # Basic logic search
            needle = text.lower()
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                if needle in item.text(0).lower():
                    self.tree.setCurrentItem(item)
                    return

    def _group_parent_map(self) -> dict[str, set[str]]:
        pm = {}
        if self._project:
            for gn, g in self._project.groups.items():
                for c in g.children: pm.setdefault(c, set()).add(gn)
        return pm

    def _expand_item_path(self, item: QTreeWidgetItem) -> None:
        curr = item.parent()
        while curr:
            curr.setExpanded(True)
            curr = curr.parent()

    def closeEvent(self, event) -> None:
        if self._dirty:
            ans = QMessageBox.question(self, "Exit", "Save changes before exit?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if ans == QMessageBox.StandardButton.Yes:
                self._export_workspace()
                event.accept()
            elif ans == QMessageBox.StandardButton.No: event.accept()
            else: event.ignore()
        else: event.accept()

    def _variable_sort_key(self, row: object) -> tuple[int, str, str]:
        sp = str(getattr(row, "source_path", ""))
        k = str(getattr(row, "key", ""))
        p = 0 if "all" in sp else 1 if "group_vars" in sp else 2
        return p, sp, k
