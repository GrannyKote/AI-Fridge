import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from .config import settings
from .database import get_session
from .routers import auth, pantry, shopping

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="AI-Fridge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(pantry.router)
app.include_router(shopping.router)


@app.exception_handler(OperationalError)
async def database_unavailable(_: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Database unavailable: %s", exc.orig or exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Нет соединения с базой данных"},
    )


@app.get("/api/health", tags=["service"])
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(text("select 1"))
    return {"status": "ok", "schema": settings.db_schema}
