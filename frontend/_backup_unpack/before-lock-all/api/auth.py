import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_email_token,
    decode_refresh_token,
    verify_password,
)
from app.database.session import get_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.schemas.user import UserResponse
from app.services.emails import send_verification


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


def build_tokens(user: User) -> dict:
    data = {"sub": str(user.id)}

    return {
        "access_token": create_access_token(data),
        "refresh_token": create_refresh_token(data),
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(User).where(User.email == data.email)
    )

    user = result.scalar_one_or_none()

    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return build_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Обменять refresh-токен на новую пару токенов."""
    try:
        payload = decode_refresh_token(data.refresh_token)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return build_tokens(user)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


# ----- Подтверждение почты -----

# Повторное письмо — не чаще раза в минуту на человека
RESEND_INTERVAL = 60
_last_resend: dict[int, float] = {}


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email(
    data: VerifyEmailRequest,
    session: AsyncSession = Depends(get_session),
):
    """Ссылка из письма. Вход не нужен: письмо могут открыть на другом устройстве."""
    try:
        payload = decode_email_token(data.token)
        user_id = int(payload["sub"])
        email = str(payload["email"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired",
        )

    user = await session.get(User, user_id)

    # После смены почты старая ссылка уже не подходит
    if user is None or user.email.lower() != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or expired",
        )

    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        await session.commit()

    return {"email": user.email, "email_verified": True}


@router.post("/verify-email/resend", status_code=status.HTTP_204_NO_CONTENT)
async def resend_verification(
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Отправить письмо со ссылкой ещё раз."""
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    now = time.monotonic()
    last = _last_resend.get(current_user.id)

    if last is not None and now - last < RESEND_INTERVAL:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait a minute before requesting another email",
        )

    _last_resend[current_user.id] = now
    background.add_task(
        send_verification, current_user.id, current_user.username, current_user.email
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
