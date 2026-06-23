"""Удалённое управление доступом: kill-switch + принудительное обновление."""

from .gate import (
    GateDecision,
    evaluate_status,
    check_remote,
    status_url,
    DEFAULT_STATUS_URL,
    RELEASES_URL,
)

__all__ = [
    "GateDecision",
    "evaluate_status",
    "check_remote",
    "status_url",
    "DEFAULT_STATUS_URL",
    "RELEASES_URL",
]
