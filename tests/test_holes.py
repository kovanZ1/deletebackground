"""Тесты вывода вырезов из маски и обрезки по объекту."""
import cv2
import numpy as np

from casecut.core.holes import fill_silhouette, derive_holes
from casecut.core.mask_apply import crop_to_content


def test_fill_silhouette():
    m = np.zeros((100, 100), np.uint8)
    cv2.rectangle(m, (20, 20), (80, 80), 255, -1)
    cv2.circle(m, (50, 40), 8, 0, -1)
    outer = fill_silhouette(m)
    assert outer[40, 50] == 255   # дыра заполнена во внешнем силуэте
    assert outer[10, 10] == 0


def test_derive_holes():
    m = np.zeros((120, 120), np.uint8)
    cv2.rectangle(m, (20, 20), (100, 100), 255, -1)
    cv2.circle(m, (50, 45), 10, 0, -1)
    holes = derive_holes(m)
    assert len(holes) == 1
    x, y, w, h = holes[0]
    assert 35 <= x <= 45 and 30 <= y <= 40
    assert 15 <= w <= 25 and 15 <= h <= 25


def test_crop_to_content():
    rgba = np.zeros((100, 100, 4), np.uint8)
    rgba[30:70, 40:60, 3] = 255
    rgba[30:70, 40:60, :3] = 120
    out = crop_to_content(rgba)
    assert out.shape[0] == 40 and out.shape[1] == 20


def test_build_template_auto_holes():
    from casecut.store.device_store import build_template
    from synth import render_case, make_mask_from_body
    ref_img, ref_gt = render_case(canvas=(800, 600), center=(300, 400),
                                  case_size=(200, 400), seed=5)
    ref_mask = make_mask_from_body(ref_gt["body_mask"], hole_center=(300, 250), hole_radius=22)
    tpl = build_template("AUTO_HOLES", ref_img, ref_mask)  # camera_holes не передаём
    assert len(tpl.camera_holes) >= 1
