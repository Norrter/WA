// Переход по ссылке из письма: #/verify-email/<токен>

import { useEffect, useState } from "react";

import { auth } from "../api";
import { useAuth } from "../components/Auth";
import { Icon } from "../components/Icon";
import { useScene } from "../components/Scene";
import { ThemeToggle } from "../components/ThemeSwitch";

type State =
  | { kind: "checking" }
  | { kind: "done"; email: string }
  | { kind: "error"; message: string };

export function VerifyEmailPage({ token }: { token: string }) {
  useScene("colonnade");

  const { user, setUser } = useAuth();
  const [state, setState] = useState<State>({ kind: "checking" });

  useEffect(() => {
    let cancelled = false;

    auth
      .verifyEmail(token)
      .then(async (result) => {
        if (cancelled) return;
        setState({ kind: "done", email: result.email });
        // Если человек уже вошёл — обновляем профиль, чтобы пропала плашка
        if (user) setUser(await auth.me());
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState({
          kind: "error",
          message: error instanceof Error ? error.message : "Не удалось подтвердить почту",
        });
      });

    return () => {
      cancelled = true;
    };
    // проверяем ссылку один раз
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <main className="auth verify-page">
      <header className="auth-head">
        <div className="auth-top">
          <a className="auth-back" href="#/">
            ← На главную
          </a>
          <ThemeToggle />
        </div>
        <p className="eyebrow">Подтверждение почты</p>
      </header>

      <section className="verify-card" aria-live="polite">
        {state.kind === "checking" && (
          <>
            <span className="verify-icon" aria-hidden="true">
              <Icon name="timer" size={30} />
            </span>
            <h1 className="verify-title">Проверяем ссылку…</h1>
          </>
        )}

        {state.kind === "done" && (
          <>
            <span className="verify-icon is-done" aria-hidden="true">
              <Icon name="check" size={30} strokeWidth={2.4} />
            </span>
            <h1 className="verify-title">Почта подтверждена</h1>
            <p className="verify-text">
              Адрес <strong>{state.email}</strong> подтверждён. Теперь на него будут приходить
              письма от Greek's Gym.
            </p>
            <a className="btn btn-primary btn-block" href={user ? "#/" : "#/login"}>
              {user ? "Перейти в приложение" : "Войти"}
            </a>
          </>
        )}

        {state.kind === "error" && (
          <>
            <span className="verify-icon is-error" aria-hidden="true">
              <Icon name="close" size={30} strokeWidth={2.2} />
            </span>
            <h1 className="verify-title">Не получилось</h1>
            <p className="verify-text">{state.message}</p>
            <a className="btn btn-primary btn-block" href={user ? "#/" : "#/login"}>
              {user ? "Перейти в приложение" : "Войти и отправить снова"}
            </a>
          </>
        )}
      </section>
    </main>
  );
}
