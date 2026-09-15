import { LotteryCatalog, LotteryRoom, Today } from "./Discovery";
import type { Highlights } from "./Discovery";
import { BingoTicketDetail, BingoView } from "./BingoView";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { motion } from "motion/react";

import { ApiError, miniAppApi } from "./api";
import { CART_MAX_TICKETS, configuredCartTtl, loadCart, saveCart } from "./cart";
import {
  Balance,
  EmptyState,
  GrandNumberSet,
  Icon,
  NumberSet,
  PrimaryButton,
  Skeleton,
  StatusBadge,
} from "./components";
import { countdown, formatCas, formatDrawLabel, formatMoscow, formatTicketLabel } from "./format";
import { MINIAPP_TEXTS as copy } from "./content";
import { FastPicker, FastView } from "./FastView";
import { isFastLottery } from "./fast";
import { newestLiveFeed } from "./live";
import { isGrandLottery, lotteryCombination, matchLabel } from "./grand";
import { errorHaptic, requestTelegramWriteAccess, selectionHaptic, successHaptic } from "./telegram";
import type { Account, CartTicket, Dashboard, Favorite, LiveFeed, Lottery, NotificationPreferences, PurchaseResult, Ticket, UserNotification } from "./types";

type View = "catalog" | "home" | "live" | "fast" | "account" | "cart";
type TicketView = "active" | "history";
type AccountView = "overview" | "tickets" | "notifications";
interface CartReceipt { ticketCount: number; totalCost: number }

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

function compactCombination(ticket: Ticket, lottery?: Lottery): string {
  const offset = lottery?.secondary_storage_offset;
  if (!offset) return ticket.numbers.join("  ");
  const main = ticket.numbers.filter((value) => value <= offset).join("  ");
  const special = ticket.numbers.filter((value) => value > offset).map((value) => value - offset).join("  ");
  return `${main}  +  ${special}`;
}

function TicketCard({ ticket, lottery, index = 0, onOpen }: { ticket: Ticket; lottery?: Lottery; index?: number; onOpen: () => void }) {
  const refunded = ticket.status === "REFUNDED";
  const complete = ticket.status !== "PURCHASED";
  const winner = complete && ticket.prize_amount > 0;
  const matches = ticket.matches ?? 0;
  return <button className={`ticket-card compact-ticket ${winner ? "winner" : ""}`} onClick={onOpen} style={{ "--item-index": index } as CSSProperties} type="button">
    <div className="ticket-meta">
      <div><span className="eyebrow">{ticket.lottery_name}{ticket.source === "AUTO_PLAY" ? " · АВТОБИЛЕТ" : ""}</span><h3>{formatTicketLabel(ticket.lottery_code, ticket.public_number)}</h3></div>
      <StatusBadge active={!complete} label={refunded ? "Возврат" : undefined} />
    </div>
    <div className="compact-combination">{compactCombination(ticket, lottery)}<span>Открыть билет →</span></div>
    {complete && <div className={`ticket-result ${winner ? "win" : "loss"} ${refunded ? "refunded" : ""}`}>
      <div><span>{refunded ? "Билет возвращён" : matches > 0 ? `Совпадений: ${matchLabel(ticket.lottery_code, matches, ticket.numbers.length === 7)}` : "Совпадений нет"}</span><small>{refunded ? "Стоимость зачислена на баланс" : winner ? "Выигрыш зачислен" : "Без выигрыша"}</small></div>
      <strong>{refunded ? `+${formatCas(ticket.purchase_price)}` : winner ? `+${formatCas(ticket.prize_amount)}` : "0 CAS"}</strong>
    </div>}
  </button>;
}

function TicketGroups({ tickets, lotteries, now, active, onOpen }: { tickets: Ticket[]; lotteries: Lottery[]; now: number; active: boolean; onOpen: (ticket: Ticket) => void }) {
  const groups = new Map<string, Ticket[]>();
  for (const ticket of tickets) {
    const key = `${ticket.lottery_code}:${ticket.draw_number}`;
    groups.set(key, [...(groups.get(key) ?? []), ticket]);
  }
  return <div className="ticket-groups">{Array.from(groups.entries()).map(([key, items], groupIndex) => {
    const first = items[0];
    const total = first.draw_ticket_count ?? items.length;
    const lottery = lotteries.find((item) => item.code === first.lottery_code);
    return <section className={`ticket-draw-group lottery-${first.lottery_code} ${active && groupIndex === 0 ? "next-ticket-group" : ""}`} key={key}><header><div>{active && groupIndex === 0 && <b>Следующий</b>}<span className="eyebrow">{first.lottery_name}</span><h2>{formatDrawLabel(first.lottery_code, first.draw_number)}</h2><time>{formatMoscow(first.scheduled_at)} МСК{active ? ` · через ${countdown(first.scheduled_at, now)}` : ""}</time></div><div><strong>{total}</strong><small>{plural(total, "билет", "билета", "билетов")}</small></div></header><div className="ticket-group-list">{items.map((ticket, index) => <TicketCard index={index} key={ticket.id} lottery={lottery} onOpen={() => onOpen(ticket)} ticket={ticket} />)}</div></section>;
  })}</div>;
}

