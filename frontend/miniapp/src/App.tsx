import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { motion } from "motion/react";

import { ApiError, miniAppApi } from "./api";
import { CART_MAX_TICKETS, configuredCartTtl, loadCart, saveCart } from "./cart";
import {
  Balance,
  EmptyState,
  Icon,
  NumberSet,
  PrimaryButton,
  SignalSet,
  Skeleton,
  StatusBadge,
} from "./components";
import { countdown, formatCas, formatDraw, formatDrawLabel, formatMoscow, formatMoscowTime, formatTicketLabel } from "./format";
import { MINIAPP_TEXTS as copy } from "./content";
import { LiveView } from "./LiveView";
import { FastPicker, FastView } from "./FastView";
import { isFastLottery } from "./fast";
import { LotteryVisual } from "./LotteryVisuals";
import { randomCombination } from "./random";
import { errorHaptic, requestTelegramWriteAccess, selectionHaptic, successHaptic } from "./telegram";
import type { Account, CartTicket, Dashboard, Favorite, LiveFeed, Lottery, NotificationPreferences, Ticket, UserNotification } from "./types";

type View = "home" | "live" | "fast" | "account" | "cart";
type TicketView = "active" | "history";
type AccountView = "overview" | "tickets" | "notifications";

interface AppProps {
  initData: string;
  localDev?: boolean;
}

function initialView(): View {
  if (import.meta.env.VITE_DESIGN_PREVIEW !== "true") return "home";
  const screen = new URLSearchParams(window.location.search).get("screen");
  return screen === "live" || screen === "fast" || screen === "account" || screen === "cart" ? screen : "home";
}

function plural(value: number, one: string, few: string, many: string): string {
  const lastTwo = value % 100;
  const last = value % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return many;
  if (last === 1) return one;
  if (last >= 2 && last <= 4) return few;
  return many;
}

const salesLabels: Record<Lottery["sales_status"], string> = {
  OPEN: "Продажи открыты",
  CLOSING_SOON: "Скоро закроются",
  CLOSED: "Продажи закрыты",
  DRAWING: "Идёт розыгрыш",
  COMPLETED: "Тираж завершён",
};

function TicketCard({ ticket, index = 0 }: { ticket: Ticket; index?: number }) {
  const complete = ticket.status === "SETTLED";
  const winner = complete && ticket.prize_amount > 0;
  const matches = ticket.matches ?? 0;
  return <article className={`ticket-card ${winner ? "winner" : ""}`} style={{ "--item-index": index } as CSSProperties}>
    <div className="ticket-meta">
      <div><span className="eyebrow">{ticket.lottery_name}{ticket.source === "AUTO_PLAY" ? " · АВТОБИЛЕТ" : ""}</span><h3>{formatTicketLabel(ticket.lottery_code, ticket.public_number)}</h3></div>
      <StatusBadge active={!complete} />
    </div>
    {isFastLottery(ticket.lottery_code) ? <SignalSet values={ticket.numbers} winning={ticket.winning_numbers} code={ticket.lottery_code as "flash" | "shadow"} /> : <NumberSet values={ticket.numbers} winning={ticket.winning_numbers} animate={winner} />}
    <div className="ticket-footer"><span>{formatDrawLabel(ticket.lottery_code, ticket.draw_number)}</span><span>{formatMoscow(ticket.scheduled_at)} МСК</span></div>
    {complete && <div className={`ticket-result ${winner ? "win" : "loss"}`}>
      <div><span>{matches > 0 ? `Совпадений: ${matches}` : "Совпадений нет"}</span><small>{winner ? "Выигрыш зачислен" : "Без выигрыша"}</small></div>
      <strong>{winner ? `+${formatCas(ticket.prize_amount)}` : "0 CAS"}</strong>
    </div>}
  </article>;
}

function TicketGroups({ tickets }: { tickets: Ticket[] }) {
  const groups = new Map<string, Ticket[]>();
  for (const ticket of tickets) {
    const key = `${ticket.lottery_code}:${ticket.draw_number}`;
    groups.set(key, [...(groups.get(key) ?? []), ticket]);
  }
  return <div className="ticket-groups">{Array.from(groups.entries()).map(([key, items]) => {
    const first = items[0];
    return <section className={`ticket-draw-group lottery-${first.lottery_code}`} key={key}><header><div><span className="eyebrow">{first.lottery_name}</span><h2>{formatDrawLabel(first.lottery_code, first.draw_number)}</h2></div><div><strong>{items.length}</strong><small>{plural(items.length, "билет", "билета", "билетов")}</small></div></header><div className="ticket-group-list">{items.map((ticket, index) => <TicketCard index={index} key={ticket.id} ticket={ticket} />)}</div></section>;
  })}</div>;
}

function NextDraw({ lottery, now, nearest, onLive, onPlay }: { lottery: Lottery; now: number; nearest: boolean; onLive: () => void; onPlay: () => void }) {
  const startsIn = lottery.scheduled_at ? new Date(lottery.scheduled_at).getTime() - now : Infinity;
  return <motion.section animate={{ opacity: 1, y: 0 }} className={`next-draw featured-draw lottery-${lottery.code}`} initial={{ opacity: 0, y: 10 }} transition={{ duration: .34, ease: [0.2, 0.75, 0.25, 1] }}>
    <div className="hero-scene"><LotteryVisual code={lottery.code} /></div>
    <header className="draw-product-bar"><span><i />{nearest ? "Ближайший тираж" : "Выбранная лотерея"}</span><b>{lottery.kind} · {lottery.numbers_to_pick} ИЗ {lottery.max_number}</b></header>
    <div className="draw-product-title"><div><strong>{lottery.name}</strong><span>{lottery.draw_number ? formatDrawLabel(lottery.code, lottery.draw_number) : "Расписание готовится"}</span></div></div>
    <div className="featured-jackpot"><span>{lottery.code === "september" ? copy.september.mainPrizeLabel : "Джекпот"}</span><strong>{formatCas(lottery.jackpot)}</strong></div>
    {lottery.code === "september" && <p className="september-moodline">{copy.september.moodline}</p>}
    {lottery.code === "grob" && <p className="grob-moodline">{copy.grob.moodline}</p>}
    <div className="draw-control-panel"><div className="countdown"><span>До старта</span><strong>{countdown(lottery.scheduled_at, now)}</strong><small>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Дата уточняется"}</small></div><div className="draw-player-stat"><span>Ваши билеты</span><strong>{lottery.player_ticket_count}</strong><small>{lottery.sales_close_at ? `До ${formatMoscowTime(lottery.sales_close_at)} МСК` : ""}</small></div></div>
    <div className="featured-meta"><span className={`sales-state ${lottery.sales_status.toLowerCase()}`}>{salesLabels[lottery.sales_status]}</span></div>
    <div className="featured-actions"><button className="live-cta" onClick={onLive} type="button"><Icon name="live" /> {startsIn <= 5 * 60_000 ? copy.actions.watchLive : copy.actions.openLive}</button><PrimaryButton className="split-button" disabled={!lottery.scheduled_at || lottery.ticket_price === null} onClick={onPlay}><b>{lottery.purchase_available ? copy.actions.chooseNumbers : "Проверить продажи"}</b><small>{lottery.ticket_price !== null ? formatCas(lottery.ticket_price) : "—"}</small></PrimaryButton></div>
  </motion.section>;
}

