"""Dev-утилита: отрендерить окно offscreen и сохранить скриншоты экранов."""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "tests"))

from PySide6 import QtWidgets  # noqa: E402
from casecut.ui.app import _ensure_qt_plugins  # noqa: E402
from casecut.ui.main_window import MainWindow  # noqa: E402
from synth import render_case  # noqa: E402


def main():
    _ensure_qt_plugins()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    mw = MainWindow(devices_dir=tempfile.mkdtemp())
    mw.resize(1040, 700)
    img, _ = render_case(canvas=(900, 650), center=(430, 330), case_size=(240, 470))
    mw.teach.canvas.set_image(img)
    mw.teach.canvas.propose_outline()
    mw.teach.device.setText("iPhone 15 Pro")
    mw.show()
    for _ in range(6):
        app.processEvents()
    p1 = os.path.abspath(os.path.join(HERE, "..", "ui_teach.png"))
    mw.grab().save(p1)
    mw.nav.setCurrentRow(1)
    for _ in range(6):
        app.processEvents()
    p2 = os.path.abspath(os.path.join(HERE, "..", "ui_auto.png"))
    mw.grab().save(p2)
    print("saved:", p1, p2)


if __name__ == "__main__":
    main()
