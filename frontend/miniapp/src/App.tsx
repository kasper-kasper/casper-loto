import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import { ApiError, miniAppApi } from "./api";
import { configuredCartTtl, loadCart, saveCart } from "./cart";
import {
  Balance,
  EmptyState,
  Icon,
  NumberSet,
  PrimaryButton,
  Skeleton,
  StatusBadge,
} from "./components";
import { countdown, formatCas, formatDraw, formatMoscow } from "./format";
import { randomCombination } from "./random";
import { errorHaptic, selectionHaptic, successHaptic } from "./telegram";
import type { CartTicket, Dashboard, Lottery, Ticket } from "./types";

type View = "home" | "tickets" | "cart";
type TicketView = "active" | "history";

interface AppProps {
  initData: string;
  localDev?: boolean;
}

function TicketCard({ ticket, index = 0 }: { ticket: Ticket; index?: number }) {
  const complete = ticket.status === "SETTLED";
  const winner = complete && ticket.prize_amount > 0;
  const matches = ticket.matches ?? 0;
  return <article className={`ticket-card ${winner ? "winner" : ""}`} style={{ "--item-index": index } as CSSProperties}>
    <div className="ticket-meta">
      <div><span className="eyebrow">{ticket.lottery_name}</span><h3>Билет #{formatDraw(ticket.public_number)}</h3></div>
      <StatusBadge active={!complete} />
    </div>
    <NumberSet values={ticket.numbers} winning={ticket.winning_numbers} animate={winner} />
    <div className="ticket-footer"><span>Тираж #{formatDraw(ticket.draw_number)}</span><span>{formatMoscow(ticket.scheduled_at)} МСК</span></div>
    {complete && <div className={`ticket-result ${winner ? "win" : "loss"}`}>
      <div><span>{matches > 0 ? `Совпадений: ${matches}` : "Совпадений нет"}</span><small>{winner ? "Выигрыш зачислен" : "Без выигрыша"}</small></div>
      <strong>{winner ? `+${formatCas(ticket.prize_amount)}` : "0 CAS"}</strong>
    </div>}
  </article>;
}

function NextDraw({ lottery, now }: { lottery: Lottery; now: number }) {
  return <section className="next-draw">
    <div className="next-draw-accent"><span>Ближайший тираж</span><i /></div>
    <div className="next-draw-main"><div><strong>{lottery.name}</strong><small>{lottery.draw_number ? `Тираж #${formatDraw(lottery.draw_number)}` : "Расписание готовится"}</small></div><div className="countdown"><span>До старта</span><strong>{countdown(lottery.scheduled_at, now)}</strong></div></div>
    {lottery.scheduled_at && <time>{formatMoscow(lottery.scheduled_at)} МСК</time>}
  </section>;
}

function LotteryCard({ lottery, now, index, onPlay }: { lottery: Lottery; now: number; index: number; onPlay: () => void }) {
  const weekly = lottery.kind === "WEEKLY";
  return <article className={`lottery-card ${weekly ? "weekly" : "daily"}`} style={{ "--item-index": index } as CSSProperties}>
    <div className="card-pattern" aria-hidden="true"><i /><i /><i /></div>
    <div className="lottery-topline"><span className="lottery-kind">{weekly ? "WEEKLY" : "DAILY"}<b>{lottery.numbers_to_pick}/{lottery.max_number}</b></span><span className="draw-label">{lottery.draw_number ? `Тираж #${formatDraw(lottery.draw_number)}` : "Нет тиража"}</span></div>
    <div className="lottery-identity"><h2>{lottery.name}</h2><p>{weekly ? "Главный тираж недели" : "Ежедневный шанс"}</p></div>
    <div className={`jackpot-block ${lottery.jackpot === 0 ? "zero" : ""}`}><span>Текущий джекпот</span><strong>{formatCas(lottery.jackpot)}</strong></div>
    <div className="draw-clock"><span>До тиража</span><strong>{countdown(lottery.scheduled_at, now)}</strong></div>
    <PrimaryButton className="split-button" disabled={!lottery.purchase_available} onClick={onPlay}>
      {lottery.purchase_available ? <><b>Выбрать числа</b><small>{formatCas(lottery.ticket_price ?? 0)}</small></> : weekly ? "Продажи закрыты" : "Скоро откроется"}
    </PrimaryButton>
  </article>;
}