function LotterySwitcher({ lotteries, selected, now, onSelect }: { lotteries: Lottery[]; selected: string; now: number; onSelect: (code: string) => void }) {
  return <div className="lottery-switcher" aria-label="Расписание лотерей">{lotteries.map((lottery, index) => <motion.button aria-label={`${lottery.name} · ${lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "нет тиража"}`} aria-pressed={selected === lottery.code} className={`lottery-switch lottery-${lottery.code} ${selected === lottery.code ? "selected" : ""}`} key={lottery.code} onClick={() => { selectionHaptic(); onSelect(lottery.code); }} type="button" whileTap={{ scale: .97 }}><small>{String(index + 1).padStart(2, "0")}</small><span>{lottery.name.replace("-Лото", "").replace("-лото", "")}</span><strong>{lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "—"}</strong><i>{lottery.scheduled_at ? countdown(lottery.scheduled_at, now) : "Нет тиража"}</i>{selected === lottery.code && <b />}</motion.button>)}</div>;
}

function NumberPicker({ lottery, purchasing, success, initialNumbers = [], favorites, cartRemaining, onClose, onBuy, onAdd, onAddMany, onSaveFavorite, onDeleteFavorite }: { lottery: Lottery; purchasing: boolean; success: boolean; initialNumbers?: number[]; favorites: Favorite[]; cartRemaining: number; onClose: () => void; onBuy: (numbers: number[], drawCount: 1 | 5) => void; onAdd: (numbers: number[], drawCount: 1 | 5) => void; onAddMany: (combinations: number[][], drawCount: 1 | 5) => void; onSaveFavorite: (numbers: number[]) => void; onDeleteFavorite: (id: string) => void }) {
  const [selected, setSelected] = useState<number[]>(initialNumbers);
  const [drawCount, setDrawCount] = useState<1 | 5>(1);
  const ready = selected.length === lottery.numbers_to_pick;
  const saved = favorites.some((favorite) => favorite.numbers.length === selected.length && favorite.numbers.every((value, index) => value === selected[index]));
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
  const numberGroups = lottery.code === "september"
    ? [[1, 11], [12, 22], [23, 33]] as const
    : [[1, lottery.max_number]] as const;
  const pickerMood: Record<string, string> = {
    september: "Три главы одного сентябрьского вечера",
    pll: "Ночная координатная сетка",
    pss: "Тишина северного озера перед грозой",
    khan: "Четыре знака для одного тиража",
    weekly: "Соберите персональный клубный билет",
    grob: "Три числа. Одна аккуратно оформленная могила.",
  };

  return <div className={`picker-shell lottery-${lottery.code}`}>
    <div className="picker-heading"><div className="picker-scene"><LotteryVisual code={lottery.code} context="picker" /></div><button className="icon-button" onClick={onClose} type="button" aria-label="Закрыть"><Icon name="arrow" /></button><div><span className="eyebrow">{lottery.name} · {formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</span><h1>Выберите {lottery.numbers_to_pick} чисел</h1><p>{pickerMood[lottery.code] ?? "Ваша комбинация на ближайший тираж"}</p></div></div>
    {lottery.code === "september" && <div className="september-picker-note"><span>03 / 09</span><strong>{copy.september.pickerInstruction}</strong></div>}
    <div className="picker-summary"><div><span>К оплате за комбинацию</span><strong>{formatCas((lottery.ticket_price ?? 0) * drawCount)}</strong></div><div className="selection-meter"><span>Выбрано</span><strong>{selected.length}<i>/ {lottery.numbers_to_pick}</i></strong></div></div>
    <div className="picker-board"><div className="picker-board-label"><span>{lottery.code === "grob" ? "Поле захоронений" : "Поле комбинации"}</span><small>{lottery.code === "september" ? "Три части · 33 числа" : `${lottery.max_number} чисел · выберите ${lottery.numbers_to_pick}`}</small></div><div className="number-grid" aria-label="Выбор чисел">{numberGroups.map(([from, to], groupIndex) => <div className="number-group" key={from}>{lottery.code === "september" && <span className="number-group-label">{groupIndex === 0 ? "Начало" : groupIndex === 1 ? "Середина" : "После"}</span>}{Array.from({ length: to - from + 1 }, (_, index) => from + index).map((value) => <motion.button aria-pressed={selected.includes(value)} className={selected.includes(value) ? "pick-number selected" : "pick-number"} key={value} onClick={() => toggle(value)} type="button" whileTap={{ scale: lottery.code === "grob" ? .82 : .88 }}><span>{value}</span><i aria-hidden="true" /></motion.button>)}</div>)}</div></div>
    <div className="selected-combination"><span>{lottery.code === "grob" ? "Ваша могила" : "Ваш билет"}</span><div>{Array.from({ length: lottery.numbers_to_pick }, (_, index) => <i className={selected[index] ? "filled" : ""} key={index}>{selected[index] ?? "—"}</i>)}</div></div>
    <button className="secondary-button random-button" onClick={randomize} type="button"><Icon name="spark" />{copy.actions.randomNumbers}</button>
    <section className="multi-draw-choice"><div><strong>Повторить комбинацию</strong><small>Без автопродления и скрытых списаний</small></div><div><button className={drawCount === 1 ? "selected" : ""} onClick={() => setDrawCount(1)} type="button">1 тираж</button><button className={drawCount === 5 ? "selected" : ""} onClick={() => setDrawCount(5)} type="button">5 тиражей</button></div>{drawCount === 5 && <p>Эти числа участвуют в текущем и следующих 4 тиражах. Полная сумма оплачивается сейчас.</p>}</section>
    {ready && <button className={`favorite-action ${saved ? "saved" : ""}`} disabled={saved} onClick={() => onSaveFavorite(selected)} type="button">{saved ? "★ Комбинация сохранена" : "☆ Сохранить комбинацию"}</button>}
    {favorites.length > 0 && <div className="favorite-list"><span>Избранные</span>{favorites.map((favorite) => <div key={favorite.id}><button onClick={() => setSelected(favorite.numbers)} type="button">{favorite.numbers.join(" · ")}</button><button aria-label="Удалить из избранного" onClick={() => onDeleteFavorite(favorite.id)} type="button">×</button></div>)}</div>}
    <div className="quick-batches"><div><span>Быстрая корзина</span><small>Случайные комбинации</small></div><div>{[5, 10, 25, 50, 100].map((count) => <button disabled={purchasing || cartRemaining < count} key={count} onClick={() => onAddMany(Array.from({ length: count }, () => randomCombination(lottery.max_number, lottery.numbers_to_pick)), drawCount)} type="button">+{count}</button>)}</div></div>
    <div className="picker-actions"><button className="secondary-button" disabled={!ready || purchasing} onClick={() => onAdd(selected, drawCount)} type="button">{copy.actions.addToCart}</button><PrimaryButton disabled={!ready} loading={purchasing} success={success} onClick={() => onBuy(selected, drawCount)}>{success ? "Билет куплен" : purchasing ? "Оформляем…" : drawCount === 5 ? copy.actions.buyFiveDraws : copy.actions.buyTicket}</PrimaryButton></div>
    <p className="picker-note">Комбинация фиксируется после подтверждения покупки.</p>
  </div>;
}

function BottomNavigation({ view, unreadNotifications, onChange }: { view: View; unreadNotifications: number; onChange: (view: View) => void }) {
  const items: { id: View; label: string; icon: "home" | "live" | "fast" | "profile"; count: number }[] = [
    { id: "home", label: copy.navigation.home, icon: "home", count: 0 },
    { id: "live", label: copy.navigation.live, icon: "live", count: 0 },
    { id: "fast", label: copy.navigation.fast, icon: "fast", count: 0 },
    { id: "account", label: copy.navigation.account, icon: "profile", count: unreadNotifications },
  ];
  return <nav className="bottom-nav" aria-label="Основная навигация">{items.map((item) => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => { selectionHaptic(); onChange(item.id); }} type="button"><i className="nav-indicator" /><span><Icon name={item.icon} />{item.count > 0 && <small>{item.count}</small>}</span><b>{item.label}</b></button>)}</nav>;
}

