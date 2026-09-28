"""Фото чека -> список строк. Модель одна на процесс."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

_reader = None
_lock = Lock()


def warm() -> None:
    """Скачать веса, если их ещё нет, и поднять распознавание в память."""
    _get_reader()


def read_lines(path: str | Path) -> list[str]:
    """Получаем путь к файлу
    Считываем строки. Возвращаем список строк."""
    image = Path(path)
    if not image.is_file():
        raise FileNotFoundError(f"Файл фото не найден: {image}")

    lines = _get_reader().readtext(str(image), detail=0)
    return [line.strip() for line in lines if line and line.strip()]


def _get_reader():
    global _reader
    if _reader is not None:
        return _reader
    with _lock:
        if _reader is None:
            _reader = _load_reader()
    return _reader


def _load_reader():
    import easyocr

    from receipts.device import cuda_available

    gpu = cuda_available()
    try:
        return easyocr.Reader(["ru", "en"], gpu=gpu)
    except Exception:
        if not gpu:
            raise
        return easyocr.Reader(["ru", "en"], gpu=False)
