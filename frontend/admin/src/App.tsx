import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import { ApiError, adminApi } from "./api";
import type {
  AdminSession,
  AuditEntry,
  Dashboard,
  Draw,
  DrawDetail,
  Lottery,
  NumberStatisticsReport,
  NotificationItem,
  Player,
  ReleaseNote,
  ScheduleEntry,
  TicketAnalytics,
  Transaction,
} from "./types";

type View = "dashboard" | "players" | "lotteries" | "schedule" | "draws" | "ledger" | "statistics" | "ticket-analytics" | "notifications" | "audit" | "development";

const navigation: { id: View; label: string; code: string }[] = [
  { id: "dashboard", label: "Обзор", code: "01" },
  { id: "players", label: "Игроки", code: "02" },
  { id: "lotteries", label: "Лотереи", code: "03" },
  { id: "schedule", label: "Расписание", code: "04" },
  { id: "draws", label: "Архив тиражей", code: "05" },
  { id: "ledger", label: "Журнал CAS", code: "06" },
  { id: "statistics", label: "Статистика чисел", code: "07" },
  { id: "ticket-analytics", label: "Аналитика билетов", code: "08" },
  { id: "notifications", label: "Уведомления", code: "09" },
  { id: "audit", label: "Аудит действий", code: "10" },
  { id: "development", label: "Разработка", code: "11" },
];

const viewStorageKey = "k-loto:admin-view";

function storedView(): View {
  const path = window.location.pathname.split("/").filter(Boolean).at(-1);
  const remembered = window.localStorage.getItem(viewStorageKey);
  const candidate = path || remembered || "dashboard";
  return navigation.some((item) => item.id === candidate) ? candidate as View : "dashboard";
}

const drawStatuses: Record<string, string> = { PENDING: "Ожидает", RUNNING: "Выполняется", COMPLETED: "Завершён", FAILED: "Ошибка" };
const transactionTypes: Record<string, string> = {
  ADMIN_BALANCE_ADJUSTMENT: "Изменение баланса администратором",
  TICKET_PURCHASE: "Покупка билета",
  PRIZE_PAYOUT: "Выплата выигрыша",
  JACKPOT_PAYOUT: "Выплата джекпота",
  RESERVE_ADJUSTMENT: "Изменение резерва",
  SYSTEM_ADJUSTMENT: "Системное начисление",
};
const accountKinds: Record<string, string> = {
  USER_BALANCE: "Баланс игрока", JACKPOT: "Джекпот", DISTRIBUTION: "Фонд распределения", RESERVE: "Резерв",
};
const auditActions: Record<string, string> = {
  BALANCE_ADJUSTED: "Баланс изменён", LOTTERY_CONFIGURED: "Настройки лотереи изменены",
  RESERVE_ADJUSTED: "Резерв изменён", WEB_ACCOUNT_CONFIGURED: "Web-доступ настроен",
};
const entityTypes: Record<string, string> = { USER: "Игрок", LOTTERY: "Лотерея", WEB_ACCOUNT: "Web-аккаунт" };

function translated(value: string, dictionary: Record<string, string>): string {
  return dictionary[value] ?? value.replaceAll("_", " ").toLocaleLowerCase("ru-RU");
}

function schedule(value: Record<string, unknown>): string {
  const weekday = value.weekday === "sunday" ? "воскресенье" : String(value.weekday ?? "");
  const time = String(value.draw_time ?? "");
  const slots = Array.isArray(value.slots) ? value.slots.map(String).join(" · ") : "";
  return [weekday, slots ? `${slots} МСК` : time && `${time} МСК`].filter(Boolean).join(", ") || "не задано";
}

function cas(value: number | null | undefined): string {
  return `${(value ?? 0).toLocaleString("ru-RU")} CAS`;
}

function compactCas(value: number | null | undefined): string {
  const amount = value ?? 0;
  const absolute = Math.abs(amount);
  const format = (divisor: number, suffix: string) => `${(amount / divisor).toLocaleString("ru-RU", { maximumFractionDigits: 1 })} ${suffix} CAS`;
  if (absolute >= 1_000_000_000) return format(1_000_000_000, "млрд");
  if (absolute >= 1_000_000) return format(1_000_000, "млн");
  if (absolute >= 10_000) return format(1_000, "тыс.");
  return cas(amount);
}

function date(value: string | null): string {
  return value ? new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";
}

function drawNumber(value: number): string {
  return String(value).padStart(4, "0");
}

