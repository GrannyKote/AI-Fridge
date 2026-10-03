from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..dependencies import current_user_id
from ..schemas import NewsListItemOut, NewsOut
from ..services import news as news_service

router = APIRouter(prefix="/api", tags=["news"])


def _to_news(item, seen: bool) -> NewsOut:
    return NewsOut(
        id=item.id,
        header=item.header,
        body=item.body or "",
        is_seen=seen,
    )


@router.get("/news", response_model=list[NewsListItemOut])
def list_news(
    session: Session = Depends(get_session),
    user_id: int = Depends(current_user_id),
) -> list[NewsListItemOut]:
    return [NewsListItemOut(**row) for row in news_service.list_news(session, user_id)]


@router.post("/news/{news_id}/seen", response_model=NewsOut)
def mark_news_seen(
    news_id: int,
    session: Session = Depends(get_session),
    user_id: int = Depends(current_user_id),
) -> NewsOut:
    item = news_service.mark_seen(session, user_id, news_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Новость не найдена")
    return _to_news(item, seen=True)
