"""Главное окно (Вариант B): боковая навигация + страницы Обучение / Авто."""
from __future__ import annotations

from pathlib import Path

from PySide6 import QtWidgets

from .teach_page import TeachPage
from .auto_page import AutoPage


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, devices_dir=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CaseCutoutTool")
        self.resize(1040, 700)
        devices_dir = Path(devices_dir) if devices_dir else (Path.cwd() / "devices")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        lay = QtWidgets.QHBoxLayout(central)

        self.nav = QtWidgets.QListWidget()
        self.nav.addItems(["Обучение", "Авто"])
        self.nav.setFixedWidth(150)
        self.nav.setCurrentRow(0)
        lay.addWidget(self.nav)

        self.stack = QtWidgets.QStackedWidget()
        self.teach = TeachPage(devices_dir)
        self.auto = AutoPage(devices_dir)
        self.stack.addWidget(self.teach)
        self.stack.addWidget(self.auto)
        lay.addWidget(self.stack, 1)

        self.nav.currentRowChanged.connect(self._switch)

    def _switch(self, row: int):
        self.stack.setCurrentIndex(row)
        if row == 1:
            self.auto.refresh_devices()