function NumberPicker({ lottery, purchasing, success, onClose, onBuy, onAdd }: { lottery: Lottery; purchasing: boolean; success: boolean; onClose: () => void; onBuy: (numbers: number[]) => void; onAdd: (numbers: number[]) => void }) {
  const [selected, setSelected] = useState<number[]>([]);
  const ready = selected.length === lottery.numbers_to_pick;
  const toggle = (value: number) => {
    setSelected((current) => {
      if (!current.includes(value) && current.length >= lottery.numbers_to_pick) return current;
      selectionHaptic();
      return current.includes(value) ? current.filter((item) => item !== value) : [...current, value].sort((left, right) => left - right);
    });
  };
  const randomize = () => {
    selectionHaptic();
    setSelected(randomCombination(lottery.max_number, lottery.numbers_to_pick));
  };

  return <div className="picker-shell">
    <div className="picker-heading"><button className="icon-button" onClick={onClose} type="button" aria-label="Закрыть"><Icon name="arrow" /></button><div><span className="eyebrow">{lottery.name} · тираж #{formatDraw(lottery.draw_number ?? 0)}</span><h1>Выберите {lottery.numbers_to_pick} чисел</h1></div></div>
    <div className="picker-summary"><div><span>Стоимость билета</span><strong>{formatCas(lottery.ticket_price ?? 0)}</strong></div><div className="selection-meter"><span>Выбрано</span><strong>{selected.length}<i>/ {lottery.numbers_to_pick}</i></strong></div></div>
    <div className="number-grid" aria-label="Выбор чисел">{Array.from({ length: lottery.max_number }, (_, index) => index + 1).map((value) => <button aria-pressed={selected.includes(value)} className={selected.includes(value) ? "pick-number selected" : "pick-number"} key={value} onClick={() => toggle(value)} type="button"><span>{value}</span></button>)}</div>
    <button className="secondary-button random-button" onClick={randomize} type="button"><Icon name="spark" />Случайные числа</button>
    <div className="picker-actions"><button className="secondary-button" disabled={!ready || purchasing} onClick={() => onAdd(selected)} type="button">В корзину</button><PrimaryButton disabled={!ready} loading={purchasing} success={success} onClick={() => onBuy(selected)}>{success ? "Билет куплен" : purchasing ? "Оформляем…" : "Купить билет"}</PrimaryButton></div>
    <p className="picker-note">Комбинация фиксируется после подтверждения покупки.</p>
  </div>;
}

function BottomNavigation({ view, activeTickets, cartCount, onChange }: { view: View; activeTickets: number; cartCount: number; onChange: (view: View) => void }) {
  const items: { id: View; label: string; icon: "home" | "ticket" | "cart"; count: number }[] = [
    { id: "home", label: "Главная", icon: "home", count: 0 },
    { id: "tickets", label: "Билеты", icon: "ticket", count: activeTickets },
    { id: "cart", label: "Корзина", icon: "cart", count: cartCount },
  ];
  return <nav className="bottom-nav" aria-label="Основная навигация">{items.map((item) => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => { selectionHaptic(); onChange(item.id); }} type="button"><i className="nav-indicator" /><span><Icon name={item.icon} />{item.count > 0 && <small>{item.count}</small>}</span><b>{item.label}</b></button>)}</nav>;
}

