import { useState, type FormEvent } from "react";

import { useAuth } from "../components/Auth";
import { useScene } from "../components/Scene";
import { useToast } from "../components/Toast";
import { Button, Field } from "../components/ui";

export function LoginPage() {
  useScene("struggle");

  const { login, register } = useAuth();
  const toast = useToast();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, username, password);
      }
    } catch (error) {
      toast.error(error);
      setBusy(false);
    }
  };

  return (
    <main className="auth">
      <header className="auth-head">
        <p className="eyebrow">Журнал тренировок</p>
        <h1 className="auth-title">
          Greek's
          <br />
          Gym
        </h1>
        <p className="auth-lead">
          Программа, расписание и каждый подход в одном месте. Тренируйтесь
          как герои, записывайте как летописцы.
        </p>
      </header>

      <section className="auth-form" aria-label={mode === "login" ? "Вход" : "Регистрация"}>
        <div className="tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={mode === "login" ? "active" : ""}
            onClick={() => setMode("login")}
          >
            Вход
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
            className={mode === "register" ? "active" : ""}
            onClick={() => setMode("register")}
          >
            Регистрация
          </button>
        </div>

        <form className="form" onSubmit={submit}>
          <Field label="Email">
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </Field>

          {mode === "register" && (
            <Field label="Имя пользователя" hint="Не короче 3 символов">
              <input
                autoComplete="username"
                required
                minLength={3}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </Field>
          )}

          <Field label="Пароль" hint={mode === "register" ? "Не короче 8 символов" : undefined}>
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={mode === "register" ? 8 : undefined}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>

          <Button variant="primary" type="submit" busy={busy} className="btn-block">
            {mode === "login" ? "Войти" : "Создать аккаунт"}
          </Button>
        </form>
      </section>
    </main>
  );
}
