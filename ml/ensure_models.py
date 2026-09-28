"""Скачать веса в домашнюю папку, если их там ещё нет.

В образе это /root: каталоги .EasyOCR и .cache/huggingface.
Повторный запуск ничего не качает, файлы уже лежат в слое образа.
"""

from __future__ import annotations

import time
from pathlib import Path

_OCR = ("craft_mlt_25k.pth", "cyrillic_g2.pth")
_WHISPER = "models--Systran--faster-whisper-small"


def _ocr_dir() -> Path:
    return Path.home() / ".EasyOCR" / "model"


def _whisper_ready() -> bool:
    hub = Path.home() / ".cache" / "huggingface" / "hub" / _WHISPER
    return any((snapshot / "model.bin").is_file() for snapshot in hub.glob("snapshots/*"))


def ensure() -> None:
    missing_ocr = [name for name in _OCR if not (_ocr_dir() / name).is_file()]
    if missing_ocr:
        print(f"Качаю EasyOCR в {_ocr_dir()}: {', '.join(missing_ocr)}", flush=True)
        import easyocr

        easyocr.Reader(["ru", "en"], gpu=False)
    else:
        print(f"EasyOCR уже есть в {_ocr_dir()}", flush=True)

    if _whisper_ready():
        print("Whisper уже есть в", Path.home() / ".cache" / "huggingface", flush=True)
        return

    print("Качаю Whisper small в", Path.home() / ".cache" / "huggingface", flush=True)
    from faster_whisper import WhisperModel

    WhisperModel("small", device="cpu", compute_type="int8")


def _drop_partial_ocr() -> None:
    partial = _ocr_dir() / "temp.zip"
    partial.unlink(missing_ok=True)


if __name__ == "__main__":
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            ensure()
            raise SystemExit(0)
        except Exception as exc:
            last_error = exc
            _drop_partial_ocr()
            print(f"Попытка {attempt} не удалась: {exc}", flush=True)
            time.sleep(15)
    print(f"Веса не скачались: {last_error}", flush=True)
    raise SystemExit(1)
