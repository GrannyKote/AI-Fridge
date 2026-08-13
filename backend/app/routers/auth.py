from fastapi import APIRouter, Depends, HTTPException, status
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


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> UserOut:
    if users.find_by_login(session, payload.login) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Такой логин уже занят")

    user, group = users.create_with_group(session, payload.login, payload.password)
    return _to_out(user, [group])


@router.post("/login", response_model=UserOut)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> UserOut:
    user = users.find_by_login(session, payload.login)

    # Пароли хранятся в открытом виде — сравниваем как есть.
    if user is None or user.password != payload.password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")

    return _to_out(user, users.list_groups(session, user.id))
