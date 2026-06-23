"""Тесты: писемый путь хранения + волшебная палочка (flood-select)."""
import cv2
import numpy as np

from casecut.paths import devices_dir, user_data_dir
from casecut.core.mask_edit import MaskEditor, flood_select, ERASE


def test_devices_dir_is_writable_not_programfiles():
    d = str(devices_dir())
    assert "Program Files" not in d
    assert d.replace("\\", "/").endswith("CaseCutoutTool/devices")
    assert str(user_data_dir()) in d


def _img_with_block():
    img = np.full((100, 100, 3), 200, np.uint8)         # светлый фон
    cv2.rectangle(img, (30, 30), (70, 70), (20, 20, 20), -1)  # тёмный блок
    return img


def test_flood_select_picks_similar_region_only():
    img = _img_with_block()
    reg = flood_select(img, (10, 10), tol=20)            # клик по фону
    assert reg[10, 10]
    assert not reg[50, 50]                               # тёмный блок не попал


def test_magic_erase_removes_similar_pixels():
    img = _img_with_block()
    ed = MaskEditor(mask=np.full((100, 100), 255, np.uint8))
    assert ed.magic(img, 10, 10, tol=20, mode=ERASE) is True
    assert ed.mask[10, 10] == 0      # фон стёрт
    assert ed.mask[50, 50] == 255    # блок остался
    ed.undo()
    assert ed.mask[10, 10] == 255    # откат работает
