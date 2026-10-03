"""Сохранение отзывов и приложенных картинок."""

from datetime import datetime

from sqlalchemy.orm import Session

from ..models import Feedback, FeedbackItem

MAX_IMAGES = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_TEXT_LENGTH = 4000
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
