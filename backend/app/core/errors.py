from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


# Имя ограничения в базе -> понятное сообщение для клиента
CONSTRAINT_MESSAGES = {
    "ix_users_email": "Email already registered",
    "ix_users_username": "Username already registered",
    "uq_program_days_program_id_order_index": (
        "A day with this order_index already exists in this program"
    ),
    "uq_program_exercises_program_day_id_order_index": (
        "An exercise with this order_index already exists in this day"
    ),
    "uq_workout_sets_workout_exercise_set_number": (
        "This set number is already logged for this exercise"
    ),
    "program_exercises_exercise_id_fkey": (
        "Exercise is used in programs and cannot be deleted"
    ),
}


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    """Нарушение ограничений базы превращаем в 409 вместо 500."""
    text = str(exc.orig)

    detail = "Conflict with existing data"

    for constraint_name, message in CONSTRAINT_MESSAGES.items():
        if constraint_name in text:
            detail = message
            break

    return JSONResponse(
        status_code=409,
        content={"detail": detail},
    )
