"""Голос -> список фраз. Модель одна на процесс."""

from __future__ import annotations

import re
from pathlib import Path
from threading import Lock

# Запятая и точка внутри числа не режут фразу: «1,5» и «2.5» остаются целиком.
_SPLIT_RE = re.compile(r"(?<!\d),(?!\d)|(?<!\d)\.(?!\d)|\s+и\s+", re.IGNORECASE)
_model = None
_lock = Lock()


def warm() -> None:
    """Скачать веса, если их ещё нет, и поднять распознавание в память."""
    _get_model()


def split_phrases(text: str) -> list[str]:
    parts = _SPLIT_RE.split(text)
    return [part.strip() for part in parts if part.strip()]


def read_lines(path: str | Path) -> list[str]:
    audio = Path(path)
    if not audio.is_file():
        raise FileNotFoundError(f"Файл аудио не найден: {audio}")

    segments, _info = _get_model().transcribe(str(audio), language="ru")
    text = " ".join(segment.text.strip() for segment in segments)
    return split_phrases(text)


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is None:
            _model = _load_model()
    return _model


def _load_model():
    from faster_whisper import WhisperModel

    from receipts.device import cuda_available

    if cuda_available():
        try:
            return WhisperModel("small", device="cuda", compute_type="float16")
        except Exception:
            return WhisperModel("small", device="cpu", compute_type="int8")
    return WhisperModel("small", device="cpu", compute_type="int8")
