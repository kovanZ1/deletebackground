"""Холст редактора маски: фото + маска, кисть/ластик/вырез/лассо, undo/redo."""
from __future__ import annotations

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from ..core.mask_edit import MaskEditor, ADD, ERASE
from ..core.silhouette import detect_silhouette
from .imageqt import bgr_to_qimage, overlay_mask


class MaskCanvas(QtWidgets.QWidget):
    maskChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bgr = None
        self.editor: MaskEditor | None = None
        self.tool = "brush"            # brush | erase | cutout | lasso
        self.radius = 18
        self._last = None
        self._drag_start = None
        self._lasso: list = []
        self.setMinimumSize(380, 380)
        self.setMouseTracking(True)

    # --- состояние ---
    def set_image(self, bgr: np.ndarray) -> None:
        self._bgr = bgr.copy()
        self.editor = MaskEditor(size=bgr.shape[:2])
        self._lasso = []
        self.update()

    def has_image(self) -> bool:
        return self._bgr is not None

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self._lasso = []
        self.update()

    def set_radius(self, r) -> None:
        self.radius = max(1, int(r))

    def propose_outline(self) -> None:
        if self._bgr is None or self.editor is None:
            return
        sil = detect_silhouette(self._bgr)
        if sil is not None:
            self.editor.begin_stroke()
            self.editor.mask = sil.mask.copy()
            self.maskChanged.emit()
            self.update()

    def undo(self) -> None:
        if self.editor:
            self.editor.undo()
            self.maskChanged.emit()
            self.update()

    def redo(self) -> None:
        if self.editor:
            self.editor.redo()
            self.maskChanged.emit()
            self.update()

    # --- геометрия фит-в-виджет ---
    def _fit(self):
        if self._bgr is None:
            return None
        ih, iw = self._bgr.shape[:2]
        s = min(self.width() / iw, self.height() / ih)
        dw, dh = iw * s, ih * s
        ox, oy = (self.width() - dw) / 2, (self.height() - dh) / 2
        return s, ox, oy, dw, dh

    def _to_img(self, pos):
        f = self._fit()
        if not f:
            return None
        s, ox, oy, _dw, _dh = f
        return (pos.x() - ox) / s, (pos.y() - oy) / s

    def _to_widget(self, pt):
        s, ox, oy, _dw, _dh = self._fit()
        return QtCore.QPointF(pt[0] * s + ox, pt[1] * s + oy)

    # --- отрисовка ---
    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        if self._bgr is None:
            p.setPen(QtGui.QColor(150, 150, 150))
            p.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter,
                       "Откройте фото эталона")
            return
        disp = overlay_mask(self._bgr, self.editor.mask) if self.editor else self._bgr
        pix = QtGui.QPixmap.fromImage(bgr_to_qimage(disp))
        s, ox, oy, dw, dh = self._fit()
        p.drawPixmap(int(ox), int(oy),
                     pix.scaled(int(dw), int(dh),
                                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                QtCore.Qt.TransformationMode.SmoothTransformation))
        if len(self._lasso) >= 2:
            p.setPen(QtGui.QPen(QtGui.QColor(226, 75, 74), 2))
            for i in range(1, len(self._lasso)):
                p.drawLine(self._to_widget(self._lasso[i - 1]), self._to_widget(self._lasso[i]))

    # --- мышь ---
    def mousePressEvent(self, e):
        if self._bgr is None or self.editor is None:
            return
        ip = self._to_img(e.position())
        if ip is None:
            return
        if self.tool in ("brush", "erase"):
            self.editor.begin_stroke()
            self._last = ip
            self.editor.dab(ip[0], ip[1], self.radius, ADD if self.tool == "brush" else ERASE)
            self.maskChanged.emit()
            self.update()
        elif self.tool == "cutout":
            self._drag_start = ip
        elif self.tool == "lasso":
            if e.button() == QtCore.Qt.MouseButton.RightButton:
                if len(self._lasso) >= 3:
                    self.editor.cutout_polygon(self._lasso)
                    self.maskChanged.emit()
                self._lasso = []
                self.update()
            else:
                self._lasso.append(ip)
                self.update()

    def mouseMoveEvent(self, e):
        if self._bgr is None or self.editor is None:
            return
        if self.tool in ("brush", "erase") and (e.buttons() & QtCore.Qt.MouseButton.LeftButton):
            ip = self._to_img(e.position())
            if ip and self._last:
                self.editor.line(self._last[0], self._last[1], ip[0], ip[1],
                                 self.radius, ADD if self.tool == "brush" else ERASE)
                self._last = ip
                self.maskChanged.emit()
                self.update()

    def mouseReleaseEvent(self, e):
        if self.tool == "cutout" and self._drag_start is not None and self.editor is not None:
            ip = self._to_img(e.position())
            if ip:
                x0, y0 = self._drag_start
                x1, y1 = ip
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                rx, ry = abs(x1 - x0) / 2, abs(y1 - y0) / 2
                if rx > 2 and ry > 2:
                    self.editor.cutout_ellipse(cx, cy, rx, ry)
                    self.maskChanged.emit()
            self._drag_start = None
            self.update()
        self._last = None
