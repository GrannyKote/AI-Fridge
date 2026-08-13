from pydantic import BaseModel, ConfigDict, Field

LOGIN_PATTERN = r"^[a-zA-Z0-9._-]+$"


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=20, pattern=LOGIN_PATTERN)
    password: str = Field(min_length=6, max_length=256)


class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    login: str
    groups: list[GroupOut] = []
