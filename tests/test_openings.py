"""Тесты авто-выреза отверстий камеры (фон сквозь дырку)."""
import cv2
import numpy as np

from casecut.core.holes import detect_background_openings
from casecut.core.mask_edit import MaskEditor


def _case_with_hole():
    img = np.full((200, 150, 3), 205, np.uint8)              # светлый фон
    cv2.rectangle(img, (30, 20), (120, 180), (50, 50, 50), -1)  # тёмный корпус
    cv2.circle(img, (60, 55), 12, (205, 205, 205), -1)       # отверстие = цвет фона
    mask = np.zeros((200, 150), np.uint8)
    cv2.rectangle(mask, (30, 20), (120, 180), 255, -1)        # маска: тело залито (дырка закрыта)
    return img, mask


def test_detect_opening_inside_body():
    img, mask = _case_with_hole()
    reg = detect_background_openings(mask, img, bg_tol=30, min_area=40)
    assert reg[55, 60]          # отверстие найдено
    assert not reg[150, 75]     # сплошной корпус не тронут


def test_cut_openings_punches_hole():
    img, mask = _case_with_hole()
    ed = MaskEditor(mask=mask)
    n = ed.cut_openings(img, bg_tol=30, min_area=40)
    assert n > 0
    assert ed.mask[55, 60] == 0      # дырка прозрачна
    assert ed.mask[150, 75] == 255   # корпус цел
    ed.undo()
    assert ed.mask[55, 60] == 255    # откат


def test_cut_openings_guard_no_body():
    img = np.full((50, 50, 3), 205, np.uint8)
    ed = MaskEditor(size=(50, 50))   # пустая маска
    assert ed.cut_openings(img) == 0