function ScheduleView({ entries, lotteries, loadedAt }: { entries: ScheduleEntry[]; lotteries: Lottery[]; loadedAt: number }) {
  const [lotteryId, setLotteryId] = useState("");
  const focusRef = useRef<HTMLDivElement | null>(null);
  const visible = lotteryId ? entries.filter((entry) => entry.lottery_id === lotteryId) : entries;
  const now = loadedAt;
  const live = visible.find((entry) => {
    const elapsed = now - new Date(entry.scheduled_at).getTime();
    return elapsed >= 0 && elapsed <= 3 * 60_000;
  });
  const focused = live ?? visible.find((entry) => new Date(entry.scheduled_at).getTime() >= now) ?? visible.at(-1);

  useEffect(() => {
    focusRef.current?.scrollIntoView?.({ behavior: "smooth", block: "center" });
  }, [focused?.id, lotteryId]);

  const day = entries[0]?.scheduled_at
    ? new Intl.DateTimeFormat("ru-RU", { dateStyle: "long", timeZone: "Europe/Moscow" }).format(new Date(entries[0].scheduled_at))
    : new Intl.DateTimeFormat("ru-RU", { dateStyle: "long", timeZone: "Europe/Moscow" }).format(new Date(loadedAt));

  return <section className="schedule-room">
    <header className="schedule-command">
      <div><small>ОПЕРАЦИЯ // СУТОЧНЫЙ ПЛАН</small><h2>{day}</h2></div>
      <label>ЛОТЕРЕЯ<select aria-label="Лотерея расписания" value={lotteryId} onChange={(event) => setLotteryId(event.target.value)}><option value="">Все лотереи</option>{lotteries.filter((lottery) => lottery.is_active).map((lottery) => <option key={lottery.id} value={lottery.id}>{lottery.name}</option>)}</select></label>
    </header>
    <div className="schedule-head"><span>ТИРАЖ</span><span>ЛОТЕРЕЯ</span><span>ВРЕМЯ МСК</span></div>
    <div className="schedule-board">
      {visible.map((entry) => <div className={`schedule-row ${entry.id === focused?.id ? "focused" : ""}`} key={entry.id} ref={entry.id === focused?.id ? focusRef : undefined}>
        <strong>№{drawNumber(entry.public_number)}</strong>
        <b>{entry.lottery_name}</b>
        <time>{new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Europe/Moscow" }).format(new Date(entry.scheduled_at))}</time>
      </div>)}
      {!visible.length && <div className="schedule-empty">НА СЕГОДНЯ ТИРАЖЕЙ НЕТ</div>}
    </div>
  </section>;
}

function Status({ active, children }: { active: boolean; children: ReactNode }) {
  return <span className={`status ${active ? "ok" : "warn"}`}><i />{children}</span>;
}

function Login({ onAuthenticated }: { onAuthenticated: (session: AdminSession) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onAuthenticated(await adminApi.login(username, password));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось войти.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand"><span>K</span><div>CASPER CONTROL<small>PRIVATE OPERATIONS</small></div></div>
        <div className="secure-line"><i /> ЗАЩИЩЁННЫЙ КАНАЛ · ДОПУСК 007</div>
        <h1>Идентификация агента</h1>
        <p>Закрытое пространство владельца K-Loto. Доступ к оперативной сводке и управлению системой.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>ЛОГИН АДМИНИСТРАТОРА<input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} /></label>
          <label>ПАРОЛЬ<input autoComplete="current-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "ПРОВЕРЯЕМ…" : "ВОЙТИ"}</button>
        </form>
      </section>
    </main>
  );
}

