import { FormEvent, useCallback, useEffect, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import { ApiError, adminApi } from "./api";
import type {
  AdminSession,
  AuditEntry,
  Dashboard,
  Draw,
  DrawDetail,
  Lottery,
  NumberStatistic,
  NotificationItem,
  Player,
  ReleaseNote,
  Transaction,
} from "./types";

type View = "dashboard" | "players" | "lotteries" | "draws" | "ledger" | "statistics" | "notifications" | "audit" | "development";

const navigation: { id: View; label: string; code: string }[] = [
  { id: "dashboard", label: "Обзор", code: "01" },
  { id: "players", label: "Игроки", code: "02" },
  { id: "lotteries", label: "Лотереи", code: "03" },
  { id: "draws", label: "Архив тиражей", code: "04" },
  { id: "ledger", label: "Журнал CAS", code: "05" },
  { id: "statistics", label: "Статистика чисел", code: "06" },
  { id: "notifications", label: "Уведомления", code: "07" },
  { id: "audit", label: "Аудит действий", code: "08" },
  { id: "development", label: "Разработка", code: "09" },
];

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

function date(value: string | null): string {
  return value ? new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—";
}

function drawNumber(value: number): string {
  return String(value).padStart(4, "0");
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
        <div className="brand"><span>K</span><div>K-LOTO<small>СИСТЕМА УПРАВЛЕНИЯ</small></div></div>
        <div className="secure-line"><i /> ЗАЩИЩЁННАЯ ЗОНА АДМИНИСТРАТОРА</div>
        <h1>Вход в систему</h1>
        <p>Войдите, чтобы просматривать историю и выполнять контролируемые изменения.</p>
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

function DashboardView({ data }: { data: Dashboard }) {
  const metrics = [
    ["Игроки", data.counts.users],
    ["Билеты", data.counts.tickets],
    ["Завершённые тиражи", data.counts.completed_draws],
    ["Ожидают / восстановление", data.counts.pending_draws],
  ];
  return <>
    <div className="system-strip">
      <Status active={data.database_healthy}>БАЗА ДАННЫХ РАБОТАЕТ</Status>
      <Status active={data.scheduler_enabled}>ПЛАНИРОВЩИК {data.scheduler_enabled ? "АКТИВЕН" : "ОТКЛЮЧЁН"}</Status>
      <Status active={data.bot_configured}>БОТ {data.bot_configured ? "НАСТРОЕН" : "НЕ НАСТРОЕН"}</Status>
      <span>v{data.version} · работает {Math.floor(data.uptime_seconds / 60)} мин.</span>
    </div>
    <section className="metric-grid">{metrics.map(([label, value]) => <article className="metric" key={label}><small>{label}</small><strong>{value}</strong><div className="scan" /></article>)}</section>
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
  const [reserve, setReserve] = useState(String(lottery.reserve));
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
      await adminApi.setReserve(lottery.id, Number(reserve), reason);
      setReason("");
      setMessage("Цена билета, джекпот и резерв сохранены.");
      await onSaved();
    } catch (saveError) {
      setMessage(saveError instanceof Error ? saveError.message : "Не удалось сохранить настройки.");
    } finally {
      setBusy(false);
    }
  };
  return <article className="lottery-card">
    <header><div><small>{lottery.kind === "WEEKLY" ? "ЕЖЕНЕДЕЛЬНАЯ" : "ЕЖЕДНЕВНАЯ"}</small><h2>{lottery.name}</h2></div><Status active={lottery.is_active}>{lottery.is_active ? "АКТИВНА" : "НЕАКТИВНА"}</Status></header>
    <div className="fund-matrix"><span><small>ТЕКУЩИЙ ДЖЕКПОТ</small><b>{cas(lottery.current_jackpot)}</b></span><span><small>ФОНД РАСПРЕДЕЛЕНИЯ</small><b>{cas(lottery.distribution_fund)}</b></span><span><small>СЛЕДУЮЩИЙ ТИРАЖ</small><b>{lottery.next_draw_number ? `№${drawNumber(lottery.next_draw_number)}` : "—"}</b><em>{date(lottery.next_draw_at)}</em></span></div>
    <div className="config-grid"><label>Цена билета, CAS<input type="number" min="1" value={price} onChange={(e) => setPrice(e.target.value)} /></label><label>Базовый джекпот, CAS<input type="number" min="0" value={base} onChange={(e) => setBase(e.target.value)} /></label><label>Резерв, CAS<input type="number" min="0" value={reserve} onChange={(e) => setReserve(e.target.value)} /></label><label>Cutoff, минут<input type="number" min="0" max="1440" value={cutoff} onChange={(e) => setCutoff(e.target.value)} /></label><label>Лимит одной покупки<input type="number" min="1" max="1000" value={purchaseLimit} onChange={(e) => setPurchaseLimit(e.target.value)} /></label><label>Лимит игрока на тираж<input type="number" min="1" max="100000" value={playerLimit} onChange={(e) => setPlayerLimit(e.target.value)} /></label></div>
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
  return <div className="drawer"><button aria-label="Закрыть" className="close" onClick={onClose}>×</button><small>НЕИЗМЕНЯЕМАЯ ЗАПИСЬ ТИРАЖА</small><h2>{draw.lottery_name} №{drawNumber(draw.public_number)}</h2><div className="winning">{draw.winning_numbers?.map((n) => <i key={n}>{n}</i>) ?? "НЕТ РЕЗУЛЬТАТА"}</div><dl className="detail-list"><dt>Статус</dt><dd>{translated(draw.status, drawStatuses)}</dd><dt>По расписанию</dt><dd>{date(draw.scheduled_at)}</dd><dt>Проведён</dt><dd>{date(draw.executed_at)}</dd><dt>Продажи</dt><dd>{cas(draw.total_sales)}</dd><dt>Выплачено</dt><dd>{cas(draw.total_payout)}</dd><dt>Использовано из резерва</dt><dd>{cas(draw.reserve_used)}</dd><dt>Код связи</dt><dd><code>{draw.correlation_id}</code></dd></dl><h3>Билеты ({detail.tickets.length})</h3>{detail.tickets.map((ticket) => <div className="ticket-row" key={ticket.id}><b>№{drawNumber(ticket.public_number)}</b><span>{ticket.numbers.join(" · ")}</span><span>совпадений: {ticket.matches ?? "—"}</span><strong>{cas(ticket.prize_amount)}</strong></div>)}</div>;
}

