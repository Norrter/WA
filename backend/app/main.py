from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.coach import router as coach_router
from app.api.coaching import router as coaching_router
from app.api.exercises import router as exercises_router
from app.api.program_days import router as program_days_router
from app.api.program_exercises import router as program_exercises_router
from app.api.programs import router as programs_router
from app.api.progress import router as progress_router
from app.api.scheduled_workouts import router as scheduled_workouts_router
from app.api.users import router as users_router
from app.api.workout_sets import router as workout_sets_router
from app.config import settings
from app.core.errors import integrity_error_handler
from app.core.roles import sync_coach_roles
from app.database.session import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Роли тренеров берутся из COACH_EMAILS
    async with AsyncSessionLocal() as session:
        await sync_coach_roles(session)

    yield


app = FastAPI(title="Workout App API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(IntegrityError, integrity_error_handler)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(programs_router)
app.include_router(program_days_router)
app.include_router(program_exercises_router)
# progress раньше exercises: у них общий префикс /exercises
app.include_router(progress_router)
app.include_router(exercises_router)
app.include_router(scheduled_workouts_router)
app.include_router(workout_sets_router)
app.include_router(coach_router)
app.include_router(coaching_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": result.scalar() == 1,
    }
