"""Вывод внутренних вырезов (камера, датчики) из нарисованной маски.

Оператор рисует тело и вырезает дыры; bbox'ы вырезов для region-QA считаются
автоматически как «силуэт минус тело маски».
"""
from __future__ import annotations

import cv2
import numpy as np


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
