"""Пакетная обработка папки: авто-режим «папка → старт → результат».

Раскладка результата:
  <output>/<device>/<name>_alpha.png      — готовые PNG с alpha
  <output>/_preview_dark|light|gray/      — превью на 3 фонах
  <output>/_needs_review/                 — копии спорных исходников
  <output>/reports/processing_report.csv  — отчёт
"""
from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

import cv2

from .processor import process_image
from ..preview.previews import render_previews
from ..core.mask_apply import crop_to_content
from ..core.imageio import imread, imwrite

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CSV_FIELDS = ["filename", "status", "mask_used", "output_file", "error", "reasons"]


def make_substring_router(config: dict):
    """config: {pattern: device}. Сопоставление по подстроке (без регистра)."""
    items = [(p.lower(), d) for p, d in config.items()]

    def router(name: str):
        n = name.lower()
        for p, d in items:
            if p in n:
                return d
        return None

    return router


def make_regex_router(config: dict):
    """config: {regex: device}. Первое совпадение по регулярке (без регистра)."""
    items = [(re.compile(p, re.IGNORECASE), d) for p, d in config.items()]

    def router(name: str):
        for rx, d in items:
            if rx.search(name):
                return d
        return None

    return router


def process_folder(input_dir, output_dir, templates: dict, *, router=None,
                   make_previews: bool = True, crop_to_object: bool = False,
                   report_path=None, progress_cb=None):
    """Обработать все изображения папки. Возвращает (summary, rows, report_path).

    progress_cb(done, total, filename, status) — необязательный колбэк прогресса.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    review_dir = output_dir / "_needs_review"

    if router is None:
        if len(templates) == 1:
            only = next(iter(templates))
            def router(_name, _only=only):
                return _only
        else:
            raise ValueError("при нескольких шаблонах нужен router")

    rows = []
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in IMG_EXT)
    total = len(files)
    for p in files:
        row = {k: "" for k in CSV_FIELDS}
        row["filename"] = p.name
        try:
            device = router(p.name)
            if device is None or device not in templates:
                row["status"] = "ERROR"
                row["error"] = "mask_not_found"
                review_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, review_dir / p.name)
            else:
                img = imread(str(p))
                if img is None:
                    row["status"] = "ERROR"
                    row["error"] = "cannot_read"
                else:
                    res = process_image(img, templates[device])
                    row["mask_used"] = device
                    row["reasons"] = ";".join(res.reasons)
                    if res.status == "ok":
                        rgba_out = crop_to_content(res.rgba) if crop_to_object else res.rgba
                        dev_out = output_dir / device
                        dev_out.mkdir(parents=True, exist_ok=True)
                        out = dev_out / (p.stem + "_alpha.png")
                        imwrite(str(out), rgba_out)
                        row["status"] = "OK"
                        row["output_file"] = str(out.relative_to(output_dir))
                        if make_previews:
                            for k, im in render_previews(rgba_out).items():
                                pd = output_dir / f"_preview_{k}"
                                pd.mkdir(parents=True, exist_ok=True)
                                imwrite(str(pd / (p.stem + ".png")), im)
                    else:
                        review_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(p, review_dir / p.name)
                        row["status"] = "needs_review"
        except Exception as e:  # noqa: BLE001 — в отчёт, кадр не должен ронять батч
            row["status"] = "ERROR"
            row["error"] = str(e)
        rows.append(row)
        if progress_cb is not None:
            progress_cb(len(rows), total, p.name, row["status"])

    report_path = Path(report_path) if report_path else (
        output_dir / "reports" / "processing_report.csv"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)

    summary = {
        "total": len(rows),
        "ok": sum(1 for r in rows if r["status"] == "OK"),
        "needs_review": sum(1 for r in rows if r["status"] == "needs_review"),
        "error": sum(1 for r in rows if r["status"] == "ERROR"),
    }
    return summary, rows, report_path
