# Inventory Editor Specification

This repository defines the product contract for a new Ansible inventory editor.

The tool is intended to help a beginner build and maintain a correct inventory layout from zero while still being useful for advanced operators.

## What the tool should understand

- static inventories in YAML or INI form
- inventory directories with `group_vars/` and `host_vars/`
- host-specific directories inside `host_vars/<host>/`
- multiple files per host or group, such as `main.yml`, `nginx.yml`, `ha.yml`, `scanner.yml`
- `all` scope variables
- group variables
- host variables
- inline host variables
- variable provenance and effective values
- conflict and duplication analysis
- Ansible tag and vault metadata for CLI suggestions

## Default layout

The preferred working layout is a directory-based project.

Example:

```text
inventory/
  inventory.yml
  group_vars/
    all/
      main.yml
    dohled/
      main.yml
      alerts.yml
  host_vars/
    dohled01/
      main.yml
      nginx.yml
      ha.yml
```

## Design rules

1. `main.yml` is the default file for base scope data.
2. The user may add thematic files when configuration is clearly application-specific.
3. The editor must show where every variable came from.
4. The editor must show the effective value after precedence is applied.
5. The editor must warn when the same key appears in multiple places.
6. The editor must never invent values that are not present in the source.
7. The editor must keep changes reversible and create backups before saving.

## Severity levels

The analyzer reports issues in three levels:

- **A** — critical, must be fixed before the inventory can be trusted
- **B** — warning, valid but risky or confusing
- **C** — recommendation, valid but not ideal for long-term maintenance

## User guidance

The UI should guide a beginner through:

- creating a new inventory project
- adding a group
- adding a host
- choosing whether host data belongs in `main.yml` or a thematic file
- adding group variables
- reviewing conflicts and variable precedence
- exporting the project or packaging it as a snapshot

## CLI suggestion support

The editor may propose commands such as:

```bash
ansible-playbook -i inventory/inventory.yml playbooks/windows-baseline.yml --tags certificates,scanner
```

The suggestion must be presented as a recommendation that can be verified with Ansible listing commands.

## Change process

When a feature changes, update the YAML manifest first.
Then update the implementation to match the manifest.
Then update this README if the user-facing behavior changed.

## Status workflow

Feature items should move through these states:

- todo
- draft
- approved
- implemented
- changed
- deprecated

## Current intent

The first implementation should focus on:

- import
- normalized internal model
- variable origin tracking
- conflict detection
- directory-based export
- beginner-friendly guidance
- backup-safe editing

