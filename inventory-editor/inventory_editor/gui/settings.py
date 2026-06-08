from __future__ import annotations
import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".inventory_editor_settings.json"

class Settings:
    def __init__(self):
        self.default_workspace = ""
        self.default_inventory_file = ""
        self.vault_password = ""
        self.vault_password_file = ""
        self.external_editor = ""
        self.load()

    def load(self):
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text())
                self.default_workspace = data.get("default_workspace", "")
                self.default_inventory_file = data.get("default_inventory_file", "")
                self.vault_password = data.get("vault_password", "")
                self.vault_password_file = data.get("vault_password_file", "")
                self.external_editor = data.get("external_editor", "")
            except Exception:
                pass

    def save(self):
        data = {
            "default_workspace": self.default_workspace,
            "default_inventory_file": self.default_inventory_file,
            "vault_password": self.vault_password,
            "vault_password_file": self.vault_password_file,
            "external_editor": self.external_editor,
        }
        SETTINGS_FILE.write_text(json.dumps(data, indent=2))

settings = Settings()
