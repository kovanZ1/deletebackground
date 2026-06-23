"""Детектирование внешнего силуэта чехла на фото — детерминированно, без ML.

Идея: фон оценивается по рамке кадра, чехол выделяется по цветовому
расстоянию в LAB + порог Otsu, берётся крупнейший связный объект, его внешний
контур заполняется. Возвращаются габариты/площадь/центр для оценки масштаба.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Silhouette:
    mask: np.ndarray            # uint8 0/255 — заполненный внешний контур чехла
    bbox: tuple                 # (x, y, w, h)
    area: int                   # площадь силуэта, пиксели
    centroid: tuple             # (cx, cy)
    touches_border: bool        # силуэт упирается в край кадра (чехол обрезан)


def estimate_background_lab(img_bgr: np.ndarray, border_frac: float = 0.04) -> np.ndarray:
    """Медианный цвет фона (LAB) по рамке изображения."""
    h, w = img_bgr.shape[:2]
    bw = max(1, int(round(min(h, w) * border_frac)))
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    parts = [
        lab[:bw, :].reshape(-1, 3),
        lab[-bw:, :].reshape(-1, 3),
        lab[:, :bw].reshape(-1, 3),
        lab[:, -bw:].reshape(-1, 3),
    ]
    border = np.concatenate(parts, axis=0).astype(np.float32)
    return np.median(border, axis=0)


def detect_silhouette(
    img_bgr: np.ndarray,
    *,
    border_frac: float = 0.04,
    min_area_frac: float = 0.005,
    border_margin: int = 2,
) -> Silhouette | None:
    """Найти силуэт чехла. Возвращает None, если объект не выделился."""
    h, w = img_bgr.shape[:2]
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    bg = estimate_background_lab(img_bgr, border_frac)
    dist = np.linalg.norm(lab - bg[None, None, :], axis=2)

    d8 = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _t, binm = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binm = cv2.morphologyEx(binm, cv2.MORPH_OPEN, k)
    binm = cv2.morphologyEx(binm, cv2.MORPH_CLOSE, k)

    contours, _ = cv2.findContours(binm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    c = max(contours, key=cv2.contourArea)
    filled = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(filled, [c], -1, 255, thickness=cv2.FILLED)

    area = int((filled > 0).sum())
    if area < min_area_frac * h * w:
        return None

    x, y, bw_, bh_ = cv2.boundingRect(c)
    m = cv2.moments(filled, binaryImage=True)
    cx = m["m10"] / m["m00"]
    cy = m["m01"] / m["m00"]
    touches = (
        x <= border_margin
        or y <= border_margin
        or x + bw_ >= w - border_margin
        or y + bh_ >= h - border_margin
    )
    return Silhouette(filled, (x, y, bw_, bh_), area, (cx, cy), bool(touches))
