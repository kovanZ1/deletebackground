"""Тесты пакетной обработки папки и роутеров по имени файла."""
import csv

import cv2

from casecut.store.device_store import build_template
from casecut.pipeline.batch import (
    process_folder,
    make_substring_router,
    make_regex_router,
)
from synth import render_case, make_mask_from_body


def _make_ref():
    ref_img, ref_gt = render_case(canvas=(800, 600), center=(300, 400),
                                  case_size=(200, 400), seed=5)
    hole = (300, 250)
    r = 22
    ref_mask = make_mask_from_body(ref_gt["body_mask"], hole_center=hole, hole_radius=r)
    holes = [(hole[0] - r, hole[1] - r, 2 * r, 2 * r)]
    return build_template("TEST_MODEL", ref_img, ref_mask, camera_holes=holes)


def test_substring_router():
    router = make_substring_router({"HON-600": "DEV_A", "IPH-15-PRO": "DEV_B"})
    assert router("ZSMF-HON-600-1274.jpg") == "DEV_A"
    assert router("IPH-15-PRO-001.jpg") == "DEV_B"
    assert router("UNKNOWN-123.jpg") is None


def test_regex_router():
    router = make_regex_router({r"HON-?600": "DEV_A"})
    assert router("hon600_1.jpg") == "DEV_A"
    assert router("xxx.jpg") is None


def test_process_folder(tmp_path):
    tpl = _make_ref()
    inp = tmp_path / "input"
    inp.mkdir()
    out = tmp_path / "output"

    good1, _ = render_case(canvas=(800, 600), center=(320, 360),
                           case_size=(270, 540), seed=6)
    good2, _ = render_case(canvas=(800, 600), center=(300, 380),
                           case_size=(180, 360), seed=11)
    border, _ = render_case(canvas=(600, 600), center=(40, 300),
                            case_size=(220, 440), seed=8)
    cv2.imwrite(str(inp / "good1.jpg"), good1)
    cv2.imwrite(str(inp / "good2.jpg"), good2)
    cv2.imwrite(str(inp / "border.jpg"), border)

    summary, rows, report = process_folder(inp, out, {"TEST_MODEL": tpl})

    assert summary["total"] == 3
    assert summary["ok"] == 2
    assert summary["needs_review"] == 1

    assert (out / "TEST_MODEL" / "good1_alpha.png").exists()
    assert (out / "TEST_MODEL" / "good2_alpha.png").exists()
    assert (out / "_preview_dark" / "good1.png").exists()
    assert (out / "_needs_review" / "border.jpg").exists()

    # готовый PNG имеет alpha-канал
    res_png = cv2.imread(str(out / "TEST_MODEL" / "good1_alpha.png"), cv2.IMREAD_UNCHANGED)
    assert res_png.shape[2] == 4

    # CSV: заголовок + 3 строки
    assert report.exists()
    with open(report, encoding="utf-8") as f:
        data = list(csv.DictReader(f))
    assert len(data) == 3
    assert {r["filename"] for r in data} == {"good1.jpg", "good2.jpg", "border.jpg"}
    assert any(r["status"] == "OK" for r in data)
    assert any(r["status"] == "needs_review" for r in data)


def test_process_folder_unknown_mask_goes_review(tmp_path):
    tpl = _make_ref()
    inp = tmp_path / "input"
    inp.mkdir()
    out = tmp_path / "output"
    img, _ = render_case(seed=6)
    cv2.imwrite(str(inp / "ZZZ-999-1.jpg"), img)

    router = make_substring_router({"HON-600": "TEST_MODEL"})
    summary, rows, _ = process_folder(inp, out, {"TEST_MODEL": tpl}, router=router)

    assert summary["error"] == 1
    assert rows[0]["error"] == "mask_not_found"
    assert (out / "_needs_review" / "ZZZ-999-1.jpg").exists()