function DashboardView({ data, analytics }: { data: Dashboard; analytics: TicketAnalytics }) {
  const overall = analytics.overall;
  const playerResult = overall.total_payout - overall.total_sales;
  return <>
    <div className="system-strip">
      <Status active={data.database_healthy}>БАЗА ДАННЫХ РАБОТАЕТ</Status>
      <Status active={data.scheduler_enabled}>ПЛАНИРОВЩИК {data.scheduler_enabled ? "АКТИВЕН" : "ОТКЛЮЧЁН"}</Status>
      <Status active={data.bot_configured}>БОТ {data.bot_configured ? "НАСТРОЕН" : "НЕ НАСТРОЕН"}</Status>
      <span>v{data.version} · работает {Math.floor(data.uptime_seconds / 60)} мин.</span>
    </div>
    <section className="command-hero">
      <div className="command-copy"><span>ДОСЬЕ ВЛАДЕЛЬЦА · AGENT 007</span><h2>Оперативная сводка</h2><p>Вся игровая система на одном экране. Только факты, фонды и состояние миссии.</p></div>
      <div className="command-total"><small>БИЛЕТОВ КУПЛЕНО ЗА ВСЁ ВРЕМЯ</small><strong>{overall.total_tickets.toLocaleString("ru-RU")}</strong><span>{overall.active_tickets.toLocaleString("ru-RU")} сейчас участвуют в тиражах</span></div>
      <div className="command-score"><article><small>ВЫИГРЫШНЫХ</small><strong>{percentage(overall.winning_tickets, overall.settled_tickets)}</strong><span>{overall.winning_tickets.toLocaleString("ru-RU")} из {overall.settled_tickets.toLocaleString("ru-RU")} рассчитанных</span></article><article><small>РЕЗУЛЬТАТ ИГРОКОВ</small><strong className={playerResult >= 0 ? "positive" : "negative"}>{playerResult > 0 ? "+" : ""}{compactCas(playerResult)}</strong><span>выплаты минус стоимость билетов</span></article></div>
      <div className="command-scan" />
    </section>
    <section className="metric-grid overview-metrics">
      <article className="metric"><small>ПРОВЕДЕНО ТИРАЖЕЙ</small><strong>{data.counts.completed_draws.toLocaleString("ru-RU")}</strong><em>все лотереи</em></article>
      <article className="metric"><small>ПОТРАЧЕНО НА БИЛЕТЫ</small><strong>{compactCas(overall.total_sales)}</strong><em>виртуальные CAS</em></article>
      <article className="metric"><small>ВЫПЛАЧЕНО ИГРОКАМ</small><strong>{compactCas(overall.total_payout)}</strong><em>{percentage(overall.total_payout, overall.total_sales)} от стоимости билетов</em></article>
      <article className="metric"><small>ИГРОКОВ В СИСТЕМЕ</small><strong>{data.counts.users.toLocaleString("ru-RU")}</strong><em>{overall.participants.toLocaleString("ru-RU")} покупали билеты</em></article>
    </section>
    <section className="panel jackpot-command">
      <header><h2>Джекпот-контроль</h2><span>ЕДИНАЯ ФИНАНСОВАЯ СХЕМА</span></header>
      <div className="metric-grid">
        <article className="metric"><small>ФОНД КАСПЕРА</small><strong>{compactCas(data.jackpots.kasper_fund_balance)}</strong><em>обычные выигрыши и восстановление джекпотов</em></article>
        <article className="metric"><small>ДЖЕКПОТОВ СОРВАНО</small><strong>{data.jackpots.total_wins}</strong><em>по новой финансовой схеме</em></article>
        <article className="metric"><small>ВЫПЛАЧЕНО ДЖЕКПОТАМИ</small><strong>{compactCas(data.jackpots.total_paid)}</strong></article>
        <article className="metric"><small>КРУПНЕЙШИЙ ДЖЕКПОТ</small><strong>{compactCas(data.jackpots.largest_win)}</strong></article>
      </div>
      <div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Сорвано</th><th>Выплачено</th><th>Последний раз</th></tr></thead><tbody>{data.jackpots.lotteries.map((row) => <tr key={row.code}><td><b>{row.name}</b></td><td>{row.win_count}</td><td>{cas(row.total_paid)}</td><td>{date(row.last_win_at)}</td></tr>)}</tbody></table></div>
      {data.jackpots.history.length > 0 && <div className="table-wrap"><table><thead><tr><th>Дата</th><th>Лотерея</th><th>Сумма</th><th>Билеты / игроки</th><th>Новый джекпот</th></tr></thead><tbody>{data.jackpots.history.map((row) => <tr key={row.id}><td>{date(row.occurred_at)}</td><td>{row.lottery_name}</td><td className="positive">{cas(row.jackpot_amount)}</td><td>{row.winner_ticket_count} / {row.winner_user_count}</td><td>{cas(row.base_jackpot_after)}</td></tr>)}</tbody></table></div>}
    </section>
    <section className="panel control-room"><header><h2>Оперативный пульт</h2><span>ТОЛЬКО ЧТЕНИЕ · ОБНОВЛЯЕТСЯ ПРИ ОТКРЫТИИ</span></header><div className="control-status"><article><small>ПОСЛЕДНЯЯ УСПЕШНАЯ ПРОВЕРКА</small><strong>{date(data.operations.scheduler.last_succeeded_at)}</strong><span>{data.operations.scheduler.last_error ? `ОШИБКА: ${data.operations.scheduler.last_error}` : "ПЛАНИРОВЩИК В НОРМЕ"}</span></article><article><small>ЗАВИСШИЕ ТИРАЖИ</small><strong className={data.operations.stuck_draw_count ? "negative" : "positive"}>{data.operations.stuck_draw_count}</strong><span>ОЖИДАЮТ ДОСТАВКИ: {data.operations.notifications.PENDING ?? 0} · ОШИБКИ: {data.operations.notifications.FAILED ?? 0}</span></article></div><div className="operations-table"><table><thead><tr><th>Ближайший тираж</th><th>Время / cutoff</th><th>Участники</th><th>Билеты</th><th>Продажи</th><th>Статус</th></tr></thead><tbody>{data.operations.next_draws.map((draw) => <tr key={draw.id}><td><b>{draw.lottery_name}</b> №{drawNumber(draw.draw_number)}</td><td>{date(draw.scheduled_at)}<small>{date(draw.sales_close_at)}</small></td><td>{draw.participant_count}</td><td>{draw.ticket_count}</td><td>{cas(draw.total_sales)}</td><td><span className={`tag ${draw.status.toLowerCase()}`}>{translated(draw.status, drawStatuses)}</span></td></tr>)}</tbody></table></div></section>
    <div className="split">
      <section className="panel"><header><h2>Контроль фондов</h2><span>ТЕКУЩЕЕ СОСТОЯНИЕ</span></header>
        <div className="fund-list">{data.lotteries.filter((lottery) => lottery.is_active).map((lottery) => <article key={lottery.id}><div><b>{lottery.name}</b><small>ТИРАЖ {lottery.next_draw_number ? drawNumber(lottery.next_draw_number) : "—"}</small></div><dl><dt>ДЖЕКПОТ</dt><dd>{cas(lottery.current_jackpot)}</dd><dt>РАСПРЕДЕЛЕНИЕ</dt><dd>{cas(lottery.distribution_fund)}</dd><dt>РЕЗЕРВ</dt><dd>{cas(lottery.reserve)}</dd></dl></article>)}</div>
      </section>
      <section className="panel"><header><h2>Последние тиражи</h2><span>БЕЗ ВОЗМОЖНОСТИ ИЗМЕНЕНИЯ</span></header><DrawTable draws={data.recent_draws} /></section>
    </div>
    <section className="panel"><header><h2>Последние операции</h2><span>ПРОВЕРЯЕМЫЙ ЖУРНАЛ CAS</span></header><TransactionTable rows={data.recent_transactions} /></section>
  </>;
}

