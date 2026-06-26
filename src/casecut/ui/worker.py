"""Фоновый поток пакетной обработки (чтобы UI не подвисал на 100+ фото)."""
from __future__ import annotations

from PySide6 import QtCore

from ..pipeline.batch import process_folder


class BatchWorker(QtCore.QThread):
    progress = QtCore.Signal(int, int, str, str)   # done, total, filename, status
    finished_ok = QtCore.Signal(object)            # {"summary","rows","report"}
    failed = QtCore.Signal(str)

    def __init__(self, input_dir, output_dir, templates, router,
                 make_previews, crop, align="frame", parent=None):
        super().__init__(parent)
        self._args = (input_dir, output_dir, templates)
        self._router = router
        self._previews = make_previews
        self._crop = crop
        self._align = align

    def run(self):
        try:
            inp, out, templates = self._args
            summary, rows, report = process_folder(
                inp, out, templates,
                router=self._router,
                make_previews=self._previews,
                crop_to_object=self._crop,
                align=self._align,
                progress_cb=lambda d, t, n, s: self.progress.emit(d, t, n, s),
            )
            self.finished_ok.emit({"summary": summary, "rows": rows, "report": str(report)})
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
