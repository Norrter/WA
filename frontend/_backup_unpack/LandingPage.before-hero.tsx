// Главная для гостей: что это, как проходит ведение, приложение,
// тарифы и заявка. Вход для клиентов — #/login.

import { useRef, useState, type FormEvent } from "react";

import { publicApi } from "../api";
import type { Offer } from "../api/types";
import { Icon } from "../components/Icon";
import { Meander } from "../components/Meander";
import { SceneSection, useScene } from "../components/Scene";
import { ThemeToggle } from "../components/ThemeSwitch";
import { useToast } from "../components/Toast";
import { Button, Field } from "../components/ui";
import { formatNumber } from "../lib/format";
import { FAQ, FEATURES, HERO, STEPS, TRAINER } from "../lib/landing";
import { roman } from "../lib/roman";
import { useAsync } from "../lib/useAsync";

const KIND_LABEL: Record<Offer["kind"], string> = {
  offline: "В зале",
  online: "Онлайн",
  program: "Программа",
};

function priceText(offer: Offer): string {
  return offer.price > 0 ? `${formatNumber(offer.price)} ₽` : "По договорённости";
}

function scrollToId(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function LandingPage() {
  useScene("struggle");

  const offersState = useAsync(() => publicApi.offers(), []);
  const offers = offersState.data ?? [];
  const [offerId, setOfferId] = useState<number | "">("");
  const nameRef = useRef<HTMLInputElement>(null);

  const choose = (offer: Offer) => {
    setOfferId(offer.id);
    scrollToId("lead");
    window.setTimeout(() => nameRef.current?.focus({ preventScroll: true }), 500);
  };

  return (
    <div className="landing">
      <header className="landing-bar">
        <a className="brand" href="#/">Greek's Gym</a>
        <nav className="landing-nav" aria-label="Разделы">
          <button type="button" onClick={() => scrollToId("trainer")}>Тренер</button>
          <button type="button" onClick={() => scrollToId("how")}>Как это работает</button>
          <button type="button" onClick={() => scrollToId("tariffs")}>Тарифы</button>
          <button type="button" onClick={() => scrollToId("faq")}>Вопросы</button>
        </nav>
        <ThemeToggle />
        <a className="btn btn-secondary btn-small landing-login" href="#/login">
          <Icon name="profile" size={16} />
          <span>Войти</span>
        </a>
      </header>

      <section className="landing-hero" aria-labelledby="hero-title">
        <p className="eyebrow">{HERO.eyebrow}</p>
        <h1 className="landing-title" id="hero-title">
          {HERO.title[0]}
          <br />
          {HERO.title[1]}
        </h1>
        <p className="landing-lead">{HERO.lead}</p>
        <div className="landing-actions">
          <Button variant="primary" onClick={() => scrollToId("lead")}>
            Оставить заявку
          </Button>
          <Button onClick={() => scrollToId("tariffs")}>Тарифы и цены</Button>
        </div>
      </section>

      <section className="landing-section landing-trainer" aria-labelledby="trainer">
        <div className="trainer-card">
          <div className="trainer-text">
            <p className="eyebrow">{TRAINER.eyebrow}</p>
            <h2 className="landing-h2 trainer-title" id="trainer">
              {TRAINER.title[0]}
              <br />
              <span className="trainer-accent">{TRAINER.title[1]}</span>
            </h2>
            {TRAINER.name && <p className="trainer-name">{TRAINER.name}</p>}
            <p className="trainer-role">{TRAINER.role}</p>
            <ul className="trainer-points">
              {TRAINER.points.map((point) => (
                <li key={point.text}>
                  <span className="trainer-point-icon" aria-hidden="true">
                    <Icon name={point.icon} size={22} />
                  </span>
                  {point.text}
                </li>
              ))}
            </ul>
            <Button variant="primary" className="trainer-action" onClick={() => scrollToId("lead")}>
              {TRAINER.action}
              <Icon name="send" size={18} />
            </Button>
          </div>
          <img
            className="trainer-photo"
            src={TRAINER.photo}
            alt={TRAINER.name ? `Тренер ${TRAINER.name}` : "Ваш тренер"}
            loading="lazy"
            width={740}
            height={984}
          />
        </div>
      </section>

      <SceneSection scene="pillars" className="landing-section" labelledBy="how">
        <Meander />
        <p className="eyebrow">Онлайн-ведение</p>
        <h2 className="landing-h2" id="how">Как это работает</h2>
        <ol className="landing-steps">
          {STEPS.map((step, index) => (
            <li key={step.title}>
              <span className="landing-step-number">{roman(index + 1)}</span>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </li>
          ))}
        </ol>
      </SceneSection>

      <SceneSection scene="colonnade" className="landing-section" labelledBy="app">
        <p className="eyebrow">Приложение для клиентов</p>
        <h2 className="landing-h2" id="app">Всё в одном месте</h2>
        <p className="landing-text">
          Каждый клиент получает доступ к приложению Greek's Gym — с телефона или компьютера.
        </p>
        <ul className="landing-features">
          {FEATURES.map((feature) => (
            <li key={feature.title}>
              <span className="landing-feature-icon" aria-hidden="true">
                <Icon name={feature.icon} size={22} />
              </span>
              <h3>{feature.title}</h3>
              <p>{feature.text}</p>
            </li>
          ))}
        </ul>
      </SceneSection>

      <SceneSection scene="throne" className="landing-section" labelledBy="tariffs">
        <p className="eyebrow">Форматы</p>
        <h2 className="landing-h2" id="tariffs">Тарифы</h2>
        {offersState.error ? (
          <p className="landing-text">
            Не удалось загрузить тарифы.{" "}
            <button type="button" className="link-quiet" onClick={() => void offersState.reload()}>
              Повторить
            </button>
          </p>
        ) : (
          <div className="landing-offers">
            {offers.map((offer) => (
              <article key={offer.id} className={`offer ${offer.is_featured ? "is-featured" : ""}`}>
                {offer.is_featured && <span className="offer-badge">Популярный выбор</span>}
                <span className="offer-kind">{KIND_LABEL[offer.kind] ?? offer.kind}</span>
                <h3 className="offer-title">{offer.title}</h3>
                {offer.subtitle && <p className="offer-subtitle">{offer.subtitle}</p>}
                <p className="offer-price">
                  {priceText(offer)}
                  {offer.price > 0 && offer.price_unit && <small> {offer.price_unit}</small>}
                </p>
                {offer.features.length > 0 && (
                  <ul className="offer-features">
                    {offer.features.map((feature) => (
                      <li key={feature}>
                        <Icon name="check" size={16} strokeWidth={2.4} />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <Button
                  variant={offer.is_featured ? "primary" : "secondary"}
                  className="btn-block offer-button"
                  onClick={() => choose(offer)}
                >
                  Выбрать
                </Button>
              </article>
            ))}
          </div>
        )}
      </SceneSection>

      <SceneSection scene="olympus" className="landing-section landing-split" labelledBy="faq">
        <div>
          <p className="eyebrow">Частые вопросы</p>
          <h2 className="landing-h2" id="faq">Вопросы</h2>
          <div className="landing-faq">
            {FAQ.map((item) => (
              <details key={item.question}>
                <summary>
                  <span>{item.question}</span>
                  <Icon name="plus" size={18} />
                </summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </div>

        <LeadForm offers={offers} offerId={offerId} onOfferChange={setOfferId} nameRef={nameRef} />
      </SceneSection>

      <footer className="landing-footer">
        <Meander />
        <div className="landing-footer-row">
          <span className="brand">Greek's Gym</span>
          <a href="#/login">Вход для клиентов</a>
        </div>
      </footer>
    </div>
  );
}

function LeadForm({
  offers,
  offerId,
  onOfferChange,
  nameRef,
}: {
  offers: Offer[];
  offerId: number | "";
  onOfferChange: (id: number | "") => void;
  nameRef: React.RefObject<HTMLInputElement | null>;
}) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [goal, setGoal] = useState("");
  const [website, setWebsite] = useState("");
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);

    try {
      await publicApi.sendLead({
        offer_id: offerId === "" ? null : offerId,
        name: name.trim(),
        contact: contact.trim(),
        goal: goal.trim() || null,
        website,
      });
      setSent(true);
    } catch (error) {
      toast.error(error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="landing-lead-card" id="lead">
      {sent ? (
        <div className="lead-sent" role="status">
          <span className="lead-sent-icon" aria-hidden="true">
            <Icon name="check" size={28} strokeWidth={2.4} />
          </span>
          <h2 className="landing-h3">Заявка отправлена</h2>
          <p>
            Спасибо, {name.trim()}! Тренер свяжется с вами по контакту «{contact.trim()}» в
            ближайшее время.
          </p>
          <Button
            onClick={() => {
              setSent(false);
              setGoal("");
            }}
          >
            Отправить ещё одну
          </Button>
        </div>
      ) : (
        <form className="form" onSubmit={submit}>
          <div>
            <p className="eyebrow">Первый шаг</p>
            <h2 className="landing-h3">Оставить заявку</h2>
            <p className="muted small">Ни к чему не обязывает: сначала знакомство, потом оплата.</p>
          </div>

          <Field label="Как вас зовут">
            <input
              ref={nameRef}
              required
              maxLength={100}
              autoComplete="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </Field>
          <Field label="Телефон или Telegram" hint="Куда тренеру написать">
            <input
              required
              minLength={3}
              maxLength={150}
              autoComplete="tel"
              placeholder="+7 900 000-00-00 или @username"
              value={contact}
              onChange={(event) => setContact(event.target.value)}
            />
          </Field>
          <Field label="Формат">
            <select
              value={offerId}
              onChange={(event) => onOfferChange(event.target.value === "" ? "" : Number(event.target.value))}
            >
              <option value="">Пока не знаю — нужна консультация</option>
              {offers.map((offer) => (
                <option key={offer.id} value={offer.id}>
                  {offer.title} — {priceText(offer)}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Цель и опыт" hint="Необязательно">
            <textarea
              rows={3}
              maxLength={2000}
              placeholder="Например: хочу сбросить 8 кг, тренируюсь дома 3 раза в неделю"
              value={goal}
              onChange={(event) => setGoal(event.target.value)}
            />
          </Field>

          {/* Ловушка для ботов: человек это поле не видит */}
          <label className="lead-trap" aria-hidden="true">
            Сайт
            <input
              tabIndex={-1}
              autoComplete="off"
              value={website}
              onChange={(event) => setWebsite(event.target.value)}
            />
          </label>

          <label className="toggle lead-agree">
            <input type="checkbox" required checked={agree} onChange={(event) => setAgree(event.target.checked)} />
            Согласен на обработку моих данных, чтобы тренер связался со мной
          </label>

          <Button variant="primary" type="submit" busy={busy} className="btn-block" disabled={!agree}>
            Отправить заявку
          </Button>
        </form>
      )}
    </div>
  );
}