function PlayerCard({ player, onSaved }: { player: Player; onSaved: () => Promise<void> }) {
  const [amount, setAmount] = useState(String(player.balance));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [autoReason, setAutoReason] = useState("");
  const [autoBusy, setAutoBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try {
      await adminApi.setBalance(player.id, Number(amount), reason);
      setReason("");
      await onSaved();
    } finally { setBusy(false); }
  };
  const toggleAutoPlay = async () => {
    setAutoBusy(true);
    try {
      await adminApi.setAutoPlay(player.id, !player.auto_play_enabled, autoReason);
      setAutoReason("");
      await onSaved();
    } finally { setAutoBusy(false); }
  };
  return <article className="player-card">
    <div className="player-head"><div className="avatar">{player.display_name.slice(0, 1)}</div><div><h3>{player.display_name}</h3><small>@{player.username ?? "без_логина"} · TG {player.telegram_id ?? "—"}</small></div><Status active={player.is_active}>{player.is_active ? "АКТИВЕН" : "ОТКЛЮЧЁН"}</Status></div>
    <div className="player-stats"><span><small>БАЛАНС</small><b>{cas(player.balance)}</b></span><span><small>БИЛЕТЫ</small><b>{player.ticket_count}</b></span><span><small>ПОТРАЧЕНО</small><b>{cas(player.spent)}</b></span><span><small>ВЫИГРАНО</small><b>{cas(player.won)}</b></span><span><small>ИТОГ</small><b className={player.net >= 0 ? "positive" : "negative"}>{cas(player.net)}</b></span></div>
    <div className="player-automation"><div><small>АВТОУЧАСТИЕ</small><b>{player.auto_play_enabled ? "5 случайных билетов на каждый тираж" : "Отключено"}</b><span>Telegram: {player.telegram_notifications_enabled ? "разрешён" : "не разрешён"} · последний успех: {date(player.auto_play_last_succeeded_at)}{player.auto_play_last_error ? ` · ошибка: ${player.auto_play_last_error}` : ""}</span></div><label>Причина автоучастия<input value={autoReason} onChange={(event) => setAutoReason(event.target.value)} placeholder="Почему меняется автоучастие?" /></label><button disabled={autoBusy || !autoReason.trim()} onClick={() => void toggleAutoPlay()}>{player.auto_play_enabled ? "ОТКЛЮЧИТЬ" : "ВКЛЮЧИТЬ 5 БИЛЕТОВ"}</button></div>
    <div className="adjust"><label>Новый баланс<input min="0" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} /></label><label>Обязательная причина<input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Почему требуется изменение?" /></label><button disabled={busy || !reason.trim()} onClick={() => void save()}>ИЗМЕНИТЬ ЧЕРЕЗ ЖУРНАЛ</button></div>
  </article>;
}

function LotteryCard({ lottery, onSaved }: { lottery: Lottery; onSaved: () => Promise<void> }) {
  const [price, setPrice] = useState(String(lottery.ticket_price ?? 0));
  const [base, setBase] = useState(String(lottery.base_jackpot));
  const [cutoff, setCutoff] = useState(String(lottery.sales_cutoff_minutes ?? 0));
  const [purchaseLimit, setPurchaseLimit] = useState(String(lottery.max_tickets_per_purchase));
  const [playerLimit, setPlayerLimit] = useState(String(lottery.max_tickets_per_user_per_draw));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const saveAll = async () => {
    setBusy(true);
    setMessage("");
    try {
      await adminApi.configureLottery(lottery.id, Number(price), Number(base), Number(cutoff), Number(purchaseLimit), Number(playerLimit), reason);
      setReason("");
      setMessage("Цена билета, джекпот и лимиты сохранены.");
      await onSaved();
    } catch (saveError) {
      setMessage(saveError instanceof Error ? saveError.message : "Не удалось сохранить настройки.");
    } finally {
      setBusy(false);
    }
  };
  return <article className="lottery-card">
    <header><div><small>{lottery.kind === "WEEKLY" ? "ЕЖЕНЕДЕЛЬНАЯ" : "ЕЖЕДНЕВНАЯ"}</small><h2>{lottery.name}</h2></div><Status active={lottery.is_active}>{lottery.is_active ? "АКТИВНА" : "НЕАКТИВНА"}</Status></header>
    <div className="fund-matrix"><span><small>ТЕКУЩИЙ ДЖЕКПОТ</small><b>{cas(lottery.current_jackpot)}</b></span><span><small>СХЕМА ПОКУПКИ</small><b>100% в джекпот</b></span><span><small>СЛЕДУЮЩИЙ ТИРАЖ</small><b>{lottery.next_draw_number ? `№${drawNumber(lottery.next_draw_number)}` : "—"}</b><em>{date(lottery.next_draw_at)}</em></span></div>
    <div className="config-grid"><label>Цена билета, CAS<input type="number" min="1" value={price} onChange={(e) => setPrice(e.target.value)} /></label><label>Базовый джекпот, CAS<input type="number" min="0" value={base} onChange={(e) => setBase(e.target.value)} /></label><label>Cutoff, минут<input type="number" min="0" max="1440" value={cutoff} onChange={(e) => setCutoff(e.target.value)} /></label><label>Лимит одной покупки<input type="number" min="1" max="1000" value={purchaseLimit} onChange={(e) => setPurchaseLimit(e.target.value)} /></label><label>Лимит игрока на тираж<input type="number" min="1" max="100000" value={playerLimit} onChange={(e) => setPlayerLimit(e.target.value)} /></label></div>
    <label className="reason">Обязательная причина для аудита<input value={reason} onChange={(e) => setReason(e.target.value)} /></label>
    <div className="actions"><button disabled={busy || !reason.trim()} onClick={() => void saveAll()}>{busy ? "СОХРАНЯЕМ…" : "СОХРАНИТЬ ВСЕ НАСТРОЙКИ"}</button></div>
    {message && <p className={message.includes("сохранены") ? "save-message" : "save-message error"}>{message}</p>}
    <footer>Расписание: <code>{schedule(lottery.schedule)}</code> · новые значения cutoff применяются при подготовке следующих тиражей. Завершённые тиражи и купленные билеты не изменяются.</footer>
  </article>;
}

