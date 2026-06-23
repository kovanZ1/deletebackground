"""Режим обучения: открыть эталонное фото, нарисовать/поправить маску, сохранить."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PySide6 import QtCore, QtWidgets

from ..store.device_store import build_template, save_template
from .canvas import MaskCanvas


class TeachPage(QtWidgets.QWidget):
    def __init__(self, devices_dir, parent=None):
        super().__init__(parent)
        self.devices_dir = Path(devices_dir)
        self.canvas = MaskCanvas()

        root = QtWidgets.QVBoxLayout(self)

        bar = QtWidgets.QHBoxLayout()
        b_open = QtWidgets.QPushButton("Открыть фото")
        b_open.clicked.connect(self._open_image)
        b_outline = QtWidgets.QPushButton("Предложить контур")
        b_outline.clicked.connect(self.canvas.propose_outline)
        bar.addWidget(b_open)
        bar.addWidget(b_outline)
        bar.addSpacing(12)

        self._tools = QtWidgets.QButtonGroup(self)
        for key, label in [("brush", "Кисть"), ("erase", "Ластик"),
                           ("cutout", "Вырез"), ("lasso", "Лассо")]:
            btn = QtWidgets.QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _c, k=key: self.canvas.set_tool(k))
            if key == "brush":
                btn.setChecked(True)
            self._tools.addButton(btn)
            bar.addWidget(btn)

        bar.addSpacing(12)
        bar.addWidget(QtWidgets.QLabel("Кисть"))
        size = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        size.setMinimum(3)
        size.setMaximum(80)
        size.setValue(18)
        size.setFixedWidth(110)
        size.valueChanged.connect(self.canvas.set_radius)
        bar.addWidget(size)

        b_undo = QtWidgets.QPushButton("Undo")
        b_undo.clicked.connect(self.canvas.undo)
        b_redo = QtWidgets.QPushButton("Redo")
        b_redo.clicked.connect(self.canvas.redo)
        bar.addWidget(b_undo)
        bar.addWidget(b_redo)
        bar.addStretch(1)
        root.addLayout(bar)

        root.addWidget(self.canvas, 1)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(QtWidgets.QLabel("Модель:"))
        self.device = QtWidgets.QLineEdit()
        self.device.setPlaceholderText("например, iPhone 15 Pro")
        bottom.addWidget(self.device, 1)
        bottom.addWidget(QtWidgets.QLabel("Мягкость края"))
        self.feather = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.feather.setMinimum(0)
        self.feather.setMaximum(10)
        self.feather.setValue(2)
        self.feather.setFixedWidth(110)
        bottom.addWidget(self.feather)
        b_save = QtWidgets.QPushButton("Сохранить маску")
        b_save.clicked.connect(self._save)
        bottom.addWidget(b_save)
        root.addLayout(bottom)

    def _open_image(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Эталонное фото", "", "Изображения (*.jpg *.jpeg *.png *.bmp *.webp)")
        if not path:
            return
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось открыть файл")
            return
        self.canvas.set_image(img)

    def _save(self):
        device = self.device.text().strip()
        if not device:
            QtWidgets.QMessageBox.warning(self, "Нет имени", "Укажите название модели")
            return
        if not self.canvas.has_image():
            QtWidgets.QMessageBox.warning(self, "Нет фото", "Откройте эталонное фото")
            return
        mask = np.where(self.canvas.editor.mask > 127, 255, 0).astype(np.uint8)
        if mask.max() == 0:
            QtWidgets.QMessageBox.warning(self, "Пустая маска", "Нарисуйте маску чехла")
            return
        try:
            tpl = build_template(device, self.canvas._bgr, mask, feather_px=self.feather.value())
            save_template(self.devices_dir / device, tpl)
        except Exception as e:  # noqa: BLE001
            QtWidgets.QMessageBox.critical(self, "Ошибка сохранения", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "Сохранено",
            f"Маска модели «{device}» сохранена.\nВырезов найдено: {len(tpl.camera_holes)}")
