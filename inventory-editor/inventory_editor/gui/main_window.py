from __future__ import annotations
import shutil
import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QBrush, QColor, QFont, QAction, QIcon, QKeySequence, QShortcut, QTextDocument, QTextCursor
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
    QComboBox,
    QSizePolicy
)

from ruamel.yaml import YAML

from inventory_editor.analyzer.workspace_quality import analyze_workspace_scan
from inventory_editor.gui.context import ContextVariableRow, build_group_context_view, build_host_context_view
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
        
        title = QLabel("AIS - Ansible Inventory Studio")
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
        self.inv_edit = QLineEdit(getattr(settings, "default_inventory_file", ""))
        self.inv_edit.setPlaceholderText("Relative path, e.g. inventory.yml or inventories/prod.yml")
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

        browse_inv = QPushButton("...")
        browse_inv.setFixedWidth(35)
        browse_inv.clicked.connect(self._browse_inv)
        inv_layout = QHBoxLayout()
        inv_layout.addWidget(self.inv_edit)
        inv_layout.addWidget(browse_inv)

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
        form.addRow("Default Inventory File:", inv_layout)
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

    def _browse_inv(self):
        base = self.ws_edit.text().strip()
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select default inventory file",
            base if base else str(Path.home()),
            "Inventory files (*.yml *.yaml hosts inventory);;All files (*)",
        )
        if selected:
            try:
                if base:
                    rel = Path(selected).resolve().relative_to(Path(base).expanduser().resolve())
                    self.inv_edit.setText(str(rel))
                else:
                    self.inv_edit.setText(selected)
            except ValueError:
                self.inv_edit.setText(selected)

    def _browse_vf(self):
        selected, _ = QFileDialog.getOpenFileName(self, "Select Vault password file")
        if selected: self.vault_file_edit.setText(selected)

    def _browse_editor(self):
        selected, _ = QFileDialog.getOpenFileName(self, "Select Editor executable")
        if selected: self.editor_edit.setText(selected)

    def _save(self):
        settings.default_workspace = self.ws_edit.text().strip()
        settings.default_inventory_file = self.inv_edit.text().strip()
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
        self.setWindowTitle("AIS - Ansible Inventory Studio")
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

        self._find_matches: list[tuple[str, QTreeWidgetItem]] = []
        self._find_index: int = -1
        self._find_text: str = ""

        self._last_find_text: str = ""
        self._last_find_index: int = -1

        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()
        self._update_action_states()

        if workspace is not None:
            self.path_edit.setText(str(Path(workspace).expanduser().resolve()))
            self._refresh_inventory_candidates()
            self._load_workspace()
        elif settings.default_workspace:
            self.path_edit.setText(settings.default_workspace)
            self._refresh_inventory_candidates()

    def _setup_shortcuts(self) -> None:
        # Single Find shortcut binding.
        # QKeySequence.StandardKey.Find maps to Cmd+F on macOS and Ctrl+F on Windows/Linux.
        # Do not also set the same shortcut on QAction, otherwise Qt may report:
        # "Ambiguous shortcut overload: Ctrl+F".
        self.find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        self.find_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.find_shortcut.activated.connect(self._show_find_bar)


    def _setup_ui(self) -> None:
        # --- Toolbar ---
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        toolbar.addWidget(QLabel("  Workspace: "))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Path to Ansible inventory workspace directory...")
        self.path_edit.returnPressed.connect(self._reload_current_workspace)
        self.path_edit.setMinimumWidth(400)
        toolbar.addWidget(self.path_edit)
        
        self.browse_action = QAction("Browse", self)
        self.browse_action.setToolTip("Browse for workspace directory")
        self.browse_action.triggered.connect(self._browse_workspace)
        toolbar.addAction(self.browse_action)

        toolbar.addWidget(QLabel("  Inventory: "))
        self.inventory_combo = QComboBox()
        self.inventory_combo.setMinimumWidth(260)
        self.inventory_combo.setToolTip("Select inventory file used as AIS source of truth")
        self.inventory_combo.activated.connect(self._on_inventory_combo_activated)
        toolbar.addWidget(self.inventory_combo)

        self.load_action = QAction("Load", self)
        self.load_action.setToolTip("Load selected workspace and inventory file")
        self.load_action.triggered.connect(self._reload_current_workspace)
        toolbar.addAction(self.load_action)
        
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
        self.find_action.setToolTip("Search hosts, groups and variable keys (Ctrl+F / Cmd+F)")
        # Shortcut is handled by _setup_shortcuts() to avoid duplicate Ctrl+F bindings.
        self.find_action.triggered.connect(self._show_find_bar)
        toolbar.addAction(self.find_action)

        toolbar.addSeparator()

        # Dedicated search toolbar. More reliable than hidden widgets inside main toolbar.
        self.find_toolbar = QToolBar("Find Toolbar")
        self.find_toolbar.setMovable(False)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.find_toolbar)

        self.find_toolbar.addWidget(QLabel(" Find: "))

        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Find host, group or variable key...")
        self.find_edit.setMinimumWidth(320)
        # Search is intentionally executed only on Enter / Next / Previous.
        self.find_edit.returnPressed.connect(self._find_next)
        self.find_toolbar.addWidget(self.find_edit)

        self.find_prev_button = QPushButton("Previous")
        self.find_prev_button.clicked.connect(self._find_previous)
        self.find_toolbar.addWidget(self.find_prev_button)

        self.find_next_button = QPushButton("Next")
        self.find_next_button.clicked.connect(self._find_next)
        self.find_toolbar.addWidget(self.find_next_button)

        self.find_close_button = QPushButton("×")
        self.find_close_button.setToolTip("Close search")
        self.find_close_button.clicked.connect(self._hide_find_bar)
        self.find_toolbar.addWidget(self.find_close_button)

        self.find_toolbar.hide()
        
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

        toolbar.addSeparator()

        self.effective_action = QAction("Effective", self)
        self.effective_action.setToolTip("Show effective inventory variables for selected host or group")
        self.effective_action.triggered.connect(self._show_effective_config)
        toolbar.addAction(self.effective_action)

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

        # Tab: Effective Config
        effective_cont = QWidget()
        effective_lay = QVBoxLayout(effective_cont)

        effective_head = QHBoxLayout()
        effective_head.addWidget(QLabel("Limit / pattern:"))

        self.effective_limit_edit = QLineEdit()
        self.effective_limit_edit.setPlaceholderText("Optional preview note, e.g. app_servers or vm-169")
        effective_head.addWidget(self.effective_limit_edit)

        self.effective_refresh_btn = QPushButton("Refresh")
        self.effective_refresh_btn.setToolTip("Refresh effective variable view for the current selection")
        self.effective_refresh_btn.clicked.connect(self._show_effective_config)
        effective_head.addWidget(self.effective_refresh_btn)

        effective_head.addWidget(QLabel(" Find in output:"))

        self.effective_find_edit = QLineEdit()
        self.effective_find_edit.setPlaceholderText("Search text...")
        self.effective_find_edit.setMinimumWidth(220)
        self.effective_find_edit.returnPressed.connect(self._find_effective_next)
        effective_head.addWidget(self.effective_find_edit)

        self.effective_find_prev_btn = QPushButton("Previous")
        self.effective_find_prev_btn.clicked.connect(self._find_effective_previous)
        effective_head.addWidget(self.effective_find_prev_btn)

        self.effective_find_next_btn = QPushButton("Next")
        self.effective_find_next_btn.clicked.connect(self._find_effective_next)
        effective_head.addWidget(self.effective_find_next_btn)

        effective_lay.addLayout(effective_head)

        self.effective_text = QTextEdit()
        self.effective_text.setReadOnly(True)
        self.effective_text.setFont(QFont("Menlo", 10) if os.name != 'nt' else QFont("Consolas", 10))
        self.effective_text.setPlainText(
            "Select a host or group and click Effective.\n\n"
            "This first version shows a static inventory-based preview from AIS.\n"
            "It does not yet execute ansible-inventory or ansible-playbook."
        )
        effective_lay.addWidget(self.effective_text)

        self.tabs.addTab(effective_cont, "Effective Config")

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
        tools_m.addAction(self.effective_action)
        
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
        self.effective_action.setEnabled(has_proj and self._current_mode in ("group", "host"))

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
                inv_file.write_text("# Created by AIS - Ansible Inventory Studio\nall:\n  hosts:\n    localhost:\n      ansible_connection: local\n", encoding="utf-8")
            
            all_file = root / "group_vars" / "all" / "main.yml"
            if not all_file.exists():
                all_file.write_text("# Global variables\nansible_python_interpreter: auto_silent\n", encoding="utf-8")
                
            self.path_edit.setText(str(root))
            self._load_workspace()
            QMessageBox.information(self, "Success", f"Project initialized at {root}")
        except Exception as e:
            QMessageBox.critical(self, "Init Failed", str(e))

    def _discover_inventory_candidates(self, root: Path) -> list[str]:
        if not root.exists() or not root.is_dir():
            return []

        candidates: set[str] = set()

        root_names = [
            "inventory",
            "inventory.yml",
            "inventory.yaml",
            "hosts",
            "hosts.yml",
            "hosts.yaml",
        ]

        for name in root_names:
            path = root / name
            if path.is_file():
                candidates.add(name)

        for subdir_name in ("inventory", "inventories"):
            subdir = root / subdir_name
            if not subdir.is_dir():
                continue

            for pattern in ("*.yml", "*.yaml", "hosts", "inventory"):
                for path in subdir.glob(pattern):
                    if path.is_file():
                        candidates.add(str(path.relative_to(root)))

        # Fallback: root-level YAML files that are not obvious vars files.
        for path in list(root.glob("*.yml")) + list(root.glob("*.yaml")):
            if path.is_file():
                candidates.add(path.name)

        return sorted(candidates)

    def _refresh_inventory_candidates(self) -> None:
        if not hasattr(self, "inventory_combo"):
            return

        raw_path = self.path_edit.text().strip()
        root = Path(raw_path).expanduser().resolve() if raw_path else None

        previous = self.inventory_combo.currentText().strip()
        candidates = self._discover_inventory_candidates(root) if root else []

        self.inventory_combo.blockSignals(True)
        self.inventory_combo.clear()

        for item in candidates:
            self.inventory_combo.addItem(item)

        selected = ""

        # Prefer previously selected value if it still exists.
        if previous and previous in candidates:
            selected = previous

        # Then prefer saved default inventory from settings.
        if not selected:
            default_inventory = getattr(settings, "default_inventory_file", "").strip()
            if default_inventory and default_inventory in candidates:
                selected = default_inventory

        # Otherwise select the first discovered candidate.
        if not selected and candidates:
            selected = candidates[0]

        if selected:
            idx = self.inventory_combo.findText(selected)
            if idx >= 0:
                self.inventory_combo.setCurrentIndex(idx)

        self.inventory_combo.blockSignals(False)


    def _on_inventory_combo_activated(self, _index: int) -> None:
        # On Windows/WSL the combobox popup may remain visually stuck if the
        # workspace reload starts directly inside the activated signal.
        # Hide the popup first and run the reload in the next Qt event loop turn.
        if hasattr(self, "inventory_combo"):
            self.inventory_combo.hidePopup()
            self.inventory_combo.clearFocus()

        QTimer.singleShot(0, self._load_workspace)

    def _selected_inventory_file(self) -> str | None:
        if not hasattr(self, "inventory_combo"):
            return None

        selected = self.inventory_combo.currentText().strip()
        return selected or None

    def _reload_current_workspace(self) -> None:
        self._refresh_inventory_candidates()
        self._load_workspace()

    def _browse_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select inventory workspace", self.path_edit.text())
        if selected:
            self.path_edit.setText(selected)
            self._refresh_inventory_candidates()
            self._load_workspace()

    def _load_workspace(self) -> None:
        raw_path = self.path_edit.text().strip()
        if not raw_path: return

        try:
            if hasattr(self, "inventory_combo") and self.inventory_combo.count() == 0:
                self._refresh_inventory_candidates()

            selected_inventory = self._selected_inventory_file()

            project, scan = load_inventory_workspace(
                raw_path,
                vault_password=settings.vault_password,
                vault_password_file=settings.vault_password_file,
                inventory_file=selected_inventory,
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
        self.statusBar().showMessage(
            f"Loaded: {self._workspace_path} / inventory: {getattr(self._project, 'inventory_file', '-')}"
        )

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
        self._set_issues_text(self._overview.issues)
        self.variables_tree.clear()
        self.files_tree.clear()

    def _set_issues_text(self, issue_lines: list[str]) -> None:
        clean_lines = [line for line in issue_lines if str(line).strip()]
        self.issues_text.setPlainText("\n".join(clean_lines) if clean_lines else "No issues.")

        idx = self.tabs.indexOf(self.issues_text)
        if idx >= 0:
            self.tabs.setTabText(idx, "⚠ Issues" if clean_lines else "Issues")

    def _host_membership_issue_lines(self, host_name: str, branch: str) -> list[str]:
        if not self._project or host_name not in self._project.hosts:
            return []

        lines: list[str] = []

        try:
            branch_groups = self._project.branch_groups_for_context(branch)
            actual_groups = [
                group.name
                for group in self._project.ordered_groups_for_host(host_name)
            ]
            effective_vars = self._project.effective_variables_for_host(host_name)
        except Exception as exc:
            return [f"[B] Failed to calculate Ansible membership impact for host {host_name}: {exc}"]

        branch_set = set(branch_groups)
        outside_branch_groups = [
            group_name
            for group_name in actual_groups
            if group_name not in branch_set
        ]

        sources: set[str] = set()
        vault_sources: set[str] = set()
        outside_branch_sources: set[str] = set()
        outside_branch_vault_sources: set[str] = set()

        for variable in effective_vars.values():
            source = str(getattr(variable.source, "source_path", "")).strip()
            if not source:
                continue

            sources.add(source)

            if "vault" in source.lower():
                vault_sources.add(source)

            for group_name in outside_branch_groups:
                prefix = f"group_vars/{group_name}/"
                if source.startswith(prefix):
                    outside_branch_sources.add(source)

                    if "vault" in source.lower():
                        outside_branch_vault_sources.add(source)

        if len(actual_groups) > len(branch_groups) or outside_branch_groups:
            lines.append(
                f"[B] Host '{host_name}' is member of multiple Ansible inventory groups."
            )
            lines.append(
                f"    Selected AIS branch/context: {branch or '-'}"
            )
            lines.append(
                "    Selected branch groups: "
                + (", ".join(branch_groups) if branch_groups else "-")
            )
            lines.append(
                "    Actual Ansible groups for this host: "
                + (", ".join(actual_groups) if actual_groups else "-")
            )
            lines.append(
                "    Important: Ansible --limit filters target hosts only. "
                "It does not restrict group_vars loading to the selected branch."
            )

        if outside_branch_sources:
            lines.append(
                f"[B] Host '{host_name}' may load variables from groups outside selected branch '{branch}'."
            )
            for source in sorted(outside_branch_sources):
                lines.append(f"    - {source}")

        if vault_sources:
            lines.append(
                f"[B] Host '{host_name}' has vault-backed variables reachable through inventory membership."
            )
            for source in sorted(vault_sources):
                lines.append(f"    - {source}")
            lines.append(
                "    Jobs without vault secrets may fail even when --limit targets another group containing this host."
            )

        if outside_branch_vault_sources:
            lines.append(
                f"[A] Vault-backed variables exist outside selected branch '{branch}' but are still reachable by host membership."
            )
            for source in sorted(outside_branch_vault_sources):
                lines.append(f"    - {source}")
            lines.append(
                "    This is the risky case: a playbook limited to this host/branch can still require Vault because the host belongs to another group."
            )

        return lines

    def _show_group_context(self, name: str) -> None:
        view = build_group_context_view(self._project, self._scan, name)
        self.overview_text.setPlainText("\n".join(view.summary_lines))
        self._populate_variables_tree(view.variables)
        self._populate_files_tree(view.files)
        self.trace_text.setPlainText(f"Group: {name}\nHosts: {', '.join(view.hosts) or '-'}")
        self._set_issues_text(self._overview.issues if self._overview else [])

    def _show_host_context(self, name: str, branch: str) -> None:
        view = build_host_context_view(self._project, self._scan, name, branch)
        self.overview_text.setPlainText("\n".join(view.summary_lines))
        self._populate_variables_tree(view.variables)
        self._populate_files_tree(view.files)
        self.trace_text.setPlainText("Double-click a masked value to reveal for 10s.")

        issue_lines: list[str] = []
        if self._overview:
            issue_lines.extend(self._overview.issues)

        issue_lines.extend(self._host_membership_issue_lines(name, branch))
        self._set_issues_text(issue_lines)

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

    def _show_effective_config(self) -> None:
        if not self._project:
            self.statusBar().showMessage("No workspace loaded.", 5000)
            return

        if self._current_mode not in ("group", "host"):
            self.effective_text.setPlainText(
                "Select a host or group first.\n\n"
                "The Effective Config view is calculated for the current inventory context."
            )
            self.tabs.setCurrentWidget(self.effective_text.parentWidget())
            self.statusBar().showMessage("Select a host or group first.", 5000)
            return

        try:
            lines = self._build_effective_config_lines()
        except Exception as exc:
            QMessageBox.critical(self, "Effective Config Error", str(exc))
            return

        self.effective_text.setPlainText("\n".join(lines))
        self.tabs.setCurrentWidget(self.effective_text.parentWidget())
        self.statusBar().showMessage("Effective config preview refreshed.", 5000)

    def _find_effective_next(self) -> None:
        self._find_effective_text(backward=False)

    def _find_effective_previous(self) -> None:
        self._find_effective_text(backward=True)

    def _find_effective_text(self, backward: bool = False) -> None:
        needle = self.effective_find_edit.text().strip()
        if not needle:
            self.statusBar().showMessage("Enter text to search in Effective Config.", 3000)
            return

        flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)

        found = self.effective_text.find(needle, flags)

        if not found:
            cursor = self.effective_text.textCursor()
            if backward:
                cursor.movePosition(QTextCursor.MoveOperation.End)
            else:
                cursor.movePosition(QTextCursor.MoveOperation.Start)

            self.effective_text.setTextCursor(cursor)
            found = self.effective_text.find(needle, flags)

        if found:
            direction = "previous" if backward else "next"
            self.statusBar().showMessage(f"Found {direction}: {needle}", 3000)
        else:
            self.statusBar().showMessage(f"Nothing found in Effective Config: {needle}", 5000)

    def _build_effective_config_lines(self) -> list[str]:
        limit = self.effective_limit_edit.text().strip() or "-"

        lines: list[str] = []
        lines.append("Effective Config Preview")
        lines.append("=" * 100)
        lines.append("Mode: Static AIS inventory resolution")
        lines.append(f"Limit / pattern note: {limit}")
        lines.append("")
        lines.append(
            "This view is based on the currently loaded AIS inventory model "
            "(inventory, group_vars, host_vars and vault-backed variables)."
        )
        lines.append(
            "It does not yet execute ansible-inventory or ansible-playbook, "
            "so play vars, role vars, facts, set_fact and extra-vars are not included."
        )
        lines.append("")

        if self._current_mode == "host":
            return self._build_effective_host_lines(lines)

        if self._current_mode == "group":
            return self._build_effective_group_lines(lines)

        lines.append("Select a host or group first.")
        return lines

    def _build_effective_group_lines(self, lines: list[str]) -> list[str]:
        group_name = self._current_group
        if not group_name:
            lines.append("No group selected.")
            return lines

        hosts = self._hosts_for_group(group_name)

        lines.append(f"Selected group: {group_name}")
        lines.append("")
        lines.append("Affected hosts")
        lines.append("-" * 100)

        if hosts:
            for host in hosts:
                lines.append(f"  - {host}")
        else:
            lines.append("  No hosts found in this group context.")
            return lines

        # Build effective rows for every affected host.
        host_rows_map: dict[str, list[object]] = {}

        for host_name in hosts:
            try:
                host_view = build_host_context_view(
                    self._project,
                    self._scan,
                    host_name,
                    group_name,
                )
                host_rows_map[host_name] = sorted(host_view.variables, key=self._variable_sort_key)
            except Exception as exc:
                lines.append("")
                lines.append(f"Host {host_name}: failed to build context: {exc}")
                host_rows_map[host_name] = []

        common_rows = self._common_effective_rows(host_rows_map)

        lines.append("")
        lines.append("=" * 100)
        lines.append("Common effective variables for all affected hosts")
        lines.append("=" * 100)
        lines.append(
            "These variables have the same final value and source for every host in this group context."
        )
        lines.append("")

        if common_rows:
            self._append_effective_sections_by_source(lines, common_rows)
        else:
            lines.append("No common effective variables found across all affected hosts.")

        lines.append("")
        lines.append("=" * 100)
        lines.append("Per-host effective variables and differences")
        lines.append("=" * 100)

        for host_name in hosts:
            rows = host_rows_map.get(host_name, [])
            final_by_key = self._effective_final_by_key(rows)
            per_host_rows = [
                row for key, row in sorted(final_by_key.items())
                if key not in common_rows
            ]

            lines.append("")
            lines.append(f"Host: {host_name}")
            lines.append("-" * 100)

            if not rows:
                lines.append("No variables found.")
                continue

            if not per_host_rows:
                lines.append("No host-specific differences. This host currently uses only common effective variables.")
                continue

            self._append_effective_sections_by_source(lines, {
                str(getattr(row, "key", "")): row
                for row in per_host_rows
            })

        self._append_execution_context(
            lines=lines,
            context_type="group",
            selected_name=group_name,
            hosts=hosts,
            host_rows_map=host_rows_map,
        )

        return lines

    def _common_effective_rows(self, host_rows_map: dict[str, list[object]]) -> dict[str, object]:
        if not host_rows_map:
            return {}

        per_host_final: dict[str, dict[str, object]] = {
            host: self._effective_final_by_key(rows)
            for host, rows in host_rows_map.items()
        }

        hosts = list(per_host_final)
        if not hosts:
            return {}

        first_host = hosts[0]
        common: dict[str, object] = {}

        for key, first_row in per_host_final[first_host].items():
            first_value = self._effective_value_text(first_row)
            first_source = str(getattr(first_row, "source_path", ""))
            first_scope = str(getattr(first_row, "scope", ""))

            same_everywhere = True

            for host in hosts[1:]:
                row = per_host_final[host].get(key)
                if row is None:
                    same_everywhere = False
                    break

                value = self._effective_value_text(row)
                source = str(getattr(row, "source_path", ""))
                scope = str(getattr(row, "scope", ""))

                if value != first_value or source != first_source or scope != first_scope:
                    same_everywhere = False
                    break

            if same_everywhere:
                common[key] = first_row

        return common

    def _append_effective_sections_by_source(self, lines: list[str], final_by_key: dict[str, object]) -> None:
        buckets: list[tuple[str, list[tuple[str, object]]]] = [
            ("GLOBAL / group_vars/all", []),
            ("GLOBAL VAULT / group_vars/all", []),
            ("GROUP / group_vars", []),
            ("GROUP VAULT / group_vars", []),
            ("HOST / host_vars", []),
            ("HOST VAULT / host_vars", []),
            ("OTHER", []),
        ]

        bucket_map = {name: rows for name, rows in buckets}

        for key, row in sorted(final_by_key.items()):
            source = str(getattr(row, "source_path", ""))
            source_l = source.lower()
            is_vault = "vault" in source_l

            if source.startswith("group_vars/all/") or source == "group_vars/all/main.yml":
                if is_vault:
                    bucket_map["GLOBAL VAULT / group_vars/all"].append((key, row))
                else:
                    bucket_map["GLOBAL / group_vars/all"].append((key, row))

            elif source.startswith("group_vars/"):
                if is_vault:
                    bucket_map["GROUP VAULT / group_vars"].append((key, row))
                else:
                    bucket_map["GROUP / group_vars"].append((key, row))

            elif source.startswith("host_vars/"):
                if is_vault:
                    bucket_map["HOST VAULT / host_vars"].append((key, row))
                else:
                    bucket_map["HOST / host_vars"].append((key, row))

            else:
                bucket_map["OTHER"].append((key, row))

        for title, rows in buckets:
            if not rows:
                continue

            lines.append("")
            lines.append(title)
            lines.append("-" * 100)
            lines.append(f"{'KEY':30} {'VALUE':28} {'SCOPE':10} {'SOURCE'}")
            lines.append("-" * 100)

            for key, row in rows:
                value = self._effective_value_text(row)
                scope = str(getattr(row, "scope", ""))
                source = str(getattr(row, "source_path", ""))

                lines.append(
                    f"{key[:30]:30} {value[:28]:28} {scope[:10]:10} {source}"
                )


    def _build_effective_host_lines(self, lines: list[str]) -> list[str]:
        host_name = self._current_host
        branch = self._current_group or ""

        if not host_name:
            lines.append("No host selected.")
            return lines

        lines.append(f"Selected host: {host_name}")
        lines.append(f"Branch group: {branch or '-'}")
        lines.append("")

        try:
            view = build_host_context_view(
                self._project,
                self._scan,
                host_name,
                branch,
            )
            rows = sorted(view.variables, key=self._variable_sort_key)
        except Exception as exc:
            lines.append(f"Failed to build host context: {exc}")
            return lines

        lines.append("Final effective variables by source")
        lines.append("-" * 100)

        if not rows:
            lines.append("No variables found for this host.")
            return lines

        self._append_effective_sections_by_source(
            lines,
            self._effective_final_by_key(rows),
        )

        lines.append("")
        lines.append("Trace / overrides")
        lines.append("-" * 100)
        self._append_effective_trace(lines, rows)

        self._append_ansible_membership_impact(
            lines=lines,
            host_name=host_name,
            selected_branch=branch,
        )

        self._append_execution_context(
            lines=lines,
            context_type="host",
            selected_name=host_name,
            hosts=[host_name],
            host_rows_map={host_name: rows},
        )

        return lines

    def _append_ansible_membership_impact(
        self,
        lines: list[str],
        host_name: str,
        selected_branch: str,
    ) -> None:
        if not self._project:
            return

        host = self._project.hosts.get(host_name)
        if host is None:
            return

        try:
            actual_groups = self._actual_ansible_groups_for_host(host_name)
            actual_rows = self._actual_ansible_rows_for_host(host_name)
        except Exception as exc:
            lines.append("")
            lines.append("=" * 100)
            lines.append("Actual Ansible Inventory Membership Impact")
            lines.append("=" * 100)
            lines.append(f"Failed to calculate actual Ansible membership impact: {exc}")
            return

        actual_sources = self._sources_from_rows(actual_rows)
        vault_sources = [src for src in actual_sources if "vault" in src.lower()]

        branch_groups = self._project.branch_groups_for_context(selected_branch)
        branch_set = set(branch_groups)
        outside_branch_groups = [
            group_name for group_name in actual_groups
            if group_name not in branch_set
        ]

        lines.append("")
        lines.append("=" * 100)
        lines.append("Actual Ansible Inventory Membership Impact")
        lines.append("=" * 100)
        lines.append(
            "This section shows the real inventory membership impact for this host."
        )
        lines.append(
            "The selected AIS branch is useful for inspection, but Ansible host variable"
        )
        lines.append(
            "loading is based on all groups the host belongs to, not only on --limit."
        )
        lines.append("")

        lines.append("Selected AIS branch/context groups:")
        if branch_groups:
            for group_name in branch_groups:
                lines.append(f"  - {group_name}")
        else:
            lines.append("  -")
        lines.append("")

        lines.append("All Ansible inventory groups for this host:")
        if actual_groups:
            for group_name in actual_groups:
                marker = "  (outside selected branch)" if group_name in outside_branch_groups else ""
                lines.append(f"  - {group_name}{marker}")
        else:
            lines.append("  -")
        lines.append("")

        lines.append("Variable sources Ansible may load for this host:")
        if actual_sources:
            for source in actual_sources:
                lines.append(f"  - {source}")
        else:
            lines.append("  -")
        lines.append("")

        if vault_sources:
            lines.append("Vault impact:")
            for source in vault_sources:
                lines.append(f"  - {source}")
            lines.append("")
            lines.append(
                "WARNING: This host has vault-backed variables reachable through its"
            )
            lines.append(
                "inventory group membership. Jobs without vault secrets may fail even"
            )
            lines.append(
                "when --limit targets another group containing the same host."
            )
        else:
            lines.append("Vault impact:")
            lines.append("  No vault-backed variable sources detected for this host membership.")

    def _actual_ansible_groups_for_host(self, host_name: str) -> list[str]:
        if not self._project:
            return []

        groups = self._project.ordered_groups_for_host(host_name)
        return [group.name for group in groups]

    def _actual_ansible_rows_for_host(self, host_name: str) -> list[object]:
        if not self._project:
            return []

        effective = self._project.effective_variables_for_host(host_name)

        rows: list[object] = []
        for key, variable in sorted(effective.items(), key=lambda item: item[0].lower()):
            source_path = variable.source.source_path
            rows.append(
                ContextVariableRow(
                    key=key,
                    value_text=str(variable.value),
                    scope=variable.scope.value,
                    source_path=source_path,
                    source_type=variable.source.source_type,
                    color="#546e7a",
                )
            )

        return rows

    def _sources_from_rows(self, rows: list[object]) -> list[str]:
        sources: set[str] = set()

        for row in rows:
            source = str(getattr(row, "source_path", "")).strip()
            if source:
                sources.add(source)

        return sorted(sources)

    def _append_execution_context(
        self,
        lines: list[str],
        context_type: str,
        selected_name: str,
        hosts: list[str],
        host_rows_map: dict[str, list[object]],
    ) -> None:
        lines.append("")
        lines.append("=" * 100)
        lines.append("Execution / Selection Context")
        lines.append("=" * 100)

        workspace = str(self._workspace_path) if self._workspace_path else "-"
        lines.append("Inventory workspace:")
        lines.append(f"  {workspace}")
        lines.append("")

        inventory_files = self._inventory_files_for_context()
        lines.append("Inventory files detected:")
        if inventory_files:
            for item in inventory_files:
                lines.append(f"  - {item}")
        else:
            lines.append("  - inventory source not detected by AIS scan")
        lines.append("")

        lines.append("Selected AIS context:")
        if context_type == "group":
            lines.append(f"  group: {selected_name}")
        elif context_type == "host":
            lines.append(f"  host: {selected_name}")
            lines.append(f"  branch/group context: {self._current_group or '-'}")
        else:
            lines.append(f"  {context_type}: {selected_name}")
        lines.append("")

        lines.append("Suggested Ansible limit:")
        if context_type == "group":
            lines.append(f"  -l '{selected_name}'")
        elif context_type == "host":
            if self._current_group:
                lines.append(f"  -l '{selected_name}:&{self._current_group}'")
            else:
                lines.append(f"  -l '{selected_name}'")
        else:
            lines.append("  -")
        lines.append("")

        lines.append("Affected hosts in AIS static model:")
        if hosts:
            lines.append("  " + ", ".join(hosts))
        else:
            lines.append("  -")
        lines.append("")

        sources = self._effective_sources_from_host_rows(host_rows_map)
        lines.append("Variable sources used in this preview:")
        if sources:
            for source in sources:
                lines.append(f"  - {source}")
        else:
            lines.append("  -")
        lines.append("")

        lines.append("Important:")
        lines.append(
            "  Ansible --limit filters hosts. It does not remove variables from other groups"
        )
        lines.append(
            "  if the host is also a member of those groups. This view is a static AIS"
        )
        lines.append(
            "  preview based on the currently loaded inventory model."
        )

    def _effective_sources_from_host_rows(self, host_rows_map: dict[str, list[object]]) -> list[str]:
        sources: set[str] = set()

        for rows in host_rows_map.values():
            for row in rows:
                source = str(getattr(row, "source_path", "")).strip()
                if source:
                    sources.add(source)

        return sorted(sources)

    def _inventory_files_for_context(self) -> list[str]:
        if self._project and getattr(self._project, "inventory_file", ""):
            return [str(self._project.inventory_file)]

        selected = self._selected_inventory_file()
        if selected:
            return [selected]

        return []


    def _append_effective_table(self, lines: list[str], rows: list[object]) -> None:
        final_by_key = self._effective_final_by_key(rows)

        lines.append(f"{'KEY':30} {'VALUE':28} {'SCOPE':10} {'SOURCE'}")
        lines.append("-" * 100)

        for key in sorted(final_by_key):
            row = final_by_key[key]
            value = self._effective_value_text(row)
            scope = str(getattr(row, "scope", ""))
            source = str(getattr(row, "source_path", ""))

            lines.append(
                f"{key[:30]:30} {value[:28]:28} {scope[:10]:10} {source}"
            )

    def _append_effective_trace(self, lines: list[str], rows: list[object]) -> None:
        traces: dict[str, list[object]] = {}
        final_by_key = self._effective_final_by_key(rows)

        for row in rows:
            key = str(getattr(row, "key", ""))
            traces.setdefault(key, []).append(row)

        for key in sorted(traces):
            chain = traces[key]
            lines.append("")
            lines.append(key)

            for idx, row in enumerate(chain, start=1):
                value = self._effective_value_text(row)
                scope = str(getattr(row, "scope", ""))
                source = str(getattr(row, "source_path", ""))

                winner = "  <-- final" if row is final_by_key.get(key) else ""
                lines.append(f"  {idx}. [{scope}] {source}")
                lines.append(f"     value: {value}{winner}")

    def _effective_final_by_key(self, rows: list[object]) -> dict[str, object]:
        final_by_key: dict[str, object] = {}

        for row in rows:
            key = str(getattr(row, "key", ""))
            final_by_key[key] = row

        return final_by_key

    def _effective_value_text(self, row: object) -> str:
        value = str(getattr(row, "value_text", ""))
        source = str(getattr(row, "source_path", ""))

        if "vault" in source.lower():
            return "********"

        return value

    def _hosts_for_group(self, group_name: str) -> list[str]:
        if not self._project:
            return []

        result: set[str] = set()
        visited: set[str] = set()

        def collect(name: str) -> None:
            if name in visited:
                return

            visited.add(name)

            group = self._project.groups.get(name)
            if not group:
                return

            for host in getattr(group, "hosts", []):
                result.add(host)

            for child in getattr(group, "children", []):
                collect(child)

        collect(group_name)

        return sorted(result)


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
        self._show_find_bar()

    def _show_find_bar(self) -> None:
        if hasattr(self, "find_toolbar"):
            self.find_toolbar.show()

        self.find_edit.setFocus()
        self.find_edit.selectAll()

        self.statusBar().showMessage("Search opened", 3000)

        # Do not auto-search while opening the bar.
        # User can type freely and start search with Enter / Next / Previous.

    def _hide_find_bar(self) -> None:
        if hasattr(self, "find_toolbar"):
            self.find_toolbar.hide()

        self._find_matches = []
        self._find_index = -1
        self._find_text = ""

        self.statusBar().showMessage("Search closed", 3000)
        self.tree.setFocus()

    def _on_find_text_changed(self, value: str) -> None:
        # Search is intentionally not executed while typing.
        # This method is kept only as a harmless compatibility/reset hook.
        self._find_text = value.strip().lower()
        self._find_matches = []
        self._find_index = -1

        if not self._find_text:
            self.statusBar().showMessage("Search ready", 3000)
        else:
            self.statusBar().showMessage("Press Enter or Next to search", 3000)


    def _collect_find_matches(self, needle: str):
        """Collect stable global search matches.

        Default search scope:
        - all group names
        - all host names
        - all variable keys in all groups
        - all variable keys in all hosts

        Values and file paths are intentionally not searched by default.
        Matches are stable tuples, not QTreeWidgetItem references.
        """
        matches: list[tuple] = []

        if not self._project:
            return matches

        # Groups
        for group_name in sorted(self._project.groups):
            if needle in group_name.lower():
                matches.append(("group", group_name))

        # Host occurrences in the visible inventory tree.
        # A host can appear in multiple groups, and search must cycle through
        # every visible host+branch occurrence, not only the unique host object.
        def walk_host_occurrences(item: QTreeWidgetItem) -> None:
            payload = item.data(0, Qt.ItemDataRole.UserRole)

            if payload and payload[0] == "host":
                host_name = str(payload[1])
                branch = str(payload[2]) if len(payload) > 2 else ""

                if needle in host_name.lower():
                    matches.append(("host", host_name, branch))

            for i in range(item.childCount()):
                walk_host_occurrences(item.child(i))

        for i in range(self.tree.topLevelItemCount()):
            walk_host_occurrences(self.tree.topLevelItem(i))

        # Group variable keys
        for group_name, group in sorted(self._project.groups.items()):
            for var in getattr(group, "variables", []):
                key = str(getattr(var, "key", ""))
                if needle in key.lower():
                    source = self._variable_source_path(var)
                    matches.append(("group_var", group_name, key, source))

        # Host variable keys
        for host_name, host in sorted(self._project.hosts.items()):
            for var in getattr(host, "variables", []):
                key = str(getattr(var, "key", ""))
                if needle in key.lower():
                    source = self._variable_source_path(var)
                    matches.append(("host_var", host_name, key, source))

        return matches

    def _variable_source_path(self, var: object) -> str:
        source = getattr(var, "source", None)
        return str(getattr(source, "source_path", ""))



    def _run_find_step(self, direction: int) -> None:
        if not self.find_edit.isVisible() and not (
            hasattr(self, "find_toolbar") and self.find_toolbar.isVisible()
        ):
            self._show_find_bar()
            return

        needle = self.find_edit.text().strip().lower()
        if not needle:
            self.statusBar().showMessage("Enter text to search.", 3000)
            return

        previous_text = self._find_text
        previous_index = self._find_index

        self._find_matches = self._collect_find_matches(needle)

        if not self._find_matches:
            self._find_text = needle
            self._find_index = -1
            self.statusBar().showMessage(f"Nothing found for: {self.find_edit.text()}", 5000)
            self.find_edit.setFocus()
            return

        if previous_text != needle or previous_index < 0:
            self._find_index = 0 if direction >= 0 else len(self._find_matches) - 1
        else:
            self._find_index = (previous_index + direction) % len(self._find_matches)

        self._find_text = needle
        self._select_find_match()

    def _find_next(self) -> None:
        self._run_find_step(1)

    def _find_previous(self) -> None:
        self._run_find_step(-1)


    def _select_find_match(self) -> None:
        if not self._find_matches:
            return

        if self._find_index < 0 or self._find_index >= len(self._find_matches):
            self._find_index = 0

        match = self._find_matches[self._find_index]
        kind = match[0]
        label = str(match)

        if kind == "group":
            group_name = match[1]
            item = self._find_inventory_item("group", group_name)
            if item:
                self._select_tree_item(item)
                label = f"group {group_name}"
            else:
                label = f"group {group_name} not visible"

        elif kind == "host":
            host_name = match[1]
            branch = match[2] if len(match) > 2 else None
            item = self._find_inventory_item("host", host_name, branch)
            if item:
                self._select_tree_item(item)
                payload = item.data(0, Qt.ItemDataRole.UserRole)
                branch_label = payload[2] if payload and len(payload) > 2 else "-"
                label = f"host {host_name} in group {branch_label}"
            else:
                label = f"host {host_name} not visible"

        elif kind == "group_var":
            group_name, key, source = match[1], match[2], match[3]
            item = self._find_inventory_item("group", group_name)
            if item:
                self._select_tree_item(item)
            self._select_variable_key(key, source)
            label = f"variable key {key} in group {group_name} / {source}"

        elif kind == "host_var":
            host_name, key, source = match[1], match[2], match[3]
            item = self._find_inventory_item("host", host_name)
            if item:
                self._select_tree_item(item)
            self._select_variable_key(key, source)
            label = f"variable key {key} in host {host_name} / {source}"

        self.find_edit.setFocus()

        self.statusBar().showMessage(
            f"Found {self._find_index + 1}/{len(self._find_matches)}: {label}",
            7000,
        )

    def _find_inventory_item(
        self,
        node_type: str,
        name: str,
        branch: str | None = None,
    ) -> QTreeWidgetItem | None:
        def walk(parent: QTreeWidgetItem | None = None) -> QTreeWidgetItem | None:
            count = self.tree.topLevelItemCount() if parent is None else parent.childCount()
            for i in range(count):
                item = self.tree.topLevelItem(i) if parent is None else parent.child(i)
                payload = item.data(0, Qt.ItemDataRole.UserRole)

                if payload and payload[0] == node_type and payload[1] == name:
                    if node_type != "host" or branch is None or payload[2] == branch:
                        return item

                found = walk(item)
                if found:
                    return found

            return None

        return walk()

    def _select_tree_item(self, item: QTreeWidgetItem) -> None:
        self.tree.clearSelection()
        self._expand_item_path(item)
        item.setSelected(True)
        self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item, QTreeWidget.ScrollHint.PositionAtCenter)

    def _select_variable_key(self, key: str, source: str = "") -> None:
        self._select_tab_containing_widget(self.variables_tree)

        best: QTreeWidgetItem | None = None

        for i in range(self.variables_tree.topLevelItemCount()):
            item = self.variables_tree.topLevelItem(i)
            item_key = item.text(0)
            item_source = item.text(3)

            if item_key == key and (not source or item_source == source):
                best = item
                break

            if item_key == key and best is None:
                best = item

        if best:
            self.variables_tree.clearSelection()
            best.setSelected(True)
            self.variables_tree.setCurrentItem(best)
            self.variables_tree.scrollToItem(best, QTreeWidget.ScrollHint.PositionAtCenter)



    def _select_tab_containing_widget(self, widget) -> None:
        for i in range(self.tabs.count()):
            page = self.tabs.widget(i)
            if page is widget or page.isAncestorOf(widget):
                self.tabs.setCurrentIndex(i)
                return

    def _find_label(self, kind: str, item: QTreeWidgetItem) -> str:
        # Kept for backward compatibility with older search code.
        return item.text(0)



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