function AccountOverview({ account, onEnableTelegram, onSavePreferences }: { account: Account; onEnableTelegram: () => void; onSavePreferences: (preferences: NotificationPreferences) => void }) {
  const preferences = account.notification_preferences;
  const winRate = account.ticket_count ? Math.round((account.winning_ticket_count / account.ticket_count) * 100) : 0;
  return <div className="account-overview">
    <section className="account-identity"><div className="account-monogram"><span>{account.display_name.slice(0, 1)}</span><i /></div><div className="account-name"><span>{copy.account.playerLabel}</span><h2>{account.display_name}</h2><small>Участник клуба · {account.ticket_count} {plural(account.ticket_count, "билет", "билета", "билетов")}</small></div><div className="account-balance"><span>Доступно</span><strong>{formatCas(account.balance)}</strong></div></section>
    <section className="account-highlight"><div><span>Главный результат</span><strong>{formatCas(account.best_win)}</strong><small>ваш лучший выигрыш</small></div><div className="account-highlight-art" aria-hidden="true"><i /><i /><b /></div></section>
    <section className="account-scoreline"><article><span>В игре сейчас</span><strong>{account.active_ticket_count}</strong></article><article><span>Выигрышных</span><strong>{winRate}%</strong></article><article><span>Получено</span><strong>{formatCas(account.total_won)}</strong></article></section>
    <section className="account-ledger"><header><span>Ваша игровая история</span><small>За всё время</small></header><div><span>Куплено билетов</span><strong>{account.ticket_count}</strong></div><div><span>Выигрышных билетов</span><strong>{account.winning_ticket_count}</strong></div><div><span>Участие в тиражах</span><strong>{formatCas(account.total_spent)}</strong></div></section>
    <section className="notification-settings"><header><div><span>{copy.notifications.title}</span><strong>{preferences.telegram_enabled ? copy.notifications.enabled : copy.notifications.disabled}</strong></div><i className={preferences.telegram_enabled ? "enabled" : ""} /></header><p>{copy.notifications.explanation}</p>{preferences.telegram_enabled ? <button className="secondary-button notification-toggle" onClick={() => onSavePreferences({ telegram_enabled: false, draw_results_enabled: true, inactivity_reminders_enabled: true })} type="button">{copy.notifications.disable}</button> : <PrimaryButton onClick={onEnableTelegram}>{copy.notifications.enable}</PrimaryButton>}</section>
  </div>;
}

