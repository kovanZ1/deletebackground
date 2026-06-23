"""Холст редактора маски: фото + маска. Инструменты:
кисть, ластик, вырез (тянуть овал), лассо (клики, ПКМ/двойной клик — замкнуть),
волшебная палочка (клик — стереть связную область похожего цвета). undo/redo.
Курсор показывает размер кисти/ластика.
"""
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
        self.tool = "brush"            # brush | erase | cutout | lasso | magic
        self.radius = 18
        self.tolerance = 30
        self._last = None
        self._drag_start = None        # img coords
        self._drag_cur = None          # img coords
        self._lasso: list = []         # img coords
        self._cursor = None            # widget coords (QPointF)
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
        self._drag_start = None
        self._drag_cur = None
        self.update()

    def set_radius(self, r) -> None:
        self.radius = max(1, int(r))
        self.update()

    def set_tolerance(self, t) -> None:
        self.tolerance = max(1, int(t))

    def propose_outline(self) -> None:
        if self._bgr is None or self.editor is None:
            return
        sil = detect_silhouette(self._bgr)
        if sil is not None:
            self.editor.begin_stroke()
            self.editor.mask = sil.mask.copy()
            self.maskChanged.emit()
            self.update()

    def auto_holes(self) -> int:
        """Авто-вырез всех отверстий камеры (фон сквозь дырки). Возвращает кол-во px."""
        if self._bgr is None or self.editor is None:
            return 0
        n = self.editor.cut_openings(self._bgr, bg_tol=self.tolerance)
        if n:
            self.maskChanged.emit()
            self.update()
        return n

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

        # лассо: точки + линии + замыкающая
        if self._lasso:
            pen = QtGui.QPen(QtGui.QColor(226, 75, 74), 2)
            p.setPen(pen)
            pts = [self._to_widget(pt) for pt in self._lasso]
            for i in range(1, len(pts)):
                p.drawLine(pts[i - 1], pts[i])
            if len(pts) >= 2:
                dashed = QtGui.QPen(QtGui.QColor(226, 75, 74), 1, QtCore.Qt.PenStyle.DashLine)
                p.setPen(dashed)
                p.drawLine(pts[-1], pts[0])
            p.setPen(pen)
            for pt in pts:
                p.setBrush(QtGui.QColor(226, 75, 74))
                p.drawEllipse(pt, 3, 3)
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawText(int(ox) + 6, int(oy) + 18,
                       "Лассо: клики по контуру, ПКМ или двойной клик — замкнуть")

        # вырез: живое превью овала
        if self.tool == "cutout" and self._drag_start and self._drag_cur:
            a = self._to_widget(self._drag_start)
            b = self._to_widget(self._drag_cur)
            p.setPen(QtGui.QPen(QtGui.QColor(226, 75, 74), 2))
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawEllipse(QtCore.QRectF(a, b))

        # курсор кисти/ластика — кружок по размеру
        if self._cursor is not None and self.tool in ("brush", "erase"):
            rpx = self.radius * s
            col = QtGui.QColor(40, 40, 40) if self.tool == "brush" else QtGui.QColor(226, 75, 74)
            p.setPen(QtGui.QPen(col, 1.5))
            p.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            p.drawEllipse(self._cursor, rpx, rpx)
        elif self._cursor is not None and self.tool == "magic":
            c = self._cursor
            p.setPen(QtGui.QPen(QtGui.QColor(24, 95, 165), 1.5))
            p.drawLine(QtCore.QPointF(c.x() - 7, c.y()), QtCore.QPointF(c.x() + 7, c.y()))
            p.drawLine(QtCore.QPointF(c.x(), c.y() - 7), QtCore.QPointF(c.x(), c.y() + 7))

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
            self._drag_cur = ip
        elif self.tool == "magic":
            if self.editor.magic(self._bgr, ip[0], ip[1], self.tolerance, ERASE):
                self.maskChanged.emit()
                self.update()
        elif self.tool == "lasso":
            if e.button() == QtCore.Qt.MouseButton.RightButton:
                self._close_lasso()
            else:
                self._lasso.append(ip)
                self.update()

    def mouseMoveEvent(self, e):
        self._cursor = e.position()
        if self._bgr is not None and self.editor is not None:
            if self.tool in ("brush", "erase") and (e.buttons() & QtCore.Qt.MouseButton.LeftButton):
                ip = self._to_img(e.position())
                if ip and self._last:
                    self.editor.line(self._last[0], self._last[1], ip[0], ip[1],
                                     self.radius, ADD if self.tool == "brush" else ERASE)
                    self._last = ip
                    self.maskChanged.emit()
            elif self.tool == "cutout" and self._drag_start:
                self._drag_cur = self._to_img(e.position())
        self.update()

    def mouseReleaseEvent(self, e):
        if self.tool == "cutout" and self._drag_start is not None and self.editor is not None:
            ip = self._to_img(e.position()) or self._drag_cur
            if ip:
                x0, y0 = self._drag_start
                x1, y1 = ip
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                rx, ry = abs(x1 - x0) / 2, abs(y1 - y0) / 2
                if rx > 2 and ry > 2:
                    self.editor.cutout_ellipse(cx, cy, rx, ry)
                    self.maskChanged.emit()
            self._drag_start = None
            self._drag_cur = None
            self.update()
        self._last = None

    def mouseDoubleClickEvent(self, e):
        if self.tool == "lasso":
            self._close_lasso()

    def leaveEvent(self, _e):
        self._cursor = None
        self.update()

    def _close_lasso(self):
        if self.editor is not None and len(self._lasso) >= 3:
            self.editor.cutout_polygon(self._lasso)
            self.maskChanged.emit()
        self._lasso = []
        self.update()
