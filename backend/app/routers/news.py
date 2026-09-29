from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..schemas import NewsIn, NewsOut, UploadStatsOut
from ..services import news as news_service
from ..services.stats import upload_stats

router = APIRouter(prefix="/api", tags=["news"])


@router.get("/admin/stats", response_model=UploadStatsOut)
def admin_stats(user_id: int, session: Session = Depends(get_session)) -> UploadStatsOut:
    stats = upload_stats(session, user_id)
    if stats is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    return stats


@router.get("/news", response_model=list[NewsOut])
def list_news(session: Session = Depends(get_session)) -> list[NewsOut]:
    return news_service.list_news(session)


@router.get("/news/unread", response_model=NewsOut | None)
def unread_news(user_id: int, session: Session = Depends(get_session)) -> NewsOut | None:
    return news_service.unread(session, user_id)


@router.post("/news", response_model=NewsOut, status_code=status.HTTP_201_CREATED)
def publish_news(payload: NewsIn, session: Session = Depends(get_session)) -> NewsOut:
    row = news_service.publish(session, payload.user_id, payload.title, payload.body)
    if row is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    return row


@router.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(news_id: int, user_id: int, session: Session = Depends(get_session)) -> None:
    removed = news_service.remove(session, user_id, news_id)
    if removed is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Новость не найдена")


@router.post("/news/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_news_read(user_id: int, session: Session = Depends(get_session)) -> None:
    news_service.mark_read(session, user_id)
