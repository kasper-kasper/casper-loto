import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { CatalogFilter } from "./LotteryCatalog";
import { motion } from "motion/react";

import { ApiError, miniAppApi } from "./api";
import { Today } from "./Today";
import { Stories } from "./Stories";
import { MobileNavigation } from "./MobileNavigation";
import type { Highlights } from "./Today";
import { logoHorizontal, logoSymbol } from "./brand";
import { LiveSymbol } from "./LiveSymbol";
import { CART_MAX_TICKETS, configuredCartTtl, loadCart, saveCart } from "./cart";
import {
  Balance,
  EmptyState,
  GrandNumberSet,
  Icon,
  Money,
  NumberSet,
  PrimaryButton,
  Skeleton,
  StatusBadge,
} from "./components";
import { countdown, formatCas, formatDrawLabel, formatMoscow, formatTicketLabel } from "./format";
import { MINIAPP_TEXTS as copy } from "./content";
import { isFastLottery } from "./fast";
import { newestLiveFeed } from "./live";
import { broadcastPreviewConfig } from "./broadcastPreview";
import { isGrandLottery, matchLabel } from "./grand";
import { errorHaptic, requestTelegramWriteAccess, selectionHaptic, successHaptic } from "./telegram";
import type { Account, CartTicket, Dashboard, Favorite, LiveFeed, Lottery, NotificationPreferences, PurchaseResult, Ticket, UserNotification } from "./types";

const AccountOverview = lazy(() => import("./AccountHub").then(({ AccountHub }) => ({ default: AccountHub })));
const NumberPicker = lazy(() => import("./TicketComposer").then(({ TicketComposer }) => ({ default: TicketComposer })));
const LotteryCatalog = lazy(() => import("./LotteryCatalog").then(({ LotteryCatalog }) => ({ default: LotteryCatalog })));
const LotteryRoom = lazy(() => import("./Discovery").then(({ LotteryRoom }) => ({ default: LotteryRoom })));
const BingoView = lazy(() => import("./BingoView").then(({ BingoView }) => ({ default: BingoView })));
const BingoTicketDetail = lazy(() => import("./BingoView").then(({ BingoTicketDetail }) => ({ default: BingoTicketDetail })));
const FastView = lazy(() => import("./FastView").then(({ FastView }) => ({ default: FastView })));
const FastPicker = lazy(() => import("./FastView").then(({ FastPicker }) => ({ default: FastPicker })));
const KasperLiveView = lazy(() => import("./KasperLiveView").then(({ KasperLiveView }) => ({ default: KasperLiveView })));

const DrawArchive = lazy(() => import("./DrawArchive").then(({ DrawArchive }) => ({ default: DrawArchive })));

type View = "archive" | "catalog" | "home" | "live" | "fast" | "account" | "cart";
type TicketView = "active" | "history";
type AccountView = "overview" | "tickets" | "notifications";
interface CartReceipt { ticketCount: number; totalCost: number }

interface AppProps {
  initData: string;
  localDev?: boolean;
}

