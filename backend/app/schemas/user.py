from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.schemas.common import PatchModel


Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=100),
]

Password = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128),
]


class UserCreate(BaseModel):
    email: EmailStr
    username: Username
    password: Password
    # галочка «Даю согласие на обработку персональных данных» (152-ФЗ)
    consent: bool = False


class UserPatch(PatchModel):
    not_nullable = frozenset({"email", "username"})

    email: EmailStr | None = None
    username: Username | None = None
    # вес тела, кг; null — не указан
    body_weight: Annotated[float, Field(ge=20, le=400)] | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: Password


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    role: str
    body_weight: float | None = None
    # администратор: видит админ-панель (ADMIN_EMAILS)
    is_admin: bool = False
    # почта подтверждена по ссылке из письма
    email_verified: bool = False
    # тренировки и питание недоступны, пока почта не подтверждена
    diary_locked: bool = False
    created_at: datetime
    updated_at: datetime
