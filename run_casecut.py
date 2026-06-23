"""Точка входа для запуска и для PyInstaller."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from casecut.ui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
