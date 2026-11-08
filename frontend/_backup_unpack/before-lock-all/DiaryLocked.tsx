// Экран вместо тренировки и питания, пока почта не подтверждена

import { useState } from "react";

import { auth } from "../api";
import { useAuth, useUser } from "./Auth";
import { Icon } from "./Icon";
import { useToast } from "./Toast";
import { Button } from "./ui";

const TEXT = {
  workout: {
    title: "Подтвердите почту, чтобы записывать тренировки",
    text: "Подходы, веса и отметки о тренировках сохраняются только после подтверждения почты. "
      + "Программы и расписание можно смотреть уже сейчас.",
  },
  nutrition: {
    title: "Подтвердите почту, чтобы вести питание",
    text: "Дневник еды и норма КБЖУ откроются сразу после подтверждения почты.",
  },
};

export function DiaryLocked({ kind }: { kind: "workout" | "nutrition" }) {
  const user = useUser();
  const { setUser } = useAuth();
  const toast = useToast();
  const [busy, setBusy] = useState<"send" | "check" | null>(null);

  const resend = async () => {
    setBusy("send");
    try {
      await auth.resendVerification();
      toast.success(`Письмо отправлено на ${user.email}`);
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(null);
    }
  };

  // Подтвердил в почте на другом устройстве — проверяем без перезагрузки
  const check = async () => {
    setBusy("check");
    try {
      const fresh = await auth.me();
      setUser(fresh);
      if (fresh.diary_locked) toast.error(new Error("Почта ещё не подтверждена"));
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(null);
    }
  };

  const { title, text } = TEXT[kind];

  return (
    <div className="page">
      <section className="diary-locked">
        <span className="diary-locked-icon" aria-hidden="true">
          <Icon name="send" size={28} />
        </span>
        <h1 className="diary-locked-title">{title}</h1>
        <p className="diary-locked-text">{text}</p>
        <p className="diary-locked-text">
          Ссылка отправлена на <strong>{user.email}</strong>. Если письма нет — загляните в «Спам».
        </p>
        <div className="diary-locked-actions">
          <Button variant="primary" busy={busy === "send"} onClick={resend}>
            Отправить письмо ещё раз
          </Button>
          <Button busy={busy === "check"} onClick={check}>
            Я подтвердил
          </Button>
        </div>
        <a className="link-quiet" href="#/profile">Ошиблись в адресе? Поменяйте его в профиле</a>
      </section>
    </div>
  );
}
