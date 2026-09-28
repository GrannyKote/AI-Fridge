"""HTTP для кнопок «Чек» и «Голос». Кладовую не меняет."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from receipts.llm import warm as warm_llm
from receipts.normalize import normalize_lines
from receipts.payload import to_payload
from receipts.photo import read_lines as read_photo
from receipts.photo import warm as warm_photo
from receipts.store import DatabaseUnavailable, save_receipt
from receipts.voice import read_lines as read_voice
from receipts.voice import warm as warm_voice


@asynccontextmanager
async def lifespan(_app: FastAPI):
    warm_photo()
    warm_voice()
    warm_llm()
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
    return {"status": "ok"}


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

    items = normalize_lines(lines)
    payload = to_payload(items)
    try:
        payload["receipt_id"] = save_receipt(group_id, source, "\n".join(lines), items)
    except DatabaseUnavailable:
        payload["receipt_id"] = None
    return payload
