import type { LotteryScope } from "./api";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import { ApiError, adminApi, setEconomyScope } from "./api";
import { EconomyPanel } from "./EconomyPanel";
import { OperationalMonitor } from "./OperationalMonitor";
import { DistributionDraws } from "./DistributionDraws";
import logoHorizontal from "../../shared/assets/brand/logo-horizontal.png";
import "./owner-catalog.css";
import "./owner-workspace.css";
import type {
  ActivityPoint,
  AdminSession,
  AuditEntry,
  Dashboard,
  Overview,
  Draw,
  DrawDetail,
  JackpotEvent,
  KasperLiveSummary,
  Lottery,
  NumberStatisticsReport,
  NotificationItem,
  Player,
  PlayerHistoryPage,
  ReleaseNote,
  ScheduleEntry,
  TicketAnalytics,
  Transaction,
} from "./types";

type View = "economy" | "tickets" | "distribution" | "dashboard" | "fast" | "instant" | "lotteries" | "schedule" | "draws" | "jackpots" | "archive" | "players" | "analytics" | "system" | "publications";
type InstantGame = "kasper-live" | "aurora" | "vault";
type AnalyticsTab = "lotteries" | "tickets" | "numbers" | "finances";
type SystemTab = "events" | "health" | "ledger" | "notifications" | "audit" | "development" | "formats";

const navigation: { id: View; label: string; group: "main" | "manage" | "system" }[] = [
  { id: "dashboard", label: "Обзор", group: "main" },
  { id: "economy", label: "Экономика", group: "main" },
  { id: "tickets", label: "Билеты и выигрыши", group: "main" },
  { id: "jackpots", label: "Джекпоты", group: "main" },
  { id: "analytics", label: "Статистика", group: "main" },
  { id: "players", label: "Игроки", group: "manage" },
  { id: "lotteries", label: "Настройки лотерей", group: "manage" },
  { id: "fast", label: "Fast", group: "manage" },
  { id: "instant", label: "Моментальные", group: "manage" },
  { id: "draws", label: "Тиражи", group: "manage" },
  { id: "schedule", label: "Расписание", group: "manage" },
  { id: "distribution", label: "Распределительные", group: "manage" },
  { id: "system", label: "Система", group: "system" },
];

const viewStorageKey = "k-loto:admin-view";
const instantSymbolGlyphs = ["★", "◆", "●", "✦", "☾", "⚡", "♣", "7"];

function storedView(): View {
  const path = window.location.pathname.split("/").filter(Boolean).at(-1);
  const remembered = window.localStorage.getItem(viewStorageKey);
  const legacy: Record<string, View> = {
    archive: "system", ledger: "system", notifications: "system", audit: "system", development: "system",
    statistics: "analytics", "ticket-analytics": "analytics",
    vault: "instant", aurora: "instant", "kasper-live": "instant",
    facts: "publications", broadcast: "dashboard",
  };
  const raw = path || remembered || "dashboard";
  const candidate = legacy[raw] ?? raw;
  return navigation.some((item) => item.id === candidate) ? candidate as View : "dashboard";
}

function storedInstantGame(): InstantGame {
  const raw = new URLSearchParams(window.location.search).get("game")
    ?? window.location.pathname.split("/").filter(Boolean).at(-1)
    ?? window.localStorage.getItem(viewStorageKey);
  return raw === "vault" || raw === "aurora" ? raw : "kasper-live";
}

const drawStatuses: Record<string, string> = { SCHEDULED: "Запланирован", CLOSED: "Продажи закрыты", DRAWING: "Розыгрыш", SETTLING: "Начисление выигрышей", PENDING: "Ожидает", RUNNING: "Выполняется", COMPLETED: "Завершён", CANCELLED: "Отменён на паузе", FAILED: "Ошибка" };
const transactionTypes: Record<string, string> = {
  ADMIN_BALANCE_ADJUSTMENT: "Изменение баланса администратором",
  TICKET_PURCHASE: "Покупка билета",
  TICKET_REFUND: "Возврат билета",
  PRIZE_PAYOUT: "Выплата выигрыша",
  JACKPOT_PAYOUT: "Выплата джекпота",
  RESERVE_ADJUSTMENT: "Изменение резерва",
  SYSTEM_ADJUSTMENT: "Системное начисление",
};
const notificationTypes: Record<string, string> = {
  JACKPOT_WIN: "Джекпот игрока",
  INACTIVITY_REMINDER: "Напоминание",
  DELIVERY_TEST: "Проверка доставки",
  SYSTEM_ALERT: "Системное предупреждение",
  DRAW_RESULT: "Старый результат",
  TICKET_PURCHASED: "Старая покупка",
};

function displayNumber(lotteryCode: string, number: number): string {
  if (lotteryCode === "weekly" && number > 35) return `★${number - 35}`;
  if (lotteryCode === "pulse" && number > 1_000) return `ШИФР ${String(number - 1_000).padStart(3, "0")}`;
  if (lotteryCode === "pulse" && number > 12) return `P${number - 12}`;
  return String(number);
}

function displayMatches(lotteryCode: string, matches: number | null, grandFormat: boolean, ruleset?: string | null): string {
  if (matches === null) return "—";
  if (lotteryCode === "pulse" && (matches >= 100 || ruleset?.includes("cipher"))) return `${Math.floor(matches / 100)}+${Math.floor(matches / 10) % 10} · шифр ${matches % 10 ? "да" : "нет"}`;
  return (lotteryCode === "weekly" && grandFormat) || lotteryCode === "pulse" ? `${Math.floor(matches / 10)}+${matches % 10}` : String(matches);
}

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

function notificationDetail(item: NotificationItem): string {
  if (item.type !== "SYSTEM_ALERT") return item.last_error ?? "—";
  const kind = String(item.payload.kind ?? "");
  const labels: Record<string, string> = {
    stuck_draws: "Обнаружены зависшие тиражи",
    stuck_notifications: "Обнаружены зависшие уведомления",
    scheduler_error: "Ошибка планировщика",
  };
  const count = typeof item.payload.count === "number" ? ` · количество: ${item.payload.count}` : "";
  const code = item.payload.error_code ? ` · код: ${String(item.payload.error_code)}` : "";
  return `${labels[kind] ?? "Системная проверка"}${count}${code}`;
}

function schedule(value: Record<string, unknown>): string {
  if (typeof value.interval_minutes === "number") return `Каждые ${value.interval_minutes} минут · МСК`;
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
  return value ? new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short", timeZone: "Europe/Moscow" }).format(new Date(value)) : "—";
}

function drawNumber(value: number): string {
  return String(value).padStart(4, "0");
}

function BingoResultSummary({ numbers, detailed = false }: { numbers: number[] | null; detailed?: boolean }) {
  if (!numbers?.length) return <>—</>;
  const missed = Array.from({ length: 60 }, (_, index) => index + 1).filter((number) => !numbers.includes(number));
  return <div className={`bingo-result-summary ${detailed ? "detailed" : ""}`}><b>{numbers.length} ходов</b><small>Не выпали: {missed.join(" · ") || "—"}</small>{detailed && <details><summary>Полный протокол шаров</summary><div className="winning bingo-protocol">{numbers.map((number, index) => <i key={`${number}-${index}`}>{number}</i>)}</div></details>}</div>;
}

function DrawResult({ draw, detailed = false }: { draw: Draw; detailed?: boolean }) {
  if (draw.lottery_code === "bingo") return <BingoResultSummary numbers={draw.winning_numbers} detailed={detailed} />;
  if (!draw.winning_numbers?.length) return <>—</>;
  return <div className={detailed ? "winning" : "number-line"}>{draw.winning_numbers.map((number, index) => <i className={draw.lottery_code === "weekly" && number > 35 ? "special" : ""} key={`${number}-${index}`}>{displayNumber(draw.lottery_code, number)}</i>)}</div>;
}

function ScheduleView({ entries, lotteries, loadedAt }: { entries: ScheduleEntry[]; lotteries: Lottery[]; loadedAt: number }) {
  const [lotteryId, setLotteryId] = useState("");
  const [category, setCategory] = useState<"all" | "daily" | "fast" | "weekly">("all");
  const focusRef = useRef<HTMLDivElement | null>(null);
  const lotteryById = new Map(lotteries.map((lottery) => [lottery.id, lottery]));
  const fastCodes = new Set(["flash", "shadow", "pulse"]);
  const visible = entries.filter((entry) => {
    if (lotteryId && entry.lottery_id !== lotteryId) return false;
    const lottery = lotteryById.get(entry.lottery_id);
    if (category === "fast") return fastCodes.has(lottery?.code ?? "");
    if (category === "weekly") return lottery?.kind === "WEEKLY";
    if (category === "daily") return lottery?.kind === "DAILY" && !fastCodes.has(lottery.code);
    return true;
  });
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
      <div><small>Расписание на день</small><h2>{day}</h2></div>
      <label>ЛОТЕРЕЯ<select aria-label="Лотерея расписания" value={lotteryId} onChange={(event) => setLotteryId(event.target.value)}><option value="">Все лотереи</option>{lotteries.filter((lottery) => lottery.is_active).map((lottery) => <option key={lottery.id} value={lottery.id}>{lottery.name}</option>)}</select></label>
    </header>
    <SectionTabs value={category} label="Тип расписания" items={[{ id: "all", label: "Все" }, { id: "daily", label: "Daily" }, { id: "fast", label: "Fast" }, { id: "weekly", label: "Weekly / Special" }]} onChange={setCategory} />
    <div className="schedule-head"><span>ТИРАЖ</span><span>ЛОТЕРЕЯ</span><span>ВРЕМЯ МСК</span></div>
    <div className="schedule-board">
      {visible.map((entry) => { const lottery = lotteryById.get(entry.lottery_id); const isFocused = entry.id === focused?.id; const passed = new Date(entry.scheduled_at).getTime() < now; return <div className={`schedule-row lottery-${lottery?.code ?? "unknown"} ${isFocused ? "focused" : ""}`} key={entry.id} ref={isFocused ? focusRef : undefined}>
        <strong>№{drawNumber(entry.public_number)}</strong>
        <b>{entry.lottery_name}<small>{isFocused ? (passed ? "СЕЙЧАС ПО РАСПИСАНИЮ" : "БЛИЖАЙШИЙ") : passed ? "ВРЕМЯ ПРОШЛО" : "ПО РАСПИСАНИЮ"}</small></b>
        <time>{new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Europe/Moscow" }).format(new Date(entry.scheduled_at))}</time>
      </div>; })}
      {!visible.length && <div className="schedule-empty">НА СЕГОДНЯ ТИРАЖЕЙ НЕТ</div>}
    </div>
  </section>;
}

function Status({ active, children }: { active: boolean; children: ReactNode }) {
  return <span className={`status ${active ? "ok" : "warn"}`}><i />{children}</span>;
}

function ActivityChart({ refreshedAt, scope }: { refreshedAt: number; scope: LotteryScope }) {
  const [period, setPeriod] = useState<1 | 7 | 30>(1);
  const [points, setPoints] = useState<ActivityPoint[]>([]);
  const [chartError, setChartError] = useState(false);
  useEffect(() => {
    let active = true;
    void adminApi.activity(period, scope).then((rows) => { if (active) { setPoints(rows); setChartError(false); } }).catch(() => { if (active) setChartError(true); });
    return () => { active = false; };
  }, [period, refreshedAt, scope]);
  const maximum = Math.max(1, ...points.flatMap((point) => [point.total_sales, point.total_payout]));
  return <section className="panel activity-panel">
    <header><div><h2>Продажи и выплаты</h2><span>Стоимость билетов и выплаты в завершённых тиражах · МСК</span></div><div className="activity-periods">{([1, 7, 30] as const).map((days) => <button className={period === days ? "active" : ""} key={days} onClick={() => setPeriod(days)}>{days === 1 ? "24 часа" : `${days} дней`}</button>)}</div></header>
    <div className="activity-legend"><span><i className="sales" />Продажи</span><span><i className="payout" />Выплаты</span></div>
    <div className="activity-chart">{points.map((point) => <div className="activity-column" key={point.bucket_at} title={`Продажи: ${cas(point.total_sales)} · Выплаты: ${cas(point.total_payout)}`}><div><i className="sales" style={{ height: `${(point.total_sales / maximum) * 100}%` }} /><i className="payout" style={{ height: `${(point.total_payout / maximum) * 100}%` }} /></div><small>{new Intl.DateTimeFormat("ru-RU", period === 1 ? { hour: "2-digit", timeZone: "Europe/Moscow" } : { day: "2-digit", month: "2-digit", timeZone: "Europe/Moscow" }).format(new Date(point.bucket_at))}</small></div>)}</div>
    {chartError && <p role="alert" className="source-note">Не удалось обновить график. Попробуйте обновить страницу.</p>}
    {!chartError && !points.length && <p className="source-note">За выбранный период завершённых тиражей пока нет.</p>}
  </section>;
}

function Login({ onAuthenticated }: { onAuthenticated: (session: AdminSession) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberBrowser, setRememberBrowser] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onAuthenticated(await adminApi.login(username, password, rememberBrowser));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось войти.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand"><img alt="Casper Loto" src={logoHorizontal} /><small>Панель владельца</small></div>
        <div className="secure-line"><i /> Вход для владельца</div>
        <h1>Идентификация агента</h1>
        <p>Закрытое пространство владельца Casper Loto. Доступ к оперативной сводке и управлению системой.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>ЛОГИН АДМИНИСТРАТОРА<input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} /></label>
          <label>ПАРОЛЬ<input autoComplete="current-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          <label className="remember-browser"><input type="checkbox" checked={rememberBrowser} onChange={(event) => setRememberBrowser(event.target.checked)} /><span><b>Запомнить этот браузер</b><small>Вход без пароля в течение 90 дней. Выход из панели отменит доверие.</small></span></label>
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "ПРОВЕРЯЕМ…" : "ВОЙТИ"}</button>
        </form>
      </section>
    </main>
  );
}