function DevelopmentView({ changelog, devlog }: { changelog: ReleaseNote[]; devlog: ReleaseNote[] }) {
  const [kind, setKind] = useState<"changelog" | "devlog">("changelog");
  const notes = kind === "changelog" ? changelog : devlog;
  return <section className="release-journal">
    <div className="journal-tabs" role="tablist" aria-label="Журналы проекта">
      <button role="tab" aria-selected={kind === "changelog"} className={kind === "changelog" ? "active" : ""} onClick={() => setKind("changelog")}>CHANGELOG</button>
      <button role="tab" aria-selected={kind === "devlog"} className={kind === "devlog" ? "active" : ""} onClick={() => setKind("devlog")}>DEVLOG</button>
    </div>
    <p className="journal-intro">{kind === "changelog" ? "Официальная история изменений продукта." : "Подробная техническая история разработки."} Старые и новые записи доступны только после входа администратора.</p>
    <div className="journal-list">{notes.map((note) => <article key={`${kind}-${note.version}`}>
      <header><span>v{note.version}</span><time>{note.date ?? "без даты"}</time></header>
      <pre>{note.content}</pre>
    </article>)}</div>
  </section>;
}

export default function App() {
  const [session, setSession] = useState<AdminSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [view, setView] = useState<View>("dashboard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [playerSearch, setPlayerSearch] = useState("");
  const [lotteries, setLotteries] = useState<Lottery[]>([]);
  const [draws, setDraws] = useState<Draw[]>([]);
  const [drawDetail, setDrawDetail] = useState<DrawDetail | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [statistics, setStatistics] = useState<NumberStatistic[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [releaseNotes, setReleaseNotes] = useState<{ changelog: ReleaseNote[]; devlog: ReleaseNote[] }>({ changelog: [], devlog: [] });

  useEffect(() => { adminApi.session().then(setSession).catch(() => setSession(null)).finally(() => setChecking(false)); }, []);

  const load = useCallback(async (target: View) => {
    setLoading(true); setError("");
    try {
      if (target === "dashboard") setDashboard(await adminApi.dashboard());
      if (target === "players") setPlayers(await adminApi.players());
      if (target === "lotteries") setLotteries(await adminApi.lotteries());
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
        if (available[0]) setStatistics(await adminApi.statistics(available[0].id));
      }
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) setSession(null);
      setError(reason instanceof Error ? reason.message : "Не удалось выполнить запрос администратора.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!session) return;
    const task = window.setTimeout(() => void load(view), 0);
    return () => window.clearTimeout(task);
  }, [session, view, load]);

  if (checking) return <main className="boot">K-LOTO // ПРОВЕРКА СЕССИИ</main>;
  if (!session) return <Login onAuthenticated={setSession} />;

  const title = navigation.find((item) => item.id === view)?.label ?? "Управление";
  return <div className="admin-shell">
    <aside><div className="brand"><span>K</span><div>K-LOTO<small>СИСТЕМА УПРАВЛЕНИЯ</small></div></div><nav>{navigation.map((item) => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => setView(item.id)}><small>{item.code}</small>{item.label}</button>)}</nav><div className="operator"><small>АДМИНИСТРАТОР</small><b>{session.username}</b><button onClick={() => void adminApi.logout().finally(() => setSession(null))}>ЗАВЕРШИТЬ СЕАНС</button></div></aside>
    <main className="workspace"><header className="topbar"><div><small>K-LOTO / АДМИНИСТРАТОР / {title.toUpperCase()}</small><h1>{title}</h1></div><span className="utc">МСК {new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Europe/Moscow" }).format(new Date())}</span></header>
      {error && <div className="error banner">{error}</div>}{loading && <div className="loading">ЗАГРУЖАЕМ ДАННЫЕ…</div>}
      {!loading && view === "dashboard" && dashboard && <DashboardView data={dashboard} />}
      {!loading && view === "players" && <><div className="owner-search"><input aria-label="Поиск игрока" placeholder="Имя, username, Telegram ID или UUID" value={playerSearch} onChange={(event) => setPlayerSearch(event.target.value)} /></div><section className="stack">{players.filter((player) => { const query = playerSearch.trim().toLowerCase(); return !query || `${player.display_name} ${player.username ?? ""} ${player.telegram_id ?? ""} ${player.id}`.toLowerCase().includes(query); }).map((player) => <PlayerCard key={player.id} player={player} onSaved={() => load("players")} />)}</section></>}
      {!loading && view === "lotteries" && <section className="stack">{lotteries.filter((lottery) => lottery.is_active).map((lottery) => <LotteryCard key={lottery.id} lottery={lottery} onSaved={() => load("lotteries")} />)}</section>}
      {!loading && view === "draws" && <section className="panel"><header><h2>Постоянный архив тиражей</h2><span>ТОЛЬКО ПРОСМОТР</span></header><DrawTable draws={draws} onOpen={(id) => void adminApi.draw(id).then(setDrawDetail)} /></section>}
      {!loading && view === "ledger" && <><TransactionFilters onApply={(query) => void adminApi.transactions(query).then(setTransactions).catch((reason: Error) => setError(reason.message))} /><section className="panel"><header><h2>Неизменяемый журнал CAS</h2><span>ЗАПИСЕЙ: {transactions.length}</span></header><TransactionTable rows={transactions} /></section></>}
      {!loading && view === "statistics" && <StatisticsView lotteries={lotteries} rows={statistics} onLottery={(id) => void adminApi.statistics(id).then(setStatistics)} />}
      {!loading && view === "notifications" && <section className="panel"><header><h2>Очередь уведомлений</h2><span>ДОСТАВЛЕНО · ОШИБКА · ОЖИДАЕТ</span></header><div className="table-wrap"><table><thead><tr><th>Создано</th><th>Тип</th><th>Игрок</th><th>Статус</th><th>Попытки</th><th>Ошибка</th></tr></thead><tbody>{notifications.map((item) => <tr key={item.id}><td>{date(item.created_at)}</td><td>{translated(item.type, transactionTypes)}</td><td><code>{item.user_id.slice(0, 8)}</code></td><td><span className={`tag ${item.status.toLowerCase()}`}>{translated(item.status, { PENDING: "ожидает", PROCESSING: "отправляется", SENT: "доставлено", FAILED: "ошибка" })}</span></td><td>{item.attempts}</td><td>{item.last_error ?? "—"}</td></tr>)}</tbody></table></div></section>}
      {!loading && view === "audit" && <section className="panel"><header><h2>Аудит действий администратора</h2><span>ХРАНИТСЯ ПОСТОЯННО</span></header><div className="audit-list">{audit.map((item) => <article key={item.id}><time>{date(item.created_at)}</time><b>{translated(item.action, auditActions)} · {translated(item.entity_type, entityTypes)}</b><p>{item.reason ?? "Причина не указана"}</p><code>{JSON.stringify(item.old_values)} → {JSON.stringify(item.new_values)}</code></article>)}</div></section>}
      {!loading && view === "development" && <DevelopmentView changelog={releaseNotes.changelog} devlog={releaseNotes.devlog} />}
    </main>{drawDetail && <DrawDetailPanel detail={drawDetail} onClose={() => setDrawDetail(null)} />}
  </div>;
}

function TransactionFilters({ onApply }: { onApply: (query: string) => void }) {
  const [values, setValues] = useState({ type: "", user_id: "", lottery_id: "", draw_id: "", ticket_id: "", date_from: "", date_to: "" });
  const apply = (event: FormEvent) => { event.preventDefault(); const params = new URLSearchParams(); Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, key.startsWith("date_") ? new Date(value).toISOString() : value); }); onApply(params.toString()); };
  const fields: Record<string, string> = { user_id: "ID игрока", lottery_id: "ID лотереи", draw_id: "ID тиража", ticket_id: "ID билета" };
  return <form className="filters" onSubmit={apply}><select aria-label="Тип операции" value={values.type} onChange={(e) => setValues({ ...values, type: e.target.value })}><option value="">Все типы операций</option>{Object.keys(transactionTypes).map((type) => <option key={type} value={type}>{transactionTypes[type]}</option>)}</select>{Object.entries(fields).map(([key, label]) => <input key={key} placeholder={label} value={values[key as keyof typeof values]} onChange={(e) => setValues({ ...values, [key]: e.target.value })} />)}<input aria-label="Начальная дата" type="datetime-local" value={values.date_from} onChange={(e) => setValues({ ...values, date_from: e.target.value })} /><input aria-label="Конечная дата" type="datetime-local" value={values.date_to} onChange={(e) => setValues({ ...values, date_to: e.target.value })} /><button>ПРИМЕНИТЬ ФИЛЬТРЫ</button></form>;
}

function StatisticsView({ lotteries, rows, onLottery }: { lotteries: Lottery[]; rows: NumberStatistic[]; onLottery: (id: string) => void }) {
  return <section className="panel"><header><h2>Частота выпадения чисел</h2><select aria-label="Лотерея" onChange={(e) => onLottery(e.target.value)}>{lotteries.map((lottery) => <option value={lottery.id} key={lottery.id}>{lottery.name}</option>)}</select></header><div className="stat-grid">{rows.map((row) => <article key={row.number}><i>{row.number}</i><strong>{row.appearances}</strong><small>выпадений</small><div style={{ "--value": `${row.draw_percentage}%` } as CSSProperties}><span /></div><em>{row.draw_percentage}% · тиражей с последнего: {row.draws_since_last ?? "ещё не выпадало"}</em></article>)}</div><p className="source-note">Рассчитано по неизменяемой истории завершённых тиражей. Этот экран является аналитическим представлением, а не первичным источником данных.</p></section>;
}