function NotificationCenter({ notifications, onPlay, onTickets }: { notifications: UserNotification[]; onPlay: () => void; onTickets: () => void }) {
  if (!notifications.length) return <EmptyState title={copy.notifications.emptyTitle} text={copy.notifications.emptyText} />;
  return <div className="inbox-list">{notifications.map((item) => {
    const isWin = item.type === "WIN";
    const isFastResult = item.type === "DRAW_RESULT";
    const isJackpot = item.type === "JACKPOT_NEWS";
    return <article className={`${isWin ? "win" : isFastResult ? "result" : isJackpot ? "news" : "invite"} ${item.read_at ? "read" : "unread"}`} key={item.id}><div className="inbox-symbol">{isWin ? "+" : isFastResult ? "ϟ" : isJackpot ? "J" : "K"}</div><div><header><strong>{item.title}</strong><time>{formatMoscow(item.created_at)} МСК</time></header><p>{item.body}</p><button onClick={isWin || isFastResult ? onTickets : onPlay} type="button">{isWin || isFastResult ? copy.actions.openTickets : copy.actions.chooseNumbers}<span>→</span></button></div></article>;
  })}</div>;
}

function CartView({ cart, groups, purchasing, success, progress, canAdd, onClear, onRemove, onAdd, onBuy, onHome }: { cart: CartTicket[]; groups: CartTicket[][]; purchasing: boolean; success: boolean; progress: { done: number; total: number } | null; canAdd: boolean; onClear: () => void; onRemove: (id: string) => void; onAdd: () => void; onBuy: () => void; onHome: () => void }) {
  const total = cart.reduce((sum, item) => sum + item.price * item.drawCount, 0);
  if (!cart.length) return <div className="cart-empty"><div className="cart-empty-art" aria-hidden="true"><span /><i /><b>+</b></div><span className="eyebrow">Ваш следующий билет</span><h1>Корзина пока пуста</h1><p>Соберите комбинацию — мы аккуратно сохраним её здесь до оформления.</p><button className="cart-empty-action" onClick={onHome} type="button">Выбрать лотерею <span>→</span></button></div>;

  return <div className="cart-layout">
    <header className="cart-header"><div><span className="eyebrow">Готово к оформлению</span><h1>{cart.length} {plural(cart.length, "комбинация", "комбинации", "комбинаций")}</h1></div><button disabled={purchasing} onClick={onClear} type="button">Очистить</button></header>
    <div className="cart-groups">{groups.map((items, groupIndex) => <motion.section animate={{ opacity: 1, y: 0 }} className={`cart-group lottery-${items[0].lotteryCode}`} initial={{ opacity: 0, y: 9 }} key={`${items[0].lotteryCode}:${items[0].drawCount}`} transition={{ delay: groupIndex * .05 }}><header><div><span>{items[0].lotteryName}</span><strong>В группе: {items.length}</strong></div><div><small>{items[0].drawCount === 5 ? "на 5 тиражей" : "ближайший тираж"}</small><b>{formatCas(items.reduce((sum, item) => sum + item.price * item.drawCount, 0))}</b></div></header><div className="cart-ticket-stack">{items.slice(0, 5).map((ticket, index) => <article className="cart-combination" key={`${ticket.id}:${index}`}><span>{String(index + 1).padStart(2, "0")}</span><NumberSet values={ticket.numbers} /><button className="remove-button" onClick={() => { selectionHaptic(); onRemove(ticket.id); }} type="button" aria-label={`Удалить билет ${index + 1}`}><Icon name="close" /></button></article>)}{items.length > 5 && <p>+ ещё {items.length - 5} — оформим одной операцией</p>}</div></motion.section>)}</div>
    {progress && <div className="purchase-progress"><div><span>Оформляем билеты</span><strong>{progress.done} из {progress.total}</strong></div><i><span style={{ width: `${(progress.done / progress.total) * 100}%` }} /></i></div>}
    <aside className="cart-checkout"><div className="checkout-receipt"><span>Итого</span><strong>{formatCas(total)}</strong><small>{cart.length} комб. · безопасная покупка одной операцией</small></div><button aria-label="Добавить комбинацию" className="checkout-add" disabled={!canAdd || purchasing} onClick={onAdd} type="button">+ Добавить ещё</button><PrimaryButton className="checkout-buy" loading={purchasing} success={success} onClick={onBuy}>{success ? "Билеты куплены" : purchasing ? `Оформляем ${progress?.done ?? 0} из ${progress?.total ?? cart.length}` : `Купить ${cart.length} комб.`}</PrimaryButton></aside>
  </div>;
}

function PurchaseConfirmation({ count, cost, onClose, onHome, onTickets }: { count: number; cost: number; onClose: () => void; onHome: () => void; onTickets: () => void }) {
  return <div className="purchase-confirmation-backdrop" onClick={onClose} role="presentation"><motion.section animate={{ opacity: 1, y: 0, scale: 1 }} aria-modal="true" className="purchase-confirmation" initial={{ opacity: 0, y: 12, scale: .98 }} onClick={(event) => event.stopPropagation()} role="dialog" transition={{ duration: .28 }}>
    <button aria-label="Закрыть сообщение" className="purchase-confirmation-close" onClick={onClose} type="button"><Icon name="close" /></button>
    <div className="purchase-confirmation-mark">✓</div>
    <span className="eyebrow">Покупка завершена</span>
    <h2>{count === 1 ? "Билет уже участвует" : `${count} ${plural(count, "билет участвует", "билета участвуют", "билетов участвуют")}`}</h2>
    <p>Списано {formatCas(cost)}. Билет сохранён и появится в результатах после тиража.</p>
    <div><PrimaryButton onClick={onHome}>На главную</PrimaryButton><button className="secondary-button" onClick={onTickets} type="button">Мои билеты</button></div>
  </motion.section></div>;
}

