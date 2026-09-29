from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..database import get_session
from ..schemas import FeedbackEntryOut, FeedbackIn, FeedbackOut
from ..services.feedback import (
    MAX_PHOTO_BYTES,
    ensure_photo_count,
    get_photo,
    list_for_admin,
    save_feedback,
)

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
async def send_feedback(
    user_id: int = Form(...),
    message: str = Form(...),
    photos: list[UploadFile] | None = File(None),
    session: Session = Depends(get_session),
) -> FeedbackOut:
    files = photos or []
    try:
        text = FeedbackIn(user_id=user_id, message=message).message
        ensure_photo_count(len(files))
    except ValidationError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, error.errors()[0]["msg"]) from error
    except ValueError as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    stored: list[tuple[bytes, str]] = []
    for item in files:
        if not item.content_type or not item.content_type.startswith("image/"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Можно приложить только фото")
        content = await item.read()
        if not content:
            continue
        if len(content) > MAX_PHOTO_BYTES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Фото слишком большое")
        stored.append((content, item.content_type))

    row = save_feedback(session, user_id, text, stored)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return FeedbackOut(status="отправлено")


@router.get("/feedback", response_model=list[FeedbackEntryOut])
def read_feedback(user_id: int, session: Session = Depends(get_session)) -> list[FeedbackEntryOut]:
    rows = list_for_admin(session, user_id)
    if rows is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    return [FeedbackEntryOut.model_validate(row) for row in rows]


@router.get("/feedback/{feedback_id}/photos/{photo_id}")
def read_photo(
    feedback_id: int,
    photo_id: int,
    session: Session = Depends(get_session),
) -> Response:
    photo = get_photo(session, feedback_id, photo_id)
    if photo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Фото не найдено")
    return Response(content=photo.content, media_type=photo.content_type)
