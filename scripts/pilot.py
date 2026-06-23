"""Пилот на реальных фото: вырез каждого + тест master-mask (HON-600 1->2).
Делает contact-sheet'ы для визуальной оценки и кладёт RGBA в pilot_output/.
"""
import glob
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

from casecut.core.silhouette import estimate_background_lab, detect_silhouette  # noqa: E402
from casecut.core.holes import derive_holes  # noqa: E402
from casecut.core.mask_apply import compose_rgba  # noqa: E402
from casecut.preview.previews import render_preview  # noqa: E402
from casecut.store.device_store import build_template  # noqa: E402
from casecut.pipeline.processor import process_image  # noqa: E402

IN = os.path.join(ROOT, "pilot_input")
OUT = os.path.join(ROOT, "pilot_output")
os.makedirs(OUT, exist_ok=True)

DARK = (30, 30, 30)
LIGHT = (245, 245, 245)


def clean_foreground(img):
    """Детерминированная сегментация: тело корпуса (255), фон+отверстия (0).
    Сохраняет внутренние вырезы (камера), убирает внешний шум/тени."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    bg = estimate_background_lab(img)
    dist = np.linalg.norm(lab - bg[None, None, :], axis=2)
    d8 = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _t, binm = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binm = cv2.morphologyEx(binm, cv2.MORPH_OPEN, k)
    binm = cv2.morphologyEx(binm, cv2.MORPH_CLOSE, k)
    n, labels, stats, _c = cv2.connectedComponentsWithStats(binm, 8)
    if n <= 1:
        return binm
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    mask = (labels == largest).astype(np.uint8) * 255
    return mask


def fit_h(img, h):
    s = h / img.shape[0]
    return cv2.resize(img, (max(1, int(img.shape[1] * s)), h), interpolation=cv2.INTER_AREA)


def label(img, text):
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 22), (0, 0, 0), -1)
    cv2.putText(out, text, (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    return out


def hrow(panels, gap=6, bg=200):
    h = max(p.shape[0] for p in panels)
    norm = []
    for p in panels:
        if p.shape[0] != h:
            pad = np.full((h - p.shape[0], p.shape[1], 3), bg, np.uint8)
            p = np.vstack([p, pad])
        norm.append(p)
        norm.append(np.full((h, gap, 3), bg, np.uint8))
    return np.hstack(norm[:-1])


def vstack_rows(rows, gap=6, bg=200):
    w = max(r.shape[1] for r in rows)
    norm = []
    for r in rows:
        if r.shape[1] != w:
            pad = np.full((r.shape[0], w - r.shape[1], 3), bg, np.uint8)
            r = np.hstack([r, pad])
        norm.append(r)
        norm.append(np.full((gap, w, 3), bg, np.uint8))
    return np.vstack(norm[:-1])


files = sorted(glob.glob(os.path.join(IN, "*")))
H = 330
rows = []
summary = []
for f in files:
    name = os.path.splitext(os.path.basename(f))[0]
    img = cv2.imread(f, cv2.IMREAD_COLOR)
    mask = clean_foreground(img)
    rgba = compose_rgba(img, mask)
    cv2.imwrite(os.path.join(OUT, name + "_alpha.png"), rgba)
    holes = derive_holes(mask, min_area=40)
    cover = float((mask > 127).mean()) * 100
    summary.append((name, cover, len(holes)))
    on_dark = render_preview(rgba, DARK)
    on_light = render_preview(rgba, LIGHT)
    orig = label(fit_h(img, H), name)
    pdark = label(fit_h(on_dark, H), "cutout / dark")
    plight = label(fit_h(on_light, H), "cutout / light  holes=%d" % len(holes))
    rows.append(hrow([orig, pdark, plight]))

sheet = vstack_rows(rows)
cv2.imwrite(os.path.join(OUT, "contact_sheet.png"), sheet)

# --- Тест продукта: маска с HON-600 #1274 -> применяем к #1781 ---
hon = [f for f in files if "HON-600" in f]
cross = None
if len(hon) >= 2:
    ref_img = cv2.imread(hon[0], cv2.IMREAD_COLOR)
    ref_mask = clean_foreground(ref_img)
    tpl = build_template("HON-600", ref_img, ref_mask)
    tgt_img = cv2.imread(hon[1], cv2.IMREAD_COLOR)
    res = process_image(tgt_img, tpl)
    cross_rgba = res.rgba
    cv2.imwrite(os.path.join(OUT, "HON600_crossapply_alpha.png"), cross_rgba)
    a = label(fit_h(cv2.imread(hon[0]), H), "mask SOURCE: " + os.path.basename(hon[0]))
    b = label(fit_h(render_preview(cross_rgba, DARK), H), "mask APPLIED to #1781 (status=%s)" % res.status)
    c = label(fit_h(render_preview(cross_rgba, LIGHT), H), "applied / light")
    cross = hrow([a, b, c])
    cv2.imwrite(os.path.join(OUT, "HON600_crossapply.png"), cross)

print("=== SUMMARY ===")
for name, cover, nh in summary:
    print(f"{name}: alpha-покрытие {cover:.1f}% тела, вырезов(холов) найдено {nh}")
if cross is not None:
    print("HON-600 cross-apply: status =", res.status, "| reasons =", res.reasons)
print("Файлы:", OUT)
