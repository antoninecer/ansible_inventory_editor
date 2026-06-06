from inventory_editor.analyzer.file_classifier import (
    FileClassification,
    classify_file,
)


def test_inventory_file():
    assert (
        classify_file("inventory.yml")
        == FileClassification.INVENTORY_FILE
    )


def test_variable_file():
    assert (
        classify_file("group_vars/web/90-network.yml")
        == FileClassification.VARIABLE_FILE
    )


def test_vault_file():
    assert (
        classify_file("group_vars/web/vault.yml")
        == FileClassification.VAULT_FILE
    )


def test_backup_file():
    assert (
        classify_file("inventory.yml-20240522")
        == FileClassification.BACKUP_FILE
    )


def test_unknown_file():
    assert (
        classify_file("notes.txt")
        == FileClassification.UNKNOWN
    )
