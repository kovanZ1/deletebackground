"""Пути к данным приложения в ПИСЕМОЙ пользовательской папке.

Нельзя писать рядом с .exe (Program Files требует админа) — храним маски в
%LOCALAPPDATA%\\CaseCutoutTool (Windows) / ~/Library/Application Support (macOS).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "CaseCutoutTool"


def user_data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / APP_NAME


def devices_dir() -> Path:
    return user_data_dir() / "devices"
