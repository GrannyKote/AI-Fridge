"""Сохранение отзывов и приложенных картинок."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Feedback, FeedbackItem, PersonalNews, User

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TEXT_LENGTH = 4000
PREVIEW_LENGTH = 120


def _mime_for_image(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _extension_for_mime(media_type: str) -> str:
    return {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
    }.get(media_type, "bin")


def _text_preview(text: str | None, limit: int = PREVIEW_LENGTH) -> str:
    message = (text or "").strip()
    if len(message) <= limit:
        return message
    return f"{message[:limit].rstrip()}…"
ALLOWED_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}


def _read_images(uploads) -> list[bytes]:
    images: list[bytes] = []

    for upload in uploads or []:
        file_name = (upload.filename or "").strip()
        if not file_name:
            continue

        content_type = (upload.content_type or "").lower().split(";", 1)[0]
        if content_type not in ALLOWED_TYPES:
            raise ValueError("Можно прикладывать только изображения")

        content = upload.file.read()
        if not content:
            continue
        if len(content) > MAX_IMAGE_BYTES:
            raise ValueError("Каждая картинка должна быть не больше 5 МБ")

        images.append(content)

    if len(images) > MAX_IMAGES:
        raise ValueError("Можно приложить не больше трёх картинок")

    return images


def create_feedback(session: Session, user_id: int, text: str, uploads) -> tuple[Feedback, list[FeedbackItem]]:
    message = (text or "").strip()
    if not message:
        raise ValueError("Введите текст отзыва")
    if len(message) > MAX_TEXT_LENGTH:
        raise ValueError("Текст отзыва слишком длинный")

    images = _read_images(uploads)

    feedback = Feedback(
        id_user=user_id,
        datetime_created=datetime.now(),
        feedback_text=message,
        is_seen=False,
    )
    session.add(feedback)
    session.flush()

    items: list[FeedbackItem] = []
    for content in images:
        item = FeedbackItem(id_feedback=feedback.id, item=content)
        session.add(item)
        items.append(item)

    session.commit()
    session.refresh(feedback)
    for item in items:
        session.refresh(item)

    return feedback, items


def list_for_admin(session: Session) -> list[dict]:
    statement = (
        select(Feedback, User.login)
        .join(User, User.id == Feedback.id_user)
        .order_by(Feedback.datetime_created.desc(), Feedback.id.desc())
    )
    return [
        {
            "id": feedback.id,
            "login": login,
            "datetime_created": feedback.datetime_created,
            "text_preview": _text_preview(feedback.feedback_text),
            "is_seen": feedback.is_seen is True,
        }
        for feedback, login in session.execute(statement)
    ]


def _mark_seen(session: Session, feedback: Feedback) -> None:
    if feedback.is_seen is True:
        return
    feedback.is_seen = True
    feedback.datetime_seen = datetime.now(timezone.utc)
    session.commit()


def get_for_admin(session: Session, feedback_id: int) -> dict | None:
    statement = (
        select(Feedback, User.login)
        .join(User, User.id == Feedback.id_user)
        .where(Feedback.id == feedback_id)
    )
    row = session.execute(statement).first()
    if row is None:
        return None

    feedback, login = row
    _mark_seen(session, feedback)
    session.refresh(feedback)

    items = session.scalars(
        select(FeedbackItem)
        .where(FeedbackItem.id_feedback == feedback.id)
        .order_by(FeedbackItem.id)
    ).all()

    return {
        "id": feedback.id,
        "login": login,
        "datetime_created": feedback.datetime_created,
        "feedback_text": feedback.feedback_text or "",
        "is_seen": feedback.is_seen is True,
        "datetime_seen": feedback.datetime_seen,
        "items": [{"id": item.id} for item in items],
    }


def create_reply(
    session: Session,
    admin_id: int,
    feedback_id: int,
    header: str,
    body: str,
) -> PersonalNews | None:
    feedback = session.get(Feedback, feedback_id)
    if feedback is None:
        return None

    reply_header = header.strip()
    if not reply_header:
        raise ValueError("Введите заголовок ответа")

    reply = PersonalNews(
        id_user=feedback.id_user,
        id_feedback=feedback.id,
        id_user_created=admin_id,
        datetime_created=datetime.now(timezone.utc),
        header=reply_header,
        body=(body or "").strip() or None,
        datetime_seen=None,
    )
    session.add(reply)
    session.commit()
    session.refresh(reply)
    return reply


def get_item_for_admin(
    session: Session,
    feedback_id: int,
    item_id: int,
) -> tuple[bytes, str, str] | None:
    item = session.scalar(
        select(FeedbackItem).where(
            FeedbackItem.id == item_id,
            FeedbackItem.id_feedback == feedback_id,
        )
    )
    if item is None:
        return None

    media_type = _mime_for_image(item.item)
    extension = _extension_for_mime(media_type)
    return item.item, media_type, extension
