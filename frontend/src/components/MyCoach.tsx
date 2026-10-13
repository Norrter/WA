// Тренер глазами клиента: текущий тренер

import { useState } from "react";

import { coaching } from "../api";
import type { CoachingState } from "../api/types";
import { formatDay } from "../lib/dates";
import { useAsync } from "../lib/useAsync";
import { useToast } from "./Toast";
import { Button, useConfirm } from "./ui";

// Раздел в профиле: текущий тренер
export function CoachingSection() {
  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();
  const state = useAsync(() => coaching.state(), []);
  const [busy, setBusy] = useState(false);

  const run = async (action: () => Promise<CoachingState>, message: string) => {
    setBusy(true);

    try {
      state.setData(await action());
      toast.success(message);
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(false);
    }
  };

  if (!state.data) return null;

  const { coach } = state.data;

  const end = async () => {
    if (!coach) return;

    const agreed = await confirm(
      `${coach.coach.username} перестанет видеть ваши тренировки. Ваша история тренировок останется у вас.`,
      "Завершить",
    );

    if (agreed) {
      await run(coaching.end, "Сотрудничество завершено");
    }
  };

  return (
    <section className="block coaching" id="coach" aria-labelledby="coaching-title">
      <h2 className="block-title" id="coaching-title">Тренер</h2>

      {coach ? (
        <div className="coaching-current">
          <p>
            Ваш тренер — <strong>{coach.coach.username}</strong>
            <span className="muted"> ({coach.coach.email})</span>
            {coach.since && <span className="muted">, с {formatDay(coach.since.slice(0, 10))}</span>}.
          </p>
          <p className="muted small">
            Тренер видит ваши тренировки, подходы и рекорды. Менять их он не может.
          </p>
          <Button variant="danger" busy={busy} onClick={() => void end()}>
            Завершить сотрудничество
          </Button>
        </div>
      ) : (
        <p className="muted">
          Тренера пока нет. Тренер может добавить вас своим клиентом по email — тогда он появится здесь.
        </p>
      )}

      {confirmDialog}
    </section>
  );
}
