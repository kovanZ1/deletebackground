"""Обработка одного фото выученной маской устройства (детерминированно).

Силуэт цели -> оценка масштаба+сдвига от эталона -> (ручные правки) ->
применение маски -> контроль качества -> RGBA. Принт не трогается.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.silhouette import detect_silhouette
from ..core.align import estimate_alignment
from ..core.mask_apply import warp_mask, feather_alpha, compose_rgba
from ..core.region_qa import quality_check
from ..store.device_store import DeviceTemplate


@dataclass
class ProcessResult:
    status: str                 # "ok" | "needs_review"
    reasons: list
    rgba: np.ndarray | None     # BGRA
    alpha: np.ndarray | None
    scale: float | None


def process_image(img_bgr: np.ndarray, template: DeviceTemplate) -> ProcessResult:
    tgt = detect_silhouette(img_bgr)
    if tgt is None:
        return ProcessResult("needs_review", ["no_silhouette"], None, None, None)

    al = estimate_alignment(template.ref, tgt)
    s = al.scale * template.scale_tweak
    rcx, rcy = template.ref.centroid
    tcx, tcy = tgt.centroid
    tx = tcx - s * rcx + template.offset[0]
    ty = tcy - s * rcy + template.offset[1]
    matrix = np.array([[s, 0.0, tx], [0.0, s, ty]], dtype=np.float64)

    alpha = warp_mask(template.mask, matrix, img_bgr.shape[:2])
    if template.feather_px:
        alpha = feather_alpha(alpha, template.feather_px)

    qa = quality_check(alpha, matrix, template)
    reasons = list(qa.reasons)
    if tgt.touches_border:
        reasons.append("touches_border")

    status = "ok" if not reasons else "needs_review"
    rgba = compose_rgba(img_bgr, alpha)
    return ProcessResult(status, reasons, rgba, alpha, s)
