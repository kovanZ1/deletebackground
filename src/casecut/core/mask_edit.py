"""Редактирование маски кистью/ластиком/вырезом (как в фоторедакторе).

Логика отделена от GUI и работает на numpy-массиве (uint8 0/255) — тестируемо.
GUI (PySide6) будет лишь вызывать эти методы по событиям мыши.
"""
from __future__ import annotations

import cv2
import numpy as np

ADD = "add"
ERASE = "erase"


class MaskEditor:
    """Редактируемая маска с историей (undo/redo). 255 — тело, 0 — фон/вырез."""

    def __init__(self, mask: np.ndarray | None = None, size: tuple | None = None,
                 max_undo: int = 30):
        if mask is not None:
            self.mask = mask.copy()
        elif size is not None:
            h, w = size
            self.mask = np.zeros((h, w), dtype=np.uint8)
        else:
            raise ValueError("нужен mask или size")
        self._undo: list = []
        self._redo: list = []
        self._max_undo = max_undo

    # --- история ---
    def begin_stroke(self) -> None:
        """Зафиксировать состояние перед мазком (для undo одним шагом)."""
        self._undo.append(self.mask.copy())
        if len(self._undo) > self._max_undo:
            self._undo.pop(0)
        self._redo.clear()

    def end_stroke(self) -> None:
        pass

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> None:
        if not self._undo:
            return
        self._redo.append(self.mask.copy())
        self.mask = self._undo.pop()

    def redo(self) -> None:
        if not self._redo:
            return
        self._undo.append(self.mask.copy())
        self.mask = self._redo.pop()

    # --- инструменты (вызывать между begin_stroke/end_stroke) ---
    def dab(self, cx, cy, radius, mode: str = ADD) -> None:
        """Точка кисти/ластика."""
        val = 255 if mode == ADD else 0
        cv2.circle(self.mask, (int(cx), int(cy)), max(1, int(radius)), val, -1)

    def line(self, x0, y0, x1, y1, radius, mode: str = ADD) -> None:
        """Отрезок мазка (между двумя точками при перетаскивании)."""
        val = 255 if mode == ADD else 0
        r = max(1, int(radius))
        cv2.line(self.mask, (int(x0), int(y0)), (int(x1), int(y1)), val, r * 2)
        cv2.circle(self.mask, (int(x0), int(y0)), r, val, -1)
        cv2.circle(self.mask, (int(x1), int(y1)), r, val, -1)

    def cutout_polygon(self, points) -> None:
        """Вырез произвольной формы (лассо): зона внутри полигона -> 0."""
        self.begin_stroke()
        pts = np.array(points, dtype=np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(self.mask, [pts], 0)
        self.end_stroke()

    def cutout_rect(self, x, y, w, h) -> None:
        """Прямоугольный вырез -> 0."""
        self.begin_stroke()
        cv2.rectangle(self.mask, (int(x), int(y)), (int(x + w), int(y + h)), 0, -1)
        self.end_stroke()

    def cutout_ellipse(self, cx, cy, rx, ry) -> None:
        """Эллиптический вырез (под круглые отверстия камеры) -> 0."""
        self.begin_stroke()
        cv2.ellipse(self.mask, (int(cx), int(cy)), (int(rx), int(ry)), 0, 0, 360, 0, -1)
        self.end_stroke()

    def binarize(self) -> None:
        """Привести к строгому 0/255 (после сглаженных операций)."""
        self.mask = np.where(self.mask > 127, 255, 0).astype(np.uint8)
