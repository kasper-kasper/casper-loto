import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";

import { ApiError, miniAppApi } from "./api";
import { batchItems, CART_MAX_TICKETS, configuredCartTtl, loadCart, saveCart } from "./cart";
import {
  Balance,
  EmptyState,
  Icon,
  NumberSet,
  PrimaryButton,
  Skeleton,
  StatusBadge,
} from "./components";
import { countdown, formatCas, formatDraw, formatMoscow, formatMoscowTime } from "./format";
import { LiveView } from "./LiveView";
import { randomCombination } from "./random";
import { errorHaptic, selectionHaptic, successHaptic } from "./telegram";
import type { CartTicket, Dashboard, LiveFeed, Lottery, Ticket } from "./types";

type View = "home" | "live" | "tickets" | "cart";
type TicketView = "active" | "history";

interface AppProps {
  initData: string;
  localDev?: boolean;
}

function plural(value: number, one: string, few: string, many: string): string {
  const lastTwo = value % 100;
  const last = value % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return many;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
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

function NextDraw({ lottery, now, onLive, onPlay }: { lottery: Lottery; now: number; onLive: () => void; onPlay: () => void }) {
  const startsIn = lottery.scheduled_at ? new Date(lottery.scheduled_at).getTime() - now : Infinity;
  return <section className="next-draw featured-draw">
    <div className="featured-mesh" aria-hidden="true" />
    <div className="next-draw-accent"><span>Ближайший тираж</span><i /></div>
    <div className="featured-title"><div><small>{lottery.kind} · {lottery.numbers_to_pick}/{lottery.max_number}</small><strong>{lottery.name}</strong><span>{lottery.draw_number ? `Тираж #${formatDraw(lottery.draw_number)}` : "Расписание готовится"}</span></div><div className="featured-jackpot"><span>Джекпот</span><strong>{formatCas(lottery.jackpot)}</strong></div></div>
    <div className="featured-timing"><div className="countdown"><span>До старта</span><strong>{countdown(lottery.scheduled_at, now)}</strong></div><div><span>Ваши билеты</span><strong>{lottery.player_ticket_count}</strong></div></div>
    <div className="featured-meta"><span>{lottery.sales_close_at ? `Продажи до ${formatMoscowTime(lottery.sales_close_at)} МСК` : "Продажи закрыты"}</span>{lottery.scheduled_at && <time>{formatMoscow(lottery.scheduled_at)} МСК</time>}</div>
    <div className="featured-actions"><button className="live-cta" onClick={onLive} type="button"><i /> {startsIn <= 5 * 60_000 ? "Смотреть эфир" : "Открыть эфир"}</button><PrimaryButton disabled={!lottery.scheduled_at || lottery.ticket_price === null} onClick={onPlay}>{lottery.purchase_available ? "Выбрать числа" : "Проверить продажи"}</PrimaryButton></div>
  </section>;
}

function LotteryCard({ lottery, now, index, onPlay }: { lottery: Lottery; now: number; index: number; onPlay: () => void }) {
  const weekly = lottery.kind === "WEEKLY";
  return <article className={`lottery-card compact ${weekly ? "weekly" : "daily"}`} style={{ "--item-index": index } as CSSProperties}>
    <div className="card-pattern" aria-hidden="true"><i /><i /><i /></div>
    <div className="lottery-topline"><span className="lottery-kind">{weekly ? "WEEKLY" : "DAILY"}<b>{lottery.numbers_to_pick}/{lottery.max_number}</b></span><span className="draw-label">{lottery.draw_number ? `Тираж #${formatDraw(lottery.draw_number)}` : "Нет тиража"}</span></div>
    <div className="lottery-identity"><h2>{lottery.name}</h2><p>{weekly ? "Главный тираж недели" : "Ежедневный шанс"}</p></div>
    <div className={`jackpot-block ${lottery.jackpot === 0 ? "zero" : ""}`}><span>Текущий джекпот</span><strong>{formatCas(lottery.jackpot)}</strong></div>
    <div className="draw-clock"><div><span>До тиража</span><strong>{countdown(lottery.scheduled_at, now)}</strong></div><div className="card-ticket-count"><span>Ваши</span><strong>{lottery.player_ticket_count}</strong></div></div>
    <p className="sales-cutoff">{lottery.sales_close_at ? `Продажи открыты до ${formatMoscowTime(lottery.sales_close_at)} МСК` : "Продажи пока недоступны"}</p>
    <PrimaryButton className="split-button" disabled={!lottery.scheduled_at || lottery.ticket_price === null} onClick={onPlay}>
      {lottery.purchase_available ? <><b>Выбрать числа</b><small>{formatCas(lottery.ticket_price ?? 0)}</small></> : <><b>Проверить продажи</b><small>{lottery.ticket_price !== null ? formatCas(lottery.ticket_price) : "—"}</small></>}
    </PrimaryButton>
  </article>;
}

function NumberPicker({ lottery, purchasing, success, initialNumbers = [], cartRemaining, onClose, onBuy, onAdd, onAddMany }: { lottery: Lottery; purchasing: boolean; success: boolean; initialNumbers?: number[]; cartRemaining: number; onClose: () => void; onBuy: (numbers: number[]) => void; onAdd: (numbers: number[]) => void; onAddMany: (combinations: number[][]) => void }) {
  const [selected, setSelected] = useState<number[]>(initialNumbers);
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
    <div className="quick-batches"><div><span>Быстрая корзина</span><small>Случайные комбинации</small></div><div>{[5, 10, 25, 50].map((count) => <button disabled={purchasing || cartRemaining < count} key={count} onClick={() => onAddMany(Array.from({ length: count }, () => randomCombination(lottery.max_number, lottery.numbers_to_pick)))} type="button">+{count}</button>)}</div></div>
    <div className="picker-actions"><button className="secondary-button" disabled={!ready || purchasing} onClick={() => onAdd(selected)} type="button">В корзину</button><PrimaryButton disabled={!ready} loading={purchasing} success={success} onClick={() => onBuy(selected)}>{success ? "Билет куплен" : purchasing ? "Оформляем…" : "Купить билет"}</PrimaryButton></div>
    <p className="picker-note">Комбинация фиксируется после подтверждения покупки.</p>
  </div>;
}

function BottomNavigation({ view, activeTickets, cartCount, onChange }: { view: View; activeTickets: number; cartCount: number; onChange: (view: View) => void }) {
  const items: { id: View; label: string; icon: "home" | "live" | "ticket" | "cart"; count: number }[] = [
    { id: "home", label: "Главная", icon: "home", count: 0 },
    { id: "live", label: "Эфир", icon: "live", count: 0 },
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
  const [liveFeed, setLiveFeed] = useState<LiveFeed | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [cart, setCart] = useState<CartTicket[]>(() => loadCart(cartTtl));
  const [pickerLottery, setPickerLottery] = useState<Lottery | null>(null);
  const [pickerInitialNumbers, setPickerInitialNumbers] = useState<number[]>([]);
  const [loading, setLoading] = useState(authenticated);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [liveLoading, setLiveLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [purchaseSuccess, setPurchaseSuccess] = useState(false);
  const [purchaseProgress, setPurchaseProgress] = useState<{ done: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const [serverOffset, setServerOffset] = useState(0);

  const applyDashboard = useCallback((value: Dashboard) => {
    setDashboard(value);
    setServerOffset(new Date(value.server_time).getTime() - Date.now());
  }, []);

  const refreshDashboard = useCallback(async () => {
    if (!authenticated) return null;
    const value = await miniAppApi.dashboard(initData);
    applyDashboard(value);
    return value;
  }, [applyDashboard, authenticated, initData]);

  const refreshLive = useCallback(async () => {
    if (!authenticated) return;
    const requestedAt = Date.now();
    const feed = await miniAppApi.live(initData);
    const receivedAt = Date.now();
    setServerOffset(new Date(feed.server_time).getTime() - (requestedAt + receivedAt) / 2);
    setLiveFeed(feed);
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
    prepare.then(refreshDashboard).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить K-Loto.")).finally(() => setLoading(false));
  }, [authenticated, initData, localDev, refreshDashboard]);
  useEffect(() => {
    if (!authenticated) return;
    const timer = window.setInterval(() => void refreshDashboard().catch(() => undefined), 15_000);
    const resync = () => { if (document.visibilityState === "visible") void refreshDashboard().catch(() => undefined); };
    document.addEventListener("visibilitychange", resync);
    return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", resync); };
  }, [authenticated, refreshDashboard]);
  useEffect(() => {
    if (view !== "tickets" || !authenticated) return;
    miniAppApi.tickets(initData, ticketView).then(setTickets).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты.")).finally(() => setTicketsLoading(false));
  }, [authenticated, initData, ticketView, view]);
  useEffect(() => {
    if (view !== "live" || !authenticated) return;
    const initial = window.setTimeout(() => {
      void refreshLive().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось подключиться к эфиру.")).finally(() => setLiveLoading(false));
    }, 0);
    const timer = window.setInterval(() => void refreshLive().catch(() => undefined), 2_000);
    const resync = () => { if (document.visibilityState === "visible") void refreshLive().catch(() => undefined); };
    document.addEventListener("visibilitychange", resync);
    return () => { window.clearTimeout(initial); window.clearInterval(timer); document.removeEventListener("visibilitychange", resync); };
  }, [authenticated, refreshLive, view]);

  const nearestLottery = useMemo(() => dashboard?.lotteries.filter((item) => item.scheduled_at).sort((left, right) => new Date(left.scheduled_at ?? 0).getTime() - new Date(right.scheduled_at ?? 0).getTime())[0] ?? null, [dashboard]);
  const firstAvailable = dashboard?.lotteries.find((item) => item.purchase_available) ?? null;
  const repeatTicket = dashboard?.recent_results.find((ticket) => dashboard.lotteries.some((lottery) => lottery.code === ticket.lottery_code && lottery.purchase_available)) ?? null;
  const cartPreview = cart.slice(0, 50);
  const serverNow = now + serverOffset;

  const openLottery = async (lotteryCode: string, initialNumbers: number[] = []) => {
    setError(null);
    try {
      const fresh = await refreshDashboard();
      const lottery = fresh?.lotteries.find((item) => item.code === lotteryCode && item.purchase_available);
      if (!lottery) {
        setNotice("Продажи для выбранного тиража уже завершены. Показываем актуальное расписание.");
        setView("home");
        return;
      }
      setPickerInitialNumbers(initialNumbers.length === lottery.numbers_to_pick ? initialNumbers : []);
      setPickerLottery(lottery);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось обновить состояние продаж.");
    }
  };

  const addManyToCart = (lottery: Lottery, combinations: number[][]) => {
    const available = CART_MAX_TICKETS - cart.length;
    const accepted = combinations.slice(0, available);
    if (!accepted.length) {
      errorHaptic();
      setError(`В корзине может быть не более ${CART_MAX_TICKETS} билетов.`);
      return;
    }
    setCart((current) => [...current, ...accepted.map((numbers) => ({ id: crypto.randomUUID(), lotteryCode: lottery.code, lotteryName: lottery.name, price: lottery.ticket_price ?? 0, numbers: [...numbers] }))]);
    successHaptic();
    setNotice(accepted.length === 1 ? "Комбинация добавлена в корзину" : `${accepted.length} комбинаций добавлено в корзину`);
    setPickerLottery(null);
    setView("cart");
  };

  const requestPurchase = async (lotteryCode: string, combinations: number[][]) => {
    const idempotencyKey = crypto.randomUUID();
    try {
      return await miniAppApi.purchase(initData, lotteryCode, combinations, idempotencyKey);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status < 500) throw reason;
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      return miniAppApi.purchase(initData, lotteryCode, combinations, idempotencyKey);
    }
  };

  const purchaseSingle = async (lotteryCode: string, numbers: number[]) => {
    if (purchasing) return;
    setPurchasing(true); setPurchaseSuccess(false); setError(null);
    try {
      const result = await requestPurchase(lotteryCode, [numbers]);
      setPurchaseSuccess(true); successHaptic();
      setNotice(`Билет куплен · списано ${formatCas(result.total_cost)}`);
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
    if (purchasing || cart.length === 0) return;
    const groups = new Map<string, CartTicket[]>();
    for (const item of cart) groups.set(item.lotteryCode, [...(groups.get(item.lotteryCode) ?? []), item]);
    const total = cart.length;
    let done = 0;
    let totalCost = 0;
    setPurchasing(true); setPurchaseSuccess(false); setError(null); setPurchaseProgress({ done, total });
    try {
      for (const [lotteryCode, ticketsForLottery] of groups) {
        for (const batch of batchItems(ticketsForLottery)) {
          const result = await requestPurchase(lotteryCode, batch.map((ticket) => ticket.numbers));
          const purchasedIds = new Set(batch.map((ticket) => ticket.id));
          setCart((current) => current.filter((ticket) => !purchasedIds.has(ticket.id)));
          done += batch.length;
          totalCost += result.total_cost;
          setPurchaseProgress({ done, total });
          setDashboard((current) => current ? { ...current, balance: result.balance_after } : current);
        }
      }
      setPurchaseSuccess(true); successHaptic();
      setNotice(`${done} билетов куплено · списано ${formatCas(totalCost)}`);
      await refreshDashboard();
      await new Promise((resolve) => window.setTimeout(resolve, 480));
      setTicketsLoading(true); setView("tickets"); setTicketView("active");
    } catch (reason) {
      errorHaptic();
      setError(`${done ? `Куплено ${done} из ${total}. ` : ""}${reason instanceof ApiError ? reason.message : "Покупка прервана. Непроданные билеты остались в корзине."}`);
    } finally {
      setPurchasing(false); setPurchaseSuccess(false); setPurchaseProgress(null);
    }
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
  if (pickerLottery) return <main className="app-shell picker-page"><NumberPicker lottery={pickerLottery} purchasing={purchasing} success={purchaseSuccess} initialNumbers={pickerInitialNumbers} cartRemaining={CART_MAX_TICKETS - cart.length} onAdd={(numbers) => addManyToCart(pickerLottery, [numbers])} onAddMany={(combinations) => addManyToCart(pickerLottery, combinations)} onBuy={(numbers) => void purchaseSingle(pickerLottery.code, numbers)} onClose={() => setPickerLottery(null)} /></main>;

  return <main className="app-shell">
    <header className="app-header"><div className="wordmark"><span>K</span><div>K LOTO<small>ЦИФРОВАЯ ЛОТЕРЕЯ</small></div></div><div className="header-actions">{localDev && <button className="dev-badge" onClick={() => void refillDevBalance()} type="button">+ TEST CAS</button>}<Balance value={dashboard.balance} /></div></header>
    {(error || notice) && <button className={`toast ${error ? "error" : "success"}`} onClick={() => { setError(null); setNotice(null); }} type="button"><span>{error ? "!" : "✓"}</span>{error ?? notice}<Icon name="close" /></button>}

    {view === "home" && <section className="view-content" key="home">
      <div className="hero-copy refreshed"><span className="eyebrow">Сегодня в K-Loto</span><h1>Ваш следующий шанс<br /><em>уже совсем близко.</em></h1><p>Выберите комбинацию — результат и выигрыш появятся здесь автоматически.</p></div>
      {nearestLottery && <NextDraw lottery={nearestLottery} now={serverNow} onLive={() => { setLiveLoading(true); setView("live"); }} onPlay={() => void openLottery(nearestLottery.code)} />}
      <div className="quick-actions" aria-label="Быстрые действия"><button onClick={() => { setTicketsLoading(true); setView("tickets"); }} type="button"><Icon name="ticket" /><span><strong>Мои билеты</strong><small>{dashboard.active_ticket_count ? `${dashboard.active_ticket_count} активных` : "Пока нет активных"}</small></span></button>{firstAvailable && <button onClick={() => void openLottery(firstAvailable.code, randomCombination(firstAvailable.max_number, firstAvailable.numbers_to_pick))} type="button"><Icon name="spark" /><span><strong>Случайный билет</strong><small>Комбинация в один тап</small></span></button>}{repeatTicket && <button onClick={() => void openLottery(repeatTicket.lottery_code, repeatTicket.numbers)} type="button"><Icon name="repeat" /><span><strong>Повторить</strong><small>Последняя комбинация</small></span></button>}</div>
      <div className="section-heading"><div><span className="eyebrow">Игровая коллекция</span><h2>Лотереи</h2></div><span className="section-count">Доступно: {dashboard.lotteries.length}</span></div>
      <div className="lottery-list">{dashboard.lotteries.map((lottery, index) => <LotteryCard key={lottery.code} lottery={lottery} now={serverNow} index={index} onPlay={() => void openLottery(lottery.code)} />)}</div>
      <div className="section-heading"><div><span className="eyebrow">Недавнее</span><h2>Последние результаты</h2></div><button className="text-button" onClick={() => { setTicketsLoading(true); setView("tickets"); setTicketView("history"); }} type="button">Смотреть все <span>→</span></button></div>
      {dashboard.recent_results.length ? dashboard.recent_results.map((ticket, index) => <TicketCard index={index} key={ticket.id} ticket={ticket} />) : <EmptyState title="История пока пуста" text="Результаты сыгранных билетов появятся здесь после первого тиража." />}
    </section>}

    {view === "live" && <section className="view-content live-view" key="live">
      <LiveView feed={liveFeed} now={serverNow} loading={liveLoading} onPlay={(code) => void openLottery(code)} onTickets={() => { setTicketsLoading(true); setView("tickets"); }} />
    </section>}

    {view === "tickets" && <section className="view-content" key="tickets">
      <div className="page-title"><span className="eyebrow">Личный архив</span><h1>Мои билеты</h1><p>Активные комбинации и результаты тиражей.</p></div>
      <div className={`segmented-control ${ticketView}`}><i /><button className={ticketView === "active" ? "selected" : ""} onClick={() => { selectionHaptic(); setTicketsLoading(true); setTicketView("active"); }} type="button">Активные</button><button className={ticketView === "history" ? "selected" : ""} onClick={() => { selectionHaptic(); setTicketsLoading(true); setTicketView("history"); }} type="button">История</button></div>
      {ticketsLoading ? <div className="ticket-skeletons"><div className="skeleton ticket-skeleton" /><div className="skeleton ticket-skeleton" /></div> : tickets.length ? tickets.map((ticket, index) => <TicketCard index={index} key={ticket.id} ticket={ticket} />) : <EmptyState title={ticketView === "active" ? "Нет активных билетов" : "История пока пуста"} text={ticketView === "active" ? "Выберите лотерею и соберите свою комбинацию." : "Завершённые билеты появятся после розыгрыша."} action={ticketView === "active" && firstAvailable ? { label: "Выбрать лотерею", onClick: () => setView("home") } : undefined} />}
      {ticketView === "active" && firstAvailable && !ticketsLoading && tickets.length > 0 && <PrimaryButton className="sticky-action" onClick={() => void openLottery(firstAvailable.code)}>Ещё один билет</PrimaryButton>}
    </section>}

    {view === "cart" && <section className="view-content" key="cart">
      <div className="page-title cart-title"><span className="eyebrow">Перед покупкой</span><h1>Корзина</h1><p>{cart.length ? `${cart.length} ${plural(cart.length, "комбинация", "комбинации", "комбинаций")}` : "Пока без комбинаций"}</p></div>
      {cart.length ? <><div className="cart-toolbar"><span>До лимита: {CART_MAX_TICKETS - cart.length}</span><button disabled={purchasing} onClick={() => setCart([])} type="button">Очистить</button></div><div className="cart-list">{cartPreview.map((ticket, index) => <article className="cart-ticket" key={ticket.id} style={{ "--item-index": index } as CSSProperties}><div className="cart-ticket-head"><div><span className="eyebrow">{ticket.lotteryName}</span><strong>Комбинация {index + 1}</strong></div><button className="remove-button" onClick={() => { selectionHaptic(); setCart((current) => current.filter((item) => item.id !== ticket.id)); }} type="button" aria-label={`Удалить билет ${index + 1}`}><Icon name="close" /></button></div><NumberSet values={ticket.numbers} /><div className="cart-ticket-price"><span>Стоимость</span><strong>{formatCas(ticket.price)}</strong></div></article>)}</div>{cart.length > cartPreview.length && <div className="cart-overflow">Ещё {cart.length - cartPreview.length} комбинаций готовы к покупке. Для скорости показаны первые 50.</div>}<div className="cart-total"><div><span>К оплате</span><small>{cart.length} бил.</small></div><strong>{formatCas(cart.reduce((sum, item) => sum + item.price, 0))}</strong></div>{purchaseProgress && <div className="purchase-progress"><div><span>Покупаем билеты</span><strong>{purchaseProgress.done} из {purchaseProgress.total}</strong></div><i><span style={{ width: `${(purchaseProgress.done / purchaseProgress.total) * 100}%` }} /></i></div>}<button className="secondary-button" disabled={!firstAvailable || purchasing || cart.length >= CART_MAX_TICKETS} onClick={() => firstAvailable && void openLottery(firstAvailable.code)} type="button">Добавить комбинацию</button><PrimaryButton loading={purchasing} success={purchaseSuccess} onClick={() => void purchaseCart()}>{purchaseSuccess ? "Билеты куплены" : purchasing ? `Покупаем ${purchaseProgress?.done ?? 0} из ${purchaseProgress?.total ?? cart.length}` : `Купить ${cart.length} бил.`}</PrimaryButton></> : <EmptyState title="Корзина пока пуста" text="Выберите лотерею, отметьте числа и сохраните комбинацию перед покупкой." action={{ label: "Выбрать лотерею", onClick: () => setView("home") }} />}
    </section>}

    <BottomNavigation view={view} activeTickets={dashboard.active_ticket_count} cartCount={cart.length} onChange={(target) => { if (target === "tickets") setTicketsLoading(true); if (target === "live") setLiveLoading(true); setView(target); }} />
  </main>;
}
