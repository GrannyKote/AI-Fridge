"""HTTP для кнопок «Чек» и «Голос». Кладовую не меняет."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

from receipts.llm import warm as warm_llm
from receipts.normalize import read_products
from receipts.payload import to_payload
from receipts.photo import read_lines as read_photo
from receipts.photo import warm as warm_photo
from receipts.store import DatabaseUnavailable, base_product_names, save_label, save_receipt
from receipts.voice import read_lines as read_voice
from receipts.voice import warm as warm_voice


@asynccontextmanager
async def lifespan(_app: FastAPI):
    warm_photo()
    warm_voice()
    warm_llm()
    base_product_names()
    yield


app = FastAPI(title="AI-Fridge receipts", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": os.environ.get("APP_VERSION", "MVP 0.0.1")}


class LineLabelIn(BaseModel):
    raw_line: str = Field(min_length=1)
    name: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=8)
    category: str | None = None


@app.post("/groups/{group_id}/labels", status_code=204)
def remember_label(group_id: int, payload: LineLabelIn) -> None:
    """Правка из ручной формы. group_id в пути тот же, что у чека; разметка общая."""
    del group_id
    try:
        save_label(
            payload.raw_line,
            payload.name,
            payload.quantity,
            payload.unit,
            payload.category,
        )
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/groups/{group_id}/ocr")
async def ocr(group_id: int, file: UploadFile = File(...)) -> dict:
    return await _recognize(group_id, "photo", file, ".jpg")


@app.post("/groups/{group_id}/asr")
async def asr(group_id: int, file: UploadFile = File(...)) -> dict:
    return await _recognize(group_id, "voice", file, ".wav")


async def _recognize(group_id: int, source: str, file: UploadFile, suffix: str) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Пустой файл")

    own_suffix = Path(file.filename or "").suffix or suffix
    with NamedTemporaryFile(suffix=own_suffix, delete=False) as temporary:
        temporary.write(data)
        path = temporary.name

    try:
        try:
            lines = read_photo(path) if source == "photo" else read_voice(path)
        except ImportError as exc:
            raise HTTPException(
                status_code=503,
                detail="Модель не установлена. В папке ml выполните: pip install -r requirements.txt",
            ) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        Path(path).unlink(missing_ok=True)

    items, skipped = read_products(lines)
    payload = to_payload(items, skipped)
    try:
        payload["receipt_id"] = save_receipt(group_id, source, "\n".join(lines), items)
    except DatabaseUnavailable:
        payload["receipt_id"] = None
    return payload