function DashboardView({ data, analytics, refreshedAt, onOpen, onNavigate }: { data: Overview; analytics: TicketAnalytics; refreshedAt: number; onOpen: (id: string) => void; onNavigate: (view: View) => void }) {
  const overall = analytics.overall;
  const today = data.operations.today;
  return <div className="owner-overview">
    <section className="overview-intro"><div><span>ТИРАЖНЫЕ ЛОТЕРЕИ И FAST</span><h2>Вся игра в цифрах</h2><p>Билеты, выигрыши и джекпоты выбранного этапа экономики.</p></div><button className="secondary-action" onClick={() => onNavigate("instant")}>Моментальные игры ↗</button></section>
    <section className="overview-kpis" aria-label="Итоги этапа">
      <button onClick={() => onNavigate("tickets")}><small>Билеты</small><strong>{overall.total_tickets.toLocaleString("ru-RU")}</strong><span>{overall.active_tickets.toLocaleString("ru-RU")} ожидают розыгрыша <i>↗</i></span></button>
      <button onClick={() => onNavigate("tickets")}><small>Выигрышные билеты</small><strong>{overall.winning_tickets.toLocaleString("ru-RU")}</strong><span>{percentage(overall.winning_tickets, overall.settled_tickets)} от рассчитанных <i>↗</i></span></button>
      <button onClick={() => onNavigate("economy")}><small>Выплачено игрокам</small><strong className="cas-figure">{cas(overall.total_payout)}</strong><span>включая джекпоты <i>↗</i></span></button>
      <button className="jackpot-kpi" onClick={() => onNavigate("jackpots")}><small>Сорвано джекпотов</small><strong>{data.jackpots.total_wins.toLocaleString("ru-RU")}</strong><span>{cas(data.jackpots.total_paid)} выплачено <i>↗</i></span></button>
    </section>
    <section className="overview-today" aria-label="Сегодня по Москве"><div><span className="today-dot" /><h3>Сегодня</h3><small>по Москве</small></div><p><b>{today.purchased_tickets.toLocaleString("ru-RU")}</b> куплено билетов</p><p><b>{cas(today.sales)}</b> потрачено на билеты</p><p><b>{cas(today.payout)}</b> выиграно</p><p><b>{today.completed_draws}</b> тиражей завершено</p></section>
    {data.economy?.scope !== "archive" && overall.total_tickets === 0 && <div className="epoch-empty"><strong>Новый этап начинается с чистой статистики</strong><p>Здесь появятся первые покупки и результаты. Старые показатели доступны в архиве старой экономики.</p></div>}
    <EconomyPanel compact refreshedAt={refreshedAt} onExpand={() => onNavigate("economy")} />
    <section className="panel today-breakdown"><header><div><h2>Результаты дня по лотереям</h2><span>Тиражные игры · покупки и выплаты за сутки по Москве</span></div><button className="text-action" onClick={() => onNavigate("analytics")}>Вся статистика →</button></header><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Билеты</th><th>Потрачено</th><th>Выиграно</th><th>Выигрышные билеты</th></tr></thead><tbody>{(today.by_lottery ?? []).map(row => <tr key={row.lottery_id}><td><b>{row.lottery_name}</b></td><td>{row.purchased_tickets.toLocaleString("ru-RU")}</td><td>{cas(row.sales)}</td><td className="positive">{cas(row.payout)}</td><td>{row.winning_tickets}</td></tr>)}</tbody></table></div>{!today.by_lottery?.length && <p className="source-note">Сегодня ещё не было покупок или выигрышей.</p>}</section>
    <ActivityChart refreshedAt={refreshedAt} scope="all" />
    <section className="panel"><header><div><h2>Ближайшие тиражи</h2><span>Расписание по Москве</span></div><button className="text-action" onClick={() => onNavigate("schedule")}>Всё расписание →</button></header><div className="upcoming-list">{data.operations.next_draws.map(draw => <button key={draw.id} onClick={() => onOpen(draw.id)}><span><b>{draw.lottery_name}</b><small>Тираж №{drawNumber(draw.draw_number)}</small></span><time>{date(draw.scheduled_at)}</time><span>{draw.ticket_count} билетов <i>↗</i></span></button>)}</div>{!data.operations.next_draws.length && <p className="source-note">Ближайших тиражей пока нет.</p>}</section>
  </div>;
}

function FastDashboard({ data, analytics, refreshedAt, onOpen }: { data: Overview; analytics: TicketAnalytics; refreshedAt: number; onOpen: (id: string) => void }) {
  const today = data.operations.today;
  const frequency = data.jackpots.total_wins ? Math.max(1, Math.round(data.counts.completed_draws / data.jackpots.total_wins)) : null;
  return <div className="fast-command-room"><section className="fast-command"><div><span>FAST CONTROL</span><h2>Быстрые раунды</h2><p>Отдельная красная зона: продажи, результаты и частота джекпотов.</p></div><strong>{today.net >= 0 ? "+" : ""}{compactCas(today.net)}<small>итог сегодня</small></strong></section><div className="today-ticker fast-ticker"><div><b>{today.completed_draws} раундов сегодня</b><i>•</i><b>{today.purchased_tickets} билетов</b><i>•</i><b>{cas(today.sales)} продажи</b><i>•</i><b>{data.jackpots.total_wins} джекпотов за выбранный этап</b></div></div><section className="metric-grid today-metrics"><article className="metric"><small>ПРОДАЖИ СЕГОДНЯ</small><strong>{compactCas(today.sales)}</strong></article><article className="metric"><small>ВЫПЛАТЫ СЕГОДНЯ</small><strong>{compactCas(today.payout)}</strong></article><article className="metric"><small>ЧАСТОТА ДЖЕКПОТА</small><strong>{frequency ? `1 / ${frequency}` : "—"}</strong><em>примерно один на столько раундов</em></article><article className="metric"><small>ТЕКУЩИЕ ДЖЕКПОТЫ</small><strong>{compactCas(data.lotteries.reduce((sum, item) => sum + item.current_jackpot, 0))}</strong></article></section><section className="panel"><header><h2>Текущие раунды</h2><span>Продажи и состояние</span></header><div className="table-wrap"><table><thead><tr><th>Игра</th><th>Время</th><th>Статус</th><th>Билеты</th><th>Продажи</th></tr></thead><tbody>{data.operations.next_draws.map(draw => <tr key={draw.id} onClick={() => onOpen(draw.id)} className="clickable"><td><b>{draw.lottery_name}</b> №{drawNumber(draw.draw_number)}</td><td>{date(draw.scheduled_at)}</td><td>{translated(draw.status, drawStatuses)}</td><td>{draw.ticket_count}</td><td>{cas(draw.total_sales)}</td></tr>)}</tbody></table></div></section><section className="panel"><header><h2>Последние результаты</h2><span>Быстрые игры · нажмите тираж для подробностей</span></header><DrawTable draws={data.recent_draws} onOpen={onOpen} /></section><JackpotPanel data={data} analytics={analytics} onOpen={onOpen} /><ActivityChart refreshedAt={refreshedAt} scope="fast" /><TicketAnalyticsView data={analytics} /></div>;
}