function initialView(): View {
  if (import.meta.env.VITE_DESIGN_PREVIEW !== "true" && !broadcastPreviewConfig()) return "home";
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

function compactCombination(ticket: Ticket, lottery?: Lottery): string {
  if (ticket.lottery_code === "dual") return `NIGHT ${ticket.numbers.filter(value => value <= 12).join(" · ")}  /  DAWN ${ticket.numbers.filter(value => value > 12).map(value => value - 12).join(" · ")}`;
  const offset = lottery?.secondary_storage_offset;
  const cipher = ticket.numbers.find((value) => value > 1_000);
  if (!offset) return ticket.numbers.join("  ");
  const main = ticket.numbers.filter((value) => value <= offset).join("  ");
  const special = ticket.numbers.filter((value) => value > offset && value <= offset + (lottery?.secondary_max_number ?? 0)).map((value) => value - offset).join("  ");
  return `${main}  +  ${special}${cipher ? `  ·  ШИФР ${String(cipher - 1_000).padStart(3, "0")}` : ""}`;
}

function TicketCard({ ticket, lottery, index = 0, onOpen }: { ticket: Ticket; lottery?: Lottery; index?: number; onOpen: () => void }) {
  const refunded = ticket.status === "REFUNDED";
  const complete = ticket.status !== "PURCHASED";
  const winner = complete && ticket.prize_amount > 0;
  const matches = ticket.matches ?? 0;
  const dualWaiting = ticket.lottery_code === "dual" && !complete && (ticket.dual_night_matches !== null && ticket.dual_night_matches !== undefined || ticket.dual_dawn_matches !== null && ticket.dual_dawn_matches !== undefined);
  return <button className={`ticket-card compact-ticket ${winner ? "winner" : ""}`} onClick={onOpen} style={{ "--item-index": index } as CSSProperties} type="button">
    <div className="ticket-meta">
      <div><span className="eyebrow">{ticket.lottery_name}{ticket.source === "AUTO_PLAY" ? " · АВТОБИЛЕТ" : ""}</span><h3>{formatTicketLabel(ticket.lottery_code, ticket.public_number)}</h3></div>
      <StatusBadge active={!complete} label={refunded ? "Возврат" : dualWaiting ? "Первый раунд завершён" : undefined} />
    </div>
    <div className="compact-combination">{compactCombination(ticket, lottery)}<span>Открыть билет →</span></div>
    {complete && <div className={`ticket-result ${winner ? "win" : "loss"} ${refunded ? "refunded" : ""}`}>
      <div><span>{refunded ? "Билет возвращён" : ticket.lottery_code === "dual" ? `NIGHT ${ticket.dual_night_matches ?? 0}/2 · DAWN ${ticket.dual_dawn_matches ?? 0}/2` : matches > 0 ? `Совпадений: ${matchLabel(ticket.lottery_code, matches, ticket.numbers.length === 7)}` : "Совпадений нет"}</span><small>{refunded ? "Стоимость зачислена на баланс" : winner ? "Выигрыш зачислен" : "Без выигрыша"}</small></div>
      <strong>{refunded ? `+${formatCas(ticket.purchase_price)}` : winner ? `+${formatCas(ticket.prize_amount)}` : "0 CAS"}</strong>
    </div>}
  </button>;
}

function InstantHistoryCard({ ticket }: { ticket: Ticket }) {
  const winning = ticket.prize_amount > 0;
  return <article className={`ticket-card compact-ticket instant-history-ticket ${winning ? "winner" : ""}`}>
    <div className="ticket-meta"><div><span className="eyebrow">Casper LIVE</span><h3>№ {ticket.public_number.toLocaleString("ru-RU")}</h3></div><StatusBadge active={false} label={winning ? "Выигрыш" : "Без выигрыша"} /></div>
    <div className="instant-history-symbols">{(ticket.instant_symbols ?? []).map((value, index) => <i key={`${value}:${index}`}><LiveSymbol value={value} /></i>)}</div>
    <div className={`ticket-result ${winning ? "win" : "loss"}`}><div><span>{winning ? "Одинаковые символы" : "Разные символы"}</span><small>{winning ? "Выигрыш зачислен" : "Без выигрыша"}</small></div><strong>{winning ? `+${formatCas(ticket.prize_amount)}` : "0 CAS"}</strong></div>
  </article>;
}

function TicketGroups({ tickets, lotteries, now, active, onOpen }: { tickets: Ticket[]; lotteries: Lottery[]; now: number; active: boolean; onOpen: (ticket: Ticket) => void }) {
  const regularTickets = tickets.filter((ticket) => !ticket.instant_symbols);
  const instantTickets = tickets.filter((ticket) => Boolean(ticket.instant_symbols));
  const groups = new Map<string, Ticket[]>();
  for (const ticket of regularTickets) {
    const key = `${ticket.lottery_code}:${ticket.draw_number}`;
    groups.set(key, [...(groups.get(key) ?? []), ticket]);
  }
  return <div className="ticket-groups">{Array.from(groups.entries()).map(([key, items], groupIndex) => {
    const first = items[0];
    const total = first.draw_ticket_count ?? items.length;
    const lottery = lotteries.find((item) => item.code === first.lottery_code);
    return <section className={`ticket-draw-group lottery-${first.lottery_code} ${active && groupIndex === 0 ? "next-ticket-group" : ""}`} key={key}><header><div>{active && groupIndex === 0 && <b>Следующий</b>}<span className="eyebrow">{first.lottery_name}</span><h2>{first.lottery_code === "dual" ? `Билет на два раунда · #${first.draw_number} → #${first.second_draw_number ?? "—"}` : formatDrawLabel(first.lottery_code, first.draw_number)}</h2><time>{formatMoscow(first.scheduled_at)} МСК{active ? ` · через ${countdown(first.scheduled_at, now)}` : ""}</time></div><div><strong>{total}</strong><small>{plural(total, "билет", "билета", "билетов")}</small></div></header><div className="ticket-group-list">{items.map((ticket, index) => <TicketCard index={index} key={ticket.id} lottery={lottery} onOpen={() => onOpen(ticket)} ticket={ticket} />)}</div></section>;
  })}{instantTickets.length > 0 && <section className="ticket-draw-group lottery-kasper-live"><header><div><span className="eyebrow">Casper LIVE</span><h2>Мгновенные билеты</h2><time>Результат сразу после покупки</time></div><div><strong>{instantTickets.length}</strong><small>{plural(instantTickets.length, "билет", "билета", "билетов")}</small></div></header><div className="ticket-group-list">{instantTickets.map((ticket) => <InstantHistoryCard key={ticket.id} ticket={ticket} />)}</div></section>}</div>;
}

function DualTicketDetail({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const firstFinished = Boolean(ticket.first_winning_numbers?.length);
  const secondFinished = Boolean(ticket.second_winning_numbers?.length);
  const firstPhase = ticket.first_phase ?? "NIGHT";
  const round = (phase: "NIGHT" | "DAWN") => {
    const first = firstPhase === phase;
    const result = first ? ticket.first_winning_numbers : ticket.second_winning_numbers;
    const selected = ticket.numbers.filter(value => phase === "NIGHT" ? value <= 12 : value > 12).map(value => phase === "NIGHT" ? value : value - 12);
    const matches = phase === "NIGHT" ? ticket.dual_night_matches : ticket.dual_dawn_matches;
    return <section className={`dual-ticket-round ${phase.toLowerCase()}`}><header><span>{phase === "NIGHT" ? "☾" : "☀"}</span><div><strong>{phase}</strong><small>{first ? `Тираж #${ticket.draw_number}` : `Тираж #${ticket.second_draw_number ?? "—"}`}</small></div></header><div className="dual-ticket-numbers">{selected.map(value => <i className={result?.includes(value) ? "matched" : ""} key={value}>{value}</i>)}</div><p>{result?.length ? `Выпало ${result.join(" · ")} · совпало ${matches ?? 0} из 2` : `Ожидается розыгрыш ${phase}`}</p></section>;
  };
  return <div className="ticket-detail-backdrop" onClick={onClose} role="presentation"><article aria-label={`Билет Casper Dual №${ticket.public_number}`} aria-modal="true" className="dual-ticket-detail" onClick={event => event.stopPropagation()} role="dialog"><button aria-label="Закрыть билет" className="paper-close" onClick={onClose} type="button"><Icon name="close" /></button><div className="dual-ticket-scene" /><header><span>CASPER DUAL · ОДИН БИЛЕТ, ДВА РАУНДА</span><h2>Билет №{ticket.public_number}</h2><p>Первый: {firstPhase} · второй: {firstPhase === "NIGHT" ? "DAWN" : "NIGHT"}</p></header><div className="dual-ticket-rounds">{round("NIGHT")}{round("DAWN")}</div><footer><span>{secondFinished ? "Итог двух раундов" : firstFinished ? "Первый раунд завершён · билет активен" : "Ожидаем первый раунд"}</span><strong>{secondFinished ? ticket.prize_amount ? `+${formatCas(ticket.prize_amount)}` : "Без выигрыша" : "Выплата после второго раунда"}</strong><small>Стоимость билета {formatCas(ticket.purchase_price)}</small></footer></article></div>;
}

function TicketDetail({ ticket, lottery, onClose }: { ticket: Ticket; lottery?: Lottery; onClose: () => void }) {
  const completed = ticket.status !== "PURCHASED";
  const codeMode = lottery?.ruleset_code?.startsWith("code_") || ticket.lottery_name === "CODE";
  const cipher = ticket.numbers.find((value) => value > 1_000);
  const winningCipher = ticket.winning_numbers?.find((value) => value > 1_000);
  const winning = new Set(ticket.winning_numbers ?? []);
  const selected = new Set(ticket.numbers);
  const matched = new Set(ticket.numbers.filter((value) => winning.has(value)));
  const offset = lottery?.secondary_storage_offset ?? 0;
  const primaryMax = ticket.primary_max_number ?? lottery?.primary_max_number ?? lottery?.max_number ?? Math.max(...ticket.numbers, ...(ticket.winning_numbers ?? []));
  const secondaryMax = lottery?.secondary_max_number ?? 0;
  const renderField = (max: number, valueOffset = 0) => <div className="paper-number-field">{Array.from({ length: max }, (_, index) => index + 1).map((display) => {
    const value = display + valueOffset;
    return <i className={`${selected.has(value) ? "selected" : ""} ${winning.has(value) ? "winning" : ""} ${matched.has(value) ? "matched" : ""}`} key={value}>{display}</i>;
  })}</div>;
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose]);
  if (ticket.lottery_code === "dual") return <DualTicketDetail ticket={ticket} onClose={onClose} />;
  return <div className="ticket-detail-backdrop" onClick={onClose} role="presentation"><motion.article animate={{ opacity: 1, y: 0, scale: 1 }} aria-label={`Билет ${ticket.public_number}`} aria-modal="true" className={`paper-ticket lottery-${ticket.lottery_code}`} initial={{ opacity: 0, y: 18, scale: .97 }} onClick={(event) => event.stopPropagation()} role="dialog">
    <button aria-label="Закрыть билет" className="paper-close" onClick={onClose} type="button"><Icon name="close" /></button>
    <header><span>{ticket.lottery_name}</span><strong>{formatTicketLabel(ticket.lottery_code, ticket.public_number)}</strong><small>{formatDrawLabel(ticket.lottery_code, ticket.draw_number)} · {formatMoscow(ticket.scheduled_at)} МСК</small></header>
    <div className="paper-perforation" />
    <section><div className="paper-field-title"><b>{codeMode ? `${ticket.numbers.length}-значный код` : secondaryMax ? "Основное поле" : "Комбинация"}</b><small>{ticket.numbers.filter((value) => !offset || value <= offset).join(codeMode ? "" : " · ")}</small></div>{codeMode ? <div className="paper-code-field">{ticket.numbers.map((value, index) => <i className={`${ticket.winning_numbers?.[index] !== undefined ? "winning" : ""} ${ticket.winning_numbers?.[index] === value ? "matched" : ""}`} key={index}>{value}</i>)}</div> : renderField(primaryMax)}</section>
    {secondaryMax > 0 && <section className="paper-special"><div className="paper-field-title"><b>Специальное поле</b><small>{ticket.numbers.filter((value) => value > offset && value <= offset + secondaryMax).map((value) => value - offset).join(" · ")}</small></div>{renderField(secondaryMax, offset)}</section>}
    {cipher && <section className={`paper-cipher ${completed && cipher === winningCipher ? "matched" : ""}`}><span>ШИФР БИЛЕТА</span><strong>{String(cipher - 1_000).padStart(3, "0")}</strong>{completed && <small>Шифр тиража: {winningCipher ? String(winningCipher - 1_000).padStart(3, "0") : "—"}</small>}</section>}
    {ticket.status === "REFUNDED" ? <section className="paper-result"><b>Билет возвращён</b><p>Стоимость зачислена на баланс</p><strong>+{formatCas(ticket.purchase_price)}</strong></section> : completed && <section className="paper-result"><div><span>Выпавшие числа</span><strong>{compactCombination({ ...ticket, numbers: ticket.winning_numbers ?? [] }, lottery)}</strong></div><p>{ticket.matches ? `Совпало ${matchLabel(ticket.lottery_code, ticket.matches, ticket.numbers.length === 7)}` : "Совпадений нет"}</p><b className={ticket.prize_amount > 0 ? "win" : "loss"}>{ticket.prize_amount > 0 ? `Выигрыш: ${formatCas(ticket.prize_amount)}` : "Без выигрыша"}</b></section>}
    <footer><span>Стоимость</span><strong>{formatCas(ticket.purchase_price)}</strong><small>CAS · CASPER LOTO</small></footer>
  </motion.article></div>;
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

function CartView({ cart, groups, receipt, purchasing, success, progress, canAdd, onClear, onRemove, onAdd, onBuy, onTickets, onHome }: { cart: CartTicket[]; groups: CartTicket[][]; receipt: CartReceipt | null; purchasing: boolean; success: boolean; progress: { done: number; total: number } | null; canAdd: boolean; onClear: () => void; onRemove: (id: string) => void; onAdd: () => void; onBuy: () => void; onTickets: () => void; onHome: () => void }) {
  const total = cart.reduce((sum, item) => sum + item.price * item.drawCount, 0);
  if (receipt && !cart.length) return <div className="cart-success"><div className="cart-success-mark" aria-hidden="true">✓</div><span className="eyebrow">Покупка завершена</span><h1>Билеты уже в игре</h1><strong>{receipt.ticketCount} {plural(receipt.ticketCount, "билет", "билета", "билетов")} · {formatCas(receipt.totalCost)}</strong><p>Они уже участвуют в своих тиражах.</p><div><button className="primary-button" onClick={onAdd} type="button">Купить ещё</button><button onClick={onTickets} type="button">Мои билеты</button><button onClick={onHome} type="button">На главную</button></div></div>;
  if (!cart.length) return <div className="cart-empty"><div className="cart-empty-art" aria-hidden="true"><span /><i /><b>+</b></div><span className="eyebrow">Ваш следующий билет</span><h1>Корзина пока пуста</h1><p>Соберите комбинацию — мы аккуратно сохраним её здесь до оформления.</p><button className="cart-empty-action" onClick={onHome} type="button">Выбрать лотерею <span>→</span></button></div>;

  return <div className="cart-layout">
    <header className="cart-header"><div><span className="eyebrow">Готово к оформлению</span><h1>{cart.length} {plural(cart.length, "комбинация", "комбинации", "комбинаций")}</h1></div><button disabled={purchasing} onClick={onClear} type="button">Очистить</button></header>
    <div className="cart-groups">{groups.map((items, groupIndex) => <motion.section animate={{ opacity: 1, y: 0 }} className={`cart-group lottery-${items[0].lotteryCode}`} initial={{ opacity: 0, y: 9 }} key={`${items[0].lotteryCode}:${items[0].drawCount}`} transition={{ delay: groupIndex * .05 }}><header><div><span>{items[0].lotteryName}</span><strong>В группе: {items.length}</strong></div><div><small>{items[0].drawCount === 5 ? "на 5 тиражей" : "ближайший тираж"}</small><b>{formatCas(items.reduce((sum, item) => sum + item.price * item.drawCount, 0))}</b></div></header><div className="cart-ticket-stack">{items.slice(0, 5).map((ticket, index) => <article className="cart-combination" key={`${ticket.id}:${index}`}><span>{String(index + 1).padStart(2, "0")}</span>{isGrandLottery(ticket.lotteryCode) ? <GrandNumberSet values={ticket.numbers} offset={ticket.lotteryCode === "pss" ? 36 : 35} specialLabel={ticket.lotteryCode === "pss" ? "Casper Ball" : undefined} /> : <NumberSet values={ticket.numbers} />}<button className="remove-button" onClick={() => { selectionHaptic(); onRemove(ticket.id); }} type="button" aria-label={`Удалить билет ${index + 1}`}><Icon name="close" /></button></article>)}{items.length > 5 && <p>+ ещё {items.length - 5} — оформим одной операцией</p>}</div></motion.section>)}</div>
    {progress && <div className="purchase-progress"><div><span>Оформляем билеты</span><strong>{progress.done} из {progress.total}</strong></div><i><span style={{ width: `${(progress.done / progress.total) * 100}%` }} /></i></div>}
    <aside className="cart-checkout"><div className="checkout-receipt"><span>Итого</span><strong><Money value={total} /></strong><small>{cart.length} комб. · безопасная покупка одной операцией</small></div><button aria-label="Добавить комбинацию" className="checkout-add" disabled={!canAdd || purchasing} onClick={onAdd} type="button">+ Добавить ещё</button><PrimaryButton className="checkout-buy" loading={purchasing} success={success} onClick={onBuy}>{success ? "Билеты куплены" : purchasing ? `Оформляем ${progress?.done ?? 0} из ${progress?.total ?? cart.length}` : `Купить ${cart.length} комб.`}</PrimaryButton></aside>
  </div>;
}

export default function App({ initData, localDev = false }: AppProps) {
  const authenticated = Boolean(initData) || localDev;
  const [cartTtl] = useState(() => configuredCartTtl());
  const [view, setView] = useState<View>(initialView);
  const [accountView, setAccountView] = useState<AccountView>("overview");
  const [ticketView, setTicketView] = useState<TicketView>("active");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [notifications, setNotifications] = useState<UserNotification[]>([]);
  const [fastFeed, setFastFeed] = useState<LiveFeed | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [ticketTotal, setTicketTotal] = useState(0);
  const [ticketsHaveMore, setTicketsHaveMore] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [cart, setCart] = useState<CartTicket[]>(() => loadCart(cartTtl));
  const [catalogFilter, setCatalogFilter] = useState<CatalogFilter>("all");
  const [catalogScroll, setCatalogScroll] = useState(0);
  const [pickerLottery, setPickerLottery] = useState<Lottery | null>(null);
  const [pickerInitialNumbers, setPickerInitialNumbers] = useState<number[]>([]);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [ticketLotteryFilter, setTicketLotteryFilter] = useState("scope:standard");
  const [ticketWinsOnly, setTicketWinsOnly] = useState(false);
  const [loading, setLoading] = useState(authenticated);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [roomLive, setRoomLive] = useState(Boolean(broadcastPreviewConfig()));
  const [fastHighlights, setFastHighlights] = useState<Highlights | null>(null);
  const [highlights, setHighlights] = useState<Highlights | null>(null);
  const [bingoOpen, setBingoOpen] = useState((import.meta.env.VITE_DESIGN_PREVIEW === "true" && new URLSearchParams(window.location.search).get("screen") === "bingo") || broadcastPreviewConfig()?.lotteryCode === "bingo");
  const [kasperLiveOpen, setKasperLiveOpen] = useState(import.meta.env.VITE_DESIGN_PREVIEW === "true" && new URLSearchParams(window.location.search).get("screen") === "kasper-live");
  const [purchaseSuccess, setPurchaseSuccess] = useState(false);
  const [purchaseProgress, setPurchaseProgress] = useState<{ done: number; total: number } | null>(null);
  const [cartReceipt, setCartReceipt] = useState<CartReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const clockAnchor = useRef<{ server: number; monotonic: number } | null>(null);
  const clockNeedsSync = useRef(true);
  useEffect(() => {
    window.scrollTo({ top: view === "catalog" && !pickerLottery?.code && !bingoOpen && !kasperLiveOpen ? catalogScroll : 0, behavior: "instant" });
  }, [view, accountView, pickerLottery?.code, bingoOpen, kasperLiveOpen, catalogScroll]);
  const nearestDrawIn = Math.min(
    ...(dashboard?.lotteries
      .map((lottery) => lottery.scheduled_at ? Date.parse(lottery.scheduled_at) - now : Number.POSITIVE_INFINITY)
      .filter((delay) => delay >= 0) ?? [Number.POSITIVE_INFINITY]),
  );
  const clockInterval = view === "fast" || view === "live" || bingoOpen || roomLive || nearestDrawIn <= 60_000 ? 1_000 : 10_000;

  const applyDashboard = useCallback((value: Dashboard) => {
    setDashboard(value);
    setCart((current) => current.filter((ticket) => {
      const lottery = value.lotteries.find((item) => item.code === ticket.lotteryCode);
      return lottery !== undefined
        && ticket.numbers.length === lottery.numbers_to_pick
        && ticket.numbers.every((number) => number >= 1 && number <= lottery.max_number);
    }));
    if (import.meta.env.VITE_DESIGN_PREVIEW === "true" && new URLSearchParams(window.location.search).get("screen") === "picker") {
      const requestedCode = new URLSearchParams(window.location.search).get("lottery") ?? "september";
      setPickerLottery(value.lotteries.find((item) => item.code === requestedCode) ?? null);
    }
    const preview = broadcastPreviewConfig();
    if (preview && preview.lotteryCode !== "bingo") {
      setRoomLive(true);
      setPickerLottery(value.lotteries.find((item) => item.code === preview.lotteryCode) ?? null);
    }
  }, []);

  const refreshDashboard = useCallback(async () => {
    if (!authenticated) return null;
    const requestedAt = performance.now();
    const value = await miniAppApi.dashboard(initData);
    if (!performance.getEntriesByName("miniapp:dashboard-ready").length) performance.mark("miniapp:dashboard-ready");
    const receivedAt = performance.now();
    if (!clockAnchor.current || clockNeedsSync.current) {
      const server = Date.parse(value.server_time) + (receivedAt - requestedAt) / 2;
      if (Number.isFinite(server)) {
        clockAnchor.current = { server, monotonic: receivedAt };
        clockNeedsSync.current = false;
        setNow(server);
      }
    }
    applyDashboard(value);
    return value;
  }, [applyDashboard, authenticated, initData]);

  const refreshAccount = useCallback(async () => {
    if (!authenticated) return null;
    const value = await miniAppApi.account(initData);
    setAccount(value);
    return value;
  }, [authenticated, initData]);

  const applyPurchaseSnapshot = useCallback((lotteryCode: string, result: PurchaseResult, currentDrawTickets: number) => {
    setDashboard((current) => current ? {
      ...current,
      balance: result.balance_after,
      active_ticket_count: current.active_ticket_count + result.ticket_ids.length,
      total_ticket_count: current.total_ticket_count + result.ticket_ids.length,
      lotteries: current.lotteries.map((lottery) => lottery.code === lotteryCode ? { ...lottery, player_ticket_count: lottery.player_ticket_count + currentDrawTickets } : lottery),
    } : current);
    setPickerLottery((current) => current?.code === lotteryCode ? { ...current, player_ticket_count: current.player_ticket_count + currentDrawTickets } : current);
    setAccount((current) => current ? {
      ...current,
      balance: result.balance_after,
      ticket_count: current.ticket_count + result.ticket_ids.length,
      active_ticket_count: current.active_ticket_count + result.ticket_ids.length,
      total_spent: current.total_spent + result.total_cost,
    } : current);
  }, []);

  const refreshFastLive = useCallback(async () => {
    if (!authenticated) return;
    const feed = await miniAppApi.live(initData, "fast");
    setFastFeed((current) => newestLiveFeed(current, feed));
  }, [authenticated, initData]);

  useEffect(() => {
    let timer: number | null = null;
    const syncClock = () => {
      if (timer !== null) window.clearInterval(timer);
      timer = null;
      if (document.visibilityState !== "visible") {
        clockNeedsSync.current = true;
        return;
      }
      const tick = () => {
        const anchor = clockAnchor.current;
        setNow(anchor ? anchor.server + performance.now() - anchor.monotonic : Date.now());
      };
      tick();
      timer = window.setInterval(tick, clockInterval);
    };
    syncClock();
    document.addEventListener("visibilitychange", syncClock);
    return () => {
      if (timer !== null) window.clearInterval(timer);
      document.removeEventListener("visibilitychange", syncClock);
    };
  }, [clockInterval]);
  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const response = await fetch(`/version.json?t=${Date.now()}`, { cache: "no-store" });
        if (!response.ok) return;
        const value: { version?: string } = await response.json();
        if (active) setUpdateAvailable(typeof value.version === "string" && value.version !== __APP_VERSION__);
      } catch { /* Keep the app usable offline. */ }
    };
    void check();
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") void check(); }, 3_600_000);
    return () => { active = false; window.clearInterval(timer); };
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
    prepare.then(() => {
      void refreshAccount().catch(() => undefined);
      return refreshDashboard();
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить Casper Loto.")).finally(() => setLoading(false));
  }, [authenticated, initData, localDev, refreshAccount, refreshDashboard]);
  useEffect(() => {
    if (loading || !dashboard || view !== "home" || performance.getEntriesByName("miniapp:home-painted").length) return;
    let secondFrame = 0;
    const firstFrame = requestAnimationFrame(() => {
      secondFrame = requestAnimationFrame(() => {
        performance.mark("miniapp:home-painted");
        performance.measure("miniapp:navigation-to-home", { start: 0, end: "miniapp:home-painted" });
        document.documentElement.dataset.miniappHomeMs = String(Math.round(performance.now()));
      });
    });
    return () => { cancelAnimationFrame(firstFrame); cancelAnimationFrame(secondFrame); };
  }, [dashboard, loading, view]);
  useEffect(() => {
    if (!authenticated) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshDashboard().catch(() => undefined);
    }, 3_600_000);
    const resync = () => { if (document.visibilityState === "visible") void refreshDashboard().catch(() => undefined); };
    document.addEventListener("visibilitychange", resync);
    return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", resync); };
  }, [authenticated, refreshDashboard]);
  useEffect(() => {
    if (view !== "account" || accountView !== "tickets" || !authenticated) return;
    let active = true;
    miniAppApi.tickets(initData, ticketView, ticketLotteryFilter, ticketView === "history" && ticketWinsOnly).then((page) => {
      if (!active) return;
      setTickets(page.tickets);
      setTicketTotal(page.total);
      setTicketsHaveMore(page.has_more);
    }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты."); }).finally(() => { if (active) setTicketsLoading(false); });
    return () => { active = false; };
  }, [accountView, authenticated, initData, ticketLotteryFilter, ticketView, ticketWinsOnly, view]);

  const loadMoreTickets = async () => {
    setTicketsLoading(true);
    try {
      const page = await miniAppApi.tickets(initData, ticketView, ticketLotteryFilter, ticketView === "history" && ticketWinsOnly, tickets.length);
      setTickets((current) => [...current, ...page.tickets]);
      setTicketTotal(page.total);
      setTicketsHaveMore(page.has_more);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось загрузить следующую страницу билетов.");
    } finally {
      setTicketsLoading(false);
    }
  };
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
    if (view !== "fast" || !authenticated) return;
    const controller = new AbortController();
    const initial = window.setTimeout(() => {
      void refreshFastLive();
    }, 0);
    void miniAppApi.liveStream(initData, (feed) => {
      setFastFeed((current) => newestLiveFeed(current, feed));
    }, controller.signal, "fast").catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Не удалось подключиться к Fast-эфиру.");
    });
    return () => { window.clearTimeout(initial); controller.abort(); };
  }, [authenticated, initData, refreshDashboard, refreshFastLive, view]);

  const standardLotteries = useMemo(() => dashboard?.lotteries.filter((item) => !isFastLottery(item.code)) ?? [], [dashboard]);
  const fastLotteries = useMemo(() => dashboard?.lotteries.filter((item) => isFastLottery(item.code)) ?? [], [dashboard]);
  const firstAvailable = standardLotteries.find(item => item.purchase_available) ?? null;
  useEffect(() => {
    if (!authenticated || (view !== "home" && view !== "fast")) return;
    let active = true;
    const refresh = () => { if (!document.hidden) void miniAppApi.highlights(initData, view === "fast" ? "fast" : "standard").then(value => { if (active) { if (view === "fast") setFastHighlights(value); else setHighlights(value); } }).catch(() => undefined); };
    refresh();
    const timer = window.setInterval(refresh, 3_600_000);
    return () => { active = false; window.clearInterval(timer); };
  }, [authenticated, initData, view]);
  const cartGroups = useMemo(() => {
    const groups = new Map<string, CartTicket[]>();
    for (const ticket of cart) {
      const key = `${ticket.lotteryCode}:${ticket.drawCount}`;
      groups.set(key, [...(groups.get(key) ?? []), ticket]);
    }
    return Array.from(groups.values());
  }, [cart]);
  const serverNow = now;

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 2600);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    if (!error) return;
    const timer = window.setTimeout(() => setError(null), 4_500);
    return () => window.clearTimeout(timer);
  }, [error]);

  const openLottery = async (lotteryCode: string, initialNumbers: number[] = [], initialLive = false) => {
    if (lotteryCode === "kasper-live") { setKasperLiveOpen(true); return; }
    setRoomLive(initialLive);
    if (lotteryCode === "bingo") { setBingoOpen(true); return; }
    setError(null);
    // Show the already loaded lottery immediately. Fresh draw data and
    // favorites can arrive after the room is visible without blocking the tap.
    const cachedLottery = dashboard?.lotteries.find((item) => item.code === lotteryCode);
    if (cachedLottery) {
      setPickerInitialNumbers(initialNumbers.length === cachedLottery.numbers_to_pick ? initialNumbers : []);
      setFavorites([]);
      setPickerLottery(cachedLottery);
      if (cachedLottery.code !== "dual") void miniAppApi.favorites(initData, cachedLottery.code).then(setFavorites).catch(() => undefined);
    }
    try {
      const fresh = await refreshDashboard();
      const lottery = fresh?.lotteries.find((item) => item.code === lotteryCode);
      if (!lottery) {
        setNotice("Продажи для выбранного тиража уже завершены. Показываем актуальное расписание.");
        setView("home");
        return;
      }
      setPickerInitialNumbers(initialNumbers.length === lottery.numbers_to_pick ? initialNumbers : []);
      if (isFastLottery(lottery.code)) setFavorites([]);
      setPickerLottery(lottery);
      if (!isFastLottery(lottery.code) && lottery.code !== "dual") void miniAppApi.favorites(initData, lottery.code).then(setFavorites).catch(() => undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось обновить состояние продаж.");
    }
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

  const purchaseDirect = async (lotteryCode: string, combinations: number[][], drawCount: 1 | 5) => {
    if (purchasing) return false;
    setPurchasing(true); setPurchaseSuccess(false); setError(null);
    try {
      const result = await requestPurchase(lotteryCode, combinations, drawCount);
      applyPurchaseSnapshot(lotteryCode, result, combinations.length);
      setPurchaseSuccess(true); successHaptic();
      setNotice(`${combinations.length === 1 ? "Билет куплен" : `Куплено билетов: ${combinations.length}`} · списано ${formatCas(result.total_cost)}`);
      void Promise.allSettled([refreshDashboard(), refreshAccount()]).then(([dashboardRefresh]) => {
        const freshLottery = dashboardRefresh.status === "fulfilled" ? dashboardRefresh.value?.lotteries.find((lottery) => lottery.code === lotteryCode) : undefined;
        if (freshLottery) setPickerLottery((current) => current?.code === lotteryCode ? freshLottery : current);
      });
      setPickerInitialNumbers([]);
      await new Promise((resolve) => window.setTimeout(resolve, 480));
      return true;
    } catch (reason) {
      errorHaptic();
      setError(reason instanceof ApiError ? reason.message : "Покупка не выполнена.");
      return false;
    } finally {
      setPurchasing(false); setPurchaseSuccess(false);
    }
  };

  const purchaseCart = async () => {
    if (purchasing || cart.length === 0) return;
    const groups = new Map<string, CartTicket[]>();
    for (const item of cart) {
      const key = `${item.lotteryCode}:${item.drawCount}`;
      groups.set(key, [...(groups.get(key) ?? []), item]);
    }
    const total = cart.length;
    let done = 0;
    let totalCost = 0;
    setPurchasing(true); setPurchaseSuccess(false); setCartReceipt(null); setError(null); setPurchaseProgress({ done, total });
    try {
      for (const ticketsForLottery of groups.values()) {
        const sample = ticketsForLottery[0];
        const result = await requestPurchase(sample.lotteryCode, ticketsForLottery.map((ticket) => ticket.numbers), sample.drawCount);
        const purchasedIds = new Set(ticketsForLottery.map((ticket) => ticket.id));
        setCart((current) => current.filter((ticket) => !purchasedIds.has(ticket.id)));
        done += ticketsForLottery.length;
        totalCost += result.total_cost;
        setPurchaseProgress({ done, total });
        applyPurchaseSnapshot(sample.lotteryCode, result, ticketsForLottery.length);
      }
      setPurchaseSuccess(true); successHaptic();
      setNotice(`${done} ${plural(done, "билет куплен", "билета куплены", "билетов куплено")} · списано ${formatCas(totalCost)}`);
      setCartReceipt({ ticketCount: done, totalCost });
      void Promise.allSettled([refreshDashboard(), refreshAccount()]);
      await new Promise((resolve) => window.setTimeout(resolve, 480));
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
      return;
    }
    const preferences: NotificationPreferences = {
      telegram_enabled: true,
      draw_results_enabled: true,
      inactivity_reminders_enabled: true,
    };
    await saveNotificationPreferences(preferences);
    setNotice("Telegram-уведомления включены");
  };

  const refillDevBalance = async () => {
    setError(null);
    try {
      const result = await miniAppApi.devRefill();
      setDashboard((current) => current ? { ...current, balance: result.balance } : current);
      successHaptic(); setNotice("Тестовый баланс пополнен через ledger");
    } catch (reason) { errorHaptic(); setError(reason instanceof Error ? reason.message : "Баланс не пополнен."); }
  };

  if (!authenticated) return <main className="centered-message"><img alt="Casper Loto" className="standalone-brand-mark" src={logoSymbol} /><h1>Откройте Casper Loto в Telegram</h1><p>Безопасный вход выполняется автоматически при запуске Mini App.</p></main>;
  if (loading) return <Skeleton />;
  if (!dashboard) return <main className="centered-message"><div className="offline-mark">!</div><h1>Нет связи с Casper Loto</h1><p>{error}</p></main>;
  const bingoLottery = dashboard.lotteries.find(item => item.code === "bingo");
  if (kasperLiveOpen) return <Suspense fallback={<Skeleton />}><KasperLiveView initData={initData} balance={dashboard.balance} onClose={() => setKasperLiveOpen(false)} onSettled={(result) => {
    const winning = result.tickets.filter((ticket) => ticket.prize_amount > 0);
    setDashboard((current) => current ? { ...current, balance: result.balance_after, total_ticket_count: current.total_ticket_count + result.tickets.length, total_winning_ticket_count: current.total_winning_ticket_count + winning.length } : current);
    setAccount((current) => current ? { ...current, balance: result.balance_after, ticket_count: current.ticket_count + result.tickets.length, winning_ticket_count: current.winning_ticket_count + winning.length, total_spent: current.total_spent + result.total_cost, total_won: current.total_won + result.total_prize, best_win: Math.max(current.best_win, ...result.tickets.map((ticket) => ticket.prize_amount)) } : current);
  }} /></Suspense>;
  if (bingoOpen && bingoLottery) return <Suspense fallback={<Skeleton />}><BingoView initialTab={roomLive ? "live" : "choose"} lottery={bingoLottery} initData={initData} now={serverNow} balance={dashboard.balance} onClose={() => setBingoOpen(false)} onPurchased={(result) => { applyPurchaseSnapshot("bingo", result, result.ticket_ids.length); void Promise.allSettled([refreshDashboard(), refreshAccount()]); }} /></Suspense>;
  if (pickerLottery) return <main className={`app-shell picker-page ${isFastLottery(pickerLottery.code) ? "" : "draw-play-page"}`}><Suspense fallback={<Skeleton />}>{isFastLottery(pickerLottery.code) ? <FastPicker key={pickerLottery.code} error={error} lottery={pickerLottery} purchasing={purchasing} success={purchaseSuccess} onBuy={(numbers) => purchaseDirect(pickerLottery.code, [numbers], 1)} onClose={() => { setPickerLottery(null); setView(current => current === "catalog" || current === "live" ? current : "fast"); }} /> : <LotteryRoom balance={dashboard.balance} initialLive={roomLive} key={pickerLottery.code} lottery={pickerLottery} initData={initData} now={serverNow} onClose={() => { setRoomLive(false); setPickerLottery(null); }} onLiveModeChange={setRoomLive} onTickets={() => { setRoomLive(false); setPickerLottery(null); setTicketLotteryFilter(pickerLottery.code); setTicketsLoading(true); setAccountView("tickets"); setView("account"); }}><>{error && <p className="play-message is-error" role="alert">{error}</p>}{notice && <p className="play-message" role="status">{notice}</p>}<NumberPicker lottery={pickerLottery} balance={dashboard.balance} now={serverNow} purchasing={purchasing} initialNumbers={pickerInitialNumbers} favorites={favorites} onBuy={(numbers, drawCount) => purchaseDirect(pickerLottery.code, [numbers], drawCount)} onBuyMany={(combinations, drawCount) => purchaseDirect(pickerLottery.code, combinations, drawCount)} onSaveFavorite={(numbers) => void saveFavorite(numbers)} onDeleteFavorite={(id) => void deleteFavorite(id)} /></></LotteryRoom>}</Suspense></main>;

  return <main className={`app-shell ${view === "fast" ? "fast-shell" : ""}`}>
    {view !== "account" && <header className="app-header"><div aria-label="Casper Loto" className="brand-lockup"><picture><source media="(max-width: 520px)" srcSet={logoSymbol} /><img alt="" className="brand-logo-horizontal" width="138" height="46" fetchPriority="high" src={logoHorizontal} /></picture></div><div className="header-actions">{localDev && import.meta.env.VITE_DESIGN_PREVIEW !== "true" && <button className="dev-badge" onClick={() => void refillDevBalance()} type="button">+ TEST CAS</button>}{cart.length > 0 && <button aria-label={`Корзина: ${cart.length} ${plural(cart.length, "комбинация", "комбинации", "комбинаций")}`} className="header-cart" onClick={() => setView("cart")} type="button"><Icon name="cart" /><small>{cart.length}</small></button>}<Balance value={dashboard.balance} /></div></header>}
    {updateAvailable && <aside className="update-banner"><span><strong>Доступно обновление</strong><small>Корзина сохранена на этом устройстве.</small></span><button onClick={() => { const url = new URL(window.location.href); url.searchParams.set("app_update", String(Date.now())); window.location.replace(url.toString()); }} type="button">Обновить</button></aside>}
    {(error || notice) && <button className={`toast ${error ? "error" : "success"}`} onClick={() => { setError(null); setNotice(null); }} type="button"><span>{error ? "!" : "✓"}</span><span className="toast-message">{error ?? notice}</span><Icon name="close" /></button>}
    <Suspense fallback={<div className="skeleton view-loading-skeleton" aria-label="Загружаем экран" />} >
    {selectedTicket && (selectedTicket.lottery_code === "bingo" ? <BingoTicketDetail ticket={selectedTicket} onClose={() => setSelectedTicket(null)} /> : <TicketDetail lottery={dashboard.lotteries.find((item) => item.code === selectedTicket.lottery_code)} onClose={() => setSelectedTicket(null)} ticket={selectedTicket} />)}

    {view === "archive" && <Suspense fallback={<Skeleton />}><DrawArchive initData={initData} onBack={() => setView("home")} /></Suspense>}
    {view === "home" && <section className="view-content home-view" key="home"><Today stories={<Stories initData={initData} onOpen={(code) => { if (code === "casper-loto") setView("catalog"); else void openLottery(code); }} />} onArchive={() => { setView("archive"); window.scrollTo({ top: 0, behavior: "instant" }); }} lotteries={standardLotteries} now={serverNow} highlights={highlights} totalTicketCount={dashboard.total_ticket_count} totalWinningTicketCount={dashboard.total_winning_ticket_count} monthlyTotalPayout={dashboard.monthly_total_payout} onOpen={(code, live) => void openLottery(code, [], live)} onCatalog={() => setView("catalog")} onTickets={() => { setTicketsLoading(true); setTicketView("active"); setTicketWinsOnly(false); setAccountView("tickets"); setTicketLotteryFilter("scope:standard"); setView("account"); }} /></section>}
    {view === "catalog" && <section className="view-content catalog-view" key="catalog"><LotteryCatalog lotteries={dashboard.lotteries} now={serverNow} selectedFilter={catalogFilter} restoreScroll={catalogScroll} onFilterChange={filter => { setCatalogFilter(filter);setCatalogScroll(0);window.scrollTo({ top: 0, behavior: "instant" }); }} onOpen={code => { setCatalogScroll(window.scrollY);void openLottery(code); }} /></section>}
    {view === "live" && <section className="view-content catalog-view"><LotteryCatalog lotteries={dashboard.lotteries} now={serverNow} selectedFilter={catalogFilter} restoreScroll={catalogScroll} onFilterChange={filter => { setCatalogFilter(filter);setCatalogScroll(0);window.scrollTo({ top: 0, behavior: "instant" }); }} onOpen={code => { setCatalogScroll(window.scrollY);void openLottery(code); }} /></section>}

    {view === "fast" && <section className="view-content fast-world" key="fast"><FastView lotteries={fastLotteries} feed={fastFeed} now={serverNow} balance={dashboard.balance} purchasing={purchasing} onOpen={(code) => void openLottery(code)} onQuickBuy={(code, combinations) => void purchaseDirect(code, combinations, 1)} /><footer className="fast-world-footer">{fastHighlights?.last_jackpot && <div className="fast-last-jackpot"><small>ПОСЛЕДНИЙ ДЖЕКПОТ</small><strong><Money value={fastHighlights.last_jackpot.jackpot_amount} compact /></strong><span>{fastHighlights.last_jackpot.lottery_name} · {formatMoscow(fastHighlights.last_jackpot.occurred_at)} МСК</span></div>}<button className="fast-history-button" type="button" onClick={() => { setTicketsLoading(true); setTicketLotteryFilter("scope:fast"); setAccountView("tickets"); setView("account"); }}><Icon name="ticket" /><span><b>Билеты Casper Fast</b><small>Активные и история</small></span><strong>→</strong></button></footer></section>}

    {view === "account" && <section className="view-content personal-section" key="account">
      {accountView !== "overview" && <header className="personal-section-heading"><button type="button" aria-label="Обзор" onClick={() => { selectionHaptic(); setAccountView("overview"); void refreshAccount(); }}>← <span>Моё</span></button><h1>{accountView === "tickets" ? "Мои билеты" : "Уведомления"}</h1><button type="button" onClick={() => { if (accountView === "tickets") setAccountView("notifications"); else { setTicketsLoading(true); setAccountView("tickets"); } }}>{accountView === "tickets" ? "Уведомления" : "Билеты"}</button></header>}
      {accountView === "overview" && (account ? <AccountOverview account={account} lotteries={dashboard.lotteries} onCatalog={() => setView("catalog")} onTickets={() => { setTicketLotteryFilter(""); setTicketWinsOnly(false); setTicketsLoading(true); setTicketView("active"); setAccountView("tickets"); }} onHistory={() => { setTicketsLoading(true); setTicketLotteryFilter(""); setTicketWinsOnly(false); setTicketView("history"); setAccountView("tickets"); }} onNotifications={() => setAccountView("notifications")} onEnableTelegram={() => void enableTelegramNotifications()} onSavePreferences={(preferences) => void saveNotificationPreferences(preferences)} /> : <div className="skeleton account-skeleton" />)}
      {accountView === "tickets" && <><div className={`segmented-control ${ticketView}`}><i /><button className={ticketView === "active" ? "selected" : ""} onClick={() => { selectionHaptic(); if (ticketView !== "active") setTicketsLoading(true); setTicketView("active"); }} type="button">Активные</button><button className={ticketView === "history" ? "selected" : ""} onClick={() => { selectionHaptic(); if (ticketView !== "history") setTicketsLoading(true); setTicketView("history"); }} type="button">История</button></div><div className="ticket-filters"><select aria-label="Фильтр по лотерее" value={ticketLotteryFilter} onChange={(event) => { setTicketsLoading(true); setTicketLotteryFilter(event.target.value); }}><option value="scope:standard">Обычные лотереи</option><option value="scope:fast">Casper Fast</option><option value="">Все игры</option><option value="kasper-live">Casper LIVE</option>{dashboard.lotteries.map((lottery) => <option key={lottery.code} value={lottery.code}>{lottery.name}</option>)}</select>{ticketView === "history" && <button aria-pressed={ticketWinsOnly} className={ticketWinsOnly ? "active" : ""} onClick={() => { setTicketsLoading(true); setTicketWinsOnly((value) => !value); }} type="button">Только выигрыши</button>}<span>{ticketTotal} {plural(ticketTotal, "билет", "билета", "билетов")}</span></div>{ticketsLoading ? <div className="ticket-skeletons"><div className="skeleton ticket-skeleton" /><div className="skeleton ticket-skeleton" /></div> : tickets.length ? <><TicketGroups active={ticketView === "active"} lotteries={dashboard.lotteries} now={serverNow} onOpen={setSelectedTicket} tickets={tickets} />{ticketsHaveMore && <button className="load-more-tickets" disabled={ticketsLoading} onClick={() => void loadMoreTickets()} type="button">{ticketsLoading ? "Загружаем…" : `Показать ещё · ${tickets.length} из ${ticketTotal}`}</button>}</> : <EmptyState title={ticketView === "active" ? "Нет активных билетов" : "История пока пуста"} text={ticketView === "active" ? "Выберите лотерею и соберите свою комбинацию." : "Завершённые билеты появятся после розыгрыша."} action={ticketView === "active" && firstAvailable ? { label: "Выбрать лотерею", onClick: () => setView("catalog") } : undefined} />}{ticketView === "active" && firstAvailable && !ticketsLoading && tickets.length > 0 && <PrimaryButton className="sticky-action" onClick={() => void openLottery(firstAvailable.code)}>Ещё один билет</PrimaryButton>}</>}
      {accountView === "notifications" && <NotificationCenter notifications={notifications} onPlay={() => firstAvailable ? void openLottery(firstAvailable.code) : setView("home")} onTickets={() => { setTicketsLoading(true); setAccountView("tickets"); }} />}
    </section>}

    {view === "cart" && <section className="view-content" key="cart">
      <CartView cart={cart} groups={cartGroups} receipt={cartReceipt} purchasing={purchasing} success={purchaseSuccess} progress={purchaseProgress} canAdd={cart.length < CART_MAX_TICKETS} onClear={() => { setCart([]); setCartReceipt(null); }} onRemove={(id) => setCart((current) => current.filter((item) => item.id !== id))} onAdd={() => { setCartReceipt(null); setView("catalog"); }} onBuy={() => void purchaseCart()} onTickets={() => { setCartReceipt(null); setTicketsLoading(true); setTicketView("active"); setTicketLotteryFilter(""); setAccountView("tickets"); setView("account"); }} onHome={() => { setCartReceipt(null); setView("home"); }} />
    </section>}

    </Suspense>
    <MobileNavigation view={view} unreadNotifications={account?.unread_notification_count ?? 0} onChange={(target) => { if (target === "account") { setAccountView("overview"); void refreshAccount(); } if (target === view) window.scrollTo({ top: 0, behavior: "instant" }); setView(target); }} />
  </main>;
}
