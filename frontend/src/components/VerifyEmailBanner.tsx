// Напоминание вверху приложения, пока почта не подтверждена

import { useState } from "react";

import { auth } from "../api";
import { Icon } from "./Icon";
import { useToast } from "./Toast";

export function VerifyEmailBanner({ email }: { email: string }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const resend = async () => {
    setBusy(true);

    try {
      await auth.resendVerification();
      setSent(true);
      toast.success(`Письмо отправлено на ${email}`);
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="verify-banner" role="status">
      <span className="verify-banner-icon" aria-hidden="true">
        <Icon name="send" size={20} />
      </span>
      <p className="verify-banner-text">
        <strong>Подтвердите почту</strong>
        <span>
          Мы отправили ссылку на {email}. Если письма нет — проверьте «Спам».
        </span>
      </p>
      <button type="button" className="verify-banner-action" onClick={resend} disabled={busy || sent}>
        {sent ? "Отправлено" : busy ? "Отправляем…" : "Отправить ещё раз"}
      </button>
    </div>
  );
}
