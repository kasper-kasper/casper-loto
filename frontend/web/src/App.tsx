import { FormEvent, useCallback, useEffect, useState } from "react";

import { ApiError, webApi } from "./api";
import type { Dashboard, DrawResult, Ticket, WebSession } from "./types";

type View = "weekly" | "daily" | "active" | "history" | "results";

const cas = (value: number) => `${value.toLocaleString("ru-RU")} CAS`;
const date = (value: string | null) =>
  value ? new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Moscow" }).format(new Date(value)) : "—";

function Numbers({ values, winning }: { values: number[]; winning?: number[] | null }) {
  return <div className="numbers">{values.map((value) => <span className={winning?.includes(value) ? "hit" : ""} key={value}>{value}</span>)}</div>;
}

function Login({ onLogin, hint }: { onLogin: (value: WebSession) => void; hint: string }) {
  const [error, setError] = useState(hint);
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    try { onLogin(await webApi.login(String(data.get("username")), String(data.get("password")))); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Вход не выполнен."); }
    finally { setBusy(false); }
  };
  return <main className="login"><form onSubmit={(event) => void submit(event)}><h1>K-Loto</h1><p>Самый простой вход: откройте бота и нажмите «🌐 Открыть Web-версию».</p><p>Логин и пароль — запасной способ.</p><label>Логин<input name="username" autoComplete="username" required /></label><label>Пароль<input name="password" type="password" autoComplete="current-password" required /></label>{error && <p className="error">{error}</p>}<button disabled={busy}>{busy ? "Входим…" : "Войти"}</button></form></main>;
}

function TicketCard({ ticket }: { ticket: Ticket }) {
  return <article><div className="row"><strong>Билет №{ticket.public_number}</strong><span>Тираж №{ticket.draw_number}</span></div><Numbers values={ticket.numbers} winning={ticket.winning_numbers} /><p>{date(ticket.scheduled_at)} MSK · {cas(ticket.purchase_price)}</p>{ticket.status === "SETTLED" && <p><b>{ticket.matches ?? 0} совп.</b> · выигрыш {cas(ticket.prize_amount)}</p>}</article>;
}

