from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_session
from ..dependencies import current_admin_id
from ..schemas import (
    AdminFeedbackDetailOut,
    AdminFeedbackListItemOut,
    AdminFeedbackReplyCreate,
    AdminFeedbackReplyOut,
    AdminNewsListItemOut,
    AdminNewsOut,
    AdminNewsUpdate,
    AdminNewsViewerOut,
    AdminUserListItemOut,
    AdminUserPasswordUpdate,
)
from ..services import feedback as feedback_service
from ..services import news as news_service
from ..services import users as users_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserListItemOut])
def list_users(
    session: Session = Depends(get_session),
    _: int = Depends(current_admin_id),
) -> list[AdminUserListItemOut]:
    return [AdminUserListItemOut(**row) for row in users_service.list_for_admin(session)]


@router.patch("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def update_user_password(
    user_id: int,
    payload: AdminUserPasswordUpdate,
    session: Session = Depends(get_session),
    _: int = Depends(current_admin_id),
) -> None:
    if users_service.set_password(session, user_id, payload.password) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")


@router.get("/feedback", response_model=list[AdminFeedbackListItemOut])
def list_feedback(
    session: Session = Depends(get_session),
    _: int = Depends(current_admin_id),
) -> list[AdminFeedbackListItemOut]:
    return [AdminFeedbackListItemOut(**row) for row in feedback_service.list_for_admin(session)]


@router.get("/feedback/{feedback_id}", response_model=AdminFeedbackDetailOut)
def get_feedback(
    feedback_id: int,
    session: Session = Depends(get_session),
    _: int = Depends(current_admin_id),
) -> AdminFeedbackDetailOut:
    row = feedback_service.get_for_admin(session, feedback_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Отзыв не найден")
    return AdminFeedbackDetailOut(**row)


@router.get("/feedback/{feedback_id}/items/{item_id}")
def get_feedback_item(
    feedback_id: int,
    item_id: int,
    session: Session = Depends(get_session),
    _: int = Depends(current_admin_id),
    download: bool = Query(default=False),
) -> Response:
    row = feedback_service.get_item_for_admin(session, feedback_id, item_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Изображение не найдено")

    data, media_type, extension = row
    disposition = "attachment" if download else "inline"
    filename = f"feedback-{feedback_id}-{item_id}.{extension}"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


@router.post(
    "/feedback/{feedback_id}/reply",
    response_model=AdminFeedbackReplyOut,
    status_code=status.HTTP_201_CREATED,
)
def reply_to_feedback(
    feedback_id: int,
    payload: AdminFeedbackReplyCreate,
    session: Session = Depends(get_session),
    admin_id: int = Depends(current_admin_id),
) -> AdminFeedbackReplyOut:
    try:
        reply = feedback_service.create_reply(
            session,
            admin_id,
            feedback_id,
            payload.header,
            payload.body,
        )
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    if reply is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Отзыв не найден")
    return AdminFeedbackReplyOut(id=reply.id)


def _to_out(item) -> AdminNewsOut:
    return AdminNewsOut(id=item.id, header=item.header, body=item.body or "")


@router.post("/news", response_model=AdminNewsOut, status_code=status.HTTP_201_CREATED)
def create_news(
    payload: AdminNewsUpdate,
    session: Session = Depends(get_session),
    admin_id: int = Depends(current_admin_id),
) -> AdminNewsOut:
    item = news_service.create_news(session, admin_id, payload.header, payload.body)
    return _to_out(item)


@router.get("/news", response_model=list[AdminNewsListItemOut])
def list_news(
    session: Session = Depends(get_session),
    _: int = Depends(current_admin_id),
) -> list[AdminNewsListItemOut]:
    return [
        AdminNewsListItemOut(id=item.id, header=item.header)
        for item in news_service.list_all(session)
    ]


@router.get("/news/{news_id}/seen", response_model=list[AdminNewsViewerOut])
def list_news_viewers(
    news_id: int,
    session: Session = Depends(get_session),
    _: int = Depends(current_admin_id),
) -> list[AdminNewsViewerOut]:
    rows = news_service.list_news_viewers(session, news_id)
    if rows is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Новость не найдена")
    return [AdminNewsViewerOut(**row) for row in rows]


@router.get("/news/{news_id}", response_model=AdminNewsOut)
def get_news(
    news_id: int,
    session: Session = Depends(get_session),
    _: int = Depends(current_admin_id),
) -> AdminNewsOut:
    item = news_service.get_news(session, news_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Новость не найдена")
    return _to_out(item)


@router.patch("/news/{news_id}", response_model=AdminNewsOut)
def update_news(
    news_id: int,
    payload: AdminNewsUpdate,
    session: Session = Depends(get_session),
    admin_id: int = Depends(current_admin_id),
) -> AdminNewsOut:
    item = news_service.update_news(
        session,
        admin_id,
        news_id,
        payload.header,
        payload.body,
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Новость не найдена")
    return _to_out(item)


@router.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(
    news_id: int,
    session: Session = Depends(get_session),
    admin_id: int = Depends(current_admin_id),
) -> None:
    if not news_service.delete_news(session, admin_id, news_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Новость не найдена")
