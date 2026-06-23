"""Тесты CLI (без Qt): build-template -> run на синтетике."""
import cv2

from casecut.cli import main
from synth import render_case, make_mask_from_body


def test_cli_build_then_run(tmp_path):
    ref_img, ref_gt = render_case(canvas=(800, 600), center=(300, 400),
                                  case_size=(200, 400), seed=5)
    mask = make_mask_from_body(ref_gt["body_mask"], hole_center=(300, 250), hole_radius=22)
    ref_image_path = tmp_path / "ref.png"
    ref_mask_path = tmp_path / "mask.png"
    cv2.imwrite(str(ref_image_path), ref_img)
    cv2.imwrite(str(ref_mask_path), mask)
    devices = tmp_path / "devices"

    rc = main(["build-template", "--device", "M1",
               "--ref-image", str(ref_image_path), "--ref-mask", str(ref_mask_path),
               "--devices", str(devices)])
    assert rc == 0
    assert (devices / "M1" / "template.json").exists()

    inp = tmp_path / "in"
    inp.mkdir()
    out = tmp_path / "out"
    g, _ = render_case(canvas=(800, 600), center=(320, 360), case_size=(270, 540), seed=6)
    cv2.imwrite(str(inp / "a.jpg"), g)

    rc = main(["run", "--input", str(inp), "--output", str(out),
               "--devices", str(devices), "--device", "M1"])
    assert rc == 0
    assert (out / "M1" / "a_alpha.png").exists()
    assert (out / "reports" / "processing_report.csv").exists()


def test_cli_run_unknown_device(tmp_path):
    # пустое хранилище -> код возврата 2
    inp = tmp_path / "in"
    inp.mkdir()
    rc = main(["run", "--input", str(inp), "--output", str(tmp_path / "out"),
               "--devices", str(tmp_path / "devices")])
    assert rc == 2
