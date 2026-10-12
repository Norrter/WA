from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import apply_changes
from app.core.dependencies import get_current_user
from app.core.roles import role_for_email
from app.core.security import hash_password, verify_password
from app.database.session import get_session
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    UserCreate,
    UserPatch,
    UserResponse,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


async def ensure_email_and_username_free(
    session: AsyncSession,
    email: str | None,
    username: str | None,
    exclude_user_id: int | None = None,
) -> None:
    if email is not None:
        query = select(User.id).where(User.email == email)

        if exclude_user_id is not None:
            query = query.where(User.id != exclude_user_id)

        if await session.scalar(query) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

    if username is not None:
        query = select(User.id).where(User.username == username)

        if exclude_user_id is not None:
            query = query.where(User.id != exclude_user_id)

        if await session.scalar(query) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    await ensure_email_and_username_free(
        session,
        data.email,
        data.username,
    )

    user = User(
        email=data.email,
        username=data.username,
        password_hash=hash_password(data.password),
        role=role_for_email(data.email),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserPatch,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Изменить свой email и/или имя пользователя."""
    await ensure_email_and_username_free(
        session,
        data.email,
        data.username,
        exclude_user_id=current_user.id,
    )

    apply_changes(current_user, data, partial=True)

    # Роль тренера привязана к email
    current_user.role = role_for_email(current_user.email)

    await session.commit()
    await session.refresh(current_user)

    return current_user


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_password(
    data: PasswordChange,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(
        data.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(data.new_password)

    await session.commit()


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_me(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Удалить аккаунт вместе со всеми программами и тренировками."""
    await session.delete(current_user)
    await session.commit()