function DrawTable({ draws, onOpen }: { draws: Draw[]; onOpen?: (id: string) => void }) {
  return <div className="table-wrap"><table><thead><tr><th>Лотерея / тираж</th><th>Статус</th><th>По расписанию</th><th>Числа</th><th>Билеты</th><th>Продажи / выплаты</th></tr></thead><tbody>{draws.map((draw) => <tr key={draw.id} onClick={() => onOpen?.(draw.id)} className={onOpen ? "clickable" : ""}><td><b>{draw.lottery_name}</b> №{drawNumber(draw.public_number)}</td><td><span className={`tag ${draw.status.toLowerCase()}`}>{translated(draw.status, drawStatuses)}</span></td><td>{date(draw.scheduled_at)}</td><td><div className="number-line">{draw.winning_numbers?.map((n) => <i key={n}>{n}</i>) ?? "—"}</div></td><td>{draw.ticket_count}</td><td>{cas(draw.total_sales)}<small>{cas(draw.total_payout)}</small></td></tr>)}</tbody></table></div>;
}

function TransactionTable({ rows }: { rows: Transaction[] }) {
  return <div className="table-wrap"><table><thead><tr><th>Время</th><th>Тип операции</th><th>Счёт</th><th>Изменение</th><th>До → После</th><th>Код операции</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{date(row.created_at)}</td><td><span className="tag">{translated(row.type, transactionTypes)}</span></td><td>{translated(row.account_kind, accountKinds)}</td><td className={row.amount >= 0 ? "positive" : "negative"}>{row.amount > 0 ? "+" : ""}{cas(row.amount)}</td><td>{cas(row.balance_before)} → {cas(row.balance_after)}</td><td><code>{row.operation_id.slice(0, 8)}</code></td></tr>)}</tbody></table></div>;
}

function DrawDetailPanel({ detail, onClose }: { detail: DrawDetail; onClose: () => void }) {
  const draw = detail.draw;
  return <div className="drawer"><button aria-label="Закрыть" className="close" onClick={onClose}>×</button><small>НЕИЗМЕНЯЕМАЯ ЗАПИСЬ ТИРАЖА</small><h2>{draw.lottery_name} №{drawNumber(draw.public_number)}</h2><div className="winning">{draw.winning_numbers?.map((n) => <i key={n}>{n}</i>) ?? "НЕТ РЕЗУЛЬТАТА"}</div><dl className="detail-list"><dt>Статус</dt><dd>{translated(draw.status, drawStatuses)}</dd><dt>По расписанию</dt><dd>{date(draw.scheduled_at)}</dd><dt>Проведён</dt><dd>{date(draw.executed_at)}</dd><dt>Продажи</dt><dd>{cas(draw.total_sales)}</dd><dt>Выплачено</dt><dd>{cas(draw.total_payout)}</dd><dt>Использовано из Фонда Каспера</dt><dd>{cas(draw.kasper_fund_used)}</dd><dt>Код связи</dt><dd><code>{draw.correlation_id}</code></dd></dl><h3>Билеты ({detail.tickets.length})</h3>{detail.tickets.map((ticket) => <div className="ticket-row" key={ticket.id}><b>№{drawNumber(ticket.public_number)}</b><span>{ticket.numbers.join(" · ")}</span><span>совпадений: {ticket.matches ?? "—"}</span><strong>{cas(ticket.prize_amount)}</strong></div>)}</div>;
}

function DevelopmentView({ changelog, devlog }: { changelog: ReleaseNote[]; devlog: ReleaseNote[] }) {
  const [kind, setKind] = useState<"changelog" | "devlog">("changelog");
  const notes = kind === "changelog" ? changelog : devlog;
  return <section className="release-journal">
    <div className="journal-tabs" role="tablist" aria-label="Журналы проекта">
      <button role="tab" aria-selected={kind === "changelog"} className={kind === "changelog" ? "active" : ""} onClick={() => setKind("changelog")}>CHANGELOG</button>
      <button role="tab" aria-selected={kind === "devlog"} className={kind === "devlog" ? "active" : ""} onClick={() => setKind("devlog")}>DEVLOG</button>
    </div>
    <p className="journal-intro">{kind === "changelog" ? "Официальная история релизов: только то, что изменилось для владельца и игроков." : "Технический дневник работ с собственной сквозной нумерацией."} Старые записи сохранены без изменений.</p>
    <div className="journal-list">{notes.map((note) => <article key={`${kind}-${note.version}`}>
      <header><span>{kind === "devlog" && note.sequence ? `DEV-${String(note.sequence).padStart(4, "0")} · релиз v${note.version}` : `v${note.version}`}</span><time>{note.date ?? "без даты"}</time></header>
      <pre>{note.content}</pre>
    </article>)}</div>
  </section>;
}

