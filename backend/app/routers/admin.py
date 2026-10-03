from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..dependencies import current_admin_id
from ..schemas import AdminNewsListItemOut, AdminNewsOut, AdminNewsUpdate, AdminNewsViewerOut
from ..services import news as news_service

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
