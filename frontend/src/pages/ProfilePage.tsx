import { useState, type FormEvent } from "react";

import { users } from "../api";
import { useScene } from "../components/Scene";
import { useAuth, useUser } from "../components/Auth";
import { CoachingSection } from "../components/MyCoach";
import { useToast } from "../components/Toast";
import { Button, Field, PageHeader, useConfirm } from "../components/ui";

export function ProfilePage() {
  useScene("pillars");

  const user = useUser();
  const { setUser, logout } = useAuth();
  const toast = useToast();
  const [confirmDialog, confirm] = useConfirm();

  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [busy, setBusy] = useState<"profile" | "password" | null>(null);

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("profile");

    try {
      setUser(await users.update({ username, email }));
      toast.success("Профиль сохранён");
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(null);
    }
  };

  const changePassword = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("password");

    try {
      await users.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      toast.success("Пароль изменён");
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(null);
    }
  };

  const deleteAccount = async () => {
    if (
      !(await confirm(
        "Аккаунт будет удалён вместе со всеми программами, тренировками и подходами. Восстановить его нельзя.",
        "Удалить аккаунт",
      ))
    ) {
      return;
    }

    try {
      await users.deleteMe();
      logout();
    } catch (error) {
      toast.error(error);
    }
  };

  return (
    <div className="page page-narrow">
      <PageHeader title="Профиль" actions={<Button icon="logout" onClick={logout}>Выйти</Button>} />

      <section className="block">
        <h2 className="block-title">Данные</h2>
        <form className="form" onSubmit={saveProfile}>
          <Field label="Имя пользователя">
            <input required minLength={3} value={username} onChange={(e) => setUsername(e.target.value)} />
          </Field>
          <Field label="Email">
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <div>
            <Button variant="primary" type="submit" busy={busy === "profile"}>Сохранить</Button>
          </div>
        </form>
      </section>

      <CoachingSection />

      <section className="block">
        <h2 className="block-title">Пароль</h2>
        <form className="form" onSubmit={changePassword}>
          <Field label="Текущий пароль">
            <input
              type="password"
              autoComplete="current-password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </Field>
          <Field label="Новый пароль" hint="Не короче 8 символов">
            <input
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </Field>
          <div>
            <Button type="submit" busy={busy === "password"}>Сменить пароль</Button>
          </div>
        </form>
      </section>

      <section className="danger-zone">
        <h2 className="block-title">Удаление аккаунта</h2>
        <p className="muted">Удаляет все ваши данные без возможности восстановления.</p>
        <Button variant="danger" onClick={deleteAccount}>Удалить аккаунт</Button>
      </section>

      {confirmDialog}
    </div>
  );
}
