"""Проверка удалённого флага доступа: kill-switch + принудительное обновление.

При старте приложение читает status.json (по умолчанию — из этого репо через
GitHub Raw):
  enabled=false        -> приложение отключено (kill-switch);
  min_version > текущей -> требуется обновление (старые версии не запускаются).
Сетевые/парс-ошибки НЕ блокируют (fail-open), чтобы сбои сети не ломали работу.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .. import __version__

DEFAULT_STATUS_URL = (
    "https://raw.githubusercontent.com/kovanZ1/deletebackground/main/status.json"
)
RELEASES_URL = "https://github.com/kovanZ1/deletebackground/releases/latest"


@dataclass
class GateDecision:
    allowed: bool
    message: str = ""
    kind: str = "ok"          # ok | disabled | update


def status_url() -> str:
    return os.environ.get("CASECUT_STATUS_URL", DEFAULT_STATUS_URL)


def _vtuple(v) -> tuple:
    out = []
    for p in str(v).split("."):
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    return tuple(out)


def evaluate_status(data, current_version: str) -> GateDecision:
    """Чистая логика решения (тестируется без сети)."""
    if not isinstance(data, dict):
        return GateDecision(True)
    if data.get("enabled", True) is False:
        return GateDecision(
            False,
            data.get("message") or "Приложение отключено администратором.",
            "disabled",
        )
    mv = data.get("min_version")
    if mv and _vtuple(current_version) < _vtuple(mv):
        return GateDecision(
            False,
            data.get("update_message")
            or f"Доступна новая версия. Установите обновление (минимум {mv}).",
            "update",
        )
    return GateDecision(True)


def _default_fetch(url: str, timeout: float) -> str:
    import urllib.request
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310
        return r.read().decode("utf-8")


def check_remote(url: str | None = None, current_version: str | None = None,
                 timeout: float = 5.0, fetch=None) -> GateDecision:
    """Сходить за флагом и решить. При любой сетевой/парс-ошибке -> разрешено."""
    url = url or status_url()
    current_version = current_version or __version__
    fetch = fetch or _default_fetch
    try:
        raw = fetch(url, timeout)
        data = json.loads(raw)
    except Exception:  # noqa: BLE001 — fail-open
        return GateDecision(True)
    return evaluate_status(data, current_version)