export default function App({ initData, localDev = false }: AppProps) {
  const authenticated = Boolean(initData) || localDev;
  const [cartTtl] = useState(() => configuredCartTtl());
  const [view, setView] = useState<View>("home");
  const [ticketView, setTicketView] = useState<TicketView>("active");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [cart, setCart] = useState<CartTicket[]>(() => loadCart(cartTtl));
  const [pickerLottery, setPickerLottery] = useState<Lottery | null>(null);
  const [loading, setLoading] = useState(authenticated);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [purchaseSuccess, setPurchaseSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const refreshDashboard = useCallback(async () => {
    if (authenticated) setDashboard(await miniAppApi.dashboard(initData));
  }, [authenticated, initData]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => saveCart(cart, cartTtl), [cart, cartTtl]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 4_000);
    return () => window.clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (!authenticated) return;
    const prepare = localDev && !initData ? miniAppApi.devSession() : Promise.resolve();
    prepare.then(() => miniAppApi.dashboard(initData)).then(setDashboard).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить K-Loto.")).finally(() => setLoading(false));
  }, [authenticated, initData, localDev]);
  useEffect(() => {
    if (view !== "tickets" || !authenticated) return;
    miniAppApi.tickets(initData, ticketView).then(setTickets).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты.")).finally(() => setTicketsLoading(false));
  }, [authenticated, initData, ticketView, view]);

  const nearestLottery = useMemo(() => dashboard?.lotteries.filter((item) => item.scheduled_at).sort((left, right) => new Date(left.scheduled_at ?? 0).getTime() - new Date(right.scheduled_at ?? 0).getTime())[0] ?? null, [dashboard]);
  const firstAvailable = dashboard?.lotteries.find((item) => item.purchase_available) ?? null;

  const addToCart = (lottery: Lottery, numbers: number[]) => {
    setCart((current) => [...current, { id: crypto.randomUUID(), lotteryCode: lottery.code, lotteryName: lottery.name, price: lottery.ticket_price ?? 0, numbers: [...numbers] }]);
    successHaptic();
    setNotice("Комбинация добавлена в корзину");
    setPickerLottery(null);
    setView("cart");
  };

  const purchase = async (lotteryCode: string, combinations: number[][]) => {
    if (purchasing || combinations.length === 0) return;
    setPurchasing(true); setPurchaseSuccess(false); setError(null);
    try {
      const result = await miniAppApi.purchase(initData, lotteryCode, combinations, crypto.randomUUID());
      setPurchaseSuccess(true); successHaptic();
      setCart((current) => current.filter((item) => item.lotteryCode !== lotteryCode));
      setNotice(`${result.ticket_ids.length === 1 ? "Билет куплен" : "Билеты куплены"} · списано ${formatCas(result.total_cost)}`);
      await refreshDashboard();
      await new Promise((resolve) => window.setTimeout(resolve, 480));
      setPickerLottery(null); setTicketsLoading(true); setView("tickets"); setTicketView("active");
    } catch (reason) {
      errorHaptic();
      setError(reason instanceof ApiError ? reason.message : "Покупка не выполнена.");
    } finally {
      setPurchasing(false); setPurchaseSuccess(false);
    }
  };

  const purchaseCart = async () => {
    const groups = new Map<string, number[][]>();
    for (const item of cart) groups.set(item.lotteryCode, [...(groups.get(item.lotteryCode) ?? []), item.numbers]);
    for (const [lotteryCode, combinations] of groups) await purchase(lotteryCode, combinations);
  };

  const refillDevBalance = async () => {
    setError(null);
    try {
      const result = await miniAppApi.devRefill();
      setDashboard((current) => current ? { ...current, balance: result.balance } : current);
      successHaptic(); setNotice("Тестовый баланс пополнен через ledger");
    } catch (reason) { errorHaptic(); setError(reason instanceof Error ? reason.message : "Баланс не пополнен."); }
  };

  if (!authenticated) return <main className="centered-message"><div className="brand-mark">K</div><h1>Откройте K-Loto в Telegram</h1><p>Безопасный вход выполняется автоматически при запуске Mini App.</p></main>;
  if (loading) return <Skeleton />;
  if (!dashboard) return <main className="centered-message"><div className="offline-mark">!</div><h1>Нет связи с K-Loto</h1><p>{error}</p></main>;
  if (pickerLottery) return <main className="app-shell picker-page"><NumberPicker lottery={pickerLottery} purchasing={purchasing} success={purchaseSuccess} onAdd={(numbers) => addToCart(pickerLottery, numbers)} onBuy={(numbers) => void purchase(pickerLottery.code, [numbers])} onClose={() => setPickerLottery(null)} /></main>;

  return <main className="app-shell">
    <header className="app-header"><div className="wordmark"><span>K</span><div>K LOTO<small>ЦИФРОВАЯ ЛОТЕРЕЯ</small></div></div><div className="header-actions">{localDev && <button className="dev-badge" onClick={() => void refillDevBalance()} type="button">+ TEST CAS</button>}<Balance value={dashboard.balance} /></div></header>
    {(error || notice) && <button className={`toast ${error ? "error" : "success"}`} onClick={() => { setError(null); setNotice(null); }} type="button"><span>{error ? "!" : "✓"}</span>{error ?? notice}<Icon name="close" /></button>}

    {view === "home" && <section className="view-content" key="home">
      <div className="hero-copy"><span className="eyebrow">Ваш следующий шанс</span><h1>Выберите числа.<br /><em>Остальное — за удачей.</em></h1><p>Честные тиражи по расписанию. Ваши билеты всегда под рукой.</p></div>
      {nearestLottery && <NextDraw lottery={nearestLottery} now={now} />}
      <div className="section-heading"><div><span className="eyebrow">Игровая коллекция</span><h2>Лотереи</h2></div><span className="section-count">{dashboard.lotteries.length} игры</span></div>
      <div className="lottery-list">{dashboard.lotteries.map((lottery, index) => <LotteryCard key={lottery.code} lottery={lottery} now={now} index={index} onPlay={() => setPickerLottery(lottery)} />)}</div>
      <div className="section-heading"><div><span className="eyebrow">Недавнее</span><h2>Последние результаты</h2></div><button className="text-button" onClick={() => { setTicketsLoading(true); setView("tickets"); setTicketView("history"); }} type="button">Смотреть все <span>→</span></button></div>
      {dashboard.recent_results.length ? dashboard.recent_results.map((ticket, index) => <TicketCard index={index} key={ticket.id} ticket={ticket} />) : <EmptyState title="История пока пуста" text="Результаты сыгранных билетов появятся здесь после первого тиража." />}
    </section>}

    {view === "tickets" && <section className="view-content" key="tickets">
      <div className="page-title"><span className="eyebrow">Личный архив</span><h1>Мои билеты</h1><p>Активные комбинации и результаты тиражей.</p></div>
      <div className={`segmented-control ${ticketView}`}><i /><button className={ticketView === "active" ? "selected" : ""} onClick={() => { selectionHaptic(); setTicketsLoading(true); setTicketView("active"); }} type="button">Активные</button><button className={ticketView === "history" ? "selected" : ""} onClick={() => { selectionHaptic(); setTicketsLoading(true); setTicketView("history"); }} type="button">История</button></div>
      {ticketsLoading ? <div className="ticket-skeletons"><div className="skeleton ticket-skeleton" /><div className="skeleton ticket-skeleton" /></div> : tickets.length ? tickets.map((ticket, index) => <TicketCard index={index} key={ticket.id} ticket={ticket} />) : <EmptyState title={ticketView === "active" ? "Нет активных билетов" : "История пока пуста"} text={ticketView === "active" ? "Выберите лотерею и соберите свою комбинацию." : "Завершённые билеты появятся после розыгрыша."} action={ticketView === "active" && firstAvailable ? { label: "Выбрать лотерею", onClick: () => setView("home") } : undefined} />}
      {ticketView === "active" && firstAvailable && !ticketsLoading && tickets.length > 0 && <PrimaryButton className="sticky-action" onClick={() => setPickerLottery(firstAvailable)}>Ещё один билет</PrimaryButton>}
    </section>}

    {view === "cart" && <section className="view-content" key="cart">
      <div className="page-title cart-title"><span className="eyebrow">Перед покупкой</span><h1>Корзина</h1><p>{cart.length ? `${cart.length} ${cart.length === 1 ? "комбинация" : "комбинации"}` : "Пока без комбинаций"}</p></div>
      {cart.length ? <><div className="cart-list">{cart.map((ticket, index) => <article className="cart-ticket" key={ticket.id} style={{ "--item-index": index } as CSSProperties}><div className="cart-ticket-head"><div><span className="eyebrow">{ticket.lotteryName}</span><strong>Комбинация {index + 1}</strong></div><button className="remove-button" onClick={() => { selectionHaptic(); setCart((current) => current.filter((item) => item.id !== ticket.id)); }} type="button" aria-label={`Удалить билет ${index + 1}`}><Icon name="close" /></button></div><NumberSet values={ticket.numbers} /><div className="cart-ticket-price"><span>Стоимость</span><strong>{formatCas(ticket.price)}</strong></div></article>)}</div><div className="cart-total"><div><span>К оплате</span><small>{cart.length} бил.</small></div><strong>{formatCas(cart.reduce((sum, item) => sum + item.price, 0))}</strong></div><button className="secondary-button" disabled={!firstAvailable || purchasing} onClick={() => firstAvailable && setPickerLottery(firstAvailable)} type="button">Добавить комбинацию</button><PrimaryButton loading={purchasing} success={purchaseSuccess} onClick={() => void purchaseCart()}>{purchaseSuccess ? "Билеты куплены" : purchasing ? "Оформляем покупку…" : "Купить всё"}</PrimaryButton></> : <EmptyState title="Корзина пока пуста" text="Выберите лотерею, отметьте числа и сохраните комбинацию перед покупкой." action={{ label: "Выбрать лотерею", onClick: () => setView("home") }} />}
    </section>}

    <BottomNavigation view={view} activeTickets={dashboard.active_ticket_count} cartCount={cart.length} onChange={(target) => { if (target === "tickets") setTicketsLoading(true); setView(target); }} />
  </main>;
}
