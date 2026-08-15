from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_session
from ..schemas import GroupOut, LoginRequest, RegisterRequest, UserOut
from ..services import users

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_out(user, groups) -> UserOut:
    return UserOut(
        id=user.id,
        login=user.login,
        groups=[GroupOut.model_validate(group) for group in groups],
    )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return ""


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> UserOut:
    if users.find_by_login(session, payload.login) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Такой логин уже занят")

    user, group = users.create_with_group(
        session,
        payload.login,
        payload.password,
        user_agent=payload.user_agent or request.headers.get("user-agent", ""),
        ip=_client_ip(request),
    )
    return _to_out(user, [group])


@router.post("/login", response_model=UserOut)
def login(
    payload: LoginRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> UserOut:
    user = users.find_by_login(session, payload.login)
    user_agent = payload.user_agent or request.headers.get("user-agent", "")
    ip = _client_ip(request)

    # Пароли хранятся в открытом виде — сравниваем как есть.
    if user is None or user.password != payload.password:
        users.record_login_attempt(
            session,
            payload.login,
            is_success=False,
            user_agent=user_agent,
            ip=ip,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")

    users.record_login_attempt(
        session,
        payload.login,
        is_success=True,
        user_agent=user_agent,
        ip=ip,
    )
    return _to_out(user, users.list_groups(session, user.id))
