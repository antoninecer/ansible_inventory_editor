from inventory_editor.analyzer.vault import detect_vault_file
from inventory_editor.io.scanner import scan_inventory_workspace


def test_detect_ansible_vault(tmp_path):
    vault_file = tmp_path / "vault.yml"

    vault_file.write_text(
        "$ANSIBLE_VAULT;1.1;AES256\n"
        "abcdef\n",
        encoding="utf-8",
    )

    vault = detect_vault_file(vault_file)

    assert vault is not None
    assert vault.vault_version == "1.1"
    assert vault.cipher == "AES256"


def test_scan_collects_vault_metadata(tmp_path):
    root = tmp_path / "inventory"
    (root / "group_vars" / "web").mkdir(parents=True)
    (root / "group_vars" / "web" / "vault.yml").write_text(
        "$ANSIBLE_VAULT;1.1;AES256\nabcdef\n",
        encoding="utf-8",
    )

    scan = scan_inventory_workspace(root)

    assert len(scan.vault_files) == 1
    assert len(scan.vault_metadata) == 1
    assert scan.vault_metadata[0].cipher == "AES256"
