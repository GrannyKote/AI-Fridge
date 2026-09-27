"""Видеокарта, если она видна процессу. Иначе процессор."""

from __future__ import annotations


def cuda_available() -> bool:
    """Проверка наличия CUDA на устройстве для расчета"""
    try:
        import torch
    except ImportError:
        return False
    return bool(torch.cuda.is_available())