function TicketDetail({ ticket, lottery, onClose }: { ticket: Ticket; lottery?: Lottery; onClose: () => void }) {
  const completed = ticket.status !== "PURCHASED";
  const codeMode = lottery?.ruleset_code === "code_4_digits" && ticket.numbers.length === 4;
  const winning = new Set(ticket.winning_numbers ?? []);
  const selected = new Set(ticket.numbers);
  const matched = new Set(ticket.numbers.filter((value) => winning.has(value)));
  const offset = lottery?.secondary_storage_offset ?? 0;
  const primaryMax = lottery?.primary_max_number ?? lottery?.max_number ?? Math.max(...ticket.numbers, ...(ticket.winning_numbers ?? []));
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
  return <div className="ticket-detail-backdrop" onClick={onClose} role="presentation"><motion.article animate={{ opacity: 1, y: 0, scale: 1 }} aria-label={`Билет ${ticket.public_number}`} aria-modal="true" className={`paper-ticket lottery-${ticket.lottery_code}`} initial={{ opacity: 0, y: 18, scale: .97 }} onClick={(event) => event.stopPropagation()} role="dialog">
    <button aria-label="Закрыть билет" className="paper-close" onClick={onClose} type="button"><Icon name="close" /></button>
    <header><span>{ticket.lottery_name}</span><strong>{formatTicketLabel(ticket.lottery_code, ticket.public_number)}</strong><small>{formatDrawLabel(ticket.lottery_code, ticket.draw_number)} · {formatMoscow(ticket.scheduled_at)} МСК</small></header>
    <div className="paper-perforation" />
    <section><div className="paper-field-title"><b>{codeMode ? "Четырёхзначный код" : secondaryMax ? "Основное поле" : "Комбинация"}</b><small>{ticket.numbers.filter((value) => !offset || value <= offset).join(codeMode ? "" : " · ")}</small></div>{codeMode ? <div className="paper-code-field">{ticket.numbers.map((value, index) => <i className={`${ticket.winning_numbers?.[index] !== undefined ? "winning" : ""} ${ticket.winning_numbers?.[index] === value ? "matched" : ""}`} key={index}>{value}</i>)}</div> : renderField(primaryMax)}</section>
    {secondaryMax > 0 && <section className="paper-special"><div className="paper-field-title"><b>Специальное поле</b><small>{ticket.numbers.filter((value) => value > offset).map((value) => value - offset).join(" · ")}</small></div>{renderField(secondaryMax, offset)}</section>}
    {completed && <section className="paper-result"><div><span>Выпавшие числа</span><strong>{compactCombination({ ...ticket, numbers: ticket.winning_numbers ?? [] }, lottery)}</strong></div><p>{ticket.matches ? `Совпало ${matchLabel(ticket.lottery_code, ticket.matches, ticket.numbers.length === 7)}` : "Совпадений нет"}</p><b className={ticket.prize_amount > 0 ? "win" : "loss"}>{ticket.prize_amount > 0 ? `Выигрыш: ${formatCas(ticket.prize_amount)}` : "Без выигрыша"}</b></section>}
    <footer><span>Стоимость</span><strong>{formatCas(ticket.purchase_price)}</strong><small>CAS · KASPER LOTO</small></footer>
  </motion.article></div>;
}

