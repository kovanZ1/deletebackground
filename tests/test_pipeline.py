"""Тесты слоя конвейера: QA, обработчик фото, хранилище, превью."""
import numpy as np

from casecut.store.device_store import build_template, save_template, load_template
from casecut.pipeline.processor import process_image
from casecut.core.region_qa import quality_check
from casecut.preview.previews import render_previews
from synth import render_case, make_mask_from_body


def _iou(a, b):
    a = a > 127
    b = b > 127
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return inter / union if union else 0.0


def _make_ref():
    ref_img, ref_gt = render_case(canvas=(800, 600), center=(300, 400),
                                  case_size=(200, 400), seed=5)
    hole = (300, 250)
    r = 22
    ref_mask = make_mask_from_body(ref_gt["body_mask"], hole_center=hole, hole_radius=r)
    holes = [(hole[0] - r, hole[1] - r, 2 * r, 2 * r)]
    tpl = build_template("TEST_MODEL", ref_img, ref_mask, camera_holes=holes)
    return tpl


def test_processor_ok():
    tpl = _make_ref()
    tgt_img, tgt_gt = render_case(canvas=(800, 600), center=(320, 360),
                                  case_size=(270, 540), seed=6)
    res = process_image(tgt_img, tpl, align="silhouette")
    assert res.status == "ok", res.reasons
    assert _iou(res.alpha, tgt_gt["body_mask"]) > 0.88
    assert res.rgba.shape[2] == 4
    assert np.array_equal(res.rgba[:, :, :3], tgt_img)  # принт не тронут


def test_processor_needs_review_on_border():
    tpl = _make_ref()
    tgt_img, _ = render_case(canvas=(600, 600), center=(40, 300),
                             case_size=(220, 440), seed=8)
    res = process_image(tgt_img, tpl, align="silhouette")
    assert res.status == "needs_review"
    assert "touches_border" in res.reasons


def test_processor_frame_identity():
    # одинаковый кадр (одна позиция чехла) -> привязка к кадру 1:1
    ref_img, ref_gt = render_case(canvas=(800, 600), center=(300, 400),
                                  case_size=(200, 400), seed=5)
    hole = (300, 250)
    r = 22
    ref_mask = make_mask_from_body(ref_gt["body_mask"], hole_center=hole, hole_radius=r)
    tpl = build_template("T", ref_img, ref_mask, camera_holes=[(hole[0] - r, hole[1] - r, 2 * r, 2 * r)])
    # тот же кадр/позиция, другой «принт» (шум)
    tgt_img, tgt_gt = render_case(canvas=(800, 600), center=(300, 400),
                                  case_size=(200, 400), seed=99)
    res = process_image(tgt_img, tpl, align="frame")
    assert res.status == "ok", res.reasons
    assert _iou(res.alpha, tgt_gt["body_mask"]) > 0.95     # маска села 1:1
    assert res.alpha[hole[1], hole[0]] < 60                # дыра камеры на месте


def test_processor_frame_resize():
    ref_img, ref_gt = render_case(canvas=(800, 600), center=(300, 400),
                                  case_size=(200, 400), seed=5)
    ref_mask = make_mask_from_body(ref_gt["body_mask"])
    tpl = build_template("T2", ref_img, ref_mask)
    tgt_img, _ = render_case(canvas=(400, 300), center=(150, 200), case_size=(100, 200), seed=5)
    res = process_image(tgt_img, tpl, align="frame")
    assert res.alpha.shape[:2] == tgt_img.shape[:2]        # ресайз до размера фото
    assert res.rgba.shape[2] == 4


def test_qa_flags_empty_alpha():
    tpl = _make_ref()
    alpha = np.zeros((800, 600), dtype=np.uint8)
    M = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64)
    qa = quality_check(alpha, M, tpl)
    assert not qa.ok
    assert any("area_mismatch" in r for r in qa.reasons)


def test_store_roundtrip(tmp_path):
    tpl = _make_ref()
    save_template(tmp_path, tpl)
    loaded = load_template(tmp_path)
    assert loaded.device == tpl.device
    assert np.array_equal(loaded.mask, tpl.mask)
    assert tuple(loaded.ref.bbox) == tuple(tpl.ref.bbox)
    assert loaded.camera_holes == tpl.camera_holes


def test_previews_dark_background():
    tpl = _make_ref()
    tgt_img, tgt_gt = render_case(canvas=(800, 600), center=(320, 360),
                                  case_size=(270, 540), seed=6)
    res = process_image(tgt_img, tpl)
    pv = render_previews(res.rgba)
    outside = tgt_gt["body_mask"] == 0
    assert pv["dark"][outside].mean() < 40      # фон ушёл в тёмный
    assert pv["light"][outside].mean() > 220    # и в светлый