export default function App() {
  const [session, setSession] = useState<AdminSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [view, setView] = useState<View>(storedView);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [playerSearch, setPlayerSearch] = useState("");
  const [lotteries, setLotteries] = useState<Lottery[]>([]);
  const [draws, setDraws] = useState<Draw[]>([]);
  const [scheduleEntries, setScheduleEntries] = useState<ScheduleEntry[]>([]);
  const [scheduleLoadedAt, setScheduleLoadedAt] = useState(0);
  const [drawDetail, setDrawDetail] = useState<DrawDetail | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [statistics, setStatistics] = useState<NumberStatisticsReport | null>(null);
  const [statisticsLotteryId, setStatisticsLotteryId] = useState("");
  const [statisticsWindow, setStatisticsWindow] = useState(20);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [releaseNotes, setReleaseNotes] = useState<{ changelog: ReleaseNote[]; devlog: ReleaseNote[] }>({ changelog: [], devlog: [] });
  const [ticketAnalytics, setTicketAnalytics] = useState<TicketAnalytics | null>(null);

  const navigate = useCallback((target: View) => {
    window.localStorage.setItem(viewStorageKey, target);
    window.history.pushState({}, "", target === "dashboard" ? "/" : `/${target}`);
    setView(target);
  }, []);

  useEffect(() => { adminApi.session().then(setSession).catch(() => setSession(null)).finally(() => setChecking(false)); }, []);
  useEffect(() => {
    const restore = () => setView(storedView());
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  const load = useCallback(async (target: View) => {
    setLoading(true); setError("");
    try {
      if (target === "dashboard") {
        const [dashboardData, analyticsData] = await Promise.all([adminApi.dashboard(), adminApi.ticketAnalytics()]);
        setDashboard(dashboardData);
        setTicketAnalytics(analyticsData);
      }
      if (target === "players") setPlayers(await adminApi.players());
      if (target === "lotteries") setLotteries(await adminApi.lotteries());
      if (target === "schedule") {
        const [entries, available] = await Promise.all([adminApi.schedule(), adminApi.lotteries()]);
        setScheduleEntries(entries);
        setLotteries(available);
        setScheduleLoadedAt(Date.now());
      }
      if (target === "draws") setDraws(await adminApi.draws());
      if (target === "ledger") setTransactions(await adminApi.transactions());
      if (target === "audit") setAudit(await adminApi.audit());
      if (target === "notifications") setNotifications(await adminApi.notifications());
      if (target === "development") {
        const [changelog, devlog] = await Promise.all([adminApi.releaseNotes("changelog"), adminApi.releaseNotes("devlog")]);
        setReleaseNotes({ changelog, devlog });
      }
      if (target === "statistics") {
        const available = await adminApi.lotteries();
        setLotteries(available);
        const selectedId = statisticsLotteryId || available[0]?.id || "";
        setStatisticsLotteryId(selectedId);
        if (selectedId) setStatistics(await adminApi.statistics(selectedId, statisticsWindow));
      }
      if (target === "ticket-analytics") setTicketAnalytics(await adminApi.ticketAnalytics());
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) setSession(null);
      setError(reason instanceof Error ? reason.message : "Не удалось выполнить запрос администратора.");
    } finally { setLoading(false); }
  }, [statisticsLotteryId, statisticsWindow]);

  useEffect(() => {
    if (!session) return;
    const task = window.setTimeout(() => void load(view), 0);
    return () => window.clearTimeout(task);
  }, [session, view, load]);

  if (checking) return <main className="boot">K-LOTO // ПРОВЕРКА СЕССИИ</main>;
  if (!session) return <Login onAuthenticated={setSession} />;

  const title = navigation.find((item) => item.id === view)?.label ?? "Управление";
  return <div className="admin-shell">
    <aside><div className="brand"><span>K</span><div>CASPER CONTROL<small>PRIVATE OPERATIONS</small></div></div><nav>{navigation.map((item) => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => navigate(item.id)}><small>{item.code}</small>{item.label}</button>)}</nav><div className="operator"><small>AGENT 007 · ВЛАДЕЛЕЦ</small><b>{session.username}</b><button onClick={() => void adminApi.logout().finally(() => setSession(null))}>ЗАВЕРШИТЬ СЕАНС</button></div></aside>
    <main className="workspace"><header className="topbar"><div><small>СЕКРЕТНО // K-LOTO // {title.toUpperCase()}</small><h1>{title}</h1></div><div className="agent-clearance"><span>AGENT</span><strong>007</strong><small>МСК {new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Europe/Moscow" }).format(new Date())}</small></div></header>
      {error && <div className="error banner">{error}</div>}{loading && <div className="loading">ЗАГРУЖАЕМ ДАННЫЕ…</div>}
      {!loading && view === "dashboard" && dashboard && ticketAnalytics && <DashboardView data={dashboard} analytics={ticketAnalytics} />}
      {!loading && view === "players" && <><div className="owner-search"><input aria-label="Поиск игрока" placeholder="Имя, username, Telegram ID или UUID" value={playerSearch} onChange={(event) => setPlayerSearch(event.target.value)} /></div><section className="stack">{players.filter((player) => { const query = playerSearch.trim().toLowerCase(); return !query || `${player.display_name} ${player.username ?? ""} ${player.telegram_id ?? ""} ${player.id}`.toLowerCase().includes(query); }).map((player) => <PlayerCard key={player.id} player={player} onSaved={() => load("players")} />)}</section></>}
      {!loading && view === "lotteries" && <section className="stack">{lotteries.filter((lottery) => lottery.is_active).map((lottery) => <LotteryCard key={lottery.id} lottery={lottery} onSaved={() => load("lotteries")} />)}</section>}
      {!loading && view === "schedule" && <ScheduleView entries={scheduleEntries} lotteries={lotteries} loadedAt={scheduleLoadedAt} />}
      {!loading && view === "draws" && <section className="panel"><header><h2>Постоянный архив тиражей</h2><span>ТОЛЬКО ПРОСМОТР</span></header><DrawTable draws={draws} onOpen={(id) => void adminApi.draw(id).then(setDrawDetail)} /></section>}
      {!loading && view === "ledger" && <><TransactionFilters onApply={(query) => void adminApi.transactions(query).then(setTransactions).catch((reason: Error) => setError(reason.message))} /><section className="panel"><header><h2>Неизменяемый журнал CAS</h2><span>ЗАПИСЕЙ: {transactions.length}</span></header><TransactionTable rows={transactions} /></section></>}
      {!loading && view === "statistics" && statistics && <StatisticsView lotteries={lotteries} report={statistics} selectedLotteryId={statisticsLotteryId} windowSize={statisticsWindow} onLottery={setStatisticsLotteryId} onWindow={setStatisticsWindow} />}
      {!loading && view === "ticket-analytics" && ticketAnalytics && <TicketAnalyticsView data={ticketAnalytics} />}
      {!loading && view === "notifications" && <section className="panel"><header><h2>Очередь уведомлений</h2><span>ДОСТАВЛЕНО · ОШИБКА · ОЖИДАЕТ</span></header><div className="table-wrap"><table><thead><tr><th>Создано</th><th>Тип</th><th>Игрок</th><th>Статус</th><th>Попытки</th><th>Ошибка</th></tr></thead><tbody>{notifications.map((item) => <tr key={item.id}><td>{date(item.created_at)}</td><td>{translated(item.type, transactionTypes)}</td><td><code>{item.user_id.slice(0, 8)}</code></td><td><span className={`tag ${item.status.toLowerCase()}`}>{translated(item.status, { PENDING: "ожидает", PROCESSING: "отправляется", SENT: "доставлено", FAILED: "ошибка", CANCELLED: "отменено" })}</span></td><td>{item.attempts}</td><td>{item.last_error ?? "—"}</td></tr>)}</tbody></table></div></section>}
      {!loading && view === "audit" && <section className="panel"><header><h2>Аудит действий администратора</h2><span>ХРАНИТСЯ ПОСТОЯННО</span></header><div className="audit-list">{audit.map((item) => <article key={item.id}><time>{date(item.created_at)}</time><b>{translated(item.action, auditActions)} · {translated(item.entity_type, entityTypes)}</b><p>{item.reason ?? "Причина не указана"}</p><code>{JSON.stringify(item.old_values)} → {JSON.stringify(item.new_values)}</code></article>)}</div></section>}
      {!loading && view === "development" && <DevelopmentView changelog={releaseNotes.changelog} devlog={releaseNotes.devlog} />}
    </main>{drawDetail && <DrawDetailPanel detail={drawDetail} onClose={() => setDrawDetail(null)} />}
  </div>;
}

