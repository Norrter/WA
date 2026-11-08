from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database.session import get_session
from app.models.user import User, UserRole


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = await session.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_coach(
    current_user: User = Depends(get_current_user),
) -> User:
    """Пускает только тренеров."""
    if current_user.role != UserRole.coach.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coach access required",
        )

    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Пускает только администраторов (ADMIN_EMAILS)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


# Запросы, которые ничего не записывают: их пропускаем и с закрытым дневником
READ_METHODS = {"GET", "HEAD", "OPTIONS"}


optional_security = HTTPBearer(auto_error=False)


async def require_open_diary(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Пока почта не подтверждена (у новых аккаунтов), менять ничего нельзя:
    ни тренировки, ни питание, ни программы. Смотреть (GET) — можно."""
    if request.method in READ_METHODS:
        return

    # Расчёт нормы КБЖУ ничего не сохраняет
    if request.url.path.endswith("/nutrition/calculate"):
        return

    # Без токена ответит сама ручка (401)
    if credentials is None:
        return

    current_user = await get_current_user(credentials, session)

    if current_user.diary_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Confirm your email to use the diary",
        )
