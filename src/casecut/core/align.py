"""Оценка similarity-преобразования (масштаб + сдвиг, без поворота) между
эталонным силуэтом маски и силуэтом чехла на целевом фото.

Один ракурс → отличается только масштаб и положение. Поэтому достаточно
оценить scale (по габаритам и площади) и translation (совмещение центров).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .silhouette import Silhouette


@dataclass
class Alignment:
    scale: float
    tx: float
    ty: float
    matrix: np.ndarray          # 2x3 аффинная (эталон -> цель)


def estimate_alignment(ref: Silhouette, tgt: Silhouette) -> Alignment:
    """Оценить масштаб и сдвиг для переноса эталонной маски на целевое фото."""
    if ref is None or tgt is None:
        raise ValueError("нужны оба силуэта (ref и tgt)")
    _, _, rw, rh = ref.bbox
    _, _, tw, th = tgt.bbox
    if rw <= 0 or rh <= 0 or ref.area <= 0:
        raise ValueError("некорректный эталонный силуэт")

    s_w = tw / rw
    s_h = th / rh
    s_area = float(np.sqrt(tgt.area / ref.area))
    scale = float(np.median([s_w, s_h, s_area]))

    rcx, rcy = ref.centroid
    tcx, tcy = tgt.centroid
    tx = tcx - scale * rcx
    ty = tcy - scale * rcy

    matrix = np.array([[scale, 0.0, tx], [0.0, scale, ty]], dtype=np.float64)
    return Alignment(scale, tx, ty, matrix)
