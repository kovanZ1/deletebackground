"""CLI без Qt: создать маску модели и прогнать папку (для проверки на реальных фото).

Примеры:
  casecut-cli build-template --device "iPhone15Pro" --ref-image ref.jpg --ref-mask mask.png --devices devices
  casecut-cli run --input input/iPhone15Pro --output output --devices devices --device iPhone15Pro
  casecut-cli run --input input --output output --devices devices --autopick --crop
  casecut-cli list --devices devices
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from .store.device_store import (
    build_template, save_template, load_all_templates, list_devices,
)
from .pipeline.batch import process_folder, make_substring_router
from .core.imageio import imread


def _cmd_build(a) -> int:
    img = imread(a.ref_image)
    if img is None:
        print("Не удалось открыть --ref-image", file=sys.stderr)
        return 2
    mask = imread(a.ref_mask, cv2.IMREAD_GRAYSCALE)
    if mask is None:
        print("Не удалось открыть --ref-mask", file=sys.stderr)
        return 2
    tpl = build_template(a.device, img, mask, feather_px=a.feather)
    save_template(Path(a.devices) / a.device, tpl)
    print(f"Маска модели «{a.device}» сохранена в {Path(a.devices)/a.device}. "
          f"Вырезов найдено: {len(tpl.camera_holes)}")
    return 0


def _cmd_run(a) -> int:
    templates = load_all_templates(a.devices)
    if not templates:
        print(f"Нет масок в {a.devices}. Сначала build-template.", file=sys.stderr)
        return 2
    if a.autopick:
        router = make_substring_router({n: n for n in templates})
    elif a.device:
        if a.device not in templates:
            print(f"Нет модели «{a.device}». Доступны: {', '.join(templates)}", file=sys.stderr)
            return 2
        router = (lambda _n, _d=a.device: _d)  # noqa: E731
    elif len(templates) == 1:
        router = None
    else:
        print("Укажите --device ИЛИ --autopick (масок несколько)", file=sys.stderr)
        return 2

    summary, _rows, report = process_folder(
        a.input, a.output, templates, router=router,
        make_previews=not a.no_previews, crop_to_object=a.crop,
        progress_cb=lambda d, t, n, s: print(f"  [{d}/{t}] {n} -> {s}"),
    )
    print(f"\nГотово: всего {summary['total']}, OK {summary['ok']}, "
          f"на проверку {summary['needs_review']}, ошибок {summary['error']}")
    print("Отчёт:", report)
    return 0


def _cmd_list(a) -> int:
    names = list_devices(a.devices)
    if not names:
        print(f"(пусто) {a.devices}")
    for n in names:
        print(n)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="casecut-cli", description="CaseCutoutTool CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build-template", help="создать маску модели из эталонного фото и маски")
    b.add_argument("--device", required=True)
    b.add_argument("--ref-image", dest="ref_image", required=True)
    b.add_argument("--ref-mask", dest="ref_mask", required=True)
    b.add_argument("--devices", default="devices")
    b.add_argument("--feather", type=int, default=0)
    b.set_defaults(fn=_cmd_build)

    r = sub.add_parser("run", help="обработать папку фото")
    r.add_argument("--input", required=True)
    r.add_argument("--output", required=True)
    r.add_argument("--devices", default="devices")
    r.add_argument("--device")
    r.add_argument("--autopick", action="store_true")
    r.add_argument("--no-previews", dest="no_previews", action="store_true")
    r.add_argument("--crop", action="store_true")
    r.set_defaults(fn=_cmd_run)

    li = sub.add_parser("list", help="список моделей в хранилище")
    li.add_argument("--devices", default="devices")
    li.set_defaults(fn=_cmd_list)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
