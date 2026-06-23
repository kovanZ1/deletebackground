"""Чтение/запись изображений с поддержкой Unicode-путей.

cv2.imread/imwrite на Windows НЕ работают с не-ASCII путями (кириллица в имени
папки/файла) — возвращают None / не пишут. Здесь обходим это через
np.fromfile + cv2.imdecode и cv2.imencode + ndarray.tofile, которые корректно
работают с любыми путями.
"""
from __future__ import annotations

import os

import cv2
import numpy as np


def imread(path, flags=cv2.IMREAD_COLOR):
    """Прочитать изображение по пути (в т.ч. с кириллицей). None, если не вышло."""
    try:
        data = np.fromfile(os.fspath(path), dtype=np.uint8)
    except (OSError, ValueError):
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


def imwrite(path, img) -> bool:
    """Записать изображение по пути (в т.ч. с кириллицей). True при успехе."""
    p = os.fspath(path)
    ext = os.path.splitext(p)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        return False
    try:
        buf.tofile(p)
    except (OSError, ValueError):
        return False
    return True
