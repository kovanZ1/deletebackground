"""Синтетические фото чехлов для детерминированных тестов ядра.

Рисует «чехол» (скруглённый прямоугольник) известного размера/позиции на
светлом градиентном фоне с мягкой тенью и лёгким шумом. Возвращает ground-truth
(bbox/центр/площадь/маска тела), чтобы проверять детекцию и выравнивание.
"""
from __future__ import annotations

import cv2
import numpy as np


def _gradient_background(h: int, w: int) -> np.ndarray:
    top = np.array([206, 204, 208], dtype=np.float32)      # BGR, светло-серый
    bottom = np.array([190, 188, 196], dtype=np.float32)
    ramp = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    bg = top[None, None, :] * (1.0 - ramp) + bottom[None, None, :] * ramp
    return np.repeat(bg, w, axis=1)


def _rounded_rect(canvas: np.ndarray, x: int, y: int, w: int, h: int, r: int, val: int) -> None:
    cv2.rectangle(canvas, (x + r, y), (x + w - r, y + h), val, -1)
    cv2.rectangle(canvas, (x, y + r), (x + w, y + h - r), val, -1)
    for cxp, cyp in [
        (x + r, y + r), (x + w - r, y + r),
        (x + r, y + h - r), (x + w - r, y + h - r),
    ]:
        cv2.circle(canvas, (cxp, cyp), r, val, -1)


def _add_soft_shadow(bg: np.ndarray, bbox: tuple, strength: float = 16.0) -> np.ndarray:
    x, y, cw, ch = bbox
    cx = x + cw // 2 + int(cw * 0.12)
    cy = y + ch // 2 + int(ch * 0.10)
    shadow = np.zeros(bg.shape[:2], dtype=np.float32)
    cv2.ellipse(shadow, (cx, cy), (int(cw * 0.62), int(ch * 0.60)), 0, 0, 360, 1.0, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), sigmaX=max(cw, ch) * 0.06)
    return bg - shadow[..., None] * strength


def render_case(
    canvas: tuple = (800, 600),
    center: tuple | None = None,
    case_size: tuple = (220, 440),
    color: tuple = (150, 110, 135),
    shadow: bool = True,
    noise: bool = True,
    seed: int = 0,
):
    """Вернуть (img_bgr uint8, gt) где gt: bbox, centroid, area, body_mask."""
    h, w = canvas
    cw, ch = case_size
    if center is None:
        center = (w // 2, h // 2)
    cx, cy = center
    x0, y0 = cx - cw // 2, cy - ch // 2
    rng = np.random.default_rng(seed)

    bg = _gradient_background(h, w)
    bbox = (x0, y0, cw, ch)
    if shadow:
        bg = _add_soft_shadow(bg, bbox)

    body = np.zeros((h, w), dtype=np.uint8)
    r = max(8, int(min(cw, ch) * 0.12))
    _rounded_rect(body, x0, y0, cw, ch, r, 255)

    img = bg.copy()
    img[body > 0] = np.array(color, dtype=np.float32)
    if noise:
        img = img + rng.normal(0.0, 2.0, img.shape).astype(np.float32)
    img = np.clip(img, 0, 255).astype(np.uint8)

    m = cv2.moments(body, binaryImage=True)
    centroid = (m["m10"] / m["m00"], m["m01"] / m["m00"])
    area = int((body > 0).sum())
    gt = {"bbox": bbox, "centroid": centroid, "area": area, "body_mask": body}
    return img, gt


def make_mask_from_body(body_mask: np.ndarray, hole_center: tuple | None = None,
                        hole_radius: int = 22) -> np.ndarray:
    """Маска оператора: 255 на теле, 0 фон, вырез камеры = 0."""
    mask = body_mask.copy()
    if hole_center is not None:
        cv2.circle(mask, hole_center, hole_radius, 0, -1)
    return mask
