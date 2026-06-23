"""Контроль качества результата (детерминированный).

Главное под критерий проекта — проверка, что вырез камеры реально прозрачен,
и что площадь маски правдоподобна (не съехала по масштабу). Подозрительные
кадры уходят в _needs_review с конкретной причиной.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class QAResult:
    ok: bool
    reasons: list


def transform_bbox(bbox, matrix, out_hw=None):
    """Перенести bbox эталона в координаты цели по similarity-матрице (без поворота)."""
    x, y, w, h = bbox
    s = float(matrix[0, 0])
    tx = float(matrix[0, 2])
    ty = float(matrix[1, 2])
    nx = int(round(s * x + tx))
    ny = int(round(s * y + ty))
    nw = int(round(s * w))
    nh = int(round(s * h))
    if out_hw is not None:
        h_img, w_img = out_hw
        nx = max(0, min(nx, w_img - 1))
        ny = max(0, min(ny, h_img - 1))
        nw = max(0, min(nw, w_img - nx))
        nh = max(0, min(nh, h_img - ny))
    return (nx, ny, nw, nh)


def quality_check(alpha, matrix, template, *, area_tol: float = 0.18,
                  hole_alpha_max: float = 45.0) -> QAResult:
    """Проверить применённую alpha: площадь и прозрачность вырезов камеры."""
    reasons: list = []
    scale = float(matrix[0, 0])

    mask_body = float((template.mask > 127).sum())
    expected = mask_body * (scale ** 2)
    got = float((alpha > 127).sum())
    if expected > 0 and abs(got - expected) / expected > area_tol:
        reasons.append(f"area_mismatch:{got / max(expected, 1.0):.2f}")

    h_img, w_img = alpha.shape[:2]
    for hb in template.camera_holes:
        x, y, w, h = transform_bbox(hb, matrix, (h_img, w_img))
        if w <= 0 or h <= 0:
            reasons.append("camera_hole_offscreen")
            continue
        # проверяем ЦЕНТРАЛЬНУЮ зону выреза: круглая дыра вписана в bbox,
        # углы bbox — это тело (alpha=255), они бы завышали среднее.
        f = 0.5
        ix = x + int(w * (1.0 - f) / 2.0)
        iy = y + int(h * (1.0 - f) / 2.0)
        iw = max(1, int(w * f))
        ih = max(1, int(h * f))
        roi = alpha[iy:iy + ih, ix:ix + iw]
        if roi.size and float(roi.mean()) > hole_alpha_max:
            reasons.append("camera_hole_not_punched")

    return QAResult(len(reasons) == 0, reasons)