export default function App({ initData, localDev = false }: AppProps) {
  const authenticated = Boolean(initData) || localDev;
  const [cartTtl] = useState(() => configuredCartTtl());
  const [view, setView] = useState<View>(initialView);
  const [accountView, setAccountView] = useState<AccountView>("overview");
  const [ticketView, setTicketView] = useState<TicketView>("active");
  const [selectedLotteryCode, setSelectedLotteryCode] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [notifications, setNotifications] = useState<UserNotification[]>([]);
  const [liveFeed, setLiveFeed] = useState<LiveFeed | null>(null);
  const [fastFeed, setFastFeed] = useState<LiveFeed | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [cart, setCart] = useState<CartTicket[]>(() => loadCart(cartTtl));
  const [pickerLottery, setPickerLottery] = useState<Lottery | null>(null);
  const [pickerInitialNumbers, setPickerInitialNumbers] = useState<number[]>([]);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [ticketLotteryFilter, setTicketLotteryFilter] = useState("");
  const [ticketWinsOnly, setTicketWinsOnly] = useState(false);
  const [loading, setLoading] = useState(authenticated);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [liveLoading, setLiveLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [purchaseSuccess, setPurchaseSuccess] = useState(false);
  const [purchaseConfirmation, setPurchaseConfirmation] = useState<{ lotteryCode: string | null; count: number; cost: number } | null>(null);
  const [purchaseProgress, setPurchaseProgress] = useState<{ done: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showNotificationPrompt, setShowNotificationPrompt] = useState(false);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [serverOffset, setServerOffset] = useState(0);

  const applyDashboard = useCallback((value: Dashboard) => {
    setDashboard(value);
    if (import.meta.env.VITE_DESIGN_PREVIEW === "true" && new URLSearchParams(window.location.search).get("screen") === "picker") {
      const requestedCode = new URLSearchParams(window.location.search).get("lottery") ?? "september";
      setPickerLottery(value.lotteries.find((item) => item.code === requestedCode) ?? null);
    }
    if (value.app_version && value.app_version !== __APP_VERSION__) setUpdateAvailable(true);
    setServerOffset(new Date(value.server_time).getTime() - Date.now());
  }, []);

  const refreshDashboard = useCallback(async () => {
    if (!authenticated) return null;
    const value = await miniAppApi.dashboard(initData);
    applyDashboard(value);
    return value;
  }, [applyDashboard, authenticated, initData]);

  const refreshAccount = useCallback(async () => {
    if (!authenticated) return null;
    const value = await miniAppApi.account(initData);
    setAccount(value);
    return value;
  }, [authenticated, initData]);

  const refreshLive = useCallback(async () => {
    if (!authenticated) return;
    const requestedAt = Date.now();
    const feed = await miniAppApi.live(initData);
    const receivedAt = Date.now();
    setServerOffset(new Date(feed.server_time).getTime() - (requestedAt + receivedAt) / 2);
    setLiveFeed(feed);
  }, [authenticated, initData]);

  const refreshFastLive = useCallback(async () => {
    if (!authenticated) return;
    const requestedAt = Date.now();
    const feed = await miniAppApi.live(initData, "fast");
    const receivedAt = Date.now();
    setServerOffset(new Date(feed.server_time).getTime() - (requestedAt + receivedAt) / 2);
    setFastFeed(feed);
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
    prepare.then(() => Promise.all([refreshDashboard(), refreshAccount()])).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить K-Loto.")).finally(() => setLoading(false));
  }, [authenticated, initData, localDev, refreshAccount, refreshDashboard]);
  useEffect(() => {
    if (!authenticated) return;
    const timer = window.setInterval(() => void refreshDashboard().catch(() => undefined), 15_000);
    const resync = () => { if (document.visibilityState === "visible") void refreshDashboard().catch(() => undefined); };
    document.addEventListener("visibilitychange", resync);
    return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", resync); };
  }, [authenticated, refreshDashboard]);
  useEffect(() => {
    if (view !== "account" || accountView !== "tickets" || !authenticated) return;
    miniAppApi.tickets(initData, ticketView, ticketLotteryFilter, ticketWinsOnly).then(setTickets).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты.")).finally(() => setTicketsLoading(false));
  }, [accountView, authenticated, initData, ticketLotteryFilter, ticketView, ticketWinsOnly, view]);
  useEffect(() => {
    if (view !== "account" || accountView !== "notifications" || !authenticated) return;
    miniAppApi.notifications(initData).then(async (items) => {
      setNotifications(items);
      if (items.some((item) => !item.read_at)) {
        await miniAppApi.markNotificationsRead(initData);
        setNotifications((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? new Date().toISOString() })));
        await refreshAccount();
      }
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить уведомления."));
  }, [accountView, authenticated, initData, refreshAccount, view]);
  useEffect(() => {
    if (view !== "live" || !authenticated) return;
    const controller = new AbortController();
    const initial = window.setTimeout(() => {
      void refreshLive().finally(() => setLiveLoading(false));
    }, 0);
    void miniAppApi.liveStream(initData, (feed) => {
      setServerOffset(new Date(feed.server_time).getTime() - Date.now());
      setLiveFeed(feed);
      void refreshDashboard().catch(() => undefined);
    }, controller.signal).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Не удалось подключиться к эфиру.");
    });
    return () => { window.clearTimeout(initial); controller.abort(); };
  }, [authenticated, initData, refreshDashboard, refreshLive, view]);
  useEffect(() => {
    if (view !== "fast" || !authenticated) return;
    const controller = new AbortController();
    const initial = window.setTimeout(() => {
      void refreshFastLive();
    }, 0);
    void miniAppApi.liveStream(initData, (feed) => {
      setServerOffset(new Date(feed.server_time).getTime() - Date.now());
      setFastFeed(feed);
      void refreshDashboard().catch(() => undefined);
    }, controller.signal, "fast").catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Не удалось подключиться к Fast-эфиру.");
    });
    return () => { window.clearTimeout(initial); controller.abort(); };
  }, [authenticated, initData, refreshDashboard, refreshFastLive, view]);

  const standardLotteries = useMemo(() => dashboard?.lotteries.filter((item) => !isFastLottery(item.code)) ?? [], [dashboard]);
  const fastLotteries = useMemo(() => dashboard?.lotteries.filter((item) => isFastLottery(item.code)) ?? [], [dashboard]);
  const nearestLottery = useMemo(() => standardLotteries.filter((item) => item.scheduled_at && new Date(item.scheduled_at).getTime() > now + serverOffset).sort((left, right) => new Date(left.scheduled_at ?? 0).getTime() - new Date(right.scheduled_at ?? 0).getTime())[0] ?? null, [now, serverOffset, standardLotteries]);
  const selectedLottery = standardLotteries.find((item) => item.code === selectedLotteryCode) ?? nearestLottery;
  const firstAvailable = standardLotteries.find((item) => item.purchase_available) ?? null;
  const repeatTicket = dashboard?.recent_results.find((ticket) => !isFastLottery(ticket.lottery_code) && standardLotteries.some((lottery) => lottery.code === ticket.lottery_code && lottery.purchase_available)) ?? null;
  const standardRecentResult = dashboard?.recent_results.find((ticket) => !isFastLottery(ticket.lottery_code)) ?? null;
  const cartGroups = useMemo(() => {
    const groups = new Map<string, CartTicket[]>();
    for (const ticket of cart) {
      const key = `${ticket.lotteryCode}:${ticket.drawCount}`;
      groups.set(key, [...(groups.get(key) ?? []), ticket]);
    }
    return Array.from(groups.values());
  }, [cart]);
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
      setFavorites(isFastLottery(lottery.code) ? [] : await miniAppApi.favorites(initData, lottery.code));
      setPickerLottery(lottery);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось обновить состояние продаж.");
    }
  };

  const addManyToCart = (lottery: Lottery, combinations: number[][], drawCount: 1 | 5) => {
    const available = CART_MAX_TICKETS - cart.length;
    const accepted = combinations.slice(0, available);
    if (!accepted.length) {
      errorHaptic();
      setError(`В корзине может быть не более ${CART_MAX_TICKETS} билетов.`);
      return;
    }
    setCart((current) => [...current, ...accepted.map((numbers) => ({ id: crypto.randomUUID(), lotteryCode: lottery.code, lotteryName: lottery.name, price: lottery.ticket_price ?? 0, numbers: [...numbers], drawCount }))]);
    successHaptic();
    setNotice(accepted.length === 1 ? "Комбинация добавлена в корзину" : `${accepted.length} комбинаций добавлено в корзину`);
    setPickerLottery(null);
    setView("cart");
  };

  const requestPurchase = async (lotteryCode: string, combinations: number[][], drawCount: 1 | 5) => {
    const idempotencyKey = crypto.randomUUID();
    try {
      return await miniAppApi.purchase(initData, lotteryCode, combinations, idempotencyKey, drawCount);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status < 500) throw reason;
      await new Promise((resolve) => window.setTimeout(resolve, 500));
      return miniAppApi.purchase(initData, lotteryCode, combinations, idempotencyKey, drawCount);
    }
  };

  const purchaseSingle = async (lotteryCode: string, numbers: number[], drawCount: 1 | 5) => {
    if (purchasing) return;
    setPurchasing(true); setPurchaseSuccess(false); setError(null);
    try {
      const result = await requestPurchase(lotteryCode, [numbers], drawCount);
      setPurchaseSuccess(true); successHaptic();
      setNotice(`Билет куплен · списано ${formatCas(result.total_cost)}`);
      await refreshDashboard();
      const updatedAccount = await refreshAccount();
      if (!localDev && !updatedAccount?.notification_preferences.telegram_enabled && localStorage.getItem("k-loto:notification-prompt-dismissed") !== "true") setShowNotificationPrompt(true);
      await new Promise((resolve) => window.setTimeout(resolve, 480));
      setPickerLottery(null); setSelectedLotteryCode(lotteryCode); setView(isFastLottery(lotteryCode) ? "fast" : "home");
      setPurchaseConfirmation({ lotteryCode, count: 1, cost: result.total_cost });
    } catch (reason) {
      errorHaptic();
      setError(reason instanceof ApiError ? reason.message : "Покупка не выполнена.");
    } finally {
      setPurchasing(false); setPurchaseSuccess(false);
    }
  };

  const purchaseCart = async () => {
    if (purchasing || cart.length === 0) return;
    const returnLotteryCode = cart[0]?.lotteryCode ?? null;
    const groups = new Map<string, CartTicket[]>();
    for (const item of cart) {
      const key = `${item.lotteryCode}:${item.drawCount}`;
      groups.set(key, [...(groups.get(key) ?? []), item]);
    }
    const total = cart.length;
    let done = 0;
    let totalCost = 0;
    setPurchasing(true); setPurchaseSuccess(false); setError(null); setPurchaseProgress({ done, total });
    try {
      for (const ticketsForLottery of groups.values()) {
        const sample = ticketsForLottery[0];
        const result = await requestPurchase(sample.lotteryCode, ticketsForLottery.map((ticket) => ticket.numbers), sample.drawCount);
        const purchasedIds = new Set(ticketsForLottery.map((ticket) => ticket.id));
        setCart((current) => current.filter((ticket) => !purchasedIds.has(ticket.id)));
        done += ticketsForLottery.length;
        totalCost += result.total_cost;
        setPurchaseProgress({ done, total });
        setDashboard((current) => current ? { ...current, balance: result.balance_after } : current);
      }
      setPurchaseSuccess(true); successHaptic();
      setNotice(`${done} билетов куплено · списано ${formatCas(totalCost)}`);
      await refreshDashboard();
      const updatedAccount = await refreshAccount();
      if (!localDev && !updatedAccount?.notification_preferences.telegram_enabled && localStorage.getItem("k-loto:notification-prompt-dismissed") !== "true") setShowNotificationPrompt(true);
      await new Promise((resolve) => window.setTimeout(resolve, 480));
      setSelectedLotteryCode(returnLotteryCode); setView("home");
      setPurchaseConfirmation({ lotteryCode: returnLotteryCode, count: done, cost: totalCost });
    } catch (reason) {
      errorHaptic();
      setError(`${done ? `Куплено ${done} из ${total}. ` : ""}${reason instanceof ApiError ? reason.message : "Покупка прервана. Непроданные билеты остались в корзине."}`);
    } finally {
      setPurchasing(false); setPurchaseSuccess(false); setPurchaseProgress(null);
    }
  };

  const saveFavorite = async (numbers: number[]) => {
    if (!pickerLottery) return;
    try {
      const favorite = await miniAppApi.saveFavorite(initData, pickerLottery.code, numbers);
      setFavorites((current) => current.some((item) => item.id === favorite.id) ? current : [favorite, ...current]);
      successHaptic(); setNotice("Комбинация сохранена в избранное");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось сохранить комбинацию."); }
  };

  const deleteFavorite = async (id: string) => {
    if (!pickerLottery) return;
    try {
      await miniAppApi.deleteFavorite(initData, pickerLottery.code, id);
      setFavorites((current) => current.filter((item) => item.id !== id));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось удалить комбинацию."); }
  };

  const saveNotificationPreferences = async (preferences: NotificationPreferences) => {
    try {
      const saved = await miniAppApi.notificationPreferences(initData, preferences);
      setAccount((current) => current ? { ...current, notification_preferences: saved } : current);
      successHaptic();
    } catch (reason) {
      errorHaptic();
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить уведомления.");
    }
  };

  const enableTelegramNotifications = async () => {
    const allowed = await requestTelegramWriteAccess();
    if (!allowed) {
      setNotice("Разрешение не выдано. Его можно включить позже в разделе «Моё».");
      setShowNotificationPrompt(false);
      return;
    }
    const preferences: NotificationPreferences = {
      telegram_enabled: true,
      draw_results_enabled: true,
      inactivity_reminders_enabled: true,
    };
    await saveNotificationPreferences(preferences);
    localStorage.removeItem("k-loto:notification-prompt-dismissed");
    setShowNotificationPrompt(false);
    setNotice("Telegram-уведомления включены");
  };

  const dismissNotificationPrompt = () => {
    localStorage.setItem("k-loto:notification-prompt-dismissed", "true");
    setShowNotificationPrompt(false);
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
  if (pickerLottery) return <main className="app-shell picker-page">{isFastLottery(pickerLottery.code) ? <FastPicker lottery={pickerLottery} purchasing={purchasing} success={purchaseSuccess} onBuy={(numbers) => void purchaseSingle(pickerLottery.code, numbers, 1)} onClose={() => { setPickerLottery(null); setView("fast"); }} /> : <NumberPicker lottery={pickerLottery} purchasing={purchasing} success={purchaseSuccess} initialNumbers={pickerInitialNumbers} favorites={favorites} cartRemaining={CART_MAX_TICKETS - cart.length} onAdd={(numbers, drawCount) => addManyToCart(pickerLottery, [numbers], drawCount)} onAddMany={(combinations, drawCount) => addManyToCart(pickerLottery, combinations, drawCount)} onBuy={(numbers, drawCount) => void purchaseSingle(pickerLottery.code, numbers, drawCount)} onSaveFavorite={(numbers) => void saveFavorite(numbers)} onDeleteFavorite={(id) => void deleteFavorite(id)} onClose={() => setPickerLottery(null)} />}</main>;

  return <main className="app-shell">
    <header className="app-header"><div aria-label="Каспер" className="wordmark"><span aria-hidden="true">К</span><div aria-hidden="true">{copy.header.brandContinuation}</div></div><div className="header-actions">{localDev && import.meta.env.VITE_DESIGN_PREVIEW !== "true" && <button className="dev-badge" onClick={() => void refillDevBalance()} type="button">+ TEST CAS</button>}{cart.length > 0 && <button aria-label={`Корзина: ${cart.length} ${plural(cart.length, "комбинация", "комбинации", "комбинаций")}`} className="header-cart" onClick={() => setView("cart")} type="button"><Icon name="cart" /><small>{cart.length}</small></button>}<Balance value={dashboard.balance} /></div></header>
    {updateAvailable && <aside className="update-banner"><span><strong>Доступно обновление</strong><small>Корзина сохранена на этом устройстве.</small></span><button onClick={() => window.location.reload()} type="button">Обновить</button></aside>}
    {(error || notice) && <button className={`toast ${error ? "error" : "success"}`} onClick={() => { setError(null); setNotice(null); }} type="button"><span>{error ? "!" : "✓"}</span>{error ?? notice}<Icon name="close" /></button>}
    {showNotificationPrompt && <div className="permission-backdrop"><section className="permission-card"><div className="permission-mark"><Icon name="profile" /></div><span className="eyebrow">{copy.notifications.promptEyebrow}</span><h2>{copy.notifications.promptTitle}</h2><p>{copy.notifications.promptText}</p><PrimaryButton onClick={() => void enableTelegramNotifications()}>{copy.notifications.enable}</PrimaryButton><button className="permission-later" onClick={dismissNotificationPrompt} type="button">{copy.notifications.promptLater}</button></section></div>}
    {purchaseConfirmation && <PurchaseConfirmation count={purchaseConfirmation.count} cost={purchaseConfirmation.cost} onClose={() => setPurchaseConfirmation(null)} onHome={() => { setPurchaseConfirmation(null); setPickerLottery(null); setView("home"); }} onTickets={() => { setPurchaseConfirmation(null); setTicketsLoading(true); setView("account"); setAccountView("tickets"); setTicketView("active"); }} />}

    {view === "home" && <section className="view-content home-view" key="home">
      {selectedLottery && <NextDraw key={selectedLottery.code} lottery={selectedLottery} nearest={selectedLottery.code === nearestLottery?.code} now={serverNow} onLive={() => { setLiveLoading(true); setView("live"); }} onPlay={() => void openLottery(selectedLottery.code)} />}
      <LotterySwitcher lotteries={standardLotteries} selected={selectedLottery?.code ?? ""} now={serverNow} onSelect={setSelectedLotteryCode} />
      <div className="monthly-payout"><span>{copy.home.monthlyPayout}</span><strong>{formatCas(dashboard.monthly_total_payout)}</strong></div>
      <div className="home-action-row" aria-label="Быстрые действия">
        <button onClick={() => { setTicketsLoading(true); setAccountView("tickets"); setView("account"); }} type="button"><span className="action-symbol"><Icon name="ticket" /></span><span><strong>Мои билеты</strong><small>{dashboard.active_ticket_count ? `${dashboard.active_ticket_count} активных билетов` : "Активных билетов пока нет"}</small></span><b>→</b></button>
        {firstAvailable && <button onClick={() => void openLottery(firstAvailable.code, randomCombination(firstAvailable.max_number, firstAvailable.numbers_to_pick))} type="button"><span className="action-symbol"><Icon name="spark" /></span><span><strong>Случайная комбинация</strong><small>{firstAvailable.name} · {formatCas(firstAvailable.ticket_price ?? 0)}</small></span><b>→</b></button>}
      </div>
      <div className="section-heading compact-heading"><div><span className="eyebrow">{copy.home.recentResultEyebrow}</span><h2>{copy.home.recentResultTitle}</h2></div><button className="text-button" onClick={() => { setLiveLoading(true); setView("live"); }} type="button">Смотреть повтор <span>→</span></button></div>
      {standardRecentResult ? <button className={`home-result lottery-${standardRecentResult.lottery_code}`} onClick={() => { setLiveLoading(true); setView("live"); }} type="button"><span><strong>{standardRecentResult.lottery_name}</strong><small>{formatMoscow(standardRecentResult.scheduled_at)} МСК · тираж #{formatDraw(standardRecentResult.draw_number)}</small></span><NumberSet values={standardRecentResult.winning_numbers ?? []} /><b><Icon name="replay" /></b></button> : <div className="home-empty-result"><Icon name="live" /><span><strong>Первый результат ещё впереди</strong><small>После тиража здесь появятся выпавшие числа.</small></span></div>}
      {repeatTicket && <button className="repeat-combination" onClick={() => void openLottery(repeatTicket.lottery_code, repeatTicket.numbers)} type="button"><Icon name="repeat" /> Повторить последнюю комбинацию</button>}
    </section>}

    {view === "live" && <section className="view-content live-view" key="live">
      <LiveView feed={liveFeed} now={serverNow} loading={liveLoading} onPlay={(code) => void openLottery(code)} onTickets={() => { setTicketsLoading(true); setAccountView("tickets"); setView("account"); }} />
    </section>}

    {view === "fast" && <section className="view-content" key="fast"><FastView lotteries={fastLotteries} feed={fastFeed} now={serverNow} onOpen={(code) => void openLottery(code)} /></section>}

    {view === "account" && <section className="view-content" key="account">
      <div className="page-title account-title"><h1>{copy.account.title}</h1><p>{copy.account.subtitle}</p></div>
      <div className="account-tabs"><button className={accountView === "overview" ? "selected" : ""} onClick={() => { selectionHaptic(); setAccountView("overview"); void refreshAccount(); }} type="button">Обзор</button><button className={accountView === "tickets" ? "selected" : ""} onClick={() => { selectionHaptic(); setTicketsLoading(true); setAccountView("tickets"); }} type="button">Билеты{account?.active_ticket_count ? <small>{account.active_ticket_count}</small> : null}</button><button className={accountView === "notifications" ? "selected" : ""} onClick={() => { selectionHaptic(); setAccountView("notifications"); }} type="button">Уведомления{account?.unread_notification_count ? <small>{account.unread_notification_count}</small> : null}</button></div>
      {accountView === "overview" && (account ? <AccountOverview account={account} onEnableTelegram={() => void enableTelegramNotifications()} onSavePreferences={(preferences) => void saveNotificationPreferences(preferences)} /> : <div className="skeleton account-skeleton" />)}
      {accountView === "tickets" && <><div className={`segmented-control ${ticketView}`}><i /><button className={ticketView === "active" ? "selected" : ""} onClick={() => { selectionHaptic(); setTicketsLoading(true); setTicketView("active"); }} type="button">Активные</button><button className={ticketView === "history" ? "selected" : ""} onClick={() => { selectionHaptic(); setTicketsLoading(true); setTicketView("history"); }} type="button">История</button></div><div className="ticket-filters"><select aria-label="Фильтр по лотерее" value={ticketLotteryFilter} onChange={(event) => { setTicketsLoading(true); setTicketLotteryFilter(event.target.value); }}><option value="">Все лотереи</option>{dashboard.lotteries.map((lottery) => <option key={lottery.code} value={lottery.code}>{lottery.name}</option>)}</select>{ticketView === "history" && <button aria-pressed={ticketWinsOnly} className={ticketWinsOnly ? "active" : ""} onClick={() => { setTicketsLoading(true); setTicketWinsOnly((value) => !value); }} type="button">Только выигрыши</button>}</div>{ticketsLoading ? <div className="ticket-skeletons"><div className="skeleton ticket-skeleton" /><div className="skeleton ticket-skeleton" /></div> : tickets.length ? <TicketGroups tickets={tickets} /> : <EmptyState title={ticketView === "active" ? "Нет активных билетов" : "История пока пуста"} text={ticketView === "active" ? "Выберите лотерею и соберите свою комбинацию." : "Завершённые билеты появятся после розыгрыша."} action={ticketView === "active" && firstAvailable ? { label: "Выбрать лотерею", onClick: () => setView("home") } : undefined} />}{ticketView === "active" && firstAvailable && !ticketsLoading && tickets.length > 0 && <PrimaryButton className="sticky-action" onClick={() => void openLottery(firstAvailable.code)}>Ещё один билет</PrimaryButton>}</>}
      {accountView === "notifications" && <NotificationCenter notifications={notifications} onPlay={() => firstAvailable ? void openLottery(firstAvailable.code) : setView("home")} onTickets={() => { setTicketsLoading(true); setAccountView("tickets"); }} />}
    </section>}

    {view === "cart" && <section className="view-content" key="cart">
      <CartView cart={cart} groups={cartGroups} purchasing={purchasing} success={purchaseSuccess} progress={purchaseProgress} canAdd={cart.length < CART_MAX_TICKETS} onClear={() => setCart([])} onRemove={(id) => setCart((current) => current.filter((item) => item.id !== id))} onAdd={() => setView("home")} onBuy={() => void purchaseCart()} onHome={() => setView("home")} />
    </section>}

    <BottomNavigation view={view} unreadNotifications={account?.unread_notification_count ?? 0} onChange={(target) => { if (target === "account") void refreshAccount(); if (target === "live") setLiveLoading(true); setView(target); }} />
  </main>;
}