function NumberPicker({ lottery, purchasing, success, initialNumbers = [], favorites, cartRemaining, onBuy, onAdd, onAddMany, onSaveFavorite, onDeleteFavorite }: { lottery: Lottery; purchasing: boolean; success: boolean; initialNumbers?: number[]; favorites: Favorite[]; cartRemaining: number; onBuy: (numbers: number[], drawCount: 1 | 5) => Promise<boolean>; onAdd: (numbers: number[], drawCount: 1 | 5) => void; onAddMany: (combinations: number[][], drawCount: 1 | 5) => void; onSaveFavorite: (numbers: number[]) => void; onDeleteFavorite: (id: string) => void }) {
  const [selected, setSelected] = useState<number[]>(initialNumbers);
  const [drawCount, setDrawCount] = useState<1 | 5>(1);
  const grand = isGrandLottery(lottery);
  const grandOffset = lottery.secondary_storage_offset ?? 35;
  const grandMainCount = lottery.primary_numbers_to_pick ?? 5;
  const grandSpecialCount = lottery.secondary_numbers_to_pick ?? 2;
  const mainSelected = selected.filter((value) => value <= grandOffset);
  const specialSelected = selected.filter((value) => value > grandOffset);
  const ready = grand
    ? mainSelected.length === grandMainCount && specialSelected.length === grandSpecialCount
    : selected.length === lottery.numbers_to_pick;
  const saved = favorites.some((favorite) => favorite.numbers.length === selected.length && favorite.numbers.every((value, index) => value === selected[index]));
  const toggle = (value: number) => {
    setSelected((current) => {
      const inSpecialField = grand && value > grandOffset;
      const fieldCount = grand
        ? current.filter((item) => inSpecialField ? item > grandOffset : item <= grandOffset).length
        : current.length;
      const fieldLimit = inSpecialField ? grandSpecialCount : grand ? grandMainCount : lottery.numbers_to_pick;
      if (!current.includes(value) && fieldCount >= fieldLimit) return current;
      selectionHaptic();
      return current.includes(value) ? current.filter((item) => item !== value) : [...current, value].sort((left, right) => left - right);
    });
  };
  const randomize = () => {
    selectionHaptic();
    setSelected(lotteryCombination(lottery));
  };
  const buy = async () => {
    if (await onBuy(selected, drawCount)) setSelected([]);
  };
  const numberGroups = lottery.code === "september"
    ? [[1, 11], [12, 22], [23, 33]] as const
    : [[1, lottery.max_number]] as const;
  const pickerMood: Record<string, string> = {
    september: "Три главы одного сентябрьского вечера",
    pll: "Загадайте момент. Время найдёт своих.",
    pss: "Тишина северного озера перед грозой",
    khan: "Классический тираж: шесть чисел из тридцати шести",
    weekly: "Два независимых поля. Один грандиозный шанс.",
    grob: "Три числа. Одна аккуратно оформленная могила.",
  };

  return <div className={`picker-shell lottery-${lottery.code}`}>
    <div className="selection-heading"><span>{formatDrawLabel(lottery.code, lottery.draw_number ?? 0)} · ВАША КОМБИНАЦИЯ</span><h1>{lottery.code === "pll" ? "Загадайте момент." : grand ? "Пять чисел. Две звезды." : `Выберите ${lottery.numbers_to_pick} ${lottery.numbers_to_pick < 5 ? "числа" : "чисел"}`}</h1><p>{pickerMood[lottery.code] ?? "Ваша комбинация на ближайший тираж"}</p></div>
    <div className="picker-summary"><div><span>К оплате за комбинацию</span><strong>{formatCas((lottery.ticket_price ?? 0) * drawCount)}</strong></div><div className="selection-meter"><span>Выбрано</span><strong>{grand ? `${mainSelected.length}+${specialSelected.length}` : selected.length}<i>/ {grand ? "5+2" : lottery.numbers_to_pick}</i></strong></div></div>
    {grand ? <div className="grand-fields">
      <section className="picker-board grand-main-field"><div className="picker-board-label"><span>Поле №1 · Основные числа</span><small>1–35 · выберите ровно 5</small></div><div className="number-grid"><div className="number-group">{Array.from({ length: lottery.primary_max_number ?? 35 }, (_, index) => index + 1).map((value) => <motion.button aria-pressed={selected.includes(value)} className={selected.includes(value) ? "pick-number selected" : "pick-number"} key={value} onClick={() => toggle(value)} type="button" whileTap={{ scale: .86 }}><span>{value}</span><i aria-hidden="true" /></motion.button>)}</div></div></section>
      <section className="picker-board grand-special-field"><div className="picker-board-label"><span>Поле №2 · Специальные числа</span><small>1–5 · выберите ровно 2</small></div><div className="number-grid"><div className="number-group">{Array.from({ length: lottery.secondary_max_number ?? 5 }, (_, index) => index + 1).map((displayValue) => { const value = displayValue + grandOffset; return <motion.button aria-pressed={selected.includes(value)} className={selected.includes(value) ? "pick-number selected" : "pick-number"} key={value} onClick={() => toggle(value)} type="button" whileTap={{ scale: .84 }}><span>{displayValue}</span><i aria-hidden="true">★</i></motion.button>; })}</div></div></section>
    </div> : <div className="picker-board"><div className="picker-board-label"><span>{lottery.code === "grob" ? "Поле захоронений" : "Поле комбинации"}</span><small>{lottery.code === "september" ? "Три части · 33 числа" : `${lottery.max_number} чисел · выберите ${lottery.numbers_to_pick}`}</small></div><div className="number-grid" aria-label="Выбор чисел">{numberGroups.map(([from, to], groupIndex) => <div className="number-group" key={from}>{lottery.code === "september" && <span className="number-group-label">{groupIndex === 0 ? "Начало" : groupIndex === 1 ? "Середина" : "После"}</span>}{Array.from({ length: to - from + 1 }, (_, index) => from + index).map((value) => <motion.button aria-pressed={selected.includes(value)} className={selected.includes(value) ? "pick-number selected" : "pick-number"} key={value} onClick={() => toggle(value)} type="button" whileTap={{ scale: lottery.code === "grob" ? .82 : .88 }}><span>{value}</span><i aria-hidden="true" /></motion.button>)}</div>)}</div></div>}
    <div className="selected-combination"><span>{lottery.code === "grob" ? "Ваша могила" : "Ваш билет"}</span>{grand ? <GrandNumberSet values={selected} /> : <div>{Array.from({ length: lottery.numbers_to_pick }, (_, index) => <i className={selected[index] ? "filled" : ""} key={index}>{selected[index] ?? "—"}</i>)}</div>}</div>
    <button className="secondary-button random-button" onClick={randomize} type="button"><Icon name="spark" />{copy.actions.randomNumbers}</button>
    <section className="multi-draw-choice"><div><strong>Повторить комбинацию</strong><small>Без автопродления и скрытых списаний</small></div><div><button className={drawCount === 1 ? "selected" : ""} onClick={() => setDrawCount(1)} type="button">1 тираж</button><button className={drawCount === 5 ? "selected" : ""} onClick={() => setDrawCount(5)} type="button">5 тиражей</button></div>{drawCount === 5 && <p>Эти числа участвуют в текущем и следующих 4 тиражах. Полная сумма оплачивается сейчас.</p>}</section>
    {ready && <button className={`favorite-action ${saved ? "saved" : ""}`} disabled={saved} onClick={() => onSaveFavorite(selected)} type="button">{saved ? "★ Комбинация сохранена" : "☆ Сохранить комбинацию"}</button>}
    {favorites.length > 0 && <div className="favorite-list"><span>Избранные</span>{favorites.map((favorite) => <div key={favorite.id}><button onClick={() => setSelected(favorite.numbers)} type="button">{grand ? <GrandNumberSet values={favorite.numbers} /> : favorite.numbers.join(" · ")}</button><button aria-label="Удалить из избранного" onClick={() => onDeleteFavorite(favorite.id)} type="button">×</button></div>)}</div>}
    <div className="quick-batches"><div><span>Быстрая корзина</span><small>Случайные комбинации</small></div><div>{[5, 10, 25, 50, 100].map((count) => <button disabled={purchasing || cartRemaining < count} key={count} onClick={() => onAddMany(Array.from({ length: count }, () => lotteryCombination(lottery)), drawCount)} type="button">+{count}</button>)}</div></div>
    <div className="picker-actions"><button aria-label="Быстрый случайный выбор" className="picker-random-action" disabled={purchasing} onClick={randomize} type="button"><Icon name="spark" /><span>Случайно</span></button><button className="secondary-button" disabled={!ready || purchasing} onClick={() => onAdd(selected, drawCount)} type="button">{copy.actions.addToCart}</button><PrimaryButton disabled={!ready} loading={purchasing} success={success} onClick={() => void buy()}>{success ? "Билет куплен" : purchasing ? "Оформляем…" : drawCount === 5 ? copy.actions.buyFiveDraws : copy.actions.buyTicket}</PrimaryButton></div>
    <p className="picker-note">Комбинация фиксируется после подтверждения покупки.</p>
  </div>;
}