export default function App() {
  const [session, setSession] = useState<WebSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [view, setView] = useState<View>("weekly");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [results, setResults] = useState<DrawResult[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loginHint, setLoginHint] = useState("");

  const refresh = useCallback(async () => setDashboard(await webApi.dashboard()), []);
  useEffect(() => {
    const prefix = "#telegram-login=";
    const oneTimeToken = window.location.hash.startsWith(prefix)
      ? window.location.hash.slice(prefix.length)
      : "";
    if (oneTimeToken) {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
    const authentication = oneTimeToken
      ? webApi.telegramLogin(oneTimeToken)
      : webApi.session();
    authentication
      .then(async (value) => {
        setSession(value);
        setDashboard(await webApi.dashboard());
      })
      .catch((reason) => {
        setSession(null);
        if (oneTimeToken) {
          setLoginHint(reason instanceof Error ? reason.message : "Ссылка входа не сработала. Получите новую в боте.");
        }
      })
      .finally(() => setChecking(false));
  }, []);
  useEffect(() => {
    if (!session) return;
    if (view === "active" || view === "history") void webApi.tickets(view).then(setTickets);
    if (view === "results") void webApi.results().then(setResults);
  }, [session, view]);
  useEffect(() => {
    if (!session) return;
    const update = () => void refresh();
    const timer = window.setInterval(update, 15_000);
    window.addEventListener("focus", update);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", update);
    };
  }, [session, refresh]);

  if (checking) return <main className="center">Загрузка…</main>;
  if (!session) return <Login hint={loginHint} onLogin={(value) => { setSession(value); void refresh(); }} />;
  const lottery = dashboard?.lotteries.find((item) => item.kind === view.toUpperCase());
  const toggle = (value: number) => setSelected((current) => current.includes(value) ? current.filter((item) => item !== value) : current.length < (lottery?.numbers_to_pick ?? 0) ? [...current, value].sort((a, b) => a - b) : current);
  const buy = async () => {
    if (!lottery || selected.length !== lottery.numbers_to_pick) return;
    setBusy(true); setNotice("");
    try {
      const response = await webApi.purchase(lottery.kind.toLowerCase() as "weekly" | "daily", Array.from({ length: quantity }, () => [...selected]), crypto.randomUUID());
      setNotice(`Куплено билетов: ${response.ticket_ids.length}. Списано ${cas(response.total_cost)}.`);
      setSelected([]); setQuantity(1); await refresh(); setView("active");
    } catch (reason) { setNotice(reason instanceof ApiError ? reason.message : "Покупка не выполнена."); }
    finally { setBusy(false); }
  };
  const logout = async () => { await webApi.logout(); setSession(null); setDashboard(null); };

  return <main className="shell"><header><div><h1>K-Loto</h1><small>{session.display_name}</small></div><div className="balance">Баланс <b>{cas(dashboard?.balance ?? 0)}</b></div><button className="plain" onClick={() => void logout()}>Выйти</button></header><nav>{(["weekly", "daily", "active", "history", "results"] as View[]).map((item) => <button className={view === item ? "current" : ""} key={item} onClick={() => { setView(item); setSelected([]); }}>{({ weekly: "Weekly", daily: "Daily", active: `Активные (${dashboard?.active_ticket_count ?? 0})`, history: "История", results: "Результаты" })[item]}</button>)}</nav><div className="jackpots">{dashboard?.lotteries.map((item) => <button key={item.code} onClick={() => setView(item.kind.toLowerCase() as View)}><strong>{item.name}</strong><span>Текущий джекпот <b>{cas(item.jackpot)}</b></span></button>)}<button className="refresh" onClick={() => void refresh()}>↻ Обновить</button></div>{notice && <p className="notice">{notice}</p>}
    {(view === "weekly" || view === "daily") && <section><h2>{lottery ? `${lottery.name}: ${lottery.numbers_to_pick} из ${lottery.max_number}` : view}</h2>{lottery ? <><div className="summary"><span>Тираж №{lottery.draw_number ?? "—"}<small>{date(lottery.scheduled_at)} MSK</small></span><span>Билет <b>{cas(lottery.ticket_price ?? 0)}</b></span><span>Джекпот <b>{cas(lottery.jackpot)}</b></span></div><p>Выберите ровно {lottery.numbers_to_pick} числа:</p><div className="picker">{Array.from({ length: lottery.max_number }, (_, index) => index + 1).map((value) => <button aria-pressed={selected.includes(value)} key={value} onClick={() => toggle(value)}>{value}</button>)}</div><div className="purchase"><label>Количество<input type="number" min="1" max="20" value={quantity} onChange={(event) => setQuantity(Math.max(1, Math.min(20, Number(event.target.value))))} /></label><button disabled={!lottery.purchase_available || selected.length !== lottery.numbers_to_pick || busy} onClick={() => void buy()}>{busy ? "Покупаем…" : `Купить за ${cas((lottery.ticket_price ?? 0) * quantity)}`}</button></div>{!lottery.purchase_available && <p>Продажи для ближайшего тиража закрыты или лотерея ещё не настроена.</p>}</> : <p>Лотерея пока не настроена.</p>}</section>}
    {(view === "active" || view === "history") && <section><h2>{view === "active" ? "Активные билеты" : "История билетов"}</h2>{tickets.length ? tickets.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} />) : <p className="empty">Здесь пока пусто.</p>}</section>}
    {view === "results" && <section><h2>Результаты тиражей</h2>{results.length ? results.map((draw) => <article key={`${draw.lottery_code}-${draw.draw_number}`}><div className="row"><strong>{draw.lottery_name}, тираж №{draw.draw_number}</strong><span>{date(draw.scheduled_at)} MSK</span></div><Numbers values={draw.winning_numbers} /><p>Билетов: {draw.ticket_count} · выплачено: {cas(draw.total_payout)}</p></article>) : <p className="empty">Завершённых тиражей пока нет.</p>}</section>}
  </main>;
}
