"""Тесты Unicode-безопасного чтения/записи (кириллица в путях — баг OpenCV)."""
import numpy as np

from casecut.core.imageio import imread, imwrite


def test_unicode_path_roundtrip(tmp_path):
    folder = tmp_path / "Чехлы Самсунг"
    folder.mkdir()
    f = folder / "фото_розы.png"
    img = np.random.default_rng(0).integers(0, 255, (20, 30, 3), dtype=np.uint8)
    assert imwrite(f, img) is True
    back = imread(f)
    assert back is not None
    assert back.shape == img.shape


def test_imread_missing_returns_none(tmp_path):
    assert imread(tmp_path / "нет такого.png") is None


def test_store_with_cyrillic_device(tmp_path):
    from casecut.store.device_store import build_template, save_template, load_template
    from synth import render_case, make_mask_from_body
    img, gt = render_case(canvas=(800, 600), center=(300, 400), case_size=(200, 400), seed=5)
    mask = make_mask_from_body(gt["body_mask"], hole_center=(300, 250), hole_radius=22)
    tpl = build_template("Чехол Самсунг Галакси", img, mask)
    d = tmp_path / "Чехол Самсунг Галакси"
    save_template(d, tpl)
    loaded = load_template(d)
    assert np.array_equal(loaded.mask, tpl.mask)
