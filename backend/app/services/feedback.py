from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Feedback, FeedbackPhoto, User

MAX_FEEDBACK_PHOTOS = 5
MAX_PHOTO_BYTES = 8 * 1024 * 1024


def ensure_photo_count(count: int) -> None:
    if count > MAX_FEEDBACK_PHOTOS:
        raise ValueError("Можно приложить не больше пяти фото")


def save_feedback(
    session: Session,
    user_id: int,
    message: str,
    photos: list[tuple[bytes, str]],
) -> Feedback | None:
    ensure_photo_count(len(photos))
    if session.get(User, user_id) is None:
        return None

    row = Feedback(
        id_user=user_id,
        message=message,
        date_time=datetime.now(timezone.utc),
    )
    session.add(row)
    session.flush()
    for content, content_type in photos:
        session.add(
            FeedbackPhoto(
                id_feedback=row.id,
                content=content,
                content_type=content_type,
            )
        )
    session.commit()
    return row


def list_for_admin(session: Session, admin_id: int) -> list[dict] | None:
    admin = session.get(User, admin_id)
    if admin is None or admin.user_type != "admin":
        return None

    rows = session.execute(
        select(Feedback, User.login)
        .join(User, User.id == Feedback.id_user)
        .order_by(Feedback.date_time.desc(), Feedback.id.desc())
    ).all()
    photo_rows = session.execute(
        select(FeedbackPhoto.id, FeedbackPhoto.id_feedback).order_by(FeedbackPhoto.id)
    ).all()
    photos_by_feedback: dict[int, list[int]] = {}
    for photo_id, feedback_id in photo_rows:
        photos_by_feedback.setdefault(feedback_id, []).append(photo_id)

    return [
        {
            "id": row.id,
            "login": login,
            "message": row.message,
            "date_time": row.date_time,
            "photos": [{"id": photo_id} for photo_id in photos_by_feedback.get(row.id, [])],
        }
        for row, login in rows
    ]


def get_photo(session: Session, feedback_id: int, photo_id: int) -> FeedbackPhoto | None:
    photo = session.get(FeedbackPhoto, photo_id)
    if photo is None or photo.id_feedback != feedback_id:
        return None
    return photo
