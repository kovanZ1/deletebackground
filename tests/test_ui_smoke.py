"""Дымовые тесты GUI. Пропускаются, если Qt-платформа не инициализируется
(headless-окружение / проблемный плагин платформы) — чтобы не ронять весь прогон."""
import os
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")


def _qt_available() -> bool:
    code = (
        "import os; os.environ.setdefault('QT_QPA_PLATFORM','offscreen');"
        "from PySide6 import QtWidgets; QtWidgets.QApplication(['t']); print('ok')"
    )
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=40)
        return r.returncode == 0 and b"ok" in r.stdout
    except Exception:
        return False


QT_OK = _qt_available()
pytestmark = pytest.mark.skipif(
    not QT_OK, reason="Qt platform plugin недоступен в этой среде (headless/macOS)")

from PySide6 import QtWidgets  # noqa: E402
from casecut.core.mask_edit import ADD  # noqa: E402
from synth import render_case  # noqa: E402


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_mainwindow_builds(tmp_path):
    _app()
    from casecut.ui.main_window import MainWindow
    w = MainWindow(devices_dir=str(tmp_path / "devices"))
    assert w.stack.count() == 2
    w.close()


def test_canvas_brush_and_outline():
    _app()
    from casecut.ui.canvas import MaskCanvas
    c = MaskCanvas()
    img, _ = render_case(seed=5)
    c.set_image(img)
    c.set_tool("brush")
    c.set_radius(15)
    c.editor.begin_stroke()
    c.editor.dab(100, 100, 15, ADD)
    assert c.editor.mask[100, 100] == 255
    c.propose_outline()
    assert c.editor.mask.max() == 255


def test_teach_save_then_auto_lists_device(tmp_path, monkeypatch):
    _app()
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *a, **k: None)
    from casecut.ui.teach_page import TeachPage
    from casecut.ui.auto_page import AutoPage

    dev = str(tmp_path / "devices")
    tp = TeachPage(dev)
    img, _ = render_case(seed=5)
    tp.canvas.set_image(img)
    tp.canvas.propose_outline()
    tp.device.setText("MODEL_X")
    tp._save()

    ap = AutoPage(dev)
    names = [ap.device_combo.itemText(i) for i in range(ap.device_combo.count())]
    assert "MODEL_X" in names


def test_auto_page_preserves_mask_selection(tmp_path, monkeypatch):
    _app()
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *a, **k: None)
    from casecut.ui.teach_page import TeachPage
    from casecut.ui.auto_page import AutoPage

    dev = str(tmp_path / "devices")
    for name in ("Model_A", "Model_B"):
        tp = TeachPage(dev)
        img, _ = render_case(seed=5)
        tp.canvas.set_image(img)
        tp.canvas.propose_outline()
        tp.device.setText(name)
        tp._save()

    ap = AutoPage(dev)
    ap.device_combo.setCurrentIndex(ap.device_combo.findText("Model_B"))
    assert ap.device_combo.currentText() == "Model_B"
    ap.refresh_devices()                                  # раньше сбрасывал на первую
    assert ap.device_combo.currentText() == "Model_B"     # теперь выбор сохранён
