"""Голос -> список фраз. Модель грузится только в момент вызова."""

from __future__ import annotations

import re
from pathlib import Path

# Запятая и точка внутри числа не режут фразу: «1,5» и «2.5» остаются целиком.
_SPLIT_RE = re.compile(r"(?<!\d),(?!\d)|(?<!\d)\.(?!\d)|\s+и\s+", re.IGNORECASE)


def split_phrases(text: str) -> list[str]:
    parts = _SPLIT_RE.split(text)
    return [part.strip() for part in parts if part.strip()]


def read_lines(path: str | Path) -> list[str]:
    audio = Path(path)
    if not audio.is_file():
        raise FileNotFoundError(f"Файл аудио не найден: {audio}")

    from faster_whisper import WhisperModel

    from receipts.device import cuda_available

    if cuda_available():
        try:
            model = WhisperModel("small", device="cuda", compute_type="float16")
        except Exception:
            model = WhisperModel("small", device="cpu", compute_type="int8")
    else:
        model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(audio), language="ru")
    text = " ".join(segment.text.strip() for segment in segments)
    return split_phrases(text)
