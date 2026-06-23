"""Конвейер обработки: один кадр и пакетная обработка папки."""

from .processor import ProcessResult, process_image
from .batch import process_folder, make_substring_router, make_regex_router

__all__ = [
    "ProcessResult",
    "process_image",
    "process_folder",
    "make_substring_router",
    "make_regex_router",
]
