"""Мастер-маска модели: маска + геометрия эталона + параметры. Сохранение на диск.

Структура на диск:
  <folder>/mask.png        — grayscale alpha маски (255 тело, 0 фон/вырезы)
  <folder>/template.json   — геометрия эталона + параметры (feather, tweak, holes)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ..core.silhouette import detect_silhouette
from ..core.holes import derive_holes


@dataclass
class RefGeometry:
    bbox: tuple                 # (x, y, w, h) внешнего силуэта эталона
    area: int
    centroid: tuple


@dataclass
class DeviceTemplate:
    device: str
    mask: np.ndarray            # uint8 0/255
    ref: RefGeometry
    feather_px: int = 0
    scale_tweak: float = 1.0
    offset: tuple = (0.0, 0.0)
    camera_holes: list = field(default_factory=list)   # bbox'ы вырезов в коорд. эталона
    version: int = 1


def build_template(device: str, ref_img: np.ndarray, ref_mask: np.ndarray, *,
                   camera_holes=None, feather_px: int = 0) -> DeviceTemplate:
    """Собрать шаблон: геометрия эталона берётся из силуэта эталонного фото."""
    sil = detect_silhouette(ref_img)
    if sil is None:
        raise ValueError("не удалось выделить силуэт на эталонном фото")
    ref = RefGeometry(sil.bbox, sil.area, sil.centroid)
    if camera_holes is None:
        camera_holes = derive_holes(ref_mask)   # вырезы считаем из самой маски
    return DeviceTemplate(
        device=device,
        mask=ref_mask.copy(),
        ref=ref,
        feather_px=feather_px,
        camera_holes=list(camera_holes),
    )


def save_template(folder, template: DeviceTemplate) -> None:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(folder / "mask.png"), template.mask)
    meta = {
        "device": template.device,
        "ref": {
            "bbox": list(template.ref.bbox),
            "area": int(template.ref.area),
            "centroid": list(template.ref.centroid),
        },
        "feather_px": template.feather_px,
        "scale_tweak": template.scale_tweak,
        "offset": list(template.offset),
        "camera_holes": [list(h) for h in template.camera_holes],
        "version": template.version,
    }
    (folder / "template.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_devices(root) -> list:
    """Имена устройств в хранилище (папки с template.json)."""
    root = Path(root)
    if not root.exists():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "template.json").exists())


def load_all_templates(root) -> dict:
    """Загрузить все шаблоны: {device: DeviceTemplate}."""
    root = Path(root)
    return {name: load_template(root / name) for name in list_devices(root)}


def load_template(folder) -> DeviceTemplate:
    folder = Path(folder)
    mask = cv2.imread(str(folder / "mask.png"), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"маска не найдена: {folder/'mask.png'}")
    meta = json.loads((folder / "template.json").read_text(encoding="utf-8"))
    ref = RefGeometry(
        tuple(meta["ref"]["bbox"]),
        int(meta["ref"]["area"]),
        tuple(meta["ref"]["centroid"]),
    )
    return DeviceTemplate(
        device=meta["device"],
        mask=mask,
        ref=ref,
        feather_px=meta["feather_px"],
        scale_tweak=meta["scale_tweak"],
        offset=tuple(meta["offset"]),
        camera_holes=[tuple(h) for h in meta["camera_holes"]],
        version=meta["version"],
    )