function percentage(part: number, total: number): string {
  return total ? `${((part / total) * 100).toLocaleString("ru-RU", { maximumFractionDigits: 2 })}%` : "0%";
}

function TicketAnalyticsView({ data }: { data: TicketAnalytics }) {
  const overall = data.overall;
  const difficulty = (wins: number, settled: number) => {
    const rate = settled ? (wins / settled) * 100 : 0;
    if (rate >= 25) return "выигрывают часто";
    if (rate >= 10) return "умеренная сложность";
    if (rate >= 2) return "выигрыш редкий";
    return "особенно сложная";
  };
  return <>
    <section className="metric-grid analytics-metrics">
      <article className="metric"><small>ВСЕГО БИЛЕТОВ</small><strong>{overall.total_tickets.toLocaleString("ru-RU")}</strong></article>
      <article className="metric"><small>РАССЧИТАНО</small><strong>{overall.settled_tickets.toLocaleString("ru-RU")}</strong></article>
      <article className="metric"><small>ВЫИГРЫШНЫЕ БИЛЕТЫ</small><strong>{overall.winning_tickets.toLocaleString("ru-RU")}</strong><em>{percentage(overall.winning_tickets, overall.settled_tickets)} от рассчитанных</em></article>
      <article className="metric"><small>ВЫПЛАЧЕНО</small><strong>{cas(overall.total_payout)}</strong><em>{percentage(overall.total_payout, overall.total_sales)} от продаж</em></article>
    </section>
    <section className="panel analytics-panel"><header><h2>Результаты по каждой лотерее</h2><span>СРАВНЕНИЕ СЛОЖНОСТИ · КЭШ 60 СЕКУНД</span></header><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Билеты</th><th>Рассчитано</th><th>Выигрышные</th><th>Фактический шанс</th><th>Оценка по истории</th><th>Потрачено</th><th>Выплачено</th></tr></thead><tbody>{data.lotteries.map((row) => <tr key={row.lottery_id}><td><b>{row.lottery_name}</b><small>{row.is_active ? "активна" : "архивная"}</small></td><td>{row.total_tickets.toLocaleString("ru-RU")}<small>{row.active_tickets.toLocaleString("ru-RU")} активных</small></td><td>{row.settled_tickets.toLocaleString("ru-RU")}</td><td className={row.winning_tickets ? "positive" : ""}>{row.winning_tickets.toLocaleString("ru-RU")}</td><td><b>{percentage(row.winning_tickets, row.settled_tickets)}</b></td><td><span className="difficulty">{difficulty(row.winning_tickets, row.settled_tickets)}</span></td><td>{compactCas(row.total_sales)}</td><td>{compactCas(row.total_payout)}<small>{percentage(row.total_payout, row.total_sales)} возврата</small></td></tr>)}</tbody></table></div><p className="source-note">«Фактический шанс» показывает долю выигрышных билетов в уже завершённых тиражах, а не обещание будущего выигрыша. Так видно, где по реальной истории выигрывали чаще и сколько CAS возвращалось игрокам.</p></section>
  </>;
}

