from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from inventory_editor.gui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    workspace = Path(args[0]).expanduser().resolve() if args else None

    app = QApplication(sys.argv[:1])
    window = MainWindow(workspace=workspace)
    window.show()
    return app.exec()
