from pathlib import Path

from inventory_editor.models.vault import VaultFile


def detect_vault_file(path: str | Path) -> VaultFile | None:
    p = Path(path)

    try:
        first_line = p.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()[0]
    except Exception:
        return None

    if not first_line.startswith("$ANSIBLE_VAULT;"):
        return None

    parts = first_line.split(";")

    version = "unknown"
    cipher = "unknown"

    if len(parts) >= 2:
        version = parts[1]

    if len(parts) >= 3:
        cipher = parts[2]

    return VaultFile(
        source_path=str(p),
        vault_header=first_line,
        vault_version=version,
        cipher=cipher,
    )