function JackpotHistoryView({ scope, onOpen }: { scope: LotteryScope; onOpen: (id: string) => void }) {
  const [storedEvents, setEvents] = useState<JackpotEvent[]>([]);
  const [lotteries, setLotteries] = useState<Lottery[]>([]);
  const [lotteryId, setLotteryId] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadedKey, setLoadedKey] = useState("");
  const [more, setMore] = useState(false);
  const [error, setError] = useState("");
  const queryKey = `${scope}:${lotteryId}`;
  const busy = loadedKey !== queryKey || loadingMore;
  const events = loadedKey === queryKey ? storedEvents : [];
  const generation = useRef(0);
  useEffect(() => { void adminApi.lotteries().then(setLotteries).catch(() => undefined); }, []);
  useEffect(() => {
    const current = ++generation.current;
    void adminApi.jackpotEvents(scope, lotteryId, 0).then(rows => {
      if (current === generation.current) { setEvents(rows); setMore(rows.length === 100); setError(""); }
    }).catch((reason: Error) => { if (current === generation.current) setError(reason.message); })
      .finally(() => { if (current === generation.current) setLoadedKey(queryKey); });
    return () => { generation.current += 1; };
  }, [scope, lotteryId, queryKey]);
  const next = async () => {
    setLoadingMore(true);
    try {
      const rows = await adminApi.jackpotEvents(scope, lotteryId, events.length);
      setEvents(current => [...current, ...rows]); setMore(rows.length === 100);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось загрузить джекпоты."); }
    finally { setLoadingMore(false); }
  };
  return <div className="jackpot-catalog"><section className="archive-command jackpot-catalog-hero"><div><span>ИСТОРИЯ ВЫПЛАТ</span><h2>Каждый сорванный джекпот — с подробностями</h2><p>Нажмите на выигрыш, чтобы открыть тираж: увидите номер, выпавшую комбинацию, выигрышные билеты и игроков.</p></div></section><div className="section-toolbar"><label>Лотерея<select aria-label="Фильтр лотереи джекпотов" value={lotteryId} onChange={event => setLotteryId(event.target.value)}><option value="">Все лотереи</option>{lotteries.filter(item => scope === "all" || ["flash", "shadow", "pulse"].includes(item.code) === (scope === "fast")).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><span>Загружено: {events.length}</span></div>{error && <p className="error banner">{error}</p>}<section className="panel"><header><h2>Список сорванных джекпотов</h2><span>{scope === "fast" ? "FAST" : scope === "standard" ? "DAILY / WEEKLY / SPECIAL" : "ВСЕ ИГРЫ"}</span></header><div className="table-wrap"><table><thead><tr><th>Когда</th><th>Лотерея / тираж</th><th>Сумма джекпота</th><th>Билетов с джекпотом</th><th>Игроков</th><th></th></tr></thead><tbody>{events.map(event => <tr key={event.id} className="jackpot-event-row"><td>{date(event.occurred_at)} МСК</td><td><b>{event.lottery_name}</b><small>Тираж №{drawNumber(event.draw_number ?? 0)}</small></td><td className="positive"><b>{cas(event.jackpot_amount)}</b></td><td>{event.winner_ticket_count}</td><td>{event.winner_user_count}</td><td><button className="text-action" onClick={() => onOpen(event.draw_id)}>Открыть детали →</button></td></tr>)}</tbody></table></div>{busy && <p className="source-note">Загружаем джекпоты…</p>}{!busy && !events.length && !error && <p className="source-note">Сорванных джекпотов по этому фильтру пока нет.</p>}{more && <button className="draw-load-more" disabled={busy} onClick={() => void next()}>Загрузить ещё 100</button>}</section></div>;
}

function FullJackpotHistory({ scope, refreshedAt, onOpen }: { scope: LotteryScope; refreshedAt: number; onOpen: (id: string) => void }) {
  const [opened, setOpened] = useState(false);
  return <details className="full-jackpot-history" onToggle={event => setOpened(event.currentTarget.open)}><summary>Полная история джекпотов</summary>{opened && <JackpotHistoryView key={`${scope}-${refreshedAt}`} scope={scope} onOpen={onOpen} />}</details>;
}

function SystemHealth({ data }: { data: Dashboard }) {
  return <>
    <div className="system-strip"><Status active={data.database_healthy}>БАЗА ДАННЫХ {data.database_healthy ? "РАБОТАЕТ" : "НЕДОСТУПНА"}</Status><Status active={data.scheduler_enabled}>ПЛАНИРОВЩИК {data.scheduler_enabled ? "АКТИВЕН" : "ОТКЛЮЧЁН"}</Status><Status active={data.bot_configured}>БОТ {data.bot_configured ? "НАСТРОЕН" : "НЕ НАСТРОЕН"}</Status><span>v{data.version} · работает {Math.floor(data.uptime_seconds / 60)} мин.</span></div>
    <section className="panel"><header><h2>Работа расписания и доставки</h2><span>Техническая диагностика</span></header><div className="control-status"><article><small>Последняя успешная проверка</small><strong>{date(data.operations.scheduler.last_succeeded_at)}</strong><span>{data.operations.scheduler.last_error ?? "Нет сохранённой ошибки планировщика"}</span></article><article><small>Задержанные тиражи</small><strong>{data.operations.stuck_draw_count}</strong><span>Ожидают доставки: {data.operations.notifications.PENDING ?? 0} · ошибки: {(data.operations.notifications.FAILED ?? 0) + (data.operations.notifications.UNCERTAIN ?? 0)}</span></article></div></section>
    <section className="panel system-health-panel"><header><div><h2>Состояние сервисов</h2><span>Диагностика и пункты, требующие внимания</span></div></header><div className="control-status"><article><small>Последняя успешная проверка</small><strong>{date(data.operations.scheduler.last_succeeded_at)}</strong><span>{data.operations.scheduler.last_error ?? "Ошибок планировщика не зарегистрировано"}</span></article><article className={data.operations.stuck_draw_count ? "health-warning" : "health-good"}><small>Зависшие тиражи</small><strong>{data.operations.stuck_draw_count}</strong><span>{data.operations.stuck_draw_count ? "Проверьте раздел «Тиражи»" : "Все тиражи обработаны"}</span></article><article className={((data.operations.notifications.FAILED ?? 0) + (data.operations.notifications.UNCERTAIN ?? 0)) ? "health-warning" : "health-good"}><small>Доставка уведомлений</small><strong>{data.operations.notifications.PENDING ?? 0} ожидают · {(data.operations.notifications.FAILED ?? 0) + (data.operations.notifications.UNCERTAIN ?? 0)} требуют проверки</strong><span>{((data.operations.notifications.FAILED ?? 0) + (data.operations.notifications.UNCERTAIN ?? 0)) ? "Вкладка «Уведомления» содержит детали" : "Ошибок доставки нет"}</span></article></div><details className="system-account-details"><summary>Показать текущие счета и фонды по лотереям</summary><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Джекпот</th><th>Распределение</th><th>Резерв</th></tr></thead><tbody>{data.lotteries.map(lottery => <tr key={lottery.id}><td>{lottery.name}</td><td>{cas(lottery.current_jackpot)}</td><td>{cas(lottery.distribution_fund)}</td><td>{cas(lottery.reserve)}</td></tr>)}</tbody></table></div></details></section>
  </>;
}

function ActionConfirm({ title, details, busy, onConfirm, onCancel }: { title: string; details: string[]; busy: boolean; onConfirm: () => void; onCancel: () => void }) {
  return <div className="action-confirm" role="dialog" aria-modal="true" aria-label={title}><div><small>ПРОВЕРКА ПЕРЕД ДЕЙСТВИЕМ</small><h3>{title}</h3>{details.map(item => <p key={item}>{item}</p>)}<b>Завершённые тиражи и купленные билеты не изменятся.</b><footer><button className="secondary-action" onClick={onCancel}>Отмена</button><button disabled={busy} onClick={onConfirm}>{busy ? "Выполняем…" : "Подтвердить"}</button></footer></div></div>;
}

function InlineConfirm({ summary, busy, confirmLabel, onConfirm, onCancel }: { summary: string; busy: boolean; confirmLabel: string; onConfirm: () => void; onCancel: () => void }) {
  return <div className="inline-confirm" role="group" aria-label="Подтверждение изменения"><span><b>Вы уверены?</b><small>{summary}</small></span><button className="primary" disabled={busy} onClick={onConfirm}>{busy ? "Сохраняем…" : confirmLabel}</button><button className="secondary-action" disabled={busy} onClick={onCancel}>Нет</button></div>;
}

const autoPlayReasons: Record<string, string> = { INSUFFICIENT_BALANCE: "Недостаточно CAS", TICKET_LIMIT_REACHED: "Достигнут лимит билетов", SALES_CLOSED: "Продажи закрыты", INVALID_COMBINATION: "Неподходящая комбинация", TECHNICAL_ERROR: "Техническая ошибка", InsufficientBalance: "Недостаточно CAS", NoAvailableDraw: "Продажи закрыты", InvalidTicket: "Неподходящая комбинация", ConfigurationError: "Техническая ошибка" };

function PlayerCard({ player, onSaved }: { player: Player; onSaved: () => Promise<void> }) {
  const [formError, setFormError] = useState("");
  const [amount, setAmount] = useState(String(player.balance));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [autoReason, setAutoReason] = useState("");
  const [autoTickets, setAutoTickets] = useState(String(player.auto_play_tickets_per_draw));
  const [autoBusy, setAutoBusy] = useState(false);
  const [confirmation, setConfirmation] = useState<"balance" | "auto-on" | "auto-off" | null>(null);
  const [operations, setOperations] = useState<Transaction[] | null>(null);
  const [operationsHasMore, setOperationsHasMore] = useState(false);
  const [operationsFilter, setOperationsFilter] = useState("");
  const [operationsBusy, setOperationsBusy] = useState(false);
  const operationsRequest = useRef(0);
  const operationsInFlight = useRef(false);
  useEffect(() => () => { operationsRequest.current += 1; }, []);
  const [history, setHistory] = useState<PlayerHistoryPage | null>(null);
  const [historyFilter, setHistoryFilter] = useState("all");
  const [historyLottery, setHistoryLottery] = useState("");
  const [historyPageLoading, setHistoryPageLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [loadedHistoryKey, setLoadedHistoryKey] = useState("");
  const [copiedPlayerId, setCopiedPlayerId] = useState(false);
  const historyKey = `${player.id}:${historyFilter}:${historyLottery}`;
  const historyLoading = loadedHistoryKey !== historyKey || historyPageLoading;
  const shownHistory = historyLoading ? null : history;
  useEffect(() => {
    let current = true;
    void adminApi.playerTicketHistory(player.id, historyFilter, historyLottery, 0)
      .then((page) => { if (current) { setHistory(page); setHistoryError(""); setLoadedHistoryKey(historyKey); } })
      .catch((reason: Error) => { if (current) { setHistoryError(reason.message); setLoadedHistoryKey(historyKey); } });
    return () => { current = false; };
  }, [player.id, historyFilter, historyLottery, historyKey]);
  const loadMoreHistory = async () => {
    if (!history || historyLoading || history.items.length >= history.total) return;
    setHistoryPageLoading(true);
    setHistoryError("");
    try {
      const page = await adminApi.playerTicketHistory(player.id, historyFilter, historyLottery, history.items.length);
      setHistory((current) => current ? { ...page, items: [...current.items, ...page.items] } : page);
    } catch (reason) { setHistoryError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты."); }
    finally { setHistoryPageLoading(false); }
  };
  const requestOperations = async (filter: string, append = false) => {
    if (append && (!operations || !operationsHasMore || operationsInFlight.current)) return;
    const generation = append ? operationsRequest.current : ++operationsRequest.current;
    operationsInFlight.current = true;
    setOperationsBusy(true); setFormError("");
    if (!append) { setOperations([]); setOperationsHasMore(false); }
    try {
      const last = append ? operations?.at(-1) : undefined;
      const rows = await adminApi.playerTransactions(player.id, 0, filter, last);
      if (generation !== operationsRequest.current) return;
      setOperations(current => append && current ? [...current, ...rows.filter(row => !current.some(item => item.id === row.id))] : rows);
      setOperationsHasMore(rows.length === 100);
    } catch (reason) { if (generation === operationsRequest.current) setFormError(reason instanceof Error ? reason.message : "Не удалось загрузить операции."); }
    finally { if (generation === operationsRequest.current) { operationsInFlight.current = false; setOperationsBusy(false); } }
  };
  const toggleOperations = () => {
    if (operations) { operationsRequest.current += 1; operationsInFlight.current = false; setOperationsBusy(false); setOperations(null); }
    else void requestOperations(operationsFilter);
  };
  const save = async () => {
    setBusy(true); setFormError("");
    try {
      await adminApi.setBalance(player.id, Number(amount), reason);
      setReason("");
      await onSaved();
      setConfirmation(null);
    } catch (reason) { setFormError(reason instanceof Error ? reason.message : "Не удалось изменить баланс."); } finally { setBusy(false); }
  };
  const configureAutoPlay = async (enabled: boolean) => {
    setAutoBusy(true); setFormError("");
    try {
      await adminApi.setAutoPlay(player.id, enabled, Number(autoTickets), autoReason);
      setAutoReason("");
      await onSaved();
      setConfirmation(null);
    } catch (reason) { setFormError(reason instanceof Error ? reason.message : "Не удалось изменить автоучастие."); } finally { setAutoBusy(false); }
  };
  const autoStatus = !player.auto_play_enabled ? "Отключено" : player.auto_play_last_error ? (autoPlayReasons[player.auto_play_last_error] ?? "Техническая ошибка") : player.auto_play_last_succeeded_at ? "Работает" : "Ожидает открытого тиража";
  return <article className="player-card">
    {formError && <p className="error" role="alert">{formError}</p>}
    <div className="player-head"><div className="avatar">{player.display_name.slice(0, 1)}</div><div><h3>{player.display_name}</h3><small>@{player.username ?? "без_логина"} · Telegram ID {player.telegram_id ?? "—"}</small><div className="player-id-line"><span>Внутренний ID</span><code title={player.id}>{player.id}</code><button type="button" onClick={() => void navigator.clipboard?.writeText(player.id).then(() => { setCopiedPlayerId(true); window.setTimeout(() => setCopiedPlayerId(false), 1500); })}>{copiedPlayerId ? "Скопирован" : "Копировать"}</button></div></div><Status active={player.is_active}>{player.is_active ? "АКТИВЕН" : "ОТКЛЮЧЁН"}</Status></div>
    <div className="player-stats"><span><small>БАЛАНС</small><b>{cas(player.balance)}</b></span><span><small>АКТИВНЫЕ БИЛЕТЫ</small><b>{player.active_ticket_count}</b><em>{player.ticket_count} всего</em></span><span><small>ПОТРАЧЕНО</small><b>{cas(player.spent)}</b></span><span><small>ВЫИГРАНО</small><b>{cas(player.won)}</b></span><span><small>ИТОГ</small><b className={player.net >= 0 ? "positive" : "negative"}>{cas(player.net)}</b></span></div>
    <section className="player-lottery-history"><header><div><small>СТАТИСТИКА ИГРОКА</small><h4>Результаты по лотереям</h4></div><span>За всё время</span></header><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Билеты</th><th>Активные</th><th>Выигрыши</th><th>Потрачено</th><th>Выплачено</th><th>Итог</th></tr></thead><tbody>{shownHistory?.lottery_stats.map((stat) => <tr key={stat.lottery_code}><td>{stat.lottery_name}</td><td>{stat.ticket_count}</td><td>{stat.active_ticket_count}</td><td>{stat.winning_ticket_count}</td><td>{cas(stat.spent)}</td><td>{cas(stat.won)}</td><td className={stat.won - stat.spent >= 0 ? "positive" : "negative"}>{cas(stat.won - stat.spent)}</td></tr>)}</tbody></table></div></section>
    <section className="player-ticket-history"><header><div><small>ПОКУПКИ И РЕЗУЛЬТАТЫ</small><h4>История билетов</h4></div><span>{shownHistory ? `${shownHistory.total.toLocaleString("ru-RU")} записей` : "Загружаем…"}</span></header><div className="player-history-controls"><div className="player-history-tabs" role="group" aria-label="Фильтр билетов">{[["all", "Все"], ["purchases", "Покупки"], ["wins", "Выигрыши"]].map(([key, label]) => <button key={key} className={historyFilter === key ? "active" : ""} onClick={() => setHistoryFilter(key)}>{label}</button>)}</div><select aria-label="Фильтр по лотерее" value={historyLottery} onChange={(event) => setHistoryLottery(event.target.value)}><option value="">Все лотереи</option>{shownHistory?.lottery_stats.map((stat) => <option key={stat.lottery_code} value={stat.lottery_code}>{stat.lottery_name}</option>)}</select></div>{historyError && <p role="alert" className="source-note negative">{historyError}</p>}{shownHistory?.items.length ? <div className="player-ticket-list">{shownHistory.items.map((ticket) => <article key={ticket.id} className={ticket.prize_amount > 0 ? "winner" : ""}><div className="player-ticket-main"><strong>{ticket.lottery_name}</strong><span>Билет №{ticket.public_number}{ticket.draw_number ? ` · тираж №${ticket.draw_number}` : " · мгновенный"}</span><small>{date(ticket.purchased_at)} · {ticket.source === "AUTO_PLAY" ? "Автоучастие" : ticket.ticket_kind === "INSTANT" ? "Мгновенный билет" : "Покупка"}</small></div><div className="player-ticket-number-group"><code className="player-ticket-numbers">{ticket.ticket_kind === "INSTANT" ? `Символы: ${ticket.numbers.map((value) => instantSymbolGlyphs[value - 1] ?? "●").join(" · ")}` : ticket.numbers.map((number) => displayNumber(ticket.lottery_code, number)).join(" · ")}</code>{ticket.winning_numbers?.length ? <small>Выпали: {ticket.winning_numbers.map((number) => displayNumber(ticket.lottery_code, number)).join(" · ")}</small> : null}</div><div className="player-ticket-outcome"><span>Покупка {cas(ticket.purchase_price)}</span><b className={ticket.prize_amount > 0 ? "positive" : ""}>{ticket.prize_amount > 0 ? `Выигрыш +${cas(ticket.prize_amount)}` : ticket.status === "REFUNDED" ? "Возврат" : ticket.status === "PURCHASED" ? "Тираж ещё не завершён" : "Без выигрыша"}</b></div></article>)}</div> : !historyLoading && <p className="source-note">В этой выборке билетов нет.</p>}{shownHistory && shownHistory.items.length < shownHistory.total && <button className="player-history-more" disabled={historyLoading} onClick={() => void loadMoreHistory()}>{historyLoading ? "Загружаем…" : `Показать ещё · ${Math.min(100, shownHistory.total - shownHistory.items.length)} из ${shownHistory.total - shownHistory.items.length}`}</button>}</section>
    <div className="player-automation compact"><div><small>АВТОУЧАСТИЕ · {autoStatus.toLocaleUpperCase("ru-RU")}</small><b>{player.auto_play_enabled ? `${player.auto_play_tickets_per_draw} случайных билетов на каждый тираж` : "Выключена"}</b><span>Только ближайшие 5 тиражей каждой разрешённой лотереи. Casper Dual исключена и не может быть включена здесь.</span><span>Последняя проверка: {date(player.auto_play_last_attempted_at)} · успех: {date(player.auto_play_last_succeeded_at)}</span></div><div className="notification-state"><small>УВЕДОМЛЕНИЯ</small><b>{player.telegram_notifications_enabled ? "Telegram разрешён" : "Telegram выключен"}</b></div><label>Билетов на тираж<input aria-label="Билетов автоучастия на тираж" type="number" min="1" max="5" value={autoTickets} onChange={(event) => setAutoTickets(event.target.value)} /></label><label>Причина автоучастия<input value={autoReason} onChange={(event) => setAutoReason(event.target.value)} placeholder="Почему меняется автоучастие?" /></label><button disabled={autoBusy || !autoReason.trim() || Number(autoTickets) < 1 || Number(autoTickets) > 5} onClick={() => setConfirmation("auto-on")}>{player.auto_play_enabled ? "СОХРАНИТЬ АВТОУЧАСТИЕ" : "ВКЛЮЧИТЬ АВТОУЧАСТИЕ"}</button>{player.auto_play_enabled && <button className="secondary-action" disabled={autoBusy || !autoReason.trim()} onClick={() => setConfirmation("auto-off")}>ОТКЛЮЧИТЬ</button>}</div>
    <div className="adjust"><label>Новый баланс<input min="0" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} /></label><label>Обязательная причина<input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Почему требуется изменение?" /></label><button disabled={busy || !reason.trim()} onClick={() => setConfirmation("balance")}>ПРОВЕРИТЬ ИЗМЕНЕНИЕ</button></div>
    <button className="player-operations-toggle" onClick={toggleOperations}>{operations ? "Скрыть движения CAS" : "Показать движения CAS"}</button>{operations && <div className="player-operations"><p className="ledger-explainer">Одна запись — одно движение по счёту. Покупку и комбинацию каждого билета смотрите в истории билетов выше.</p><div className="player-history-controls"><select aria-label="Фильтр движения CAS" value={operationsFilter} onChange={(event) => { const filter = event.target.value; setOperationsFilter(filter); void requestOperations(filter); }}><option value="">Все движения</option><option value="TICKET_PURCHASE">Покупки билетов</option><option value="PRIZE_PAYOUT">Выплаты выигрышей</option><option value="JACKPOT_PAYOUT">Выплаты джекпота</option></select><span>Загружено: {operations.length}{operationsHasMore ? "+" : ""}</span></div><TransactionTable rows={operations} userId={player.id} />{operationsHasMore && <button className="player-history-more" disabled={operationsBusy} onClick={() => void requestOperations(operationsFilter, true)}>Загрузить ещё 100 операций CAS</button>}</div>}
    {confirmation === "balance" && <ActionConfirm title={`Баланс · ${player.display_name}`} details={[`Было: ${cas(player.balance)}`, `Станет: ${cas(Number(amount))}`, `Изменение: ${cas(Number(amount) - player.balance)}`, `Причина: ${reason}`]} busy={busy} onCancel={() => setConfirmation(null)} onConfirm={() => void save()} />}
    {(confirmation === "auto-on" || confirmation === "auto-off") && <ActionConfirm title={`Автоучастие · ${player.display_name}`} details={[`Состояние: ${confirmation === "auto-on" ? "включено" : "выключено"}`, `Билетов на тираж: ${autoTickets}`, `Причина: ${autoReason}`]} busy={autoBusy} onCancel={() => setConfirmation(null)} onConfirm={() => void configureAutoPlay(confirmation === "auto-on")} />}
  </article>;
}

function LotteryCard({ lottery, onSaved }: { lottery: Lottery; onSaved: () => Promise<void> }) {
  const [price, setPrice] = useState(String(lottery.ticket_price ?? 0));
  const [base, setBase] = useState(String(lottery.base_jackpot));
  const [currentJackpot, setCurrentJackpot] = useState(String(lottery.current_jackpot));
  const [cutoff, setCutoff] = useState(String(lottery.sales_cutoff_minutes ?? 0));
  const [purchaseLimit, setPurchaseLimit] = useState(String(lottery.max_tickets_per_purchase));
  const [playerLimit, setPlayerLimit] = useState(String(lottery.max_tickets_per_user_per_draw));
  const [reason, setReason] = useState("Изменение настроек владельцем");
  const [busy, setBusy] = useState(false);
  const [jackpotBusy, setJackpotBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [confirmation, setConfirmation] = useState<"settings" | "jackpot" | null>(null);
  const saveAll = async () => {
    setBusy(true);
    setMessage("");
    try {
      await adminApi.configureLottery(lottery.id, Number(price), Number(base), Number(cutoff), Number(purchaseLimit), Number(playerLimit), reason);
      setMessage("Цена билета, базовый джекпот и лимиты сохранены.");
      await onSaved();
      setConfirmation(null);
    } catch (saveError) {
      setConfirmation(null);
      setMessage(saveError instanceof Error ? saveError.message : "Не удалось сохранить настройки.");
    } finally {
      setBusy(false);
    }
  };
  const saveJackpot = async () => {
    setJackpotBusy(true);
    setMessage("");
    try {
      await adminApi.setJackpot(lottery.id, Number(currentJackpot), reason);
      setMessage("Текущий джекпот изменён через журнал CAS.");
      await onSaved();
      setConfirmation(null);
    } catch (saveError) {
      setConfirmation(null);
      setMessage(saveError instanceof Error ? saveError.message : "Не удалось изменить текущий джекпот.");
    } finally {
      setJackpotBusy(false);
    }
  };
  const messageIsSuccess = message.includes("сохранен") || message.includes("изменён");
  return <article className="lottery-card">
    <header><div><small>{["flash", "shadow", "pulse"].includes(lottery.code) ? "БЫСТРАЯ" : lottery.kind === "WEEKLY" ? "ЕЖЕНЕДЕЛЬНАЯ" : "ЕЖЕДНЕВНАЯ"}</small><h2>{lottery.name}</h2></div><Status active={lottery.is_active}>{lottery.is_active ? "АКТИВНА" : "НЕАКТИВНА"}</Status></header>
    <div className="fund-matrix"><span><small>ТЕКУЩИЙ ДЖЕКПОТ</small><b>{cas(lottery.current_jackpot)}</b></span><span><small>СХЕМА ПОКУПКИ</small><b>100% в джекпот</b></span><span><small>СЛЕДУЮЩИЙ ТИРАЖ</small><b>{lottery.next_draw_number ? `№${drawNumber(lottery.next_draw_number)}` : "—"}</b><em>{date(lottery.next_draw_at)}</em></span></div>
    <div className="config-grid"><label>Цена билета, CAS<input type="number" min="1" value={price} onChange={(e) => setPrice(e.target.value)} /></label><label>Базовый джекпот после выигрыша, CAS<input type="number" min="0" value={base} onChange={(e) => setBase(e.target.value)} /></label><label>Закрыть продажи за, минут<input type="number" min="0" max="1440" value={cutoff} onChange={(e) => setCutoff(e.target.value)} /></label><label>Лимит одной покупки<input type="number" min="1" max="1000" value={purchaseLimit} onChange={(e) => setPurchaseLimit(e.target.value)} /></label><label>Лимит игрока на тираж<input type="number" min="1" max="100000" value={playerLimit} onChange={(e) => setPlayerLimit(e.target.value)} /></label></div>
    <label className="reason">Комментарий для истории изменений<input value={reason} onChange={(e) => setReason(e.target.value)} /></label>
    <div className="lottery-actions"><div className="actions"><button disabled={busy || jackpotBusy || !reason.trim()} onClick={() => setConfirmation("settings")}>{busy ? "СОХРАНЯЕМ…" : "СОХРАНИТЬ НАСТРОЙКИ"}</button></div><div className="jackpot-adjust"><label>Текущий джекпот, CAS<input type="number" min="0" value={currentJackpot} onChange={(e) => setCurrentJackpot(e.target.value)} /></label><button disabled={busy || jackpotBusy || !reason.trim()} onClick={() => setConfirmation("jackpot")}>{jackpotBusy ? "МЕНЯЕМ…" : "ИЗМЕНИТЬ ДЖЕКПОТ"}</button></div></div>
    {confirmation === "settings" && <InlineConfirm summary={`Цена ${cas(lottery.ticket_price ?? 0)} → ${cas(Number(price))} · базовый джекпот ${cas(lottery.base_jackpot)} → ${cas(Number(base))}`} busy={busy} confirmLabel="Да, сохранить" onCancel={() => setConfirmation(null)} onConfirm={() => void saveAll()} />}
    {confirmation === "jackpot" && <InlineConfirm summary={`${cas(lottery.current_jackpot)} → ${cas(Number(currentJackpot))}`} busy={jackpotBusy} confirmLabel="Да, изменить" onCancel={() => setConfirmation(null)} onConfirm={() => void saveJackpot()} />}
    {message && <p className={messageIsSuccess ? "save-message" : "save-message error"} role={messageIsSuccess ? undefined : "alert"}>{message}</p>}
    <footer>Расписание: <code>{schedule(lottery.schedule)}</code> · новое время закрытия продаж применяются при подготовке следующих тиражей. Завершённые тиражи и купленные билеты не изменяются.</footer>
  </article>;
}

function PlayersView({ players, search, onSearch, onResults, onReload }: { players: Player[]; search: string; onSearch: (value: string) => void; onResults: (players: Player[]) => void; onReload: () => Promise<void> }) {
  const [selectedId, setSelectedId] = useState("");
  const [searchError, setSearchError] = useState("");
  useEffect(() => {
    let current = true;
    const timer = window.setTimeout(() => {
      setSearchError("");
      void adminApi.players(search.trim()).then((rows) => { if (current) onResults(rows); }).catch(() => { if (current) setSearchError("Поиск временно недоступен."); });
    }, 250);
    return () => { current = false; window.clearTimeout(timer); };
  }, [search, onResults]);
  const query = search.trim().replace(/^@/, "").toLocaleLowerCase("ru-RU");
  const visible = players.filter((player) => !query || `${player.display_name} ${player.username ?? ""} ${player.telegram_id ?? ""} ${player.id}`.toLocaleLowerCase("ru-RU").includes(query));
  const activeId = visible.some((player) => player.id === selectedId) ? selectedId : visible[0]?.id ?? "";
  const selected = players.find((player) => player.id === activeId);
  return <section className="player-directory">
    <div className="player-finder">
      <label><span>Быстрый поиск игрока</span><input autoFocus aria-label="Поиск игрока" placeholder="Внутренний ID, имя, @username или Telegram ID" value={search} onChange={(event) => onSearch(event.target.value)} /></label>
      <div className="player-search-meta"><b>{visible.length}</b><span>{query ? "найдено" : `последних игроков: ${players.length}`}</span>{search && <button onClick={() => onSearch("")}>Сбросить</button>}</div>
      <div className="player-results" role="list" aria-label="Результаты поиска игроков">{visible.map((player) => <button type="button" role="listitem" aria-label={`Открыть игрока ${player.display_name}`} className={player.id === activeId ? "active" : ""} key={player.id} onClick={() => setSelectedId(player.id)}><span className="avatar">{player.display_name.slice(0, 1)}</span><span><b>{player.display_name} ·</b><small>{player.username ? `@${player.username}` : `TG ${player.telegram_id ?? "—"}`} · ID {player.id.slice(0, 8)}</small></span><span><b>{cas(player.balance)}</b><small>{player.active_ticket_count} активных бил.</small></span></button>)}</div>
      {!visible.length && <p className="source-note">Игрок не найден. Проверьте username или Telegram ID.</p>}
      {searchError && <p role="alert" className="source-note negative">{searchError}</p>}
    </div>
    <div className="player-detail">{selected ? <PlayerCard key={selected.id} player={selected} onSaved={onReload} /> : <div className="player-empty"><b>Выберите игрока</b><span>Справа появятся баланс, билеты, выигрыши и действия.</span></div>}</div>
  </section>;
}

function DrawTable({ draws, onOpen, showRuleset = false }: { draws: Draw[]; onOpen?: (id: string) => void; showRuleset?: boolean }) {
  return <div className="table-wrap"><table><thead><tr><th>Лотерея / тираж</th><th>Статус</th><th>По расписанию</th><th>Результат</th><th>Билеты</th><th>Продажи / выплаты</th></tr></thead><tbody>{draws.map((draw) => <tr key={draw.id} onClick={() => onOpen?.(draw.id)} className={onOpen ? "clickable" : ""}><td>{onOpen ? <button className="text-action" onClick={event => { event.stopPropagation(); onOpen(draw.id); }}>{draw.lottery_name} №{drawNumber(draw.public_number)}</button> : <><b>{draw.lottery_name}</b> №{drawNumber(draw.public_number)}</>}{draw.is_distribution && <small className="tag distribution">Распределительный</small>}{showRuleset && draw.ruleset_code && <small>Старая версия правил: {draw.ruleset_code}</small>}</td><td><span className={`tag ${draw.status.toLowerCase()}`}>{translated(draw.status, drawStatuses)}</span></td><td>{date(draw.scheduled_at)}</td><td><DrawResult draw={draw} /></td><td>{draw.ticket_count}</td><td>{cas(draw.total_sales)}<small>{cas(draw.total_payout)}</small></td></tr>)}</tbody></table></div>;
}

function TransactionTable({ rows, userId, onOpenPlayer }: { rows: Transaction[]; userId?: string; onOpenPlayer?: (userId: string) => void }) {
  return <div className="table-wrap"><table><thead><tr><th>Время</th><th>Игрок</th><th>Тип операции</th><th>Счёт</th><th>Изменение</th><th>До → После</th><th>Код операции</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{date(row.created_at)}</td><td>{row.user_id ? row.user_id === userId ? "Этот игрок" : onOpenPlayer ? <button type="button" className="transaction-player-link" onClick={() => onOpenPlayer(row.user_id!)}>{row.user_id.slice(0, 8)}…</button> : <code>{row.user_id.slice(0, 8)}…</code> : "—"}</td><td><span className="tag">{translated(row.type, transactionTypes)}</span></td><td>{translated(row.account_kind, accountKinds)}</td><td className={row.amount >= 0 ? "positive" : "negative"}>{row.amount > 0 ? "+" : ""}{cas(row.amount)}</td><td>{cas(row.balance_before)} → {cas(row.balance_after)}</td><td><code>{row.operation_id.slice(0, 8)}</code></td></tr>)}</tbody></table></div>;
}

function DrawDetailPanel({ detail, onClose, onOpenPlayer }: { detail: DrawDetail; onClose: () => void; onOpenPlayer: (ticket: DrawDetail["tickets"][number]) => void }) {
  const draw = detail.draw;
  const distributed = (draw.distributed_amount ?? 0) > 0;
  const jackpotWon = (draw.jackpot_amount ?? 0) > 0;
  const bingo = draw.lottery_code === "bingo";
  const [ticketFilter, setTicketFilter] = useState<"all" | "winners" | "jackpot">(bingo && draw.status === "COMPLETED" ? "winners" : "all");
  const [page, setPage] = useState({ items: detail.tickets, hasMore: false, after: null as number | null });
  const [started, setStarted] = useState(false);
  const [pageLoading, setPageLoading] = useState(false);
  const [pageError, setPageError] = useState("");
  const [pageRetry, setPageRetry] = useState(0);
  const pageRequest = useRef(0);
  const pageInFlight = useRef(false);
  useEffect(() => {
    if (!started) return;
    const generation = ++pageRequest.current;
    pageInFlight.current = true;
    void adminApi.drawPage(draw.id, ticketFilter).then(result => {
      if (generation === pageRequest.current) setPage({ items: result.tickets, hasMore: !!result.has_more, after: result.next_after ?? null });
    }).catch((reason: Error) => { if (generation === pageRequest.current) setPageError(reason.message); })
      .finally(() => { if (generation === pageRequest.current) { pageInFlight.current = false; setPageLoading(false); } });
    return () => { pageRequest.current += 1; };
  }, [draw.id, ticketFilter, started, pageRetry]);
  const loadMore = async () => {
    if (!page.hasMore || page.after == null || pageInFlight.current) return;
    const generation = pageRequest.current;
    pageInFlight.current = true; setPageLoading(true); setPageError("");
    try {
      const result = await adminApi.drawPage(draw.id, ticketFilter, page.after);
      if (generation === pageRequest.current) setPage(current => ({ items: [...current.items, ...result.tickets.filter(row => !current.items.some(item => item.id === row.id))], hasMore: !!result.has_more, after: result.next_after ?? null }));
    } catch (reason) { if (generation === pageRequest.current) setPageError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты."); }
    finally { if (generation === pageRequest.current) { pageInFlight.current = false; setPageLoading(false); } }
  };
  const chooseFilter = (filter: typeof ticketFilter) => {
    if (started && filter === ticketFilter) return;
    pageRequest.current += 1;
    setPage({ items: [], hasMore: false, after: null });
    setPageLoading(true); setPageError(""); setTicketFilter(filter); setStarted(true);
  };
  const summary = detail.ticket_summary;
  const winningTickets = page.items.filter((ticket) => ticket.prize_amount > 0);
  const jackpotTickets = page.items.filter((ticket) => ticket.is_jackpot_winner);
  const shownTickets = ticketFilter === "winners" ? winningTickets : page.items;
  const participantCount = summary?.participants ?? new Set(page.items.map((ticket) => ticket.user_id)).size;
  const bingoStages = summary?.bingo_stages.map(stage => ({ ...stage, firstMove: stage.first_move })) ?? (draw.ruleset_code === "bingo_12_60_economy_v2" ? [0, 1, 2, 3] : [0, 1, 2]).map((stage) => {
    const winners = page.items.filter((ticket) => (ticket.bingo_result?.amounts[stage] ?? 0) > 0);
    const firstMove = winners.length ? Math.min(...winners.map((ticket) => ticket.bingo_result?.moves[Math.min(stage, 2)] ?? 0)) : null;
    return { winners: winners.length, payout: winners.reduce((sum, ticket) => sum + (ticket.bingo_result?.amounts[stage] ?? 0), 0), firstMove };
  });
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose]);
  return <div className="drawer" role="dialog" aria-modal="true" aria-label={`Тираж ${draw.lottery_name} №${drawNumber(draw.public_number)}`}><button aria-label="Закрыть" className="close" onClick={onClose}>×</button><small>НЕИЗМЕНЯЕМАЯ ЗАПИСЬ ТИРАЖА</small><h2>{draw.lottery_name} №{drawNumber(draw.public_number)}</h2><DrawResult draw={draw} detailed />{draw.is_distribution && <section className="distribution-result" aria-label="Итог распределительного тиража"><h3>Распределительный тираж</h3>{draw.status !== "COMPLETED" ? <p>Распределение назначено. Итог появится после расчёта.</p> : distributed ? <dl className="detail-list"><dt>Распределено из джекпота</dt><dd>{cas(draw.distributed_amount)}</dd><dt>Категория</dt><dd>{draw.distribution_category === "all" ? "Все купленные билеты" : draw.distribution_category?.startsWith("bingo-tour-") ? `Bingo · тур ${draw.distribution_category.slice(-1)}` : displayMatches(draw.lottery_code, Number(draw.distribution_category), draw.winning_numbers?.length === 7, draw.ruleset_code)}</dd><dt>Билетов с долей распределения</dt><dd>{summary?.jackpot_winners ?? "—"}</dd><dt>Обычные призы</dt><dd>{cas(draw.total_payout - (draw.distributed_amount ?? 0))}</dd><dt>Все выплаты</dt><dd>{cas(draw.total_payout)}</dd></dl> : <p>{jackpotWon ? "Полная комбинация угадана — выплачен джекпот." : "Купленных билетов нет — джекпот перенесён дальше."}</p>}</section>}{bingo && draw.status === "COMPLETED" && <section className="bingo-stage-summary">{bingoStages.map((stage, index) => <article key={index}><small>{["РАННЯЯ СТРОКА", "ДВЕ СТРОКИ", "ДЖЕКПОТ", "ПОЛНАЯ КАРТОЧКА · 58"][index]}</small><strong>{stage.winners ? `${stage.winners} бил.` : "Нет победителя"}</strong><span>{stage.firstMove ? `ход ${stage.firstMove} · ${cas(stage.payout)}` : index === 2 ? "Джекпот перенесён" : "Приз не выплачен"}</span></article>)}</section>}{jackpotWon && <div className="jackpot-hit"><small>ДЖЕКПОТ ЭТОГО ТИРАЖА СОРВАН</small><strong>{cas(draw.jackpot_amount)}</strong><span>Эта сумма делится между билетами джекпот-категории. Общая выплата тиража указана отдельно.</span></div>}{jackpotTickets.length > 0 && <section className="jackpot-winners"><h3>{distributed ? "Получатели распределения" : "Кто сорвал джекпот"}</h3>{jackpotTickets.map((ticket) => <article key={ticket.id}><div><small>Билет №{drawNumber(ticket.public_number)}</small><strong>{ticket.player_name ?? "Игрок"}</strong><span>{ticket.player_username ? `@${ticket.player_username}` : "без username"} · TG {ticket.player_telegram_id ?? "—"}</span></div><b>{cas(ticket.prize_amount)}</b><button onClick={() => onOpenPlayer(ticket)}>Открыть игрока →</button></article>)}</section>}<dl className="detail-list"><dt>Статус</dt><dd>{translated(draw.status, drawStatuses)}</dd><dt>По расписанию</dt><dd>{date(draw.scheduled_at)}</dd><dt>Проведён</dt><dd>{date(draw.executed_at)}</dd><dt>Игроков</dt><dd>{participantCount.toLocaleString("ru-RU")}</dd><dt>Билетов</dt><dd>{draw.ticket_count.toLocaleString("ru-RU")}</dd><dt>Выигрышных</dt><dd>{(summary?.winners ?? winningTickets.length).toLocaleString("ru-RU")}</dd><dt>Продажи</dt><dd>{cas(draw.total_sales)}</dd><dt>Все выплаты тиража</dt><dd>{cas(draw.total_payout)}</dd><dt>Джекпот до тиража</dt><dd>{cas(draw.jackpot_opening)}</dd><dt>Джекпот после тиража</dt><dd>{cas(draw.jackpot_closing)}</dd><dt>Использовано из Фонда Каспера</dt><dd>{cas(draw.kasper_fund_used)}</dd></dl><div className="ticket-list-heading"><h3>Билеты · загружено {shownTickets.length}</h3><div><button className={ticketFilter === "winners" ? "active" : ""} onClick={() => chooseFilter("winners")}>Выигрышные · {summary?.winners ?? winningTickets.length}</button><button className={ticketFilter === "all" ? "active" : ""} onClick={() => chooseFilter("all")}>Все · {summary?.total ?? page.items.length}</button><button className={ticketFilter === "jackpot" ? "active" : ""} onClick={() => chooseFilter("jackpot")}>{distributed ? "Распределение" : "Джекпот"} · {summary?.jackpot_winners ?? jackpotTickets.length}</button></div></div>{shownTickets.map((ticket) => <div className={`ticket-row ${bingo ? "bingo-ticket-row" : ""} ${ticket.is_jackpot_winner ? "jackpot-ticket" : ""}`} key={ticket.id}><b>№{drawNumber(ticket.public_number)}</b><span className="ticket-owner"><b>{ticket.player_name ?? "Игрок"}</b><small>{ticket.player_username ? `@${ticket.player_username}` : `TG ${ticket.player_telegram_id ?? "—"}`}</small></span><span>{bingo ? <span className="bingo-ticket-numbers">{[0, 1, 2].map((row) => <i key={row}>{ticket.numbers.slice(row * 4, row * 4 + 4).join(" · ")}</i>)}</span> : ticket.numbers.map((number) => displayNumber(draw.lottery_code, number)).join(" · ")}</span><span>{bingo && ticket.bingo_result ? ticket.bingo_result.moves.map((move, index) => `${["строка", "две", "полный"][index]}: ${move <= 60 ? `ход ${move}` : "не закрыто"}`).join(" · ") : `совпадений: ${displayMatches(draw.lottery_code, ticket.matches, ticket.numbers.length === 7, draw.ruleset_code)}`}</span><strong>{ticket.is_jackpot_winner && <small>{distributed ? "РАСПРЕДЕЛЕНИЕ" : "ДЖЕКПОТ"}</small>}{cas(ticket.prize_amount)}</strong></div>)}{!started && !page.items.length && <button className="player-history-more" onClick={() => chooseFilter(ticketFilter)}>Показать билеты</button>}{pageLoading && <p role="status">Загружаем билеты…</p>}{pageError && <p role="alert">{pageError}<button onClick={() => { if (page.items.length) void loadMore(); else { setPageLoading(true); setPageError(""); setPageRetry(value => value + 1); } }}>Повторить загрузку</button></p>}{page.hasMore && <button className="player-history-more" disabled={pageLoading} onClick={() => void loadMore()}>Загрузить ещё 50 билетов</button>}{started && !pageLoading && !pageError && !shownTickets.length && <p className="source-note">По этому фильтру билетов нет.</p>}</div>;
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

function SectionTabs<T extends string>({ value, items, onChange, label }: { value: T; items: Array<{ id: T; label: string }>; onChange: (value: T) => void; label: string }) {
  return <div className="section-tabs" role="tablist" aria-label={label}>{items.map((item) => <button type="button" role="tab" aria-selected={value === item.id} className={value === item.id ? "active" : ""} key={item.id} onClick={() => onChange(item.id)}>{item.label}</button>)}</div>;
}

function DrawsView({ lotteries, onOpen, scope, onScope, archivedOnly = false }: { lotteries: Lottery[]; onOpen: (id: string) => void; scope: LotteryScope; onScope?: (scope: LotteryScope) => void; archivedOnly?: boolean }) {
  const [period, setPeriod] = useState<"future" | "today" | "completed" | "failed" | "archived" | "distribution">(archivedOnly ? "archived" : "today");
  const [lotteryId, setLotteryId] = useState("");
  const [rows, setRows] = useState<Draw[]>([]);
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const query = useCallback((offset: number) => new URLSearchParams({ scope, period, limit: "100", offset: String(offset), ...(lotteryId ? { lottery_id: lotteryId } : {}) }).toString(), [scope, period, lotteryId]);
  useEffect(() => {
    const current = ++generation.current;
    const timer = window.setTimeout(() => {
      setBusy(true); setRows([]); setError("");
      void adminApi.draws(query(0)).then(data => { if (current === generation.current) { setRows(data); setMore(data.length === 100); } }).catch(() => { if (current === generation.current) setError("Не удалось загрузить тиражи"); }).finally(() => { if (current === generation.current) setBusy(false); });
    }, 0);
    return () => { window.clearTimeout(timer); generation.current = current + 1; };
  }, [query]);
  const next = async () => {
    const current = generation.current; setBusy(true);
    try { const data = await adminApi.draws(query(rows.length)); if (current === generation.current) { setRows(values => [...values, ...data]); setMore(data.length === 100); } }
    catch { if (current === generation.current) setError("Не удалось загрузить следующую страницу"); }
    finally { if (current === generation.current) setBusy(false); }
  };
  return <>{archivedOnly && <section className="archive-command"><div><span>ИСТОРИЯ ФОРМАТОВ</span><h2>Архив завершённых лотерей</h2><p>Здесь старые Daily и версии Fast до обновлений. Откройте любой тираж, чтобы увидеть результат, билеты и выплаты.</p></div></section>}<div className="section-toolbar">{archivedOnly ? <SectionTabs value={scope} label="Тип игр в архиве" items={[{ id: "standard", label: "Daily / остальные" }, { id: "fast", label: "Старые Fast" }, { id: "all", label: "Всё" }]} onChange={onScope ?? (() => undefined)} /> : <SectionTabs value={period} label="Период тиражей" items={[{ id: "future", label: "Будущие" }, { id: "today", label: "Сегодня" }, { id: "completed", label: "Завершённые" }, { id: "distribution", label: "Распределительные" }, { id: "failed", label: "Ошибки" }]} onChange={setPeriod} />}<select aria-label="Лотерея тиражей" value={lotteryId} onChange={e => setLotteryId(e.target.value)}><option value="">Все игры</option>{lotteries.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></div><section className="panel"><header><h2>{archivedOnly ? "Старые форматы и тиражи" : "Тиражи"}</h2><span>ЗАГРУЖЕНО: {rows.length}</span></header>{error && <p role="alert">{error}</p>}{archivedOnly && <div className="archive-table-note">В архив попадают завершённые тиражи неактивных лотерей и предыдущих версий правил. История не удаляется после обновления формата.</div>}<DrawTable draws={rows} onOpen={onOpen} />{busy && <p className="source-note">Загружаем…</p>}{!busy && !rows.length && !error && <p className="source-note">{archivedOnly ? "Архивных тиражей по этому фильтру пока нет." : "В выбранном периоде тиражей нет."}</p>}{more && <button className="draw-load-more" disabled={busy} onClick={() => void next()}>Показать ещё 100</button>}</section></>;
}

function JackpotPanel({ data, analytics, onOpen }: { data: Overview; analytics?: TicketAnalytics; onOpen?: (id: string) => void }) {
  const last = data.jackpots.last_win ?? data.jackpots.history[0];
  const [showHistory, setShowHistory] = useState(false);
  const [lotteryFilter, setLotteryFilter] = useState("");
  const history = data.jackpots.history.filter((event) => !lotteryFilter || event.lottery_code === lotteryFilter);
  return <section className="panel jackpot-command">
    <header><div><h2>Джекпоты</h2><span>За выбранный этап · один сорванный джекпот = один тираж, даже если победителей несколько</span></div></header>
    <div className="metric-grid jackpot-metrics">
      <article className="metric jackpot-count"><small>Всего сорвано джекпотов</small><strong>{data.jackpots.total_wins.toLocaleString("ru-RU")}</strong><em>тиражей с выплатой джекпота</em></article>
      <article className="metric"><small>Общая сумма джекпотов</small><strong>{cas(data.jackpots.total_paid)}</strong><em>действительно выплачено игрокам</em></article>
      <article className="metric latest-jackpot"><small>Последний выигрыш джекпота</small><strong>{last ? cas(last.jackpot_amount) : "Пока не сорван"}</strong><em>{last ? `${last.lottery_name} · ${date(last.occurred_at)} МСК` : "Здесь появится первая выплата"}</em>{last && onOpen && <button className="text-action" onClick={() => onOpen(last.draw_id)}>Тираж {last.draw_number ? `№${drawNumber(last.draw_number)}` : "и билеты"} →</button>}</article>
      <article className="metric"><small>Самый крупный джекпот</small><strong>{cas(data.jackpots.largest_win)}</strong><em>рекорд одного тиража за этап</em></article>
    </div>
    <h3 className="subheading">По каждой лотерее</h3>
    <div className="table-wrap"><table className="jackpot-lotteries"><thead><tr><th>Лотерея</th><th>Сейчас разыгрывается</th><th>Сорвано</th><th>Выплачено за этап</th><th>Последний выигрыш</th>{analytics && <th>Билетов рассчитано</th>}</tr></thead><tbody>{data.jackpots.lotteries.map((row) => {
      const lottery = data.lotteries.find((item) => item.code === row.code);
      const ticketRow = analytics?.lotteries.find((item) => item.lottery_id === (row.lottery_id ?? lottery?.id));
      return <tr key={row.code} className={`lottery-row lottery-${row.code}`}><td><b>{row.name}</b><small>{row.is_active === false ? "В архиве" : ["flash", "shadow", "pulse"].includes(row.code) ? "Fast" : lottery?.kind === "WEEKLY" ? "Еженедельная" : "Ежедневная"}</small></td><td>{data.economy?.scope !== "archive" && lottery?.is_active ? cas(lottery.current_jackpot) : "—"}<small>{data.economy?.scope === "archive" ? "Остаток текущего этапа скрыт" : lottery?.is_active ? date(lottery.next_draw_at) : "Нет продаж"}</small></td><td><b className="win-count">{row.win_count}</b></td><td>{cas(row.total_paid)}</td><td>{row.last_win_amount != null ? <><b>{cas(row.last_win_amount)}</b><small>{date(row.last_win_at)} МСК</small>{row.last_draw_id && onOpen && <button className="text-action" onClick={() => onOpen(row.last_draw_id!)}>Открыть тираж №{drawNumber(row.last_draw_number ?? 0)} →</button>}</> : row.win_count ? <span>Сумма недоступна<small>{date(row.last_win_at)}</small></span> : <span className="muted">Ещё не сорван</span>}</td>{analytics && <td>{ticketRow?.settled_tickets.toLocaleString("ru-RU") ?? "—"}<small>{ticketRow?.active_tickets.toLocaleString("ru-RU") ?? "—"} активных сейчас</small></td>}</tr>;
    })}</tbody></table></div>
    <p className="source-note">Сумма джекпота относится ко всему тиражу и может делиться между несколькими билетами. Количество билетов помогает сравнить объём участия; прошлые выигрыши не определяют следующий результат.</p>
    <button className="history-toggle" aria-expanded={showHistory} onClick={() => setShowHistory((value) => !value)}>{showHistory ? "Скрыть историю джекпотов" : `Показать последние выигрыши (${data.jackpots.history.length})`} <span>{showHistory ? "−" : "+"}</span></button>
    {showHistory && <div className="jackpot-history"><label>Лотерея в истории джекпотов<select value={lotteryFilter} onChange={(event) => setLotteryFilter(event.target.value)}><option value="">Все лотереи</option>{data.jackpots.lotteries.map((lottery) => <option key={lottery.code} value={lottery.code}>{lottery.name}</option>)}</select></label><p className="source-note">Последние 50 джекпотов выбранного раздела. Итоги выше учитывают выбранный этап экономики.</p><div className="table-wrap"><table><thead><tr><th>Дата, МСК</th><th>Лотерея / тираж</th><th>Джекпот этого тиража</th><th>Выигрышных билетов</th><th>Игроков-победителей</th></tr></thead><tbody>{history.map((row) => <tr key={row.id}><td>{date(row.occurred_at)}</td><td>{onOpen ? <button className="text-action" onClick={() => onOpen(row.draw_id)}>{row.lottery_name} {row.draw_number ? `№${drawNumber(row.draw_number)}` : "→"}</button> : row.lottery_name}</td><td className="positive">{cas(row.jackpot_amount)}</td><td>{row.winner_ticket_count}</td><td>{row.winner_user_count}</td></tr>)}</tbody></table></div>{!history.length && <p className="source-note">В показанной части истории нет джекпотов этой лотереи.</p>}</div>}
  </section>;
}

function AnalyticsView({ tab, onTab, dashboard, analytics, lotteries, statistics, selectedLotteryId, windowSize, onLottery, onWindow }: { tab: AnalyticsTab; onTab: (tab: AnalyticsTab) => void; dashboard: Overview; analytics: TicketAnalytics; lotteries: Lottery[]; statistics: NumberStatisticsReport | null; selectedLotteryId: string; windowSize: number; onLottery: (id: string) => void; onWindow: (size: number) => void }) {
  const jackpotById = new Map(dashboard.jackpots.lotteries.map((row) => [row.lottery_id ?? dashboard.lotteries.find((item) => item.code === row.code)?.id, row]));
  const rows = analytics.lotteries.map((row) => ({ ...row, jackpot: jackpotById.get(row.lottery_id ?? undefined) }));
  const fast = rows.filter((row) => ["flash", "shadow", "pulse"].includes(row.jackpot?.code ?? ""));
  const regular = rows.filter((row) => !fast.includes(row));
  const renderComparison = (items: typeof rows, title: string) => <section className="panel analytics-panel"><header><h2>{title}</h2><span>ФАКТИЧЕСКАЯ ИСТОРИЯ</span></header><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Тиражей с джекпотом</th><th>Билеты / выигрышные</th><th>Выигрышных билетов</th><th>Потрачено</th><th>Выплачено</th><th>Выплаты / покупки</th><th>Крупнейший джекпот</th></tr></thead><tbody>{items.map((row) => <tr key={row.lottery_id}><td><b>{row.lottery_name}</b></td><td>{row.jackpot?.win_count ?? 0}</td><td>{row.settled_tickets.toLocaleString("ru-RU")} / {row.winning_tickets.toLocaleString("ru-RU")}</td><td>{percentage(row.winning_tickets, row.settled_tickets)}</td><td>{compactCas(row.total_sales)}</td><td>{compactCas(row.total_payout)}</td><td>{percentage(row.total_payout, row.total_sales)}</td><td>{compactCas(row.jackpot?.largest_win ?? 0)}</td></tr>)}</tbody></table></div></section>;
  return <>
    <SectionTabs value={tab} label="Разделы аналитики" items={[{ id: "lotteries", label: "Лотереи" }, { id: "tickets", label: "Билеты" }, { id: "numbers", label: "Числа" }, { id: "finances", label: "Финансы" }]} onChange={onTab} />
    {tab === "lotteries" && <>{fast.length > 0 && renderComparison(fast, "Fast: результаты этапа")}{renderComparison(regular, "Daily, Weekly и Special")}</>}
    {tab === "tickets" && <TicketAnalyticsView data={analytics} />}
    {tab === "numbers" && statistics && <StatisticsView lotteries={lotteries} report={statistics} selectedLotteryId={selectedLotteryId} windowSize={windowSize} onLottery={onLottery} onWindow={onWindow} />}
    {tab === "numbers" && !statistics && <div className="loading">ЗАГРУЖАЕМ СТАТИСТИКУ ЧИСЕЛ…</div>}
    {tab === "finances" && <JackpotPanel data={dashboard} />}
  </>;
}

function OperationalLog({ transactions, notifications, audit, dashboard, onOpenPlayer }: { transactions: Transaction[]; notifications: NotificationItem[]; audit: AuditEntry[]; dashboard: Dashboard | null; onOpenPlayer: (userId: string) => void }) {
  const [source, setSource] = useState<"all" | "money" | "draw" | "admin" | "notification">("all");
  const [search, setSearch] = useState("");
  const entries = [
    ...transactions.map((item) => ({ id: `money-${item.id}`, source: "money" as const, at: item.created_at, level: "info", title: translated(item.type, transactionTypes), detail: `${item.amount > 0 ? "+" : ""}${cas(item.amount)} · ${translated(item.account_kind, accountKinds)}`, link: item.draw_id, userId: item.user_id })),
    ...notifications.map((item) => ({ id: `notification-${item.id}`, source: "notification" as const, at: item.created_at, level: (item.status === "FAILED" || item.status === "UNCERTAIN") ? "error" : item.status === "PENDING" ? "warn" : "info", title: `Уведомление: ${translated(item.type, notificationTypes)}`, detail: `${translated(item.status, { PENDING: "ожидает", PROCESSING: "отправляется", SENT: "доставлено", FAILED: "ошибка", CANCELLED: "отменено", UNCERTAIN: "результат отправки неизвестен" })}${item.last_error ? ` · ${item.last_error}` : ""}`, link: null, userId: item.user_id })),
    ...audit.map((item) => ({ id: `admin-${item.id}`, source: "admin" as const, at: item.created_at, level: "warn", title: translated(item.action, auditActions), detail: `${translated(item.entity_type, entityTypes)} · ${item.reason ?? "без комментария"}`, link: null, userId: null })),
    ...(dashboard?.recent_draws ?? []).map((item) => ({ id: `draw-${item.id}`, source: "draw" as const, at: item.executed_at ?? item.scheduled_at, level: (item.status === "FAILED" || item.status === "UNCERTAIN") ? "error" : "info", title: `${item.lottery_name} №${drawNumber(item.public_number)}`, detail: `${translated(item.status, drawStatuses)} · ${item.ticket_count} бил. · продажи ${cas(item.total_sales)} · выплаты ${cas(item.total_payout)}`, link: item.id, userId: null })),
  ].sort((left, right) => new Date(right.at).getTime() - new Date(left.at).getTime());
  const normalized = search.trim().toLocaleLowerCase("ru-RU");
  const visible = entries.filter((entry) => (source === "all" || entry.source === source) && (!normalized || `${entry.title} ${entry.detail} ${entry.userId ?? ""}`.toLocaleLowerCase("ru-RU").includes(normalized)));
  const sourceLabels = { money: "CAS", draw: "Тираж", admin: "Админ", notification: "Уведомление" };
  return <section className="panel operational-log"><header><div><h2>Лента событий</h2><span>Деньги, тиражи, действия администратора и доставка сообщений в одном месте</span></div><b>{visible.length} записей</b></header><div className="log-controls"><input aria-label="Поиск в логах" placeholder="Найти событие, игрока или ошибку" value={search} onChange={(event) => setSearch(event.target.value)} /><div>{(["all", "money", "draw", "admin", "notification"] as const).map((item) => <button className={source === item ? "active" : ""} key={item} onClick={() => setSource(item)}>{item === "all" ? "Все" : sourceLabels[item]}</button>)}</div></div><div className="event-log">{visible.map((entry) => <article className={entry.level} key={entry.id}><time>{date(entry.at)}</time><span className={`log-source ${entry.source}`}>{sourceLabels[entry.source]}</span><div><b>{entry.title}</b><p>{entry.detail}</p>{entry.userId && <button className="transaction-player-link" onClick={() => onOpenPlayer(entry.userId!)}>Игрок · {entry.userId.slice(0, 8)}…</button>}</div></article>)}</div>{!visible.length && <p className="source-note">По этому фильтру событий нет.</p>}</section>;
}

function SystemView({ tab, onTab, transactions, notifications, audit, onTransactions, onOpenPlayer, dashboard, releaseNotes }: { dashboard: Dashboard | null; releaseNotes: { changelog: ReleaseNote[]; devlog: ReleaseNote[] }; tab: SystemTab; onTab: (tab: SystemTab) => void; transactions: Transaction[]; notifications: NotificationItem[]; audit: AuditEntry[]; onTransactions: (query: string) => void; onOpenPlayer: (userId: string) => void }) {
  return <>
    <SectionTabs value={tab} label="Системные журналы" items={[{ id: "events", label: "Лента событий" }, { id: "health", label: "Состояние" }, { id: "ledger", label: "Журнал CAS" }, { id: "notifications", label: "Уведомления" }, { id: "audit", label: "Аудит действий" }, { id: "development", label: "Разработка" }, { id: "formats", label: "История форматов" }]} onChange={onTab} />
    {tab === "events" && <OperationalLog transactions={transactions} notifications={notifications} audit={audit} dashboard={dashboard} onOpenPlayer={onOpenPlayer} />}
    {tab === "health" && dashboard && <><SystemHealth data={dashboard} /><OperationalMonitor /></>}
    {tab === "development" && <DevelopmentView changelog={releaseNotes.changelog} devlog={releaseNotes.devlog} />}
    {tab === "ledger" && <><TransactionFilters onApply={onTransactions} /><section className="panel"><header><div><h2>Неизменяемый журнал CAS</h2><small>Нажмите ID игрока, чтобы открыть его историю</small></div><span>ЗАПИСЕЙ: {transactions.length}</span></header><TransactionTable rows={transactions} onOpenPlayer={onOpenPlayer} /></section></>}
    {tab === "notifications" && <section className="panel"><header><h2>Очередь уведомлений</h2><span>ДОСТАВЛЕНО · ОШИБКА · ОЖИДАЕТ</span></header><div className="table-wrap"><table><thead><tr><th>Создано</th><th>Тип и что произошло</th><th>Игрок</th><th>Статус</th><th>Попытки</th><th>Ключ события</th></tr></thead><tbody>{notifications.map((item) => <tr key={item.id}><td>{date(item.created_at)}</td><td><b>{translated(item.type, notificationTypes)}</b><small>{notificationDetail(item)}</small></td><td><code>{item.user_id.slice(0, 8)}</code></td><td><span className={`tag ${item.status.toLowerCase()}`}>{translated(item.status, { PENDING: "ожидает", PROCESSING: "отправляется", SENT: "доставлено", FAILED: "ошибка", CANCELLED: "отменено", UNCERTAIN: "результат отправки неизвестен" })}</span></td><td>{item.attempts}</td><td><code>{item.event_key}</code></td></tr>)}</tbody></table></div></section>}
    {tab === "audit" && <section className="panel"><header><h2>Аудит действий администратора</h2><span>ХРАНИТСЯ ПОСТОЯННО</span></header><div className="audit-list">{audit.map((item) => <article key={item.id}><time>{date(item.created_at)}</time><b>{translated(item.action, auditActions)} · {translated(item.entity_type, entityTypes)}</b><p>{item.reason ?? "Причина не указана"}</p><code>{JSON.stringify(item.old_values)} → {JSON.stringify(item.new_values)}</code></article>)}</div></section>}
  </>;
}

function KasperLiveAdmin({ data, game = "kasper-live" }: { data: KasperLiveSummary; game?: string }) {
  return <section className="kasper-live-admin">
    <header><small>МГНОВЕННАЯ ЛОТЕРЕЯ</small><h2>{game === "vault" ? "Casper Vault" : game === "aurora" ? "Casper Aurora" : "Casper LIVE"}</h2><p>Только общий итог. Данные игроков в этом разделе не показываются.</p></header>
    <div className="kasper-live-admin-grid">
      <article><span>КОЛИЧЕСТВО БИЛЕТОВ</span><strong>{data.ticket_count.toLocaleString("ru-RU")}</strong></article>
      <article><span>ВЫИГРЫШИ</span><strong>{data.winning_tickets.toLocaleString("ru-RU")}</strong></article>
      <article><span>ПРОИГРЫШИ</span><strong>{data.losing_tickets.toLocaleString("ru-RU")}</strong></article>
      <article><span>РЕЗУЛЬТАТ</span><strong className={data.result >= 0 ? "positive" : "negative"}>{data.result >= 0 ? "+" : "−"}{cas(Math.abs(data.result))}</strong></article>
    </div>
  </section>;
}

export default function App() {
  const [economyMode, setEconomyMode] = useState<"current" | "archive">("current");
  const [session, setSession] = useState<AdminSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [view, setView] = useState<View>(storedView);
  const [loadedSection, setLoadedSection] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<Overview | null>(null);
  const [technicalDashboard, setTechnicalDashboard] = useState<Dashboard | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [playerSearch, setPlayerSearch] = useState("");
  const [lotteries, setLotteries] = useState<Lottery[]>([]);
  const [scope, setScope] = useState<LotteryScope>("all");
  const [archiveScope, setArchiveScope] = useState<LotteryScope>("all");
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
  const [instantGame, setInstantGame] = useState<InstantGame>(storedInstantGame);
  const [kasperLive, setKasperLive] = useState<KasperLiveSummary | null>(null);
  const [analyticsTab, setAnalyticsTab] = useState<AnalyticsTab>("lotteries");
  const [systemTab, setSystemTab] = useState<SystemTab>(() => window.location.pathname === "/development" ? "development" : window.location.pathname === "/archive" ? "formats" : "health");
  const [managementOpen, setManagementOpen] = useState(() => navigation.some(item => item.id === storedView() && item.group === "manage"));
  const [loadedAt, setLoadedAt] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const loadGeneration = useRef(0);
  const applyPlayerResults = useCallback((rows: Player[]) => setPlayers(rows), []);

  const navigate = useCallback((target: View) => {
    window.localStorage.setItem(viewStorageKey, target);
    window.history.pushState({}, "", target === "dashboard" ? "/" : `/${target}`);
    loadGeneration.current += 1;
    setDrawDetail(null);
    if (navigation.find(item => item.id === target)?.group === "manage") setManagementOpen(true);
    setView(target);
  }, []);

  useEffect(() => { setEconomyScope("current"); adminApi.session().then(setSession).catch(() => setSession(null)).finally(() => setChecking(false)); }, []);
  useEffect(() => {
    const restore = () => { setView(storedView()); setInstantGame(storedInstantGame()); };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  const load = useCallback(async (target: View, silent = false) => {
    const generation = ++loadGeneration.current;
    const apply = (update: () => void) => { if (generation === loadGeneration.current) update(); };
    if (!silent) setLoading(true);
    setRefreshing(true);
    setError("");
    try {
      if (target === "dashboard") {
        const [dashboardData, analyticsData] = await Promise.all([adminApi.overview("all"), adminApi.ticketAnalytics("all")]);
        apply(() => { setDashboard(dashboardData); });
        apply(() => { setTicketAnalytics(analyticsData); });
      }
      if (target === "fast") {
        const [dashboardData, analyticsData] = await Promise.all([adminApi.overview("fast"), adminApi.ticketAnalytics("fast")]);
        apply(() => { setDashboard(dashboardData); setTicketAnalytics(analyticsData); });
      }
      if (target === "instant") {
        const fetchSummary = instantGame === "vault" ? adminApi.vault : instantGame === "aurora" ? adminApi.aurora : adminApi.kasperLive;
        const data = await fetchSummary(); apply(() => setKasperLive(data));
      }
      if (target === "players") { const rows = await adminApi.players(); apply(() => setPlayers(rows)); }
      if (target === "lotteries") { const rows = await adminApi.lotteries(); apply(() => setLotteries(rows)); }
      if (target === "schedule") {
        const [entries, available] = await Promise.all([adminApi.schedule(scope), adminApi.lotteries()]);
        apply(() => { setScheduleEntries(entries); });
        apply(() => { setLotteries(available); });
        apply(() => { setScheduleLoadedAt(Date.now()); });
      }
      if (target === "draws") {
        const available = await adminApi.lotteries();
        apply(() => { setLotteries(available); });
      }
      if (target === "jackpots") { const data = await adminApi.overview(scope); apply(() => setDashboard(data)); }
      if (target === "tickets") { const [rows, available] = await Promise.all([adminApi.ticketAnalytics(scope), adminApi.lotteries()]); apply(() => { setTicketAnalytics(rows); setLotteries(available); }); }
      if (target === "archive") { const available = await adminApi.lotteries(); apply(() => setLotteries(available)); }
      if (target === "system") {
        if (systemTab === "formats") { const available = await adminApi.lotteries(); apply(() => setLotteries(available)); }
        if (systemTab === "events" || systemTab === "ledger") {
          const rows = await adminApi.transactions(); apply(() => setTransactions(rows));
        }
        if (systemTab === "events" || systemTab === "notifications") {
          const rows = await adminApi.notifications(); apply(() => setNotifications(rows));
        }
        if (systemTab === "events" || systemTab === "audit") {
          const rows = await adminApi.audit(); apply(() => setAudit(rows));
        }
        if (systemTab === "events" || systemTab === "health") {
          const data = await adminApi.dashboard(); apply(() => setTechnicalDashboard(data));
        }
        if (systemTab === "development") {
          const [changelog, devlog] = await Promise.all([adminApi.releaseNotes("changelog"), adminApi.releaseNotes("devlog")]);
          apply(() => setReleaseNotes({ changelog, devlog }));
        }
      }
      if (target === "analytics") {
        const [available, dashboardData, analyticsData] = await Promise.all([adminApi.lotteries(), adminApi.overview(scope), adminApi.ticketAnalytics(scope)]);
        apply(() => { setLotteries(available); });
        apply(() => { setDashboard(dashboardData); });
        apply(() => { setTicketAnalytics(analyticsData); });
        const scoped = available.filter(l => l.code !== "bingo" && (scope === "all" || ["flash", "shadow", "pulse"].includes(l.code) === (scope === "fast")));
        apply(() => setStatisticsLotteryId(current => scoped.some(l => l.id === current) ? current : scoped[0]?.id || ""));
      }
      apply(() => { setLoadedAt(Date.now()); setLoadedSection(`${target}:${scope}:${instantGame}:${systemTab}:${economyMode}`); });
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) setSession(null);
      apply(() => setError(reason instanceof Error ? reason.message : "Не удалось выполнить запрос администратора."));
    } finally { apply(() => { setLoading(false); setRefreshing(false); }); }
  }, [scope, instantGame, systemTab, economyMode]);

  useEffect(() => {
    if (!session) return;
    const task = window.setTimeout(() => void load(view), 0);
    return () => { window.clearTimeout(task); loadGeneration.current += 1; };
  }, [session, view, load]);


  useEffect(() => {
    if (!session || view !== "analytics" || analyticsTab !== "numbers" || !statisticsLotteryId) return;
    let current = true;
    void adminApi.statistics(statisticsLotteryId, statisticsWindow).then(report => { if (current) setStatistics(report); })
      .catch((reason: Error) => { if (current) setError(reason.message); });
    return () => { current = false; };
  }, [session, view, analyticsTab, statisticsLotteryId, statisticsWindow, loadedAt, scope, economyMode]);

  const openDraw = (id: string) => { const generation = loadGeneration.current; void adminApi.draw(id).then(detail => { if (generation === loadGeneration.current) setDrawDetail(detail); }).catch((reason: Error) => { if (generation === loadGeneration.current) setError(reason.message); }); };
  const openPlayerFromTicket = (ticket: DrawDetail["tickets"][number]) => {
    setPlayerSearch(ticket.player_username ?? String(ticket.player_telegram_id ?? ticket.user_id));
    setDrawDetail(null);
    navigate("players");
  };
  const openPlayerById = (userId: string) => { setPlayerSearch(userId); navigate("players"); };

  if (checking) return <main className="boot">CASPER LOTO // ПРОВЕРКА СЕССИИ</main>;
  if (!session) return <Login onAuthenticated={setSession} />;

  const visibleLotteries = lotteries.filter(l => scope === "all" || ["flash", "shadow", "pulse"].includes(l.code) === (scope === "fast"));
  const ready = !loading && loadedSection === `${view}:${scope}:${instantGame}:${systemTab}:${economyMode}`;
  const title = navigation.find((item) => item.id === view)?.label ?? "Управление";
  return <div className={`admin-shell ${view === "fast" ? "fast-admin" : ""}`}>
    <aside><div className="brand"><img alt="Casper Loto" src={logoHorizontal} /><small>Панель владельца</small></div>
      <nav aria-label="Основные разделы"><span className="nav-caption">ГЛАВНОЕ</span>{navigation.filter(item => item.group === "main").map(item => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => navigate(item.id)}>{item.label}</button>)}</nav>
      <details className="management-nav" open={managementOpen} onToggle={event => setManagementOpen(event.currentTarget.open)}><summary>Управление</summary><nav aria-label="Управление">{navigation.filter(item => item.group === "manage").map(item => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => navigate(item.id)}>{item.label}</button>)}</nav></details>
      <nav className="utility-nav" aria-label="Служебные разделы"><button className={view === "system" ? "active" : ""} onClick={() => navigate("system")}>Система</button><button className={economyMode === "archive" ? "active" : ""} onClick={() => {
        const mode = economyMode === "current" ? "archive" : "current";
        setEconomyScope(mode); loadGeneration.current += 1; setLoadedSection(""); setDrawDetail(null); setStatistics(null);
        setEconomyMode(mode); navigate("dashboard");
      }}>{economyMode === "archive" ? "Вернуться к новой экономике" : "Архив старой экономики"}</button></nav>
      <div className="operator"><small>ВЛАДЕЛЕЦ</small><b>{session.username}</b><button onClick={() => void adminApi.logout().finally(() => setSession(null))}>Выйти</button></div>
    </aside>
    <main className="workspace" key={economyMode}>
      {economyMode === "archive" && <div className="banner">Архив старой экономики · Только просмотр. Переключай разделы меню, чтобы посмотреть старые показатели, тиражи и билеты.</div>}<header className="topbar"><div><small>Casper Loto · управление</small><h1>{title}</h1></div><div className="refresh-control"><span>{loadedAt ? `Обновлено ${date(new Date(loadedAt).toISOString())} МСК` : "Загружаем данные"}</span>{view !== "publications" && <button disabled={loading || refreshing} onClick={() => void load(view, true)}>{refreshing ? "Обновляем…" : "Обновить данные"}</button>}</div></header>
      <div className={`economy-context ${economyMode}`}><span className="context-dot" /><strong>{economyMode === "archive" ? "Архив старой экономики" : "Новый этап экономики"}</strong><span>{economyMode === "current" && dashboard?.economy?.started_at ? `С ${date(dashboard.economy.started_at)} МСК` : "Статистика выбранного этапа"}</span>{economyMode === "current" && dashboard?.economy?.paused && <b>Приложение на паузе</b>}</div>
      {["lotteries", "schedule", "draws", "jackpots", "analytics", "tickets"].includes(view) && <div className="scope-toolbar"><SectionTabs label="Тип игр" value={scope} items={[{ id: "standard", label: "Лотереи" }, { id: "fast", label: "Fast" }, { id: "all", label: "Всё" }]} onChange={value => { setStatistics(null); setScope(value); }} /><p>{scope === "standard" ? "Обычные лотереи. Быстрые тиражи и их выигрыши — в Fast." : scope === "fast" ? "Только быстрые игры: FLASH, CODE и PULSE." : "Полная картина: обычные лотереи и Fast вместе."} Игроки и Фонд Каспера общие.</p></div>}
      {error && <div className="error banner" role="alert">{error}</div>}{(loading || (!ready && !error)) && <div className="loading">ЗАГРУЖАЕМ ДАННЫЕ…</div>}
      {ready && view === "dashboard" && dashboard && ticketAnalytics && <DashboardView data={dashboard} analytics={ticketAnalytics} refreshedAt={loadedAt} onOpen={openDraw} onNavigate={(target) => { if (target === "system") setSystemTab("health"); navigate(target); }} />}
      {ready && view === "economy" && <EconomyPanel refreshedAt={loadedAt} />}
      {ready && view === "tickets" && ticketAnalytics && <><TicketAnalyticsView data={ticketAnalytics} /><section className="ticket-shortcuts"><div><h2>Найти конкретный билет</h2><p>Открой тираж или историю игрока: внутри доступны номера билетов, комбинации и выплаты.</p></div><button onClick={() => navigate("players")}>Билеты игрока →</button></section><DrawsView key={`tickets-${scope}-${loadedAt}`} scope={scope} lotteries={visibleLotteries} onOpen={openDraw} /></>}
      {ready && view === "fast" && dashboard && ticketAnalytics && <FastDashboard data={dashboard} analytics={ticketAnalytics} refreshedAt={loadedAt} onOpen={openDraw} />}
      {ready && view === "jackpots" && dashboard && <><JackpotPanel data={dashboard} onOpen={openDraw} /><FullJackpotHistory scope={scope} refreshedAt={loadedAt} onOpen={openDraw} /></>}
      {ready && view === "archive" && <DrawsView key={`archive-${archiveScope}-${loadedAt}`} archivedOnly lotteries={lotteries} onOpen={openDraw} scope={archiveScope} onScope={setArchiveScope} />}
      {ready && view === "distribution" && <DistributionDraws key={loadedAt} onOpen={openDraw} />}
      {view === "instant" && <SectionTabs value={instantGame} label="Моментальные лотереи" items={[{ id: "kasper-live", label: "Casper LIVE" }, { id: "aurora", label: "Casper Aurora" }, { id: "vault", label: "Casper Vault" }]} onChange={(game) => { if (game === instantGame) return; loadGeneration.current += 1; setKasperLive(null); setInstantGame(game); window.history.pushState({}, "", `/instant?game=${game}`); }} />}
      {ready && view === "instant" && kasperLive && <KasperLiveAdmin data={kasperLive} game={instantGame} />}
      {ready && view === "players" && <PlayersView players={players} search={playerSearch} onSearch={setPlayerSearch} onResults={applyPlayerResults} onReload={() => load("players")} />}
      {ready && view === "lotteries" && <section className="stack">{visibleLotteries.filter((lottery) => lottery.is_active).map((lottery) => <LotteryCard key={lottery.id} lottery={lottery} onSaved={() => load("lotteries")} />)}</section>}
      {ready && view === "schedule" && <ScheduleView key={scope} entries={scheduleEntries} lotteries={visibleLotteries} loadedAt={scheduleLoadedAt} />}
      {ready && view === "draws" && <DrawsView key={`${scope}-${loadedAt}`} scope={scope} lotteries={visibleLotteries} onOpen={openDraw} />}
      {ready && view === "analytics" && dashboard && ticketAnalytics && <AnalyticsView tab={analyticsTab} onTab={setAnalyticsTab} dashboard={dashboard} analytics={ticketAnalytics} lotteries={visibleLotteries} statistics={statistics} selectedLotteryId={statisticsLotteryId} windowSize={statisticsWindow} onLottery={id => { setStatistics(null); setStatisticsLotteryId(id); }} onWindow={size => { setStatistics(null); setStatisticsWindow(size); }} />}
      {ready && view === "publications" && <p>Раздел публикаций отключён.</p>}
      {ready && view === "system" && <SystemView key={loadedAt} dashboard={technicalDashboard} releaseNotes={releaseNotes} tab={systemTab} onTab={setSystemTab} transactions={transactions} notifications={notifications} audit={audit} onTransactions={(query) => void adminApi.transactions(query).then(setTransactions).catch((reason: Error) => setError(reason.message))} onOpenPlayer={openPlayerById} />}
      {ready && view === "system" && systemTab === "formats" && <DrawsView key={`formats-${archiveScope}-${loadedAt}`} archivedOnly lotteries={lotteries} onOpen={openDraw} scope={archiveScope} onScope={setArchiveScope} />}
    </main>{drawDetail && <DrawDetailPanel key={drawDetail.draw.id} detail={drawDetail} onClose={() => setDrawDetail(null)} onOpenPlayer={openPlayerFromTicket} />}
  </div>;
}

function percentage(part: number, total: number): string {
  return total ? `${((part / total) * 100).toLocaleString("ru-RU", { maximumFractionDigits: 2 })}%` : "0%";
}

function TicketAnalyticsView({ data }: { data: TicketAnalytics }) {
  const overall = data.overall;
  return <>
    <section className="metric-grid analytics-metrics">
      <article className="metric"><small>ВСЕГО БИЛЕТОВ</small><strong>{overall.total_tickets.toLocaleString("ru-RU")}</strong></article>
      <article className="metric"><small>РАССЧИТАНО</small><strong>{overall.settled_tickets.toLocaleString("ru-RU")}</strong></article>
      <article className="metric"><small>ВЫИГРЫШНЫЕ БИЛЕТЫ</small><strong>{overall.winning_tickets.toLocaleString("ru-RU")}</strong><em>{percentage(overall.winning_tickets, overall.settled_tickets)} от рассчитанных</em></article>
      <article className="metric"><small>ВЫПЛАЧЕНО</small><strong>{cas(overall.total_payout)}</strong><em>{percentage(overall.total_payout, overall.total_sales)} от продаж</em></article>
    </section>
    <section className="panel analytics-panel"><header><h2>Результаты по каждой лотерее</h2><span>Доля выигрышных билетов среди рассчитанных</span></header><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Билеты</th><th>Рассчитано</th><th>Выигрышные</th><th>Доля выигрышных</th><th>Потрачено</th><th>Выплачено</th></tr></thead><tbody>{data.lotteries.map((row) => <tr key={row.lottery_id}><td><b>{row.lottery_name}</b><small>{row.is_active ? "активна" : "архивная"}</small></td><td>{row.total_tickets.toLocaleString("ru-RU")}<small>{row.active_tickets.toLocaleString("ru-RU")} активных</small></td><td>{row.settled_tickets.toLocaleString("ru-RU")}</td><td className={row.winning_tickets ? "positive" : ""}>{row.winning_tickets.toLocaleString("ru-RU")}</td><td><b>{percentage(row.winning_tickets, row.settled_tickets)}</b></td><td>{compactCas(row.total_sales)}</td><td>{compactCas(row.total_payout)}<small>{percentage(row.total_payout, row.total_sales)} возврата</small></td></tr>)}</tbody></table></div><p className="source-note">«Доля выигрышных» показывает долю выигрышных билетов в уже завершённых тиражах, а не обещание будущего выигрыша. Так видно, где по реальной истории выигрывали чаще и сколько CAS возвращалось игрокам.</p></section>
  </>;
}

function TransactionFilters({ onApply }: { onApply: (query: string) => void }) {
  const [values, setValues] = useState({ type: "", user_id: "", lottery_id: "", draw_id: "", ticket_id: "", date_from: "", date_to: "" });
  const apply = (event: FormEvent) => { event.preventDefault(); const params = new URLSearchParams(); Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, key.startsWith("date_") ? new Date(value).toISOString() : value); }); onApply(params.toString()); };
  const fields: Record<string, string> = { user_id: "ID игрока", lottery_id: "ID лотереи", draw_id: "ID тиража", ticket_id: "ID билета" };
  return <form className="filters" onSubmit={apply}><select aria-label="Тип операции" value={values.type} onChange={(e) => setValues({ ...values, type: e.target.value })}><option value="">Все типы операций</option>{Object.keys(transactionTypes).map((type) => <option key={type} value={type}>{transactionTypes[type]}</option>)}</select>{Object.entries(fields).map(([key, label]) => <input key={key} placeholder={label} value={values[key as keyof typeof values]} onChange={(e) => setValues({ ...values, [key]: e.target.value })} />)}<input aria-label="Начальная дата" type="datetime-local" value={values.date_from} onChange={(e) => setValues({ ...values, date_from: e.target.value })} /><input aria-label="Конечная дата" type="datetime-local" value={values.date_to} onChange={(e) => setValues({ ...values, date_to: e.target.value })} /><button>ПРИМЕНИТЬ ФИЛЬТРЫ</button></form>;
}

