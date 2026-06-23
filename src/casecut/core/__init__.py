"""Детерминированное ядро: силуэт, выравнивание (масштаб+сдвиг), применение маски."""

from .silhouette import Silhouette, detect_silhouette, estimate_background_lab
from .align import Alignment, estimate_alignment
from .mask_apply import warp_mask, feather_alpha, compose_rgba

__all__ = [
    "Silhouette",
    "detect_silhouette",
    "estimate_background_lab",
    "Alignment",
    "estimate_alignment",
    "warp_mask",
    "feather_alpha",
    "compose_rgba",
]
