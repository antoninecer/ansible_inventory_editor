import subprocess
import tempfile
import os
from pathlib import Path
from inventory_editor.gui.settings import settings

class VaultHandler:
    @staticmethod
    def _get_password_args():
        if settings.vault_password_file:
            p = Path(settings.vault_password_file).expanduser().resolve()
            if not p.exists():
                raise Exception(f"Vault password file not found: {p}")
            return ["--vault-password-file", str(p)]
        elif settings.vault_password:
            # Create a temporary password file for the command
            fd, path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as f:
                f.write(settings.vault_password)
            return ["--vault-password-file", path, "TEMP_CLEANUP", path]
        
        # If no credentials, we must fail early if encryption/decryption is requested
        raise Exception("No Vault password or password file configured in Settings.")

    @classmethod
    def decrypt(cls, file_path: Path) -> str:
        pw_args = cls._get_password_args()
        
        cleanup_path = None
        if "TEMP_CLEANUP" in pw_args:
            idx = pw_args.index("TEMP_CLEANUP")
            cleanup_path = pw_args[idx+1]
            pw_args = pw_args[:idx]

        args = ["ansible-vault", "decrypt", "--output=-", str(file_path)]
        try:
            # text=True and input="" to prevent hanging on stdin
            result = subprocess.run(args + pw_args, capture_output=True, text=True, check=True, input="")
            return result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or "Unknown error"
            raise Exception(f"Decryption failed: {error_msg.strip()}")
        finally:
            if cleanup_path and os.path.exists(cleanup_path):
                os.remove(cleanup_path)

    @classmethod
    def encrypt(cls, content: str, file_path: Path):
        pw_args = cls._get_password_args()
        
        cleanup_path = None
        if "TEMP_CLEANUP" in pw_args:
            idx = pw_args.index("TEMP_CLEANUP")
            cleanup_path = pw_args[idx+1]
            pw_args = pw_args[:idx]

        fd, temp_path = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(content)
            
            args = ["ansible-vault", "encrypt", temp_path]
            # Capture output and provide empty input to avoid hangs
            subprocess.run(args + pw_args, check=True, capture_output=True, text=True, input="")
            
            # Read encrypted content back and write to destination
            encrypted_content = Path(temp_path).read_text()
            file_path.write_text(encrypted_content)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or "Unknown error"
            raise Exception(f"Encryption failed: {error_msg.strip()}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if cleanup_path and os.path.exists(cleanup_path):
                os.remove(cleanup_path)

    @staticmethod
    def has_credentials() -> bool:
        return bool(settings.vault_password or settings.vault_password_file)
