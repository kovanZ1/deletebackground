"""Точка входа GUI-приложения."""
from __future__ import annotations

import os
import sys


def _ensure_qt_plugins() -> None:
    """Привязать путь к плагинам Qt из PySide6 (важно для PyInstaller/.exe и venv)."""
    import PySide6
    plug = os.path.join(os.path.dirname(PySide6.__file__), "Qt", "plugins")
    if os.path.isdir(plug):
        os.environ.setdefault("QT_PLUGIN_PATH", plug)
        from PySide6 import QtCore
        QtCore.QCoreApplication.addLibraryPath(plug)


def main():
    _ensure_qt_plugins()
    from PySide6 import QtCore, QtGui, QtWidgets
    from .main_window import MainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    selftest = bool(os.environ.get("CASECUT_SELFTEST"))
    if not selftest:
        try:
            from ..control.gate import check_remote, RELEASES_URL
            decision = check_remote()
        except Exception:
            decision = None
        if decision is not None and not decision.allowed:
            box = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Icon.Critical, "CaseCutoutTool", decision.message)
            if decision.kind == "update":
                open_btn = box.addButton(
                    "Открыть страницу загрузки", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
                box.addButton("Закрыть", QtWidgets.QMessageBox.ButtonRole.RejectRole)
                box.exec()
                if box.clickedButton() is open_btn:
                    QtGui.QDesktopServices.openUrl(QtCore.QUrl(RELEASES_URL))
            else:
                box.exec()
            return

    win = MainWindow()
    win.show()
    if selftest:
        for _ in range(3):
            app.processEvents()
        return 0
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
