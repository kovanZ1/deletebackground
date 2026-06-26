"""Авто-режим: выбрать папку, подобрать маску, обработать всё, увидеть отчёт."""
from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from ..store.device_store import load_all_templates
from ..pipeline.batch import make_substring_router
from .worker import BatchWorker


class AutoPage(QtWidgets.QWidget):
    def __init__(self, devices_dir, parent=None):
        super().__init__(parent)
        self.devices_dir = Path(devices_dir)
        self._worker = None
        self._output_dir = None
        self._report = None

        root = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QGridLayout()

        self.input_edit = QtWidgets.QLineEdit()
        b_in = QtWidgets.QPushButton("Выбрать…")
        b_in.clicked.connect(lambda: self._pick(self.input_edit))
        form.addWidget(QtWidgets.QLabel("Папка с фото"), 0, 0)
        form.addWidget(self.input_edit, 0, 1)
        form.addWidget(b_in, 0, 2)

        self.output_edit = QtWidgets.QLineEdit()
        b_out = QtWidgets.QPushButton("Выбрать…")
        b_out.clicked.connect(lambda: self._pick(self.output_edit))
        form.addWidget(QtWidgets.QLabel("Папка результата"), 1, 0)
        form.addWidget(self.output_edit, 1, 1)
        form.addWidget(b_out, 1, 2)

        self.device_combo = QtWidgets.QComboBox()
        self.autopick = QtWidgets.QCheckBox("Автоподбор по имени файла")
        self.autopick.toggled.connect(self.device_combo.setDisabled)
        form.addWidget(QtWidgets.QLabel("Маска (модель)"), 2, 0)
        form.addWidget(self.device_combo, 2, 1)
        form.addWidget(self.autopick, 2, 2)
        root.addLayout(form)

        opts = QtWidgets.QHBoxLayout()
        self.cb_frame = QtWidgets.QCheckBox("Привязка к кадру")
        self.cb_frame.setChecked(True)
        self.cb_frame.setToolTip("Одинаковые кадры: маска ставится в координатах кадра без "
                                 "поиска силуэта (без смещения вырезов). Снять — если кадры разные.")
        self.cb_prev = QtWidgets.QCheckBox("Создать превью")
        self.cb_prev.setChecked(True)
        self.cb_crop = QtWidgets.QCheckBox("Обрезать по объекту")
        opts.addWidget(self.cb_frame)
        opts.addWidget(self.cb_prev)
        opts.addWidget(self.cb_crop)
        opts.addStretch(1)
        self.b_run = QtWidgets.QPushButton("Обработать")
        self.b_run.clicked.connect(self._run)
        opts.addWidget(self.b_run)
        root.addLayout(opts)

        self.progress = QtWidgets.QProgressBar()
        self.status = QtWidgets.QLabel("Готов к работе")
        root.addWidget(self.progress)
        root.addWidget(self.status)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Файл", "Статус", "Маска", "Причины"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)

        actions = QtWidgets.QHBoxLayout()
        self.b_review = QtWidgets.QPushButton("Открыть _needs_review")
        self.b_review.clicked.connect(lambda: self._open(self._output_dir, "_needs_review"))
        self.b_outdir = QtWidgets.QPushButton("Открыть папку результата")
        self.b_outdir.clicked.connect(lambda: self._open(self._output_dir))
        actions.addStretch(1)
        actions.addWidget(self.b_review)
        actions.addWidget(self.b_outdir)
        root.addLayout(actions)

        self.refresh_devices()

    def refresh_devices(self):
        current = self.device_combo.currentText()      # сохранить выбор пользователя
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self._templates = load_all_templates(self.devices_dir)
        self.device_combo.addItems(list(self._templates.keys()))
        if current:
            idx = self.device_combo.findText(current)
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)
        self.device_combo.blockSignals(False)

    def _pick(self, edit):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Выбор папки")
        if d:
            edit.setText(d)

    def _open(self, base, sub=None):
        if not base:
            return
        path = Path(base) / sub if sub else Path(base)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))

    def _run(self):
        self.refresh_devices()
        inp = self.input_edit.text().strip()
        out = self.output_edit.text().strip()
        if not inp or not out:
            QtWidgets.QMessageBox.warning(self, "Папки", "Укажите папку с фото и папку результата")
            return
        if not self._templates:
            QtWidgets.QMessageBox.warning(self, "Нет масок", "Сначала создайте маску в режиме «Обучение»")
            return
        if self.autopick.isChecked():
            router = make_substring_router({name: name for name in self._templates})
        else:
            dev = self.device_combo.currentText()
            router = lambda _n, _d=dev: _d  # noqa: E731

        self._output_dir = out
        self.b_run.setEnabled(False)
        self.table.setRowCount(0)
        self.status.setText("Обработка…")
        align = "frame" if self.cb_frame.isChecked() else "silhouette"
        self._worker = BatchWorker(inp, out, self._templates, router,
                                   self.cb_prev.isChecked(), self.cb_crop.isChecked(),
                                   align=align)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_progress(self, done, total, name, status):
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.status.setText(f"{done}/{total} · {name} → {status}")

    def _on_done(self, payload):
        self.b_run.setEnabled(True)
        s = payload["summary"]
        self.status.setText(
            f"Готово: всего {s['total']}, OK {s['ok']}, на проверку {s['needs_review']}, ошибок {s['error']}")
        for r in payload["rows"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, key in enumerate(["filename", "status", "mask_used", "reasons"]):
                self.table.setItem(row, col, QtWidgets.QTableWidgetItem(str(r.get(key, ""))))
        self._report = payload["report"]

    def _on_fail(self, msg):
        self.b_run.setEnabled(True)
        self.status.setText("Ошибка")
        QtWidgets.QMessageBox.critical(self, "Ошибка обработки", msg)
