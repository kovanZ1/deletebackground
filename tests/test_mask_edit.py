"""Тесты ядра редактирования маски: кисть, ластик, вырез, undo/redo."""
import numpy as np

from casecut.core.mask_edit import MaskEditor, ADD, ERASE


def test_brush_add_and_undo():
    ed = MaskEditor(size=(100, 100))
    ed.begin_stroke()
    ed.dab(50, 50, 10, ADD)
    ed.end_stroke()
    assert ed.mask[50, 50] == 255
    assert ed.mask.max() == 255
    ed.undo()
    assert ed.mask[50, 50] == 0
    assert ed.mask.max() == 0


def test_eraser():
    ed = MaskEditor(mask=np.full((100, 100), 255, np.uint8))
    ed.begin_stroke()
    ed.dab(50, 50, 12, ERASE)
    ed.end_stroke()
    assert ed.mask[50, 50] == 0
    assert ed.mask[0, 0] == 255


def test_line_paints_path():
    ed = MaskEditor(size=(100, 200))
    ed.begin_stroke()
    ed.line(10, 50, 190, 50, 5, ADD)
    ed.end_stroke()
    assert ed.mask[50, 10] == 255
    assert ed.mask[50, 100] == 255
    assert ed.mask[50, 190] == 255
    assert ed.mask[90, 100] == 0


def test_cutout_rect_undo_redo():
    ed = MaskEditor(mask=np.full((100, 100), 255, np.uint8))
    ed.cutout_rect(40, 40, 20, 20)
    assert ed.mask[50, 50] == 0
    assert ed.mask[10, 10] == 255
    ed.undo()
    assert ed.mask[50, 50] == 255
    ed.redo()
    assert ed.mask[50, 50] == 0


def test_cutout_polygon():
    ed = MaskEditor(mask=np.full((100, 100), 255, np.uint8))
    ed.cutout_polygon([(40, 40), (60, 40), (60, 60), (40, 60)])
    assert ed.mask[50, 50] == 0
    assert ed.mask[10, 10] == 255


def test_cutout_ellipse():
    ed = MaskEditor(mask=np.full((100, 100), 255, np.uint8))
    ed.cutout_ellipse(50, 50, 12, 12)
    assert ed.mask[50, 50] == 0
    assert ed.mask[10, 10] == 255
