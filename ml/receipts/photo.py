"""Фото чека -> список строк. Модель грузится только в момент вызова."""

from __future__ import annotations

from pathlib import Path


def read_lines(path: str | Path) -> list[str]:
    """Получаем путь к файлу
    Считываем строки. Возвращаем список строк."""
    image = Path(path)
    if not image.is_file():
        raise FileNotFoundError(f"Файл фото не найден: {image}")

    import easyocr

    from receipts.device import cuda_available

    gpu = cuda_available()
    try:
        reader = easyocr.Reader(["ru", "en"], gpu=gpu)
    except Exception:
        if not gpu:
            raise
        reader = easyocr.Reader(["ru", "en"], gpu=False)
    lines = reader.readtext(str(image), detail=0)
    return [line.strip() for line in lines if line and line.strip()]
