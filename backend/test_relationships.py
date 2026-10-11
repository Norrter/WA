import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.session import AsyncSessionLocal
from app.models.program import Program
from app.models.program_day import ProgramDay
from app.models.program_exercise import ProgramExercise


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Program)
            .options(
                selectinload(Program.days)
                .selectinload(ProgramDay.exercises)
                .selectinload(ProgramExercise.exercise)
            )
            .where(Program.id == 1)
        )

        program = result.scalar_one()

        print("Программа:")
        print(f"  ID: {program.id}")
        print(f"  Название: {program.name}")

        print("\nДни программы:")

        for day in program.days:
            print(f"  {day.order_index}. {day.name}")

            for program_exercise in day.exercises:
                print(
                    f"      {program_exercise.order_index}. "
                    f"{program_exercise.exercise.name} — "
                    f"{program_exercise.sets} × "
                    f"{program_exercise.target_reps} — "
                    f"{program_exercise.target_weight} кг"
                )


if __name__ == "__main__":
    asyncio.run(main())