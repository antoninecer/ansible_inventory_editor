# AIS Roadmap

This roadmap describes the current state and planned direction of **AIS - Ansible Inventory Studio**.

AIS is already usable as a desktop tool for inspecting and editing Ansible inventory workspaces, especially directory-based `group_vars`, `host_vars` and Ansible Vault-backed variable files.

---

## Current focus

The current focus is:

- keep the project clean and understandable
- stabilize the current desktop application
- make the repository presentable
- document what AIS already does
- avoid promising features that are not implemented yet
- improve the strongest feature: Effective Config Preview

---

## Implemented

### Core model

- Project model
- Host model
- Group model
- Variable model
- Variable source tracking
- Basic workspace scan
- Basic project overview
- Effective variable view based on the AIS model

### Inventory import

- YAML inventory import
- `group_vars` import
- `host_vars` import
- `group_vars/all` support
- directory-per-host support
- multiple variable files per host/group
- detection of backup files
- detection of unknown workspace files

### Vault support

- Ansible Vault file detection
- Vault metadata detection
- Vault-backed value masking in UI
- Internal opening/editing of vault files when credentials are available
- recommendation to use `vault.yml` for encrypted variables
- vault source separation in Effective Config output

### GUI

- desktop GUI based on PySide6
- inventory tree
- group and host context views
- variables view
- files view
- issues view
- settings dialog
- about dialog
- add group
- add host
- add variable
- source file opening/editing
- basic search toolbar
- application rename to AIS - Ansible Inventory Studio

### Effective Config Preview

- selected host effective variables
- selected group affected hosts
- common effective variables for all affected hosts
- per-host differences
- source grouping:
  - `group_vars/all`
  - group-specific `group_vars`
  - host-specific `host_vars`
  - vault-backed files
- masked secret values
- trace / override chain for selected host
- execution / selection context
- suggested Ansible `--limit` expression
- warning that `--limit` filters hosts, not group variable inheritance

### Documentation

- product README
- English + Czech README sections
- current limitations listed
- roadmap started
- old planning documents moved under `docs/`

---

## Partially implemented

These areas exist but are not yet complete or production-grade.

### Search

Current state:

- search toolbar exists
- inventory navigation works
- variable-key search is being improved

Needed:

- stable global search across all hosts, groups and variable keys
- no live search while typing
- predictable Enter / Next / Previous behavior
- optional search scopes later:
  - hosts/groups
  - variable keys
  - variable values
  - file paths

### Conflict analysis

Current state:

- basic issue reporting exists
- workspace quality scan exists

Needed:

- better duplicate variable detection
- better type mismatch detection
- better override conflict explanation
- UI view for conflict details
- severity levels

### Safe editing

Current state:

- workspace export exists
- editing works for common use cases

Needed:

- before/after save audit
- safer write workflow
- clear changed-file summary before save
- stronger tests around export behavior

### Comment preservation

Current state:

- YAML handling exists
- ruamel.yaml is used in parts of the project

Needed:

- consistent comment-preserving round-trip behavior
- tests proving comments and formatting are preserved where expected

### CLI support

Current state:

- CLI-related modules and tests exist
- some command suggestions exist

Needed:

- clean documented CLI entry points
- stable commands for inspect/search/effective-config
- clear separation between GUI and core logic

---

## Planned next steps

### 1. Stabilize documentation and repo structure

- keep root README as the main product README
- keep `inventory-editor/README.md` as a short pointer to root README
- keep roadmap in `docs/ROADMAP.md`
- remove Gemini/local AI workflow files from the public project
- remove legacy prototype files
- remove generated cache/build artifacts
- keep planning manifests under `docs/`

### 2. Stabilize Effective Config

- use the same source grouping for group and host views
- improve host context explanation
- show all variable sources clearly
- keep vault values masked
- improve output search inside Effective Config
- later optionally compare AIS output with `ansible-inventory`

### 3. Stabilize search

- make search global for host names, group names and variable keys
- keep search execution explicit through Enter / Next / Previous
- avoid searching secret values by default
- avoid searching file paths by default unless enabled later

### 4. Refactor GUI modules

`main_window.py` is becoming too large.

Planned split:

- `gui/dialogs.py`
- `gui/search.py`
- `gui/effective_config.py`
- `gui/main_window.py`

This should happen after the current behavior is stable.

### 5. Improve tests

Priority test areas:

- loader behavior
- exporter behavior
- effective variable calculation
- vault detection
- effective config generation
- search result collection
- save behavior

---

## Later / considered

These ideas are useful but not immediate priorities.

### Ansible-backed verification

Use real Ansible commands to verify static AIS results:

- `ansible-inventory --host`
- `ansible-inventory --graph`
- `ansible-playbook --list-hosts`
- `ansible-playbook --list-tags`
- `ansible-playbook --list-tasks`

This would help distinguish:

- static AIS inventory model
- actual Ansible runtime behavior

### Save audit

Possible future feature:

- capture before-save state
- capture after-save state
- show changed files
- show text diff for non-vault files
- show hash change for vault files
- store local audit record

This is not intended to become a backup system.

### Packaging

Possible packaging targets:

- macOS `.app`
- standalone PyInstaller build
- signed release later

### CLI mode

Possible commands:

- `ais inspect`
- `ais search`
- `ais effective`
- `ais validate`
- `ais export`

### VS Code extension

Possible later frontend.

Not a current priority.

### Remote audit API

Postponed.

The current direction is local-first. Remote audit collection may be reconsidered later.

---

## Explicitly out of scope for now

- replacing Ansible
- replacing Git
- replacing Ansible Vault
- cloud synchronization
- secrets management
- full Ansible runtime simulation
- full playbook-aware variable resolution
- dynamic inventory execution
- role/fact/set_fact runtime analysis
