"""Один проход маленькой модели по строкам OCR. Вес один на процесс."""

from __future__ import annotations

import os
from pathlib import Path

_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
_llm = None


def model_path() -> Path | None:
    """Файл GGUF: переменная LLM_MODEL, образ /opt/llm или локальный кэш."""
    candidates = []
    if os.environ.get("LLM_MODEL"):
        candidates.append(Path(os.environ["LLM_MODEL"]))
    candidates.append(Path("/opt/llm") / _FILENAME)
    candidates.append(Path(__file__).resolve().parents[1] / ".model-cache" / "llm" / _FILENAME)
    for path in candidates:
        if path.is_file():
            return path
    return None


def enabled() -> bool:
    """В тестах модель выключена. В контейнере её включает LLM_MODEL или /opt/llm."""
    if os.environ.get("LLM_MODEL"):
        path = model_path()
        return path is not None
    return (Path("/opt/llm") / _FILENAME).is_file()


def warm() -> None:
    """Поднять модель в память, если она включена."""
    if enabled():
        _get()


def generate(prompt: str) -> str:
    """Ответ модели на один чек. Температура низкая: нужно стабильное JSON."""
    result = _get().create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты разбираешь строки чека после OCR. "
                    "Верни только JSON-массив. "
                    "Для покупки укажи i — номер строки и product — обычное название. "
                    "Цену, магазин и слова вроде «восстановленный» в product не включай. "
                    "Строку без покупки пропусти."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    return result["choices"][0]["message"]["content"]


def _get():
    global _llm
    if _llm is None:
        path = model_path()
        if path is None:
            raise FileNotFoundError("Нет файла модели LLM")
        from llama_cpp import Llama

        _llm = Llama(
            model_path=str(path),
            n_ctx=2048,
            n_threads=4,
            n_gpu_layers=0,
            verbose=False,
        )
    return _llm
