from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.config import settings


password_hash = PasswordHash.recommended()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def _create_token(
    data: dict,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    to_encode = data.copy()

    to_encode.update(
        {
            "exp": datetime.now(timezone.utc) + expires_delta,
            "type": token_type,
        }
    )

    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    return _create_token(
        data,
        ACCESS_TOKEN_TYPE,
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    return _create_token(
        data,
        REFRESH_TOKEN_TYPE,
        expires_delta
        or timedelta(days=settings.refresh_token_expire_days),
    )


def _decode_token(token: str, expected_type: str) -> dict:
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    # refresh-токеном нельзя пользоваться как access-токеном и наоборот
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Wrong token type")

    return payload


def decode_access_token(token: str) -> dict:
    return _decode_token(token, ACCESS_TOKEN_TYPE)


def decode_refresh_token(token: str) -> dict:
    return _decode_token(token, REFRESH_TOKEN_TYPE)
