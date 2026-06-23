"""Мосты между OpenCV (BGR np.uint8) и Qt (QImage), плюс наложение маски."""
from __future__ import annotations

import cv2
import numpy as np
from PySide6 import QtGui

OVERLAY_BGR = (117, 158, 29)   # teal #1D9E75 в BGR


def bgr_to_qimage(bgr: np.ndarray) -> QtGui.QImage:
    h, w = bgr.shape[:2]
    rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    return QtGui.QImage(rgb.data, w, h, 3 * w, QtGui.QImage.Format.Format_RGB888).copy()


def overlay_mask(bgr: np.ndarray, mask: np.ndarray, alpha: float = 0.40) -> np.ndarray:
    """Подсветить тело маски поверх фото + контур (для наглядности в редакторе)."""
    ov = bgr.copy()
    body = mask > 127
    if body.any():
        tint = np.array(OVERLAY_BGR, dtype=np.float32)
        ov[body] = (bgr[body].astype(np.float32) * (1 - alpha) + tint * alpha).astype(np.uint8)
    cnts, _ = cv2.findContours((mask > 127).astype(np.uint8) * 255,
                               cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(ov, cnts, -1, OVERLAY_BGR, 2)
    return ov