function StatisticsView({ lotteries, report, selectedLotteryId, windowSize, onLottery, onWindow }: { lotteries: Lottery[]; report: NumberStatisticsReport; selectedLotteryId: string; windowSize: number; onLottery: (id: string) => void; onWindow: (size: number) => void }) {
  const eligibleLotteries = lotteries.filter((lottery) => lottery.code !== "bingo");
  const selectedLottery = eligibleLotteries.find((lottery) => lottery.id === selectedLotteryId);
  const numberLabel = (number: number) => displayNumber(selectedLottery?.code ?? "", number);
  const ranked = [...report.numbers].sort((left, right) => right.appearances - left.appearances || left.number - right.number);
  const hottest = ranked[0];
  const coldest = ranked.at(-1);
  const windowLabel = windowSize === 0 ? "все доступные" : `последние ${windowSize}`;
  return <>
    <section className="statistics-brief">
      <div><span>История выпадений</span><h2>{report.lottery_name}</h2><p>Статистика показана для выбранного этапа экономики. История тиражей и их номера сохранены.</p></div>
      <article><small>УЧТЕНО ТИРАЖЕЙ</small><strong>{report.draw_count}</strong><span>{windowLabel}</span></article>
      <article><small>ЧАЩЕ ВСЕГО</small><strong>{hottest?.appearances ? numberLabel(hottest.number) : "—"}</strong><span>{hottest?.appearances ? `${hottest.appearances} выпадений` : "данные накапливаются"}</span></article>
      <article><small>РЕЖЕ ВСЕГО</small><strong>{coldest?.appearances || report.draw_count ? coldest ? numberLabel(coldest.number) : "—" : "—"}</strong><span>{coldest ? `${coldest.appearances} выпадений` : "данные накапливаются"}</span></article>
    </section>
    <section className="panel statistics-panel"><header><div><h2>Выпавшие числа</h2><span>{report.draw_count ? `${date(report.first_draw_at)} — ${date(report.last_draw_at)}` : "ПОКА НЕТ ЗАВЕРШЁННЫХ ТИРАЖЕЙ В ПЕРИОДЕ"}</span></div><div className="statistics-controls"><select aria-label="Лотерея" value={selectedLotteryId} onChange={(e) => onLottery(e.target.value)}>{eligibleLotteries.map((lottery) => <option value={lottery.id} key={lottery.id}>{lottery.name}</option>)}</select><select aria-label="Количество тиражей" value={windowSize} onChange={(e) => onWindow(Number(e.target.value))}><option value={0}>Все</option><option value={10}>10 тиражей</option><option value={20}>20 тиражей</option><option value={50}>50 тиражей</option><option value={100}>100 тиражей</option></select></div></header><div className="stat-grid">{report.numbers.map((row) => <article key={row.number}><i>{numberLabel(row.number)}</i><strong>{row.appearances}</strong><small>выпадений</small><div style={{ "--value": `${row.draw_percentage}%` } as CSSProperties}><span /></div><em>{row.draw_percentage}% тиражей</em><b>{row.draws_since_last === null ? "ещё не выпадало" : row.draws_since_last === 0 ? "в последнем тираже" : `${row.draws_since_last} тир. назад`}</b></article>)}</div><p className="source-note">Для Casper Grand символ ★ обозначает специальное поле. Bingo здесь не показывается: в нём важен порядок закрытия строк, а не частота почти всех 60 шаров. Частота чисел нужна только для наблюдения за историей и не повышает вероятность следующего результата.</p></section>
  </>;
}
