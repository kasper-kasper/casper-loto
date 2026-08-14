import { useCallback, useEffect, useState } from "react";

import { ApiError, miniAppApi } from "./api";
import { configuredCartTtl, loadCart, saveCart } from "./cart";
import { countdown, formatCas, formatDraw, formatMoscow } from "./format";
import { randomCombination } from "./random";
import type { CartTicket, Dashboard, Lottery, Ticket } from "./types";

type View = "home" | "tickets" | "cart";
type TicketView = "active" | "history";

interface AppProps {
  initData: string;
}

function Numbers({ values, winning }: { values: number[]; winning?: number[] | null }) {
  return (
    <div className="number-row" aria-label={`Числа: ${values.join(", ")}`}>
      {values.map((value) => (
        <span className={winning?.includes(value) ? "number won" : "number"} key={value}>
          {value}
        </span>
      ))}
    </div>
  );
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return (
    <div className="empty-state">
      <span className="empty-mark">○</span>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

function TicketCard({ ticket }: { ticket: Ticket }) {
  const complete = ticket.status === "SETTLED";
  return (
    <article className="ticket-card">
      <div className="ticket-meta">
        <div>
          <span className="eyebrow">{ticket.lottery_name}</span>
          <h3>Билет {formatDraw(ticket.public_number)}</h3>
        </div>
        <span className={complete ? "status complete" : "status active"}>
          {complete ? "Завершён" : "Активен"}
        </span>
      </div>
      <Numbers values={ticket.numbers} winning={ticket.winning_numbers} />
      <div className="ticket-footer">
        <span>Тираж {formatDraw(ticket.draw_number)}</span>
        <span>{formatMoscow(ticket.scheduled_at)} MSK</span>
      </div>
      {complete && (
        <div className="ticket-result">
          <span>Совпадений: {ticket.matches ?? 0}</span>
          <strong>{formatCas(ticket.prize_amount)}</strong>
        </div>
      )}
    </article>
  );
}

function LotteryCard({
  lottery,
  now,
  onPlay,
}: {
  lottery: Lottery;
  now: number;
  onPlay: () => void;
}) {
  const weekly = lottery.kind === "WEEKLY";
  return (
    <article className={`lottery-card ${weekly ? "weekly" : "daily"}`}>
      <div className="lottery-topline">
        <span className="lottery-kind">{weekly ? "WEEKLY" : "DAILY"}</span>
        <span className="draw-label">
          {lottery.draw_number ? `Тираж ${formatDraw(lottery.draw_number)}` : "Нет тиража"}
        </span>
      </div>
      <h2>{lottery.name}</h2>
      <p className="lottery-format">
        {lottery.numbers_to_pick} из {lottery.max_number}
      </p>
      <div className="jackpot-block">
        <span>Джекпот</span>
        <strong>{formatCas(lottery.jackpot)}</strong>
      </div>
      <div className="draw-clock">
        <span>До тиража</span>
        <strong>{countdown(lottery.scheduled_at, now)}</strong>
      </div>
      <button
        className="primary-button"
        disabled={!lottery.purchase_available}
        onClick={onPlay}
        type="button"
      >
        {lottery.purchase_available
          ? `Купить за ${formatCas(lottery.ticket_price ?? 0)}`
          : weekly
            ? "Продажи закрыты"
            : "Скоро"}
      </button>
    </article>
  );
}

function NumberPicker({
  lottery,
  onClose,
  onBuy,
  onAdd,
}: {
  lottery: Lottery;
  onClose: () => void;
  onBuy: (numbers: number[]) => void;
  onAdd: (numbers: number[]) => void;
}) {
  const [selected, setSelected] = useState<number[]>([]);
  const ready = selected.length === lottery.numbers_to_pick;
  const toggle = (value: number) => {
    setSelected((current) => {
      if (current.includes(value)) return current.filter((item) => item !== value);
      if (current.length >= lottery.numbers_to_pick) return current;
      return [...current, value].sort((left, right) => left - right);
    });
  };
  const randomize = () =>
    setSelected(randomCombination(lottery.max_number, lottery.numbers_to_pick));

  return (
    <div className="picker-shell">
      <div className="picker-heading">
        <button className="icon-button" onClick={onClose} type="button" aria-label="Закрыть">
          ←
        </button>
        <div>
          <span className="eyebrow">Weekly · тираж {formatDraw(lottery.draw_number ?? 0)}</span>
          <h1>Выберите 5 чисел</h1>
        </div>
      </div>
      <div className="selection-meter">
        <span>Выбрано</span>
        <strong>{selected.length} / {lottery.numbers_to_pick}</strong>
      </div>
      <div className="number-grid">
        {Array.from({ length: lottery.max_number }, (_, index) => index + 1).map((value) => (
          <button
            aria-pressed={selected.includes(value)}
            className={selected.includes(value) ? "pick-number selected" : "pick-number"}
            key={value}
            onClick={() => toggle(value)}
            type="button"
          >
            {value}
          </button>
        ))}
      </div>
      <button className="secondary-button" onClick={randomize} type="button">
        Случайные числа
      </button>
      <div className="picker-actions">
        <button className="secondary-button" disabled={!ready} onClick={() => onAdd(selected)} type="button">
          Добавить ещё
        </button>
        <button className="primary-button" disabled={!ready} onClick={() => onBuy(selected)} type="button">
          Купить
        </button>
      </div>
    </div>
  );
}

export default function App({ initData }: AppProps) {
  const [cartTtl] = useState(() => configuredCartTtl());
  const [view, setView] = useState<View>("home");
  const [ticketView, setTicketView] = useState<TicketView>("active");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [cart, setCart] = useState<CartTicket[]>(() => loadCart(cartTtl));
  const [pickerLottery, setPickerLottery] = useState<Lottery | null>(null);
  const [loading, setLoading] = useState(Boolean(initData));
  const [purchasing, setPurchasing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [now, setNow] = useState(0);

  const refreshDashboard = useCallback(async () => {
    if (!initData) return;
    const data = await miniAppApi.dashboard(initData);
    setDashboard(data);
  }, [initData]);

  useEffect(() => {
    const initial = window.requestAnimationFrame(() => setNow(Date.now()));
    const timer = window.setInterval(() => setNow(Date.now()), 30_000);
    return () => {
      window.cancelAnimationFrame(initial);
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => saveCart(cart, cartTtl), [cart, cartTtl]);

  useEffect(() => {
    if (!initData) return;
    miniAppApi
      .dashboard(initData)
      .then(setDashboard)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить K-Loto.");
      })
      .finally(() => setLoading(false));
  }, [initData]);

  useEffect(() => {
    if (view !== "tickets" || !initData) return;
    miniAppApi
      .tickets(initData, ticketView)
      .then(setTickets)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты.");
      });
  }, [initData, ticketView, view]);

  const addToCart = (numbers: number[]) => {
    setCart((current) => [...current, { id: crypto.randomUUID(), numbers: [...numbers] }]);
    setNotice("Билет добавлен в корзину.");
    setPickerLottery(null);
    setView("cart");
  };

  const purchase = async (combinations: number[][]) => {
    if (purchasing || combinations.length === 0) return;
    setPurchasing(true);
    setError(null);
    try {
      const result = await miniAppApi.purchase(initData, combinations, crypto.randomUUID());
      setCart([]);
      setPickerLottery(null);
      setNotice(
        `${result.ticket_ids.length === 1 ? "Билет куплен" : "Билеты куплены"}. Списано ${formatCas(result.total_cost)}.`,
      );
      await refreshDashboard();
      setView("tickets");
      setTicketView("active");
    } catch (reason) {
      const message = reason instanceof ApiError ? reason.message : "Покупка не выполнена.";
      setError(message);
    } finally {
      setPurchasing(false);
    }
  };

  if (!initData) {
    return (
      <main className="centered-message">
        <div className="brand-mark">K</div>
        <h1>Откройте K-Loto в Telegram</h1>
        <p>Mini App принимает только подписанные данные запуска Telegram.</p>
      </main>
    );
  }

  if (loading) {
    return <main className="centered-message"><div className="loader" /><p>Загружаем тиражи…</p></main>;
  }

  if (!dashboard) {
    return <main className="centered-message"><h1>Нет связи с K-Loto</h1><p>{error}</p></main>;
  }

  const weekly = dashboard.lotteries.find((item) => item.kind === "WEEKLY") ?? null;

  if (pickerLottery) {
    return (
      <main className="app-shell">
        <NumberPicker
          lottery={pickerLottery}
          onAdd={addToCart}
          onBuy={(numbers) => void purchase([numbers])}
          onClose={() => setPickerLottery(null)}
        />
        {purchasing && <div className="blocking-state">Покупаем билет…</div>}
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="wordmark"><span>K</span> LOTO</div>
        <div className="balance-pill"><small>Баланс</small><strong>{formatCas(dashboard.balance)}</strong></div>
      </header>

      {(error || notice) && (
        <button className={error ? "toast error" : "toast"} onClick={() => { setError(null); setNotice(null); }} type="button">
          {error ?? notice}
        </button>
      )}

      {view === "home" && (
        <section className="view-content">
          <div className="hero-copy">
            <span className="eyebrow">Следующий шанс</span>
            <h1>Выберите числа.<br />Остальное — за удачей.</h1>
          </div>
          <div className="lottery-list">
            {dashboard.lotteries.map((lottery) => (
              <LotteryCard key={lottery.code} lottery={lottery} now={now} onPlay={() => setPickerLottery(lottery)} />
            ))}
          </div>
          <div className="section-heading">
            <div><span className="eyebrow">Недавнее</span><h2>Последние результаты</h2></div>
            <button className="text-button" onClick={() => { setView("tickets"); setTicketView("history"); }} type="button">Все</button>
          </div>
          {dashboard.recent_results.length ? dashboard.recent_results.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} />) : (
            <EmptyState title="История пока пуста" text="Здесь появятся результаты сыгранных билетов." />
          )}
        </section>
      )}

      {view === "tickets" && (
        <section className="view-content">
          <div className="page-title"><span className="eyebrow">Мои билеты</span><h1>Тиражи</h1></div>
          <div className="segmented-control">
            <button className={ticketView === "active" ? "selected" : ""} onClick={() => setTicketView("active")} type="button">Активные</button>
            <button className={ticketView === "history" ? "selected" : ""} onClick={() => setTicketView("history")} type="button">История</button>
          </div>
          {tickets.length ? tickets.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} />) : (
            <EmptyState title={ticketView === "active" ? "Нет активных билетов" : "История пуста"} text={ticketView === "active" ? "Выберите пять чисел для ближайшего Weekly-тиража." : "Завершённые билеты появятся после розыгрыша."} />
          )}
          {ticketView === "active" && weekly?.purchase_available && (
            <button className="primary-button sticky-action" onClick={() => setPickerLottery(weekly)} type="button">Купить билет</button>
          )}
        </section>
      )}

      {view === "cart" && (
        <section className="view-content">
          <div className="page-title"><span className="eyebrow">Weekly</span><h1>Корзина</h1><p>{cart.length} бил.</p></div>
          {cartTtl === null && <p className="config-note">Постоянное хранение включится после настройки TTL владельцем.</p>}
          {cart.length ? (
            <>
              <div className="cart-list">
                {cart.map((ticket, index) => (
                  <article className="cart-ticket" key={ticket.id}>
                    <div><span className="eyebrow">Билет {index + 1}</span><Numbers values={ticket.numbers} /></div>
                    <button className="remove-button" onClick={() => setCart((current) => current.filter((item) => item.id !== ticket.id))} type="button" aria-label={`Удалить билет ${index + 1}`}>×</button>
                  </article>
                ))}
              </div>
              <div className="cart-total"><span>Итого</span><strong>{formatCas((weekly?.ticket_price ?? 0) * cart.length)}</strong></div>
              <button className="secondary-button" disabled={!weekly?.purchase_available} onClick={() => weekly && setPickerLottery(weekly)} type="button">Добавить ещё билет</button>
              <button className="primary-button" disabled={purchasing || !weekly?.purchase_available} onClick={() => void purchase(cart.map((item) => item.numbers))} type="button">{purchasing ? "Покупаем…" : "Купить всё"}</button>
            </>
          ) : (
            <EmptyState title="Корзина пуста" text="Соберите одну или несколько комбинаций Weekly 5 из 20." />
          )}
        </section>
      )}

      <nav className="bottom-nav" aria-label="Основная навигация">
        <button className={view === "home" ? "active" : ""} onClick={() => setView("home")} type="button"><span>⌂</span>Главная</button>
        <button className={view === "tickets" ? "active" : ""} onClick={() => setView("tickets")} type="button"><span>▤</span>Билеты<small>{dashboard.active_ticket_count || ""}</small></button>
        <button className={view === "cart" ? "active" : ""} onClick={() => setView("cart")} type="button"><span>◇</span>Корзина<small>{cart.length || ""}</small></button>
      </nav>
    </main>
  );
}
