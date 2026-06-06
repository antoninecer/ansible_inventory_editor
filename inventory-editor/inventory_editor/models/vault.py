from dataclasses import dataclass


@dataclass(slots=True)
class VaultFile:
    source_path: str
    vault_header: str
    vault_version: str
    cipher: str
