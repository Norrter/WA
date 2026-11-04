// Питание клиента у тренера — только просмотр: норма, дневник за день и неделя

import { useState } from "react";

import { coach } from "../api";
import { MEALS } from "../lib/nutrition";
import { today } from "../lib/dates";
import { useAsync } from "../lib/useAsync";
import { DaySwitch, DayTotals, MealBlock, NormSummary, WeekBlock } from "../pages/NutritionPage";
import { ErrorNote, Loading } from "./ui";

export function ClientNutrition({ clientId }: { clientId: number }) {
  const [date, setDate] = useState(today());
  const state = useAsync(() => coach.nutrition(clientId, date), [clientId, date]);

  return (
    <section className="block client-nutrition" aria-labelledby="client-nutrition-title">
      <h2 className="block-title" id="client-nutrition-title">Питание</h2>
      {state.error && <ErrorNote error={state.error} onRetry={() => void state.reload()} />}
      {!state.data && !state.error && <Loading />}
      {state.data && (
        <>
          {state.data.profile ? (
            <NormSummary profile={state.data.profile} />
          ) : (
            <p className="muted">Клиент ещё не рассчитал норму КБЖУ.</p>
          )}

          <div className="client-nutrition-day">
            <DaySwitch date={date} onChange={setDate} titleId="client-nutrition-day" />
            <DayTotals day={state.data.day} />
            {state.data.day.entries.length === 0 ? (
              <p className="muted client-nutrition-empty">За этот день записей нет.</p>
            ) : (
              <div className="meals">
                {MEALS.map((meal) => {
                  const entries = state.data!.day.entries.filter((entry) => entry.meal === meal.value);
                  return entries.length > 0 ? (
                    <MealBlock key={meal.value} label={meal.label} entries={entries} />
                  ) : null;
                })}
              </div>
            )}
          </div>

          <WeekBlock
            summary={state.data.week}
            end={date}
            target={state.data.day.targets?.kcal ?? null}
            idPrefix="client-nutrition"
          />
        </>
      )}
    </section>
  );
}
