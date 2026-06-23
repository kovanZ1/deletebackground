"""Вывод внутренних вырезов (камера, датчики) из нарисованной маски.

Оператор рисует тело и вырезает дыры; bbox'ы вырезов для region-QA считаются
автоматически как «силуэт минус тело маски».
"""
from __future__ import annotations

import cv2
import numpy as np

from .silhouette import estimate_background_lab


def detect_background_openings(mask: np.ndarray, image_bgr: np.ndarray, *,
                               bg_tol: float = 28.0, min_area: int = 60,
                               max_area_frac: float = 0.18,
                               border_frac: float = 0.04) -> np.ndarray:
    """Найти отверстия камеры на фото: внутри тела маски пиксели цвета фона
    (сквозь дырку виден фон). Возвращает булеву маску этих областей для вырезания.
    Защита: компонент не больше max_area_frac тела (чтобы не съесть корпус)."""
    body = mask > 127
    out = np.zeros(mask.shape, dtype=bool)
    if not body.any():
        return out
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    bg = estimate_background_lab(image_bgr, border_frac)
    bgdist = np.linalg.norm(lab - bg[None, None, :], axis=2)
    opening = (body & (bgdist < bg_tol)).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    opening = cv2.morphologyEx(opening, cv2.MORPH_OPEN, k)
    n, labels, stats, _c = cv2.connectedComponentsWithStats(opening, 8)
    body_area = int(body.sum())
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area or area > max_area_frac * body_area:
            continue
        out[labels == i] = True
    return out


def fill_silhouette(mask: np.ndarray) -> np.ndarray:
    """Заполнить внутренние дыры -> внешний силуэт (255 внутри внешнего контура)."""
    m = (mask > 127).astype(np.uint8) * 255
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(m)
    if not contours:
        return out
    c = max(contours, key=cv2.contourArea)
    cv2.drawContours(out, [c], -1, 255, thickness=cv2.FILLED)
    return out


def derive_holes(mask: np.ndarray, min_area: int = 25) -> list:
    """bbox'ы внутренних вырезов: (внешний силуэт) И НЕ (тело маски)."""
    outer = fill_silhouette(mask)
    holes = ((outer > 0) & (mask <= 127)).astype(np.uint8) * 255
    n, _labels, stats, _c = cv2.connectedComponentsWithStats(holes, 8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area >= min_area:
            boxes.append((int(x), int(y), int(w), int(h)))
    return boxes
