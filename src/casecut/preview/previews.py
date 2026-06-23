"""Композитинг RGBA поверх сплошного фона для контроля края/ореола/вырезов."""
from __future__ import annotations

import numpy as np

DARK = (30, 30, 30)        # BGR
LIGHT = (255, 255, 255)
GRAY = (128, 128, 128)


def render_preview(rgba_bgra: np.ndarray, bg_color) -> np.ndarray:
    """Наложить BGRA на сплошной фон bg_color (BGR) -> BGR uint8."""
    h, w = rgba_bgra.shape[:2]
    fg = rgba_bgra[:, :, :3].astype(np.float32)
    a = (rgba_bgra[:, :, 3].astype(np.float32) / 255.0)[:, :, None]
    bg = np.empty((h, w, 3), dtype=np.float32)
    bg[:] = np.array(bg_color, dtype=np.float32)
    out = fg * a + bg * (1.0 - a)
    return np.clip(out, 0, 255).astype(np.uint8)


def render_previews(rgba_bgra: np.ndarray) -> dict:
    return {
        "dark": render_preview(rgba_bgra, DARK),
        "light": render_preview(rgba_bgra, LIGHT),
        "gray": render_preview(rgba_bgra, GRAY),
    }
