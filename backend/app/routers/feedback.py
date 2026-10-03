from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..dependencies import current_user_id
from ..schemas import FeedbackItemOut, FeedbackOut
from ..services import feedback as feedback_service

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(
    text: str = Form(min_length=1, max_length=4000),
    images: list[UploadFile] | None = File(default=None),
    session: Session = Depends(get_session),
    user_id: int = Depends(current_user_id),
) -> FeedbackOut:
    try:
        created, items = feedback_service.create_feedback(session, user_id, text, images)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    return FeedbackOut(
        id=created.id,
        id_user=created.id_user,
        datetime_created=created.datetime_created,
        feedback_text=created.feedback_text or "",
        items=[FeedbackItemOut(id=item.id) for item in items],
    )