function BottomNavigation({ view, unreadNotifications, onChange }: { view: View; unreadNotifications: number; onChange: (view: View) => void }) {
  const items: { id: View; label: string; icon: "home" | "catalog" | "fast" | "profile"; count: number }[] = [
    { id: "home", label: "Сегодня", icon: "home", count: 0 },
    { id: "catalog", label: "Лотереи", icon: "catalog", count: 0 },
    { id: "fast", label: copy.navigation.fast, icon: "fast", count: 0 },
    { id: "account", label: copy.navigation.account, icon: "profile", count: unreadNotifications },
  ];
  return <nav className="bottom-nav" aria-label="Основная навигация">{items.map((item) => <button aria-label={item.id === "account" && item.count > 0 ? `${item.label}: есть непрочитанные уведомления` : item.label} className={view === item.id ? "active" : ""} key={item.id} onClick={() => { selectionHaptic(); onChange(item.id); }} type="button"><i className="nav-indicator" /><span><Icon name={item.icon} />{item.id === "account" && item.count > 0 && <small className="notification-dot" />}</span><b>{item.label}</b></button>)}</nav>;
}

function AccountOverview({ account, onTickets, onHistory, onEnableTelegram, onSavePreferences }: { onTickets: () => void; onHistory: () => void; account: Account; onEnableTelegram: () => void; onSavePreferences: (preferences: NotificationPreferences) => void }) {
  const preferences = account.notification_preferences;
  const winRate = account.ticket_count ? Math.round((account.winning_ticket_count / account.ticket_count) * 100) : 0;
  const net = account.total_won - account.total_spent;
  const favoriteOffset = account.favorite_lottery_code === "weekly" ? 35 : account.favorite_lottery_code === "pulse" ? 10 : 0;
  return <div className="account-overview">
    <section className="account-identity"><div className="account-monogram"><span>{account.display_name.slice(0, 1)}</span><i /></div><div className="account-name"><span>{copy.account.playerLabel}</span><h2>{account.display_name}</h2><small>Участник клуба · {account.ticket_count} {plural(account.ticket_count, "билет", "билета", "билетов")}</small></div><div className="account-balance"><span>Доступно</span><strong>{formatCas(account.balance)}</strong></div></section>
    <div className="account-shortcuts"><button onClick={onTickets} type="button"><Icon name="ticket" /><span><strong>Активные билеты</strong><small>{account.active_ticket_count ? `${account.active_ticket_count} в ближайших тиражах` : "Пока нет билетов в игре"}</small></span><b>→</b></button><button onClick={onHistory} type="button"><Icon name="replay" /><span><strong>История участия</strong><small>Завершённые тиражи и выигрыши</small></span><b>→</b></button></div>
    <section className="account-highlight"><div><span>Главный результат</span><strong>{formatCas(account.best_win)}</strong><small>ваш лучший выигрыш</small></div><div className="account-highlight-art" aria-hidden="true"><i /><i /><b /></div></section>
    <section className="account-scoreline"><article><span>В игре сейчас</span><strong>{account.active_ticket_count}</strong></article><article><span>Выигрышных от всех</span><strong>{winRate}%</strong></article><article><span>Выиграно − потрачено</span><strong className={net >= 0 ? "positive" : "negative"}>{net >= 0 ? "+" : "−"}{formatCas(Math.abs(net))}</strong></article></section>
    <section className="account-ledger"><header><span>Ваша игровая история</span><small>За всё время</small></header><div><span>Всего билетов</span><strong>{account.ticket_count}</strong></div><div><span>Выигрышных билетов</span><strong>{account.winning_ticket_count}</strong></div><div><span>Потрачено</span><strong>{formatCas(account.total_spent)}</strong></div><div><span>Выиграно</span><strong>{formatCas(account.total_won)}</strong></div><div><span>Самый крупный выигрыш</span><strong>{formatCas(account.best_win)}</strong></div></section>
    <section className="account-favorites"><header><span>Ваш игровой почерк</span><small>По всем билетам</small></header><div><span>Любимая лотерея</span><strong>{account.favorite_lottery_name ?? "Пока определяется"}</strong></div><div><span>Чаще всего выбираете</span>{account.favorite_numbers?.length ? <p>{account.favorite_numbers.map((value) => <i key={value}>{favoriteOffset && value > favoriteOffset ? `★${value - favoriteOffset}` : value}</i>)}</p> : <strong>Пока мало данных</strong>}</div></section>
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

function CartView({ cart, groups, receipt, purchasing, success, progress, canAdd, onClear, onRemove, onAdd, onBuy, onTickets, onHome }: { cart: CartTicket[]; groups: CartTicket[][]; receipt: CartReceipt | null; purchasing: boolean; success: boolean; progress: { done: number; total: number } | null; canAdd: boolean; onClear: () => void; onRemove: (id: string) => void; onAdd: () => void; onBuy: () => void; onTickets: () => void; onHome: () => void }) {
  const total = cart.reduce((sum, item) => sum + item.price * item.drawCount, 0);
  if (receipt && !cart.length) return <div className="cart-success"><div className="cart-success-mark" aria-hidden="true">✓</div><span className="eyebrow">Покупка завершена</span><h1>Билеты уже в игре</h1><strong>{receipt.ticketCount} {plural(receipt.ticketCount, "билет", "билета", "билетов")} · {formatCas(receipt.totalCost)}</strong><p>Они уже участвуют в своих тиражах.</p><div><button className="primary-button" onClick={onAdd} type="button">Купить ещё</button><button onClick={onTickets} type="button">Мои билеты</button><button onClick={onHome} type="button">На главную</button></div></div>;
  if (!cart.length) return <div className="cart-empty"><div className="cart-empty-art" aria-hidden="true"><span /><i /><b>+</b></div><span className="eyebrow">Ваш следующий билет</span><h1>Корзина пока пуста</h1><p>Соберите комбинацию — мы аккуратно сохраним её здесь до оформления.</p><button className="cart-empty-action" onClick={onHome} type="button">Выбрать лотерею <span>→</span></button></div>;

  return <div className="cart-layout">
    <header className="cart-header"><div><span className="eyebrow">Готово к оформлению</span><h1>{cart.length} {plural(cart.length, "комбинация", "комбинации", "комбинаций")}</h1></div><button disabled={purchasing} onClick={onClear} type="button">Очистить</button></header>
    <div className="cart-groups">{groups.map((items, groupIndex) => <motion.section animate={{ opacity: 1, y: 0 }} className={`cart-group lottery-${items[0].lotteryCode}`} initial={{ opacity: 0, y: 9 }} key={`${items[0].lotteryCode}:${items[0].drawCount}`} transition={{ delay: groupIndex * .05 }}><header><div><span>{items[0].lotteryName}</span><strong>В группе: {items.length}</strong></div><div><small>{items[0].drawCount === 5 ? "на 5 тиражей" : "ближайший тираж"}</small><b>{formatCas(items.reduce((sum, item) => sum + item.price * item.drawCount, 0))}</b></div></header><div className="cart-ticket-stack">{items.slice(0, 5).map((ticket, index) => <article className="cart-combination" key={`${ticket.id}:${index}`}><span>{String(index + 1).padStart(2, "0")}</span>{isGrandLottery(ticket.lotteryCode) ? <GrandNumberSet values={ticket.numbers} /> : <NumberSet values={ticket.numbers} />}<button className="remove-button" onClick={() => { selectionHaptic(); onRemove(ticket.id); }} type="button" aria-label={`Удалить билет ${index + 1}`}><Icon name="close" /></button></article>)}{items.length > 5 && <p>+ ещё {items.length - 5} — оформим одной операцией</p>}</div></motion.section>)}</div>
    {progress && <div className="purchase-progress"><div><span>Оформляем билеты</span><strong>{progress.done} из {progress.total}</strong></div><i><span style={{ width: `${(progress.done / progress.total) * 100}%` }} /></i></div>}
    <aside className="cart-checkout"><div className="checkout-receipt"><span>Итого</span><strong>{formatCas(total)}</strong><small>{cart.length} комб. · безопасная покупка одной операцией</small></div><button aria-label="Добавить комбинацию" className="checkout-add" disabled={!canAdd || purchasing} onClick={onAdd} type="button">+ Добавить ещё</button><PrimaryButton className="checkout-buy" loading={purchasing} success={success} onClick={onBuy}>{success ? "Билеты куплены" : purchasing ? `Оформляем ${progress?.done ?? 0} из ${progress?.total ?? cart.length}` : `Купить ${cart.length} комб.`}</PrimaryButton></aside>
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
  const [pickerLottery, setPickerLottery] = useState<Lottery | null>(null);
  const [pickerInitialNumbers, setPickerInitialNumbers] = useState<number[]>([]);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [ticketLotteryFilter, setTicketLotteryFilter] = useState("scope:standard");
  const [ticketWinsOnly, setTicketWinsOnly] = useState(false);
  const [loading, setLoading] = useState(authenticated);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [purchasing, setPurchasing] = useState(false);
  const [roomLive, setRoomLive] = useState(false);
  const [fastHighlights, setFastHighlights] = useState<Highlights | null>(null);
  const [highlights, setHighlights] = useState<Highlights | null>(null);
  const [bingoOpen, setBingoOpen] = useState(import.meta.env.VITE_DESIGN_PREVIEW === "true" && new URLSearchParams(window.location.search).get("screen") === "bingo");
  const [purchaseSuccess, setPurchaseSuccess] = useState(false);
  const [purchaseProgress, setPurchaseProgress] = useState<{ done: number; total: number } | null>(null);
  const [cartReceipt, setCartReceipt] = useState<CartReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const clockAnchor = useRef<{ server: number; monotonic: number } | null>(null);
  const clockNeedsSync = useRef(true);

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
  }, []);

  const refreshDashboard = useCallback(async () => {
    if (!authenticated) return null;
    const requestedAt = performance.now();
    const value = await miniAppApi.dashboard(initData);
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
      timer = window.setInterval(tick, 200);
    };
    syncClock();
    document.addEventListener("visibilitychange", syncClock);
    return () => {
      if (timer !== null) window.clearInterval(timer);
      document.removeEventListener("visibilitychange", syncClock);
    };
  }, []);
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
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") void check(); }, 60_000);
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
    prepare.then(() => Promise.all([refreshDashboard(), refreshAccount()])).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить K-Loto.")).finally(() => setLoading(false));
  }, [authenticated, initData, localDev, refreshAccount, refreshDashboard]);
  useEffect(() => {
    if (!authenticated) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void refreshDashboard().catch(() => undefined);
    }, 15_000);
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
      void refreshDashboard().catch(() => undefined);
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
    const timer = window.setInterval(refresh, 15000);
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

  const openLottery = async (lotteryCode: string, initialNumbers: number[] = [], initialLive = false) => {
    setRoomLive(initialLive);
    if (lotteryCode === "bingo") { setBingoOpen(true); return; }
    setError(null);
    try {
      const fresh = await refreshDashboard();
      const lottery = fresh?.lotteries.find((item) => item.code === lotteryCode);
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
    setCartReceipt(null);
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

  if (!authenticated) return <main className="centered-message"><img alt="Kasper Loto" className="standalone-brand-mark" src="/brand/kasper-symbol.svg" /><h1>Откройте Kasper Loto в Telegram</h1><p>Безопасный вход выполняется автоматически при запуске Mini App.</p></main>;
  if (loading) return <Skeleton />;
  if (!dashboard) return <main className="centered-message"><div className="offline-mark">!</div><h1>Нет связи с K-Loto</h1><p>{error}</p></main>;
  const bingoLottery = dashboard.lotteries.find(item => item.code === "bingo");
  if (bingoOpen && bingoLottery) return <BingoView initialTab={roomLive ? "live" : "choose"} lottery={bingoLottery} initData={initData} now={serverNow} balance={dashboard.balance} onClose={() => setBingoOpen(false)} onPurchased={(result) => { applyPurchaseSnapshot("bingo", result, result.ticket_ids.length); void Promise.allSettled([refreshDashboard(), refreshAccount()]); }} />;
  if (pickerLottery) return <main className="app-shell picker-page">{isFastLottery(pickerLottery.code) ? <FastPicker lottery={pickerLottery} purchasing={purchasing} success={purchaseSuccess} onBuy={(numbers) => purchaseDirect(pickerLottery.code, [numbers], 1)} onClose={() => { setPickerLottery(null); setView("fast"); }} /> : <LotteryRoom balance={dashboard.balance} initialLive={roomLive} key={pickerLottery.code} lottery={pickerLottery} initData={initData} now={serverNow} onClose={() => setPickerLottery(null)} onTickets={() => { setPickerLottery(null); setTicketLotteryFilter(pickerLottery.code); setTicketsLoading(true); setAccountView("tickets"); setView("account"); }}><NumberPicker lottery={pickerLottery} purchasing={purchasing} success={purchaseSuccess} initialNumbers={pickerInitialNumbers} favorites={favorites} cartRemaining={CART_MAX_TICKETS - cart.length} onAdd={(numbers, drawCount) => addManyToCart(pickerLottery, [numbers], drawCount)} onAddMany={(combinations, drawCount) => addManyToCart(pickerLottery, combinations, drawCount)} onBuy={(numbers, drawCount) => purchaseDirect(pickerLottery.code, [numbers], drawCount)} onSaveFavorite={(numbers) => void saveFavorite(numbers)} onDeleteFavorite={(id) => void deleteFavorite(id)} /></LotteryRoom>}</main>;

  return <main className={`app-shell ${view === "fast" ? "fast-shell" : ""}`}>
    <header className="app-header"><div aria-label="Kasper Loto" className="brand-lockup"><img alt="" className="brand-logo-horizontal" src="/brand/kasper-loto-horizontal.svg" /><img alt="" className="brand-logo-symbol" src="/brand/kasper-symbol.svg" /></div><div className="header-actions">{localDev && import.meta.env.VITE_DESIGN_PREVIEW !== "true" && <button className="dev-badge" onClick={() => void refillDevBalance()} type="button">+ TEST CAS</button>}{cart.length > 0 && <button aria-label={`Корзина: ${cart.length} ${plural(cart.length, "комбинация", "комбинации", "комбинаций")}`} className="header-cart" onClick={() => setView("cart")} type="button"><Icon name="cart" /><small>{cart.length}</small></button>}<Balance value={dashboard.balance} /></div></header>
    {updateAvailable && <aside className="update-banner"><span><strong>Доступно обновление</strong><small>Корзина сохранена на этом устройстве.</small></span><button onClick={() => { const url = new URL(window.location.href); url.searchParams.set("app_update", String(Date.now())); window.location.replace(url.toString()); }} type="button">Обновить</button></aside>}
    {(error || notice) && <button className={`toast ${error ? "error" : "success"}`} onClick={() => { setError(null); setNotice(null); }} type="button"><span>{error ? "!" : "✓"}</span><span className="toast-message">{error ?? notice}</span><Icon name="close" /></button>}
    {selectedTicket && (selectedTicket.lottery_code === "bingo" ? <BingoTicketDetail ticket={selectedTicket} onClose={() => setSelectedTicket(null)} /> : <TicketDetail lottery={dashboard.lotteries.find((item) => item.code === selectedTicket.lottery_code)} onClose={() => setSelectedTicket(null)} ticket={selectedTicket} />)}

    {view === "home" && <section className="view-content home-view" key="home"><Today lotteries={standardLotteries} now={serverNow} highlights={highlights} totalTicketCount={dashboard.total_ticket_count} totalWinningTicketCount={dashboard.total_winning_ticket_count} monthlyTotalPayout={dashboard.monthly_total_payout} onOpen={(code, live) => void openLottery(code, [], live)} onCatalog={() => setView("catalog")} onTickets={() => { setTicketsLoading(true); setAccountView("tickets"); setTicketLotteryFilter("scope:standard"); setView("account"); }} /></section>}
    {view === "catalog" && <section className="view-content catalog-view" key="catalog"><LotteryCatalog lotteries={standardLotteries} onOpen={code => void openLottery(code)} /></section>}
    {view === "live" && <section className="view-content catalog-view"><LotteryCatalog lotteries={standardLotteries} onOpen={code => void openLottery(code)} /></section>}

    {view === "fast" && <section className="view-content fast-world" key="fast"><FastView lotteries={fastLotteries} feed={fastFeed} now={serverNow} balance={dashboard.balance} purchasing={purchasing} onOpen={(code) => void openLottery(code)} onQuickBuy={(code, combinations) => void purchaseDirect(code, combinations, 1)} /><footer className="fast-world-footer">{fastHighlights?.last_jackpot && <div className="fast-last-jackpot"><small>ПОСЛЕДНИЙ ДЖЕКПОТ</small><strong>{formatCas(fastHighlights.last_jackpot.jackpot_amount)}</strong><span>{fastHighlights.last_jackpot.lottery_name} · {formatMoscow(fastHighlights.last_jackpot.occurred_at)} МСК</span></div>}<button className="fast-history-button" type="button" onClick={() => { setTicketsLoading(true); setTicketLotteryFilter("scope:fast"); setAccountView("tickets"); setView("account"); }}><Icon name="ticket" /><span><b>Билеты Kasper Fast</b><small>Активные и история</small></span><strong>→</strong></button></footer></section>}

    {view === "account" && <section className="view-content" key="account">
      <div className="page-title account-title"><h1>{copy.account.title}</h1><p>{copy.account.subtitle}</p></div>
      <div className="account-tabs"><button className={accountView === "overview" ? "selected" : ""} onClick={() => { selectionHaptic(); setAccountView("overview"); void refreshAccount(); }} type="button"><Icon name="profile" />Обзор</button><button className={accountView === "tickets" ? "selected" : ""} onClick={() => { selectionHaptic(); if (accountView !== "tickets") setTicketsLoading(true); setAccountView("tickets"); }} type="button"><Icon name="ticket" />Билеты{account?.active_ticket_count ? <small>{account.active_ticket_count}</small> : null}</button><button aria-label={account?.unread_notification_count ? "Уведомления: есть непрочитанные" : "Уведомления"} className={accountView === "notifications" ? "selected" : ""} onClick={() => { selectionHaptic(); setAccountView("notifications"); }} type="button"><Icon name="live" />Уведомления{account?.unread_notification_count ? <small className="notification-dot" /> : null}</button></div>
      {accountView === "overview" && (account ? <AccountOverview account={account} onTickets={() => { setTicketsLoading(true); setTicketView("active"); setAccountView("tickets"); }} onHistory={() => { setTicketsLoading(true); setTicketView("history"); setAccountView("tickets"); }} onEnableTelegram={() => void enableTelegramNotifications()} onSavePreferences={(preferences) => void saveNotificationPreferences(preferences)} /> : <div className="skeleton account-skeleton" />)}
      {accountView === "tickets" && <><div className={`segmented-control ${ticketView}`}><i /><button className={ticketView === "active" ? "selected" : ""} onClick={() => { selectionHaptic(); if (ticketView !== "active") setTicketsLoading(true); setTicketView("active"); }} type="button">Активные</button><button className={ticketView === "history" ? "selected" : ""} onClick={() => { selectionHaptic(); if (ticketView !== "history") setTicketsLoading(true); setTicketView("history"); }} type="button">История</button></div><div className="ticket-filters"><select aria-label="Фильтр по лотерее" value={ticketLotteryFilter} onChange={(event) => { setTicketsLoading(true); setTicketLotteryFilter(event.target.value); }}><option value="scope:standard">Обычные лотереи</option><option value="scope:fast">Kasper Fast</option><option value="">Все игры</option>{dashboard.lotteries.map((lottery) => <option key={lottery.code} value={lottery.code}>{lottery.name}</option>)}</select>{ticketView === "history" && <button aria-pressed={ticketWinsOnly} className={ticketWinsOnly ? "active" : ""} onClick={() => { setTicketsLoading(true); setTicketWinsOnly((value) => !value); }} type="button">Только выигрыши</button>}<span>{ticketTotal} {plural(ticketTotal, "билет", "билета", "билетов")}</span></div>{ticketsLoading ? <div className="ticket-skeletons"><div className="skeleton ticket-skeleton" /><div className="skeleton ticket-skeleton" /></div> : tickets.length ? <><TicketGroups active={ticketView === "active"} lotteries={dashboard.lotteries} now={serverNow} onOpen={setSelectedTicket} tickets={tickets} />{ticketsHaveMore && <button className="load-more-tickets" disabled={ticketsLoading} onClick={() => void loadMoreTickets()} type="button">{ticketsLoading ? "Загружаем…" : `Показать ещё · ${tickets.length} из ${ticketTotal}`}</button>}</> : <EmptyState title={ticketView === "active" ? "Нет активных билетов" : "История пока пуста"} text={ticketView === "active" ? "Выберите лотерею и соберите свою комбинацию." : "Завершённые билеты появятся после розыгрыша."} action={ticketView === "active" && firstAvailable ? { label: "Выбрать лотерею", onClick: () => setView("catalog") } : undefined} />}{ticketView === "active" && firstAvailable && !ticketsLoading && tickets.length > 0 && <PrimaryButton className="sticky-action" onClick={() => void openLottery(firstAvailable.code)}>Ещё один билет</PrimaryButton>}</>}
      {accountView === "notifications" && <NotificationCenter notifications={notifications} onPlay={() => firstAvailable ? void openLottery(firstAvailable.code) : setView("home")} onTickets={() => { setTicketsLoading(true); setAccountView("tickets"); }} />}
    </section>}

    {view === "cart" && <section className="view-content" key="cart">
      <CartView cart={cart} groups={cartGroups} receipt={cartReceipt} purchasing={purchasing} success={purchaseSuccess} progress={purchaseProgress} canAdd={cart.length < CART_MAX_TICKETS} onClear={() => { setCart([]); setCartReceipt(null); }} onRemove={(id) => setCart((current) => current.filter((item) => item.id !== id))} onAdd={() => { setCartReceipt(null); setView("catalog"); }} onBuy={() => void purchaseCart()} onTickets={() => { setCartReceipt(null); setTicketsLoading(true); setTicketView("active"); setTicketLotteryFilter(""); setAccountView("tickets"); setView("account"); }} onHome={() => { setCartReceipt(null); setView("home"); }} />
    </section>}

    <BottomNavigation view={view} unreadNotifications={account?.unread_notification_count ?? 0} onChange={(target) => { if (target === "account") void refreshAccount(); setView(target); }} />
  </main>;
}
