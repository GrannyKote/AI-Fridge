"""Шаг 1. Фото чека -> сырые строки. Модель одна на процесс."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

# Только русские буквы и знаки чека. Латиница вроде «g» вместо «д» отсекается.
_ALLOW = (
    "0123456789"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    " .,:%/\\-№\"'«»"
)

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

    prepared = _prepare(image)
    detections = _get_reader().readtext(
        prepared,
        detail=1,
        decoder="beamsearch",
        beamWidth=5,
        allowlist=_ALLOW,
        contrast_ths=0.05,
        adjust_contrast=0.7,
        mag_ratio=1.5,
        text_threshold=0.6,
        low_text=0.3,
    )
    return _group_lines(detections)


def _get_reader():
    global _reader
    if _reader is not None:
        return _reader
    with _lock:
        if _reader is None:
            _reader = _load_reader()
    return _reader


def _prepare(path: Path):
    """Поворот по снимку телефона, размер под чек и усиление бледного термотекста."""
    import cv2
    import numpy as np
    from PIL import Image, ImageOps

    rgb = np.array(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    long_side = max(height, width)
    if long_side > 2000:
        scale = 2000 / long_side
        interpolation = cv2.INTER_AREA
    elif long_side < 1200:
        scale = 1200 / long_side
        interpolation = cv2.INTER_CUBIC
    else:
        scale = 1
        interpolation = cv2.INTER_AREA
    if scale != 1:
        gray = cv2.resize(
            gray,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=interpolation,
        )
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)


def _group_lines(detections, min_confidence: float = 0.2) -> list[str]:
    """Склеивает слова одной строки чека слева направо."""
    words = []
    for box, text, confidence in detections:
        cleaned = text.strip()
        if confidence < min_confidence or not cleaned:
            continue
        ys = [point[1] for point in box]
        xs = [point[0] for point in box]
        top, bottom = min(ys), max(ys)
        words.append((top, bottom, min(xs), cleaned))

    words.sort(key=lambda item: item[0])
    rows: list[list] = []
    for top, bottom, left, text in words:
        if rows and _same_row(top, bottom, rows[-1][0], rows[-1][1]):
            rows[-1][2].append((left, text))
            continue
        rows.append([top, bottom, [(left, text)]])

    lines = []
    for _center, _height, parts in rows:
        parts.sort(key=lambda item: item[0])
        lines.append(" ".join(part for _left, part in parts))
    return lines


def _same_row(top: float, bottom: float, other_top: float, other_bottom: float) -> bool:
    overlap = min(bottom, other_bottom) - max(top, other_top)
    if overlap <= 0:
        return False
    return overlap >= 0.5 * min(bottom - top, other_bottom - other_top)


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