function TransactionFilters({ onApply }: { onApply: (query: string) => void }) {
  const [values, setValues] = useState({ type: "", user_id: "", lottery_id: "", draw_id: "", ticket_id: "", date_from: "", date_to: "" });
  const apply = (event: FormEvent) => { event.preventDefault(); const params = new URLSearchParams(); Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, key.startsWith("date_") ? new Date(value).toISOString() : value); }); onApply(params.toString()); };
  const fields: Record<string, string> = { user_id: "ID игрока", lottery_id: "ID лотереи", draw_id: "ID тиража", ticket_id: "ID билета" };
  return <form className="filters" onSubmit={apply}><select aria-label="Тип операции" value={values.type} onChange={(e) => setValues({ ...values, type: e.target.value })}><option value="">Все типы операций</option>{Object.keys(transactionTypes).map((type) => <option key={type} value={type}>{transactionTypes[type]}</option>)}</select>{Object.entries(fields).map(([key, label]) => <input key={key} placeholder={label} value={values[key as keyof typeof values]} onChange={(e) => setValues({ ...values, [key]: e.target.value })} />)}<input aria-label="Начальная дата" type="datetime-local" value={values.date_from} onChange={(e) => setValues({ ...values, date_from: e.target.value })} /><input aria-label="Конечная дата" type="datetime-local" value={values.date_to} onChange={(e) => setValues({ ...values, date_to: e.target.value })} /><button>ПРИМЕНИТЬ ФИЛЬТРЫ</button></form>;
}

function StatisticsView({ lotteries, report, selectedLotteryId, windowSize, onLottery, onWindow }: { lotteries: Lottery[]; report: NumberStatisticsReport; selectedLotteryId: string; windowSize: number; onLottery: (id: string) => void; onWindow: (size: number) => void }) {
  const ranked = [...report.numbers].sort((left, right) => right.appearances - left.appearances || left.number - right.number);
  const hottest = ranked[0];
  const coldest = ranked.at(-1);
  const windowLabel = windowSize === 0 ? "все доступные" : `последние ${windowSize}`;
  return <>
    <section className="statistics-brief">
      <div><span>АНАЛИТИЧЕСКОЕ ДОСЬЕ</span><h2>{report.lottery_name}</h2><p>Статистика начата заново с 1 сентября 2026 года. История тиражей и их номера не изменялись.</p></div>
      <article><small>УЧТЕНО ТИРАЖЕЙ</small><strong>{report.draw_count}</strong><span>{windowLabel}</span></article>
      <article><small>ЧАЩЕ ВСЕГО</small><strong>{hottest?.appearances ? hottest.number : "—"}</strong><span>{hottest?.appearances ? `${hottest.appearances} выпадений` : "данные накапливаются"}</span></article>
      <article><small>РЕЖЕ ВСЕГО</small><strong>{coldest?.appearances || report.draw_count ? coldest?.number ?? "—" : "—"}</strong><span>{coldest ? `${coldest.appearances} выпадений` : "данные накапливаются"}</span></article>
    </section>
    <section className="panel statistics-panel"><header><div><h2>Выпавшие числа</h2><span>{report.draw_count ? `${date(report.first_draw_at)} — ${date(report.last_draw_at)}` : "ПОКА НЕТ ЗАВЕРШЁННЫХ ТИРАЖЕЙ В ПЕРИОДЕ"}</span></div><div className="statistics-controls"><select aria-label="Лотерея" value={selectedLotteryId} onChange={(e) => onLottery(e.target.value)}>{lotteries.map((lottery) => <option value={lottery.id} key={lottery.id}>{lottery.name}</option>)}</select><select aria-label="Количество тиражей" value={windowSize} onChange={(e) => onWindow(Number(e.target.value))}><option value={0}>Все</option><option value={10}>10 тиражей</option><option value={20}>20 тиражей</option><option value={50}>50 тиражей</option><option value={100}>100 тиражей</option></select></div></header><div className="stat-grid">{report.numbers.map((row) => <article key={row.number}><i>{row.number}</i><strong>{row.appearances}</strong><small>выпадений</small><div style={{ "--value": `${row.draw_percentage}%` } as CSSProperties}><span /></div><em>{row.draw_percentage}% тиражей</em><b>{row.draws_since_last === null ? "ещё не выпадало" : row.draws_since_last === 0 ? "в последнем тираже" : `${row.draws_since_last} тир. назад`}</b></article>)}</div><p className="source-note">Частота чисел нужна для наблюдения за историей, но не повышает вероятность следующего результата: каждый тираж использует независимый криптографически стойкий выбор.</p></section>
  </>;
}
