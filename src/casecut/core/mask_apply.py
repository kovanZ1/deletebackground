"""Применение маски: варп под целевое фото, мягкость края, композитинг RGBA.

Принт не трогается: RGB остаётся бит-в-бит, меняется только alpha-канал.
"""
from __future__ import annotations

import cv2
import numpy as np


def warp_mask(mask: np.ndarray, matrix: np.ndarray, out_hw: tuple) -> np.ndarray:
    """Перенести/масштабировать маску под размер целевого фото."""
    h, w = out_hw
    return cv2.warpAffine(
        mask, matrix, (w, h), flags=cv2.INTER_LINEAR, borderValue=0
    )


def feather_alpha(alpha: np.ndarray, px: int) -> np.ndarray:
    """Мягкость края: лёгкий erode против каймы фона + сглаживание."""
    if px <= 0:
        return alpha
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    a = cv2.erode(alpha, k, iterations=1)
    ksize = int(px) * 2 + 1
    return cv2.GaussianBlur(a, (ksize, ksize), 0)


def compose_rgba(img_bgr: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """BGR + alpha(uint8) -> BGRA (straight alpha). RGB не изменяется."""
    if alpha.dtype != np.uint8:
        alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    b, g, r = cv2.split(img_bgr)
    return cv2.merge([b, g, r, alpha])


def crop_to_content(rgba: np.ndarray, margin: int = 0) -> np.ndarray:
    """Обрезать BGRA по непрозрачному объекту (+ необязательный отступ)."""
    alpha = rgba[:, :, 3]
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0:
        return rgba
    h, w = rgba.shape[:2]
    x0 = max(0, int(xs.min()) - margin)
    x1 = min(w, int(xs.max()) + 1 + margin)
    y0 = max(0, int(ys.min()) - margin)
    y1 = min(h, int(ys.max()) + 1 + margin)
    return rgba[y0:y1, x0:x1]
