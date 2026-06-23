"""Тесты детерминированного ядра: силуэт, масштаб+сдвиг, применение маски."""
import numpy as np

from casecut.core.silhouette import detect_silhouette
from casecut.core.align import estimate_alignment
from casecut.core.mask_apply import warp_mask, compose_rgba
from synth import render_case, make_mask_from_body


def _iou(a, b):
    a = a > 127
    b = b > 127
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return inter / union if union else 0.0


def test_detect_silhouette_bbox():
    img, gt = render_case(canvas=(800, 600), center=(300, 400),
                          case_size=(200, 420), shadow=False, seed=1)
    sil = detect_silhouette(img)
    assert sil is not None
    gx, gy, gw, gh = gt["bbox"]
    x, y, w, h = sil.bbox
    assert abs(w - gw) <= 6 and abs(h - gh) <= 6
    assert abs(x - gx) <= 6 and abs(y - gy) <= 6
    assert not sil.touches_border
    assert abs(sil.centroid[0] - gt["centroid"][0]) <= 4
    assert abs(sil.centroid[1] - gt["centroid"][1]) <= 4


def test_detect_robust_to_shadow():
    img, gt = render_case(canvas=(800, 600), center=(300, 400),
                          case_size=(220, 440), shadow=True, seed=10)
    sil = detect_silhouette(img)
    assert sil is not None
    assert _iou(sil.mask, gt["body_mask"]) > 0.92


def test_touches_border():
    img, _ = render_case(canvas=(600, 600), center=(40, 300),
                         case_size=(200, 400), shadow=False, seed=2)
    sil = detect_silhouette(img)
    assert sil is not None
    assert sil.touches_border


def test_estimate_scale():
    ref_img, _ = render_case(canvas=(800, 600), center=(300, 400),
                             case_size=(200, 400), shadow=False, seed=3)
    tgt_img, _ = render_case(canvas=(800, 600), center=(320, 360),
                             case_size=(270, 540), shadow=False, seed=4)
    rs = detect_silhouette(ref_img)
    ts = detect_silhouette(tgt_img)
    al = estimate_alignment(rs, ts)
    assert abs(al.scale - 1.35) < 0.05


def test_end_to_end_apply():
    ref_img, ref_gt = render_case(canvas=(800, 600), center=(300, 400),
                                  case_size=(200, 400), seed=5)
    hole = (300, 250)  # дыра камеры у верха чехла
    ref_mask = make_mask_from_body(ref_gt["body_mask"], hole_center=hole, hole_radius=22)

    tgt_img, tgt_gt = render_case(canvas=(800, 600), center=(320, 360),
                                  case_size=(270, 540), seed=6)

    rs = detect_silhouette(ref_img)
    ts = detect_silhouette(tgt_img)
    al = estimate_alignment(rs, ts)
    est = warp_mask(ref_mask, al.matrix, tgt_img.shape[:2])

    # 1) тело маски совпадает с реальным силуэтом цели
    assert _iou(est, tgt_gt["body_mask"]) > 0.88

    # 2) фон прозрачен
    outside = tgt_gt["body_mask"] == 0
    assert est[outside].mean() < 8

    # 3) дыра камеры перенесена и прозрачна; центр тела — непрозрачен
    hx = al.scale * hole[0] + al.tx
    hy = al.scale * hole[1] + al.ty
    assert est[int(round(hy)), int(round(hx))] < 60
    assert est[int(round(ts.centroid[1])), int(round(ts.centroid[0]))] > 200


def test_compose_rgba_keeps_rgb():
    img, gt = render_case(seed=7)
    alpha = gt["body_mask"]
    out = compose_rgba(img, alpha)
    assert out.shape[2] == 4
    assert np.array_equal(out[:, :, :3], img)
    assert np.array_equal(out[:, :, 3], alpha)
