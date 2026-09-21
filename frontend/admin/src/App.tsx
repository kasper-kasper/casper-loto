import type { LotteryScope } from "./api";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import { ApiError, adminApi } from "./api";
import type {
  ActivityPoint,
  AdminSession,
  AuditEntry,
  Dashboard,
  Draw,
  DrawDetail,
  InterestingFact,
  InterestingFactStatus,
  Lottery,
  NumberStatisticsReport,
  NotificationItem,
  Player,
  ReleaseNote,
  ScheduleEntry,
  TicketAnalytics,
  Transaction,
} from "./types";

type View = "dashboard" | "fast" | "lotteries" | "schedule" | "draws" | "players" | "analytics" | "facts" | "broadcast" | "system";
type AnalyticsTab = "lotteries" | "tickets" | "numbers" | "finances";
type SystemTab = "events" | "health" | "ledger" | "notifications" | "audit" | "development";

const navigation: { id: View; label: string; code: string }[] = [
  { id: "dashboard", label: "Сегодня", code: "01" },
  { id: "fast", label: "Fast", code: "02" },
  { id: "lotteries", label: "Лотереи", code: "03" },
  { id: "schedule", label: "Расписание", code: "04" },
  { id: "draws", label: "Тиражи", code: "05" },
  { id: "players", label: "Игроки", code: "06" },
  { id: "analytics", label: "Аналитика", code: "07" },
  { id: "facts", label: "Interesting Facts", code: "08" },
  { id: "broadcast", label: "Тест эфира", code: "09" },
  { id: "system", label: "Система", code: "10" },
];

const viewStorageKey = "k-loto:admin-view";

function storedView(): View {
  const path = window.location.pathname.split("/").filter(Boolean).at(-1);
  const remembered = window.localStorage.getItem(viewStorageKey);
  const legacy: Record<string, View> = {
    ledger: "system", notifications: "system", audit: "system", development: "system",
    statistics: "analytics", "ticket-analytics": "analytics",
  };
  const raw = path || remembered || "dashboard";
  const candidate = legacy[raw] ?? raw;
  return navigation.some((item) => item.id === candidate) ? candidate as View : "dashboard";
}

const drawStatuses: Record<string, string> = { SCHEDULED: "Запланирован", CLOSED: "Продажи закрыты", DRAWING: "Розыгрыш", SETTLING: "Начисление выигрышей", PENDING: "Ожидает", RUNNING: "Выполняется", COMPLETED: "Завершён", FAILED: "Ошибка" };
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
  if (lotteryCode === "pulse" && number > 10) return `P${number - 10}`;
  return String(number);
}

function displayMatches(lotteryCode: string, matches: number | null, grandFormat: boolean): string {
  if (matches === null) return "—";
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
        <div className="brand"><span>K</span><div>Kasper Loto<small>Панель владельца</small></div></div>
        <div className="secure-line"><i /> Вход для владельца</div>
        <h1>Идентификация агента</h1>
        <p>Закрытое пространство владельца K-Loto. Доступ к оперативной сводке и управлению системой.</p>
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

function DashboardView({ data, analytics, refreshedAt, onOpen, onNavigate }: { data: Dashboard; analytics: TicketAnalytics; refreshedAt: number; onOpen: (id: string) => void; onNavigate: (view: View) => void }) {
  const overall = analytics.overall;
  const today = data.operations.today;
  const todayRows = today.by_lottery ?? [];
  const margin = today.sales ? (today.net / today.sales) * 100 : 0;
  const attention = data.operations.stuck_draw_count > 0 || !data.database_healthy || !data.scheduler_enabled || !!data.operations.scheduler.last_error;
  return <>
    <section className="today-command"><div><span>ОПЕРАТИВНАЯ СВОДКА · МСК</span><h2>Сегодня в K-Loto</h2><p>{today.net >= 0 ? "Лото сегодня в плюсе" : "Сегодня выплаты выше продаж"} · продажи минус выплаты: <b className={today.net >= 0 ? "positive" : "negative"}>{cas(today.net)}</b></p></div><button className={attention ? "attention-button warning" : "attention-button"} onClick={() => onNavigate("system")}>{attention ? "Требует внимания" : "Система работает"}<span>→</span></button></section>
    <div className="today-ticker"><div><span>СЕГОДНЯ</span><b>{today.completed_draws} тиражей проведено</b><i>•</i><b>{today.purchased_tickets} билетов куплено</b><i>•</i><b>{cas(today.sales)} продажи</b><i>•</i><b>{cas(today.payout)} выиграно</b><i>•</i><b className={today.net >= 0 ? "positive" : "negative"}>итог {cas(today.net)}</b></div></div>
    <section className="metric-grid today-metrics"><article className="metric"><small>ТИРАЖИ СЕГОДНЯ</small><strong>{today.completed_draws}</strong><em>уже завершены</em></article><article className="metric"><small>ПРОДАНО БИЛЕТОВ</small><strong>{today.purchased_tickets.toLocaleString("ru-RU")}</strong><em>выручка {cas(today.sales)}</em></article><article className="metric"><small>ВЫПЛАТЫ СЕГОДНЯ</small><strong>{cas(today.payout)}</strong><em>{today.winning_tickets} выигрышных билетов</em></article><article className={`metric today-result ${today.net >= 0 ? "is-positive" : "is-negative"}`}><small>ПЛЮС ЛОТО ЗА ДЕНЬ</small><strong>{today.net >= 0 ? "+" : ""}{cas(today.net)}</strong><em>продажи − все выплаты · {margin.toLocaleString("ru-RU", { maximumFractionDigits: 1 })}%</em></article></section>
    <section className="panel today-breakdown"><header><div><h2>Из чего сложился итог дня</h2><span>Покупки и выплаты за текущие сутки по Москве</span></div></header><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Продано билетов</th><th>Продажи</th><th>Выплаты</th><th>Плюс / минус</th></tr></thead><tbody>{todayRows.map((row) => <tr key={row.lottery_id}><td><b>{row.lottery_name}</b></td><td>{row.purchased_tickets.toLocaleString("ru-RU")}</td><td>{cas(row.sales)}</td><td>{cas(row.payout)}<small>{row.winning_tickets} выигрышных</small></td><td className={row.net >= 0 ? "positive" : "negative"}><b>{row.net >= 0 ? "+" : ""}{cas(row.net)}</b></td></tr>)}</tbody></table></div>{!todayRows.length && <p className="source-note">Сегодня ещё не было продаж или выплат.</p>}<p className="source-note">Это оперативный денежный результат: сумма покупок за день минус сумма фактически начисленных выигрышей за день.</p></section>
    <section className="panel"><header><div><h2>Ближайшие тиражи</h2><span>Когда играем и сколько билетов уже куплено · МСК</span></div><button className="text-action" onClick={() => onNavigate("schedule")}>Всё расписание →</button></header><div className="table-wrap"><table><thead><tr><th>Лотерея / тираж</th><th>Розыгрыш</th><th>Продажи до</th><th>Игроки</th><th>Билеты</th><th>Стоимость билетов</th></tr></thead><tbody>{data.operations.next_draws.map((draw) => <tr key={draw.id}><td><button className="text-action" onClick={() => onOpen(draw.id)}>{draw.lottery_name} №{drawNumber(draw.draw_number)}</button></td><td>{date(draw.scheduled_at)}</td><td>{date(draw.sales_close_at)}</td><td>{draw.participant_count}</td><td>{draw.ticket_count}</td><td>{cas(draw.total_sales)}</td></tr>)}</tbody></table></div>{!data.operations.next_draws.length && <p className="source-note">Ближайших тиражей пока нет.</p>}</section>
    <JackpotPanel data={data} analytics={analytics} onOpen={onOpen} />
    <ActivityChart refreshedAt={refreshedAt} scope="all" />
    <section className="metric-grid business-metrics"><article className="metric"><small>ВСЕГО ТИРАЖЕЙ</small><strong>{data.counts.completed_draws.toLocaleString("ru-RU")}</strong><em>за всю историю</em></article><article className="metric"><small>ВСЕГО БИЛЕТОВ</small><strong>{overall.total_tickets.toLocaleString("ru-RU")}</strong><em>{overall.active_tickets.toLocaleString("ru-RU")} активны</em></article><article className="metric"><small>ИГРОКИ</small><strong>{data.counts.users}</strong><em>{overall.participants} участвовали</em></article></section>
  </>;
}

function FastDashboard({ data, analytics, refreshedAt, onOpen }: { data: Dashboard; analytics: TicketAnalytics; refreshedAt: number; onOpen: (id: string) => void }) {
  const today = data.operations.today;
  const frequency = data.jackpots.total_wins ? Math.max(1, Math.round(data.counts.completed_draws / data.jackpots.total_wins)) : null;
  return <div className="fast-command-room"><section className="fast-command"><div><span>FAST CONTROL</span><h2>Быстрые раунды</h2><p>Отдельная красная зона: продажи, результаты и частота джекпотов.</p></div><strong>{today.net >= 0 ? "+" : ""}{compactCas(today.net)}<small>итог сегодня</small></strong></section><div className="today-ticker fast-ticker"><div><b>{today.completed_draws} раундов сегодня</b><i>•</i><b>{today.purchased_tickets} билетов</b><i>•</i><b>{cas(today.sales)} продажи</b><i>•</i><b>{data.jackpots.total_wins} джекпотов за всё время</b></div></div><section className="metric-grid today-metrics"><article className="metric"><small>ПРОДАЖИ СЕГОДНЯ</small><strong>{compactCas(today.sales)}</strong></article><article className="metric"><small>ВЫПЛАТЫ СЕГОДНЯ</small><strong>{compactCas(today.payout)}</strong></article><article className="metric"><small>ЧАСТОТА ДЖЕКПОТА</small><strong>{frequency ? `1 / ${frequency}` : "—"}</strong><em>примерно один на столько раундов</em></article><article className="metric"><small>ТЕКУЩИЕ ДЖЕКПОТЫ</small><strong>{compactCas(data.lotteries.reduce((sum, item) => sum + item.current_jackpot, 0))}</strong></article></section><section className="panel"><header><h2>Текущие раунды</h2><span>Продажи и состояние</span></header><div className="table-wrap"><table><thead><tr><th>Игра</th><th>Время</th><th>Статус</th><th>Билеты</th><th>Продажи</th></tr></thead><tbody>{data.operations.next_draws.map(draw => <tr key={draw.id} onClick={() => onOpen(draw.id)} className="clickable"><td><b>{draw.lottery_name}</b> №{drawNumber(draw.draw_number)}</td><td>{date(draw.scheduled_at)}</td><td>{translated(draw.status, drawStatuses)}</td><td>{draw.ticket_count}</td><td>{cas(draw.total_sales)}</td></tr>)}</tbody></table></div></section><section className="panel"><header><h2>Последние результаты</h2><span>Быстрые игры</span></header><DrawTable draws={data.recent_draws} onOpen={onOpen} /></section><ActivityChart refreshedAt={refreshedAt} scope="fast" /><TicketAnalyticsView data={analytics} /></div>;
}

function SystemHealth({ data }: { data: Dashboard }) {
  return <>
    <div className="system-strip"><Status active={data.database_healthy}>БАЗА ДАННЫХ {data.database_healthy ? "РАБОТАЕТ" : "НЕДОСТУПНА"}</Status><Status active={data.scheduler_enabled}>ПЛАНИРОВЩИК {data.scheduler_enabled ? "АКТИВЕН" : "ОТКЛЮЧЁН"}</Status><Status active={data.bot_configured}>БОТ {data.bot_configured ? "НАСТРОЕН" : "НЕ НАСТРОЕН"}</Status><span>v{data.version} · работает {Math.floor(data.uptime_seconds / 60)} мин.</span></div>
    <section className="panel"><header><h2>Работа расписания и доставки</h2><span>Техническая диагностика</span></header><div className="control-status"><article><small>Последняя успешная проверка</small><strong>{date(data.operations.scheduler.last_succeeded_at)}</strong><span>{data.operations.scheduler.last_error ?? "Нет сохранённой ошибки планировщика"}</span></article><article><small>Задержанные тиражи</small><strong>{data.operations.stuck_draw_count}</strong><span>Ожидают доставки: {data.operations.notifications.PENDING ?? 0} · ошибки: {data.operations.notifications.FAILED ?? 0}</span></article></div></section>
    <section className="panel"><header><h2>Счета и фонды</h2><span>Текущее состояние</span></header><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Джекпот</th><th>Распределение</th><th>Резерв</th></tr></thead><tbody>{data.lotteries.map((lottery) => <tr key={lottery.id}><td>{lottery.name}</td><td>{cas(lottery.current_jackpot)}</td><td>{cas(lottery.distribution_fund)}</td><td>{cas(lottery.reserve)}</td></tr>)}</tbody></table></div></section>
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
    <div className="player-head"><div className="avatar">{player.display_name.slice(0, 1)}</div><div><h3>{player.display_name}</h3><small>@{player.username ?? "без_логина"} · TG {player.telegram_id ?? "—"}</small></div><Status active={player.is_active}>{player.is_active ? "АКТИВЕН" : "ОТКЛЮЧЁН"}</Status></div>
    <div className="player-stats"><span><small>БАЛАНС</small><b>{cas(player.balance)}</b></span><span><small>АКТИВНЫЕ БИЛЕТЫ</small><b>{player.active_ticket_count}</b><em>{player.ticket_count} всего</em></span><span><small>ПОТРАЧЕНО</small><b>{cas(player.spent)}</b></span><span><small>ВЫИГРАНО</small><b>{cas(player.won)}</b></span><span><small>ИТОГ</small><b className={player.net >= 0 ? "positive" : "negative"}>{cas(player.net)}</b></span></div>
    <div className="player-automation"><div><small>АВТОУЧАСТИЕ · {autoStatus.toLocaleUpperCase("ru-RU")}</small><b>{player.auto_play_enabled ? `${player.auto_play_tickets_per_draw} случайных билетов на каждый тираж` : "Выключена"}</b><span>Последняя проверка: {date(player.auto_play_last_attempted_at)} · успех: {date(player.auto_play_last_succeeded_at)}</span></div><div className="notification-state"><small>УВЕДОМЛЕНИЯ</small><b>{player.telegram_notifications_enabled ? "Telegram разрешён" : "Telegram выключен"}</b></div><label>Билетов на тираж<input aria-label="Билетов автоучастия на тираж" type="number" min="1" max="5" value={autoTickets} onChange={(event) => setAutoTickets(event.target.value)} /></label><label>Причина автоучастия<input value={autoReason} onChange={(event) => setAutoReason(event.target.value)} placeholder="Почему меняется автоучастие?" /></label><button disabled={autoBusy || !autoReason.trim() || Number(autoTickets) < 1 || Number(autoTickets) > 5} onClick={() => setConfirmation("auto-on")}>{player.auto_play_enabled ? "СОХРАНИТЬ АВТОУЧАСТИЕ" : "ВКЛЮЧИТЬ АВТОУЧАСТИЕ"}</button>{player.auto_play_enabled && <button className="secondary-action" disabled={autoBusy || !autoReason.trim()} onClick={() => setConfirmation("auto-off")}>ОТКЛЮЧИТЬ</button>}</div>
    <div className="adjust"><label>Новый баланс<input min="0" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} /></label><label>Обязательная причина<input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Почему требуется изменение?" /></label><button disabled={busy || !reason.trim()} onClick={() => setConfirmation("balance")}>ПРОВЕРИТЬ ИЗМЕНЕНИЕ</button></div>
    <button className="player-operations-toggle" onClick={() => operations ? setOperations(null) : void adminApi.playerTransactions(player.id).then(setOperations).catch((reason: Error) => setFormError(reason.message))}>{operations ? "Скрыть последние операции" : "Показать последние операции"}</button>{operations && <div className="player-operations"><TransactionTable rows={operations} /></div>}
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
      <label><span>Быстрый поиск игрока</span><input autoFocus aria-label="Поиск игрока" placeholder="Имя, @username, Telegram ID" value={search} onChange={(event) => onSearch(event.target.value)} /></label>
      <div className="player-search-meta"><b>{visible.length}</b><span>{query ? "найдено" : `последних игроков: ${players.length}`}</span>{search && <button onClick={() => onSearch("")}>Сбросить</button>}</div>
      <div className="player-results" role="list" aria-label="Результаты поиска игроков">{visible.slice(0, 100).map((player) => <button type="button" role="listitem" aria-label={`Открыть игрока ${player.display_name}`} className={player.id === activeId ? "active" : ""} key={player.id} onClick={() => setSelectedId(player.id)}><span className="avatar">{player.display_name.slice(0, 1)}</span><span><b>{player.display_name} ·</b><small>{player.username ? `@${player.username}` : `TG ${player.telegram_id ?? "—"}`}</small></span><span><b>{cas(player.balance)}</b><small>{player.active_ticket_count} активных бил.</small></span></button>)}</div>
      {!visible.length && <p className="source-note">Игрок не найден. Проверьте username или Telegram ID.</p>}
      {searchError && <p role="alert" className="source-note negative">{searchError}</p>}
      {visible.length > 100 && <p className="source-note">Показаны первые 100 результатов. Уточните запрос.</p>}
    </div>
    <div className="player-detail">{selected ? <PlayerCard key={selected.id} player={selected} onSaved={onReload} /> : <div className="player-empty"><b>Выберите игрока</b><span>Справа появятся баланс, билеты, выигрыши и действия.</span></div>}</div>
  </section>;
}

function DrawTable({ draws, onOpen }: { draws: Draw[]; onOpen?: (id: string) => void }) {
  return <div className="table-wrap"><table><thead><tr><th>Лотерея / тираж</th><th>Статус</th><th>По расписанию</th><th>Результат</th><th>Билеты</th><th>Продажи / выплаты</th></tr></thead><tbody>{draws.map((draw) => <tr key={draw.id} onClick={() => onOpen?.(draw.id)} className={onOpen ? "clickable" : ""}><td><b>{draw.lottery_name}</b> №{drawNumber(draw.public_number)}</td><td><span className={`tag ${draw.status.toLowerCase()}`}>{translated(draw.status, drawStatuses)}</span></td><td>{date(draw.scheduled_at)}</td><td><DrawResult draw={draw} /></td><td>{draw.ticket_count}</td><td>{cas(draw.total_sales)}<small>{cas(draw.total_payout)}</small></td></tr>)}</tbody></table></div>;
}

function TransactionTable({ rows }: { rows: Transaction[] }) {
  return <div className="table-wrap"><table><thead><tr><th>Время</th><th>Тип операции</th><th>Счёт</th><th>Изменение</th><th>До → После</th><th>Код операции</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{date(row.created_at)}</td><td><span className="tag">{translated(row.type, transactionTypes)}</span></td><td>{translated(row.account_kind, accountKinds)}</td><td className={row.amount >= 0 ? "positive" : "negative"}>{row.amount > 0 ? "+" : ""}{cas(row.amount)}</td><td>{cas(row.balance_before)} → {cas(row.balance_after)}</td><td><code>{row.operation_id.slice(0, 8)}</code></td></tr>)}</tbody></table></div>;
}

function DrawDetailPanel({ detail, onClose, onOpenPlayer }: { detail: DrawDetail; onClose: () => void; onOpenPlayer: (ticket: DrawDetail["tickets"][number]) => void }) {
  const draw = detail.draw;
  const jackpotWon = (draw.jackpot_amount ?? 0) > 0;
  const bingo = draw.lottery_code === "bingo";
  const [ticketFilter, setTicketFilter] = useState<"all" | "winners">(bingo && draw.status === "COMPLETED" ? "winners" : "all");
  const winningTickets = detail.tickets.filter((ticket) => ticket.prize_amount > 0);
  const jackpotTickets = detail.tickets.filter((ticket) => ticket.is_jackpot_winner);
  const shownTickets = ticketFilter === "winners" ? winningTickets : detail.tickets;
  const participantCount = new Set(detail.tickets.map((ticket) => ticket.user_id)).size;
  const bingoStages = [0, 1, 2].map((stage) => {
    const winners = detail.tickets.filter((ticket) => (ticket.bingo_result?.amounts[stage] ?? 0) > 0);
    const firstMove = winners.length ? Math.min(...winners.map((ticket) => ticket.bingo_result?.moves[stage] ?? 0)) : null;
    return { winners: winners.length, payout: winners.reduce((sum, ticket) => sum + (ticket.bingo_result?.amounts[stage] ?? 0), 0), firstMove };
  });
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [onClose]);
  return <div className="drawer" role="dialog" aria-modal="true" aria-label={`Тираж ${draw.lottery_name} №${drawNumber(draw.public_number)}`}><button aria-label="Закрыть" className="close" onClick={onClose}>×</button><small>НЕИЗМЕНЯЕМАЯ ЗАПИСЬ ТИРАЖА</small><h2>{draw.lottery_name} №{drawNumber(draw.public_number)}</h2><DrawResult draw={draw} detailed />{bingo && draw.status === "COMPLETED" && <section className="bingo-stage-summary">{bingoStages.map((stage, index) => <article key={index}><small>{["РАННЯЯ СТРОКА", "ДВЕ СТРОКИ", "ДЖЕКПОТ"][index]}</small><strong>{stage.winners ? `${stage.winners} бил.` : "Нет победителя"}</strong><span>{stage.firstMove ? `ход ${stage.firstMove} · ${cas(stage.payout)}` : index === 2 ? "Джекпот перенесён" : "Приз не выплачен"}</span></article>)}</section>}{jackpotWon && <div className="jackpot-hit"><small>ДЖЕКПОТ ЭТОГО ТИРАЖА СОРВАН</small><strong>{cas(draw.jackpot_amount)}</strong><span>Эта сумма делится между билетами джекпот-категории. Общая выплата тиража указана отдельно.</span></div>}{jackpotTickets.length > 0 && <section className="jackpot-winners"><h3>Кто сорвал джекпот</h3>{jackpotTickets.map((ticket) => <article key={ticket.id}><div><small>Билет №{drawNumber(ticket.public_number)}</small><strong>{ticket.player_name ?? "Игрок"}</strong><span>{ticket.player_username ? `@${ticket.player_username}` : "без username"} · TG {ticket.player_telegram_id ?? "—"}</span></div><b>{cas(ticket.prize_amount)}</b><button onClick={() => onOpenPlayer(ticket)}>Открыть игрока →</button></article>)}</section>}<dl className="detail-list"><dt>Статус</dt><dd>{translated(draw.status, drawStatuses)}</dd><dt>По расписанию</dt><dd>{date(draw.scheduled_at)}</dd><dt>Проведён</dt><dd>{date(draw.executed_at)}</dd><dt>Игроков</dt><dd>{participantCount.toLocaleString("ru-RU")}</dd><dt>Билетов</dt><dd>{draw.ticket_count.toLocaleString("ru-RU")}</dd><dt>Выигрышных</dt><dd>{winningTickets.length.toLocaleString("ru-RU")}</dd><dt>Продажи</dt><dd>{cas(draw.total_sales)}</dd><dt>Все выплаты тиража</dt><dd>{cas(draw.total_payout)}</dd><dt>Джекпот до тиража</dt><dd>{cas(draw.jackpot_opening)}</dd><dt>Джекпот после тиража</dt><dd>{cas(draw.jackpot_closing)}</dd><dt>Использовано из Фонда Каспера</dt><dd>{cas(draw.kasper_fund_used)}</dd></dl><div className="ticket-list-heading"><h3>Билеты ({shownTickets.length})</h3><div><button className={ticketFilter === "winners" ? "active" : ""} onClick={() => setTicketFilter("winners")}>Выигрышные · {winningTickets.length}</button><button className={ticketFilter === "all" ? "active" : ""} onClick={() => setTicketFilter("all")}>Все · {detail.tickets.length}</button></div></div>{shownTickets.map((ticket) => <div className={`ticket-row ${bingo ? "bingo-ticket-row" : ""} ${ticket.is_jackpot_winner ? "jackpot-ticket" : ""}`} key={ticket.id}><b>№{drawNumber(ticket.public_number)}</b><span className="ticket-owner"><b>{ticket.player_name ?? "Игрок"}</b><small>{ticket.player_username ? `@${ticket.player_username}` : `TG ${ticket.player_telegram_id ?? "—"}`}</small></span><span>{bingo ? <span className="bingo-ticket-numbers">{[0, 1, 2].map((row) => <i key={row}>{ticket.numbers.slice(row * 4, row * 4 + 4).join(" · ")}</i>)}</span> : ticket.numbers.map((number) => displayNumber(draw.lottery_code, number)).join(" · ")}</span><span>{bingo && ticket.bingo_result ? ticket.bingo_result.moves.map((move, index) => `${["строка", "две", "полный"][index]}: ${move <= 60 ? `ход ${move}` : "не закрыто"}`).join(" · ") : `совпадений: ${displayMatches(draw.lottery_code, ticket.matches, ticket.numbers.length === 7)}`}</span><strong>{ticket.is_jackpot_winner && <small>ДЖЕКПОТ</small>}{cas(ticket.prize_amount)}</strong></div>)}{!shownTickets.length && <p className="source-note">В этом тираже выигрышных билетов нет.</p>}</div>;
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

function BroadcastTestView({ lotteries, miniappUrl }: { lotteries: Lottery[]; miniappUrl?: string | null }) {
  const available = lotteries.filter((lottery) => lottery.is_active && !["flash", "shadow", "pulse"].includes(lottery.code));
  const [lotteryCode, setLotteryCode] = useState(available[0]?.code ?? "");
  const [scenario, setScenario] = useState<"win" | "loss">("win");
  const selectedLotteryCode = available.some((lottery) => lottery.code === lotteryCode) ? lotteryCode : available[0]?.code ?? "";
  const start = () => {
    if (!miniappUrl || !selectedLotteryCode) return;
    const url = new URL(miniappUrl);
    url.searchParams.set("broadcast-preview", selectedLotteryCode);
    url.searchParams.set("scenario", scenario);
    url.searchParams.set("started", String(Date.now()));
    window.open(url.toString(), "_blank", "noopener,noreferrer");
  };
  return <section className="broadcast-test">
    <header><span>РЕПЕТИЦИЯ</span><h2>Проверьте эфир глазами игрока</h2><p>Через пять секунд начнётся настоящий интерфейс эфира на полностью демонстрационных данных.</p></header>
    <div className="broadcast-test-form">
      <label>Лотерея<select aria-label="Лотерея тестового эфира" value={selectedLotteryCode} onChange={(event) => setLotteryCode(event.target.value)}>{available.map((lottery) => <option key={lottery.id} value={lottery.code}>{lottery.name}</option>)}</select></label>
      <label>Результат<select aria-label="Сценарий тестового эфира" value={scenario} onChange={(event) => setScenario(event.target.value as "win" | "loss")}><option value="win">Билет выигрывает</option><option value="loss">Без выигрыша</option></select></label>
      <button className="broadcast-launch" disabled={!miniappUrl || !selectedLotteryCode} onClick={start} type="button">Запустить тестовый эфир ↗</button>
    </div>
    <div className="broadcast-safety"><i>✓</i><span><b>Изолировано от игры</b>Никаких покупок, выплат, уведомлений и записей в историю. Fast здесь намеренно отсутствует.</span></div>
    {!miniappUrl && <p className="error banner">Адрес Mini App не настроен на сервере.</p>}
  </section>;
}

function SectionTabs<T extends string>({ value, items, onChange, label }: { value: T; items: Array<{ id: T; label: string }>; onChange: (value: T) => void; label: string }) {
  return <div className="section-tabs" role="tablist" aria-label={label}>{items.map((item) => <button type="button" role="tab" aria-selected={value === item.id} className={value === item.id ? "active" : ""} key={item.id} onClick={() => onChange(item.id)}>{item.label}</button>)}</div>;
}

function DrawsView({ lotteries, onOpen, scope }: { lotteries: Lottery[]; onOpen: (id: string) => void; scope: LotteryScope }) {
  const [period, setPeriod] = useState<"future" | "today" | "completed" | "failed">("today");
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
  return <><div className="section-toolbar"><SectionTabs value={period} label="Период тиражей" items={[{ id: "future", label: "Будущие" }, { id: "today", label: "Сегодня" }, { id: "completed", label: "Завершённые" }, { id: "failed", label: "Ошибки" }]} onChange={setPeriod} /><select aria-label="Лотерея тиражей" value={lotteryId} onChange={e => setLotteryId(e.target.value)}><option value="">Все в этом разделе</option>{lotteries.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></div><section className="panel"><header><h2>Тиражи</h2><span>ЗАГРУЖЕНО: {rows.length}</span></header>{error && <p role="alert">{error}</p>}<DrawTable draws={rows} onOpen={onOpen} />{busy && <p className="source-note">Загружаем…</p>}{!busy && !rows.length && !error && <p className="source-note">В выбранном периоде тиражей нет.</p>}{more && <button className="draw-load-more" disabled={busy} onClick={() => void next()}>Показать ещё 100</button>}</section></>;
}

function JackpotPanel({ data, analytics, onOpen }: { data: Dashboard; analytics?: TicketAnalytics; onOpen?: (id: string) => void }) {
  const last = data.jackpots.last_win ?? data.jackpots.history[0];
  const [showHistory, setShowHistory] = useState(false);
  const [lotteryFilter, setLotteryFilter] = useState("");
  const history = data.jackpots.history.filter((event) => !lotteryFilter || event.lottery_code === lotteryFilter);
  return <section className="panel jackpot-command">
    <header><div><h2>Джекпоты</h2><span>За всю историю · один сорванный джекпот = один тираж, даже если победителей несколько</span></div></header>
    <div className="metric-grid jackpot-metrics">
      <article className="metric jackpot-count"><small>Всего сорвано джекпотов</small><strong>{data.jackpots.total_wins.toLocaleString("ru-RU")}</strong><em>тиражей с выплатой джекпота</em></article>
      <article className="metric"><small>Общая сумма джекпотов</small><strong>{cas(data.jackpots.total_paid)}</strong><em>действительно выплачено игрокам</em></article>
      <article className="metric latest-jackpot"><small>Последний выигрыш джекпота</small><strong>{last ? cas(last.jackpot_amount) : "Пока не сорван"}</strong><em>{last ? `${last.lottery_name} · ${date(last.occurred_at)} МСК` : "Здесь появится первая выплата"}</em>{last && onOpen && <button className="text-action" onClick={() => onOpen(last.draw_id)}>Тираж {last.draw_number ? `№${drawNumber(last.draw_number)}` : "и билеты"} →</button>}</article>
      <article className="metric"><small>Самый крупный джекпот</small><strong>{cas(data.jackpots.largest_win)}</strong><em>рекорд одного тиража за всё время</em></article>
    </div>
    <h3 className="subheading">По каждой лотерее</h3>
    <div className="table-wrap"><table className="jackpot-lotteries"><thead><tr><th>Лотерея</th><th>Сейчас разыгрывается</th><th>Сорвано</th><th>Выплачено за всё время</th><th>Последний выигрыш</th>{analytics && <th>Билетов рассчитано</th>}</tr></thead><tbody>{data.jackpots.lotteries.map((row) => {
      const lottery = data.lotteries.find((item) => item.code === row.code);
      const ticketRow = analytics?.lotteries.find((item) => item.lottery_id === (row.lottery_id ?? lottery?.id));
      return <tr key={row.code} className={`lottery-row lottery-${row.code}`}><td><b>{row.name}</b><small>{row.is_active === false ? "В архиве" : ["flash", "shadow", "pulse"].includes(row.code) ? "Fast" : lottery?.kind === "WEEKLY" ? "Еженедельная" : "Ежедневная"}</small></td><td>{lottery?.is_active ? cas(lottery.current_jackpot) : "—"}<small>{lottery?.is_active ? date(lottery.next_draw_at) : "Нет продаж"}</small></td><td><b className="win-count">{row.win_count}</b></td><td>{cas(row.total_paid)}</td><td>{row.last_win_amount != null ? <><b>{cas(row.last_win_amount)}</b><small>{date(row.last_win_at)} МСК</small>{row.last_draw_id && onOpen && <button className="text-action" onClick={() => onOpen(row.last_draw_id!)}>Открыть тираж №{drawNumber(row.last_draw_number ?? 0)} →</button>}</> : row.win_count ? <span>Сумма недоступна<small>{date(row.last_win_at)}</small></span> : <span className="muted">Ещё не сорван</span>}</td>{analytics && <td>{ticketRow?.settled_tickets.toLocaleString("ru-RU") ?? "—"}<small>{ticketRow?.active_tickets.toLocaleString("ru-RU") ?? "—"} активных сейчас</small></td>}</tr>;
    })}</tbody></table></div>
    <p className="source-note">Сумма джекпота относится ко всему тиражу и может делиться между несколькими билетами. Количество билетов помогает сравнить объём участия; прошлые выигрыши не определяют следующий результат.</p>
    <button className="history-toggle" aria-expanded={showHistory} onClick={() => setShowHistory((value) => !value)}>{showHistory ? "Скрыть историю джекпотов" : `Показать последние выигрыши (${data.jackpots.history.length})`} <span>{showHistory ? "−" : "+"}</span></button>
    {showHistory && <div className="jackpot-history"><label>Лотерея в истории джекпотов<select value={lotteryFilter} onChange={(event) => setLotteryFilter(event.target.value)}><option value="">Все лотереи</option>{data.jackpots.lotteries.map((lottery) => <option key={lottery.code} value={lottery.code}>{lottery.name}</option>)}</select></label><p className="source-note">Последние 50 джекпотов выбранного раздела. Итоги выше учитывают всю его историю.</p><div className="table-wrap"><table><thead><tr><th>Дата, МСК</th><th>Лотерея / тираж</th><th>Джекпот этого тиража</th><th>Выигрышных билетов</th><th>Игроков-победителей</th></tr></thead><tbody>{history.map((row) => <tr key={row.id}><td>{date(row.occurred_at)}</td><td>{onOpen ? <button className="text-action" onClick={() => onOpen(row.draw_id)}>{row.lottery_name} {row.draw_number ? `№${drawNumber(row.draw_number)}` : "→"}</button> : row.lottery_name}</td><td className="positive">{cas(row.jackpot_amount)}</td><td>{row.winner_ticket_count}</td><td>{row.winner_user_count}</td></tr>)}</tbody></table></div>{!history.length && <p className="source-note">В показанной части истории нет джекпотов этой лотереи.</p>}</div>}
  </section>;
}

function AnalyticsView({ tab, onTab, dashboard, analytics, lotteries, statistics, selectedLotteryId, windowSize, onLottery, onWindow }: { tab: AnalyticsTab; onTab: (tab: AnalyticsTab) => void; dashboard: Dashboard; analytics: TicketAnalytics; lotteries: Lottery[]; statistics: NumberStatisticsReport | null; selectedLotteryId: string; windowSize: number; onLottery: (id: string) => void; onWindow: (size: number) => void }) {
  const jackpotById = new Map(dashboard.jackpots.lotteries.map((row) => [row.lottery_id ?? dashboard.lotteries.find((item) => item.code === row.code)?.id, row]));
  const rows = analytics.lotteries.map((row) => ({ ...row, jackpot: jackpotById.get(row.lottery_id ?? undefined) }));
  const fast = rows.filter((row) => ["flash", "shadow", "pulse"].includes(row.jackpot?.code ?? ""));
  const regular = rows.filter((row) => !fast.includes(row));
  const renderComparison = (items: typeof rows, title: string) => <section className="panel analytics-panel"><header><h2>{title}</h2><span>ФАКТИЧЕСКАЯ ИСТОРИЯ</span></header><div className="table-wrap"><table><thead><tr><th>Лотерея</th><th>Тиражей с джекпотом</th><th>Билеты / выигрышные</th><th>Выигрышных билетов</th><th>Потрачено</th><th>Выплачено</th><th>Выплаты / покупки</th><th>Крупнейший джекпот</th></tr></thead><tbody>{items.map((row) => <tr key={row.lottery_id}><td><b>{row.lottery_name}</b></td><td>{row.jackpot?.win_count ?? 0}</td><td>{row.settled_tickets.toLocaleString("ru-RU")} / {row.winning_tickets.toLocaleString("ru-RU")}</td><td>{percentage(row.winning_tickets, row.settled_tickets)}</td><td>{compactCas(row.total_sales)}</td><td>{compactCas(row.total_payout)}</td><td>{percentage(row.total_payout, row.total_sales)}</td><td>{compactCas(row.jackpot?.largest_win ?? 0)}</td></tr>)}</tbody></table></div></section>;
  return <>
    <SectionTabs value={tab} label="Разделы аналитики" items={[{ id: "lotteries", label: "Лотереи" }, { id: "tickets", label: "Билеты" }, { id: "numbers", label: "Числа" }, { id: "finances", label: "Финансы" }]} onChange={onTab} />
    {tab === "lotteries" && <>{fast.length > 0 && renderComparison(fast, "Fast: результаты за всё время")}{renderComparison(regular, "Daily, Weekly и Special")}</>}
    {tab === "tickets" && <TicketAnalyticsView data={analytics} />}
    {tab === "numbers" && statistics && <StatisticsView lotteries={lotteries} report={statistics} selectedLotteryId={selectedLotteryId} windowSize={windowSize} onLottery={onLottery} onWindow={onWindow} />}
    {tab === "numbers" && !statistics && <div className="loading">ЗАГРУЖАЕМ СТАТИСТИКУ ЧИСЕЛ…</div>}
    {tab === "finances" && <JackpotPanel data={dashboard} />}
  </>;
}

function OperationalLog({ transactions, notifications, audit, dashboard }: { transactions: Transaction[]; notifications: NotificationItem[]; audit: AuditEntry[]; dashboard: Dashboard | null }) {
  const [source, setSource] = useState<"all" | "money" | "draw" | "admin" | "notification">("all");
  const [search, setSearch] = useState("");
  const entries = [
    ...transactions.map((item) => ({ id: `money-${item.id}`, source: "money" as const, at: item.created_at, level: "info", title: translated(item.type, transactionTypes), detail: `${item.amount > 0 ? "+" : ""}${cas(item.amount)} · ${translated(item.account_kind, accountKinds)}`, link: item.draw_id })),
    ...notifications.map((item) => ({ id: `notification-${item.id}`, source: "notification" as const, at: item.created_at, level: item.status === "FAILED" ? "error" : item.status === "PENDING" ? "warn" : "info", title: `Уведомление: ${translated(item.type, notificationTypes)}`, detail: `${translated(item.status, { PENDING: "ожидает", PROCESSING: "отправляется", SENT: "доставлено", FAILED: "ошибка", CANCELLED: "отменено" })}${item.last_error ? ` · ${item.last_error}` : ""}`, link: null })),
    ...audit.map((item) => ({ id: `admin-${item.id}`, source: "admin" as const, at: item.created_at, level: "warn", title: translated(item.action, auditActions), detail: `${translated(item.entity_type, entityTypes)} · ${item.reason ?? "без комментария"}`, link: null })),
    ...(dashboard?.recent_draws ?? []).map((item) => ({ id: `draw-${item.id}`, source: "draw" as const, at: item.executed_at ?? item.scheduled_at, level: item.status === "FAILED" ? "error" : "info", title: `${item.lottery_name} №${drawNumber(item.public_number)}`, detail: `${translated(item.status, drawStatuses)} · ${item.ticket_count} бил. · продажи ${cas(item.total_sales)} · выплаты ${cas(item.total_payout)}`, link: item.id })),
  ].sort((left, right) => new Date(right.at).getTime() - new Date(left.at).getTime());
  const normalized = search.trim().toLocaleLowerCase("ru-RU");
  const visible = entries.filter((entry) => (source === "all" || entry.source === source) && (!normalized || `${entry.title} ${entry.detail}`.toLocaleLowerCase("ru-RU").includes(normalized)));
  const sourceLabels = { money: "CAS", draw: "Тираж", admin: "Админ", notification: "Уведомление" };
  return <section className="panel operational-log"><header><div><h2>Лента событий</h2><span>Деньги, тиражи, действия администратора и доставка сообщений в одном месте</span></div><b>{visible.length} записей</b></header><div className="log-controls"><input aria-label="Поиск в логах" placeholder="Найти событие или ошибку" value={search} onChange={(event) => setSearch(event.target.value)} /><div>{(["all", "money", "draw", "admin", "notification"] as const).map((item) => <button className={source === item ? "active" : ""} key={item} onClick={() => setSource(item)}>{item === "all" ? "Все" : sourceLabels[item]}</button>)}</div></div><div className="event-log">{visible.map((entry) => <article className={entry.level} key={entry.id}><time>{date(entry.at)}</time><span className={`log-source ${entry.source}`}>{sourceLabels[entry.source]}</span><div><b>{entry.title}</b><p>{entry.detail}</p></div></article>)}</div>{!visible.length && <p className="source-note">По этому фильтру событий нет.</p>}</section>;
}

function SystemView({ tab, onTab, transactions, notifications, audit, onTransactions, dashboard, releaseNotes }: { dashboard: Dashboard | null; releaseNotes: { changelog: ReleaseNote[]; devlog: ReleaseNote[] }; tab: SystemTab; onTab: (tab: SystemTab) => void; transactions: Transaction[]; notifications: NotificationItem[]; audit: AuditEntry[]; onTransactions: (query: string) => void }) {
  return <>
    <SectionTabs value={tab} label="Системные журналы" items={[{ id: "events", label: "Лента событий" }, { id: "health", label: "Состояние" }, { id: "ledger", label: "Журнал CAS" }, { id: "notifications", label: "Уведомления" }, { id: "audit", label: "Аудит действий" }, { id: "development", label: "Разработка" }]} onChange={onTab} />
    {tab === "events" && <OperationalLog transactions={transactions} notifications={notifications} audit={audit} dashboard={dashboard} />}
    {tab === "health" && dashboard && <SystemHealth data={dashboard} />}
    {tab === "development" && <DevelopmentView changelog={releaseNotes.changelog} devlog={releaseNotes.devlog} />}
    {tab === "ledger" && <><TransactionFilters onApply={onTransactions} /><section className="panel"><header><h2>Неизменяемый журнал CAS</h2><span>ЗАПИСЕЙ: {transactions.length}</span></header><TransactionTable rows={transactions} /></section></>}
    {tab === "notifications" && <section className="panel"><header><h2>Очередь уведомлений</h2><span>ДОСТАВЛЕНО · ОШИБКА · ОЖИДАЕТ</span></header><div className="table-wrap"><table><thead><tr><th>Создано</th><th>Тип</th><th>Игрок</th><th>Статус</th><th>Попытки</th><th>Ошибка</th></tr></thead><tbody>{notifications.map((item) => <tr key={item.id}><td>{date(item.created_at)}</td><td>{translated(item.type, notificationTypes)}</td><td><code>{item.user_id.slice(0, 8)}</code></td><td><span className={`tag ${item.status.toLowerCase()}`}>{translated(item.status, { PENDING: "ожидает", PROCESSING: "отправляется", SENT: "доставлено", FAILED: "ошибка", CANCELLED: "отменено" })}</span></td><td>{item.attempts}</td><td>{item.last_error ?? "—"}</td></tr>)}</tbody></table></div></section>}
    {tab === "audit" && <section className="panel"><header><h2>Аудит действий администратора</h2><span>ХРАНИТСЯ ПОСТОЯННО</span></header><div className="audit-list">{audit.map((item) => <article key={item.id}><time>{date(item.created_at)}</time><b>{translated(item.action, auditActions)} · {translated(item.entity_type, entityTypes)}</b><p>{item.reason ?? "Причина не указана"}</p><code>{JSON.stringify(item.old_values)} → {JSON.stringify(item.new_values)}</code></article>)}</div></section>}
  </>;
}

const factTypeLabels: Record<string, string> = {
  jackpot_drought: "Серия без джекпота",
  record_current_jackpot: "Рекордный джекпот",
  jackpot_growth: "Рост джекпота",
  frequent_numbers: "Частые числа",
  overdue_numbers: "Давно не выпадали",
  daily_winner_leader: "Лидер по выигрышным билетам",
  largest_daily_win: "Крупнейший выигрыш дня",
  largest_weekly_win: "Крупнейший выигрыш недели",
  unusual_win_rate: "Необычный процент выигрышей",
  frequent_pair: "Частая пара",
  busiest_draw: "Самый заметный тираж",
};
const factStatusLabels: Record<InterestingFactStatus, string> = {
  new: "Новые", viewed: "Просмотренные", used: "Использованные", hidden: "Скрытые",
};
const factValueLabels: Record<string, string> = {
  draws_without_jackpot: "Тиражей без джекпота", jackpot: "Текущий джекпот", previous_jackpot: "Было", growth: "Рост",
  amount: "Сумма", ticket_count: "Билетов", participant_count: "Игроков", win_rate: "Доля выигрышей",
  number: "Число", numbers: "Числа", pair: "Пара", appearances: "Выпадений", draws_since_last: "Тиражей не выпадало",
  winner_count: "Победителей", winning_tickets: "Выигрышных билетов", payout: "Выплачено", sales: "Продажи",
};

function factValue(key: string, value: unknown): string {
  if (Array.isArray(value)) return value.join(" · ");
  if (typeof value === "number") {
    if (["jackpot", "previous_jackpot", "amount", "payout", "sales"].includes(key)) return cas(value);
    if (["growth", "win_rate"].includes(key)) return `${value.toLocaleString("ru-RU", { maximumFractionDigits: 1 })}%`;
    return value.toLocaleString("ru-RU");
  }
  return String(value);
}

function InterestingFactsView({ facts, lotteries, onStatus }: { facts: InterestingFact[]; lotteries: Lottery[]; onStatus: (fact: InterestingFact, status: InterestingFactStatus) => Promise<void> }) {
  const [factStatus, setFactStatus] = useState<InterestingFactStatus | "">("new");
  const [lotteryId, setLotteryId] = useState("");
  const [factType, setFactType] = useState("");
  const [copiedId, setCopiedId] = useState("");
  const types = [...new Set(facts.map((fact) => fact.fact_type))].sort();
  const visible = facts.filter((fact) => (!factStatus || fact.status === factStatus) && (!lotteryId || fact.lottery_id === lotteryId) && (!factType || fact.fact_type === factType)).sort((left, right) => right.score - left.score);
  const copy = async (fact: InterestingFact) => {
    await navigator.clipboard.writeText(`${fact.title}\n\n${fact.description}`);
    setCopiedId(fact.id);
    window.setTimeout(() => setCopiedId(""), 1800);
  };
  return <>
    <section className="facts-intro"><div><small>РЕДАКЦИОННАЯ ЛЕНТА</small><h2>Интересные факты без технического шума</h2><p>Самые сильные поводы идут первыми. Скопируйте готовый текст, отметьте использованный материал и больше не возвращайтесь к нему.</p></div><div className="fact-summary"><strong>{facts.filter((fact) => fact.status === "new").length}<small>новых</small></strong><strong>{facts.filter((fact) => fact.status === "used").length}<small>использовано</small></strong></div></section>
    <div className="facts-filters">
      <select aria-label="Статус факта" value={factStatus} onChange={(event) => setFactStatus(event.target.value as InterestingFactStatus | "")}><option value="">Все статусы</option>{Object.entries(factStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      <select aria-label="Лотерея факта" value={lotteryId} onChange={(event) => setLotteryId(event.target.value)}><option value="">Все лотереи</option>{lotteries.map((lottery) => <option key={lottery.id} value={lottery.id}>{lottery.name}</option>)}</select>
      <select aria-label="Тип факта" value={factType} onChange={(event) => setFactType(event.target.value)}><option value="">Все типы</option>{types.map((type) => <option key={type} value={type}>{factTypeLabels[type] ?? translated(type, {})}</option>)}</select>
    </div>
    {visible.length ? <section className="facts-grid">{visible.map((fact, index) => <article className={`fact-card ${fact.status} ${index === 0 ? "featured" : ""}`} key={fact.id}>
      <header><span>{factTypeLabels[fact.fact_type] ?? translated(fact.fact_type, {})}</span><b>{index === 0 ? "Лучший повод" : factStatusLabels[fact.status]}</b></header>
      <small>{fact.lottery_name} · {new Date(`${fact.generation_date}T12:00:00`).toLocaleDateString("ru-RU")}</small><h3>{fact.title}</h3><p>{fact.description}</p>
      <div className="fact-values">{Object.entries(fact.numeric_values).map(([key, value]) => <span key={key}><small>{factValueLabels[key] ?? translated(key, {})}</small><b>{factValue(key, value)}</b></span>)}</div>
      <footer><button onClick={() => void copy(fact)}>{copiedId === fact.id ? "Текст скопирован" : "Скопировать готовый текст"}</button>{fact.status !== "viewed" && <button onClick={() => void onStatus(fact, "viewed")}>Отложить</button>}{fact.status !== "used" && <button className="primary" onClick={() => void onStatus(fact, "used")}>Использовано</button>}{fact.status !== "hidden" && <button className="quiet" onClick={() => void onStatus(fact, "hidden")}>Скрыть</button>}</footer>
    </article>)}</section> : <section className="panel empty-facts"><h2>В этой выборке пока нет фактов</h2><p>Новая подборка появится автоматически после ежедневного расчёта.</p></section>}
  </>;
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
  const [scope, setScope] = useState<LotteryScope>("standard");
  const [scheduleEntries, setScheduleEntries] = useState<ScheduleEntry[]>([]);
  const [scheduleLoadedAt, setScheduleLoadedAt] = useState(0);
  const [drawDetail, setDrawDetail] = useState<DrawDetail | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [statistics, setStatistics] = useState<NumberStatisticsReport | null>(null);
  const [statisticsLotteryId, setStatisticsLotteryId] = useState("");
  const [statisticsWindow, setStatisticsWindow] = useState(20);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [interestingFacts, setInterestingFacts] = useState<InterestingFact[]>([]);
  const [releaseNotes, setReleaseNotes] = useState<{ changelog: ReleaseNote[]; devlog: ReleaseNote[] }>({ changelog: [], devlog: [] });
  const [ticketAnalytics, setTicketAnalytics] = useState<TicketAnalytics | null>(null);
  const [analyticsTab, setAnalyticsTab] = useState<AnalyticsTab>("lotteries");
  const [systemTab, setSystemTab] = useState<SystemTab>(() => window.location.pathname === "/development" ? "development" : "health");
  const [loadedAt, setLoadedAt] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const loadGeneration = useRef(0);
  const applyPlayerResults = useCallback((rows: Player[]) => setPlayers(rows), []);

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

  const load = useCallback(async (target: View, silent = false) => {
    const generation = ++loadGeneration.current;
    const apply = (update: () => void) => { if (generation === loadGeneration.current) update(); };
    if (!silent) setLoading(true);
    setRefreshing(true);
    setError("");
    try {
      if (target === "dashboard") {
        const [dashboardData, analyticsData] = await Promise.all([adminApi.dashboard("all"), adminApi.ticketAnalytics("all")]);
        apply(() => { setDashboard(dashboardData); });
        apply(() => { setTicketAnalytics(analyticsData); });
      }
      if (target === "fast") {
        const [dashboardData, analyticsData] = await Promise.all([adminApi.dashboard("fast"), adminApi.ticketAnalytics("fast")]);
        apply(() => { setDashboard(dashboardData); setTicketAnalytics(analyticsData); });
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
      if (target === "broadcast") { const rows = await adminApi.lotteries(); apply(() => setLotteries(rows)); }
      if (target === "facts") {
        const [facts, available] = await Promise.all([adminApi.interestingFacts(""), adminApi.lotteries()]);
        apply(() => { setInterestingFacts(facts); setLotteries(available); });
      }
      if (target === "system") {
        const [ledgerRows, notificationRows, auditRows, dashboardData, changelog, devlog] = await Promise.all([adminApi.transactions(), adminApi.notifications(), adminApi.audit(), adminApi.dashboard(), adminApi.releaseNotes("changelog"), adminApi.releaseNotes("devlog")]);
        apply(() => { setTransactions(ledgerRows); setNotifications(notificationRows); setAudit(auditRows); setDashboard(dashboardData); setReleaseNotes({ changelog, devlog }); });
      }
      if (target === "analytics") {
        const [available, dashboardData, analyticsData] = await Promise.all([adminApi.lotteries(), adminApi.dashboard(scope), adminApi.ticketAnalytics(scope)]);
        apply(() => { setLotteries(available); });
        apply(() => { setDashboard(dashboardData); });
        apply(() => { setTicketAnalytics(analyticsData); });
        const scoped = available.filter(l => l.code !== "bingo" && (scope === "all" || ["flash", "shadow", "pulse"].includes(l.code) === (scope === "fast")));
        const selectedId = scoped.find(l => l.id === statisticsLotteryId)?.id || scoped[0]?.id || "";
        apply(() => { setStatisticsLotteryId(selectedId); });
        if (selectedId) { const report = await adminApi.statistics(selectedId, statisticsWindow); apply(() => setStatistics(report)); }
      }
      apply(() => setLoadedAt(Date.now()));
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) setSession(null);
      apply(() => setError(reason instanceof Error ? reason.message : "Не удалось выполнить запрос администратора."));
    } finally { apply(() => { setLoading(false); setRefreshing(false); }); }
  }, [statisticsLotteryId, statisticsWindow, scope]);

  useEffect(() => {
    if (!session) return;
    const task = window.setTimeout(() => void load(view), 0);
    return () => window.clearTimeout(task);
  }, [session, view, load]);

  useEffect(() => {
    if (!session || !["dashboard", "fast"].includes(view)) return;
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") void load(view, true); }, 30_000);
    return () => window.clearInterval(timer);
  }, [session, view, load]);

  const openDraw = (id: string) => { void adminApi.draw(id).then(setDrawDetail).catch((reason: Error) => setError(reason.message)); };
  const openPlayerFromTicket = (ticket: DrawDetail["tickets"][number]) => {
    setPlayerSearch(ticket.player_username ?? String(ticket.player_telegram_id ?? ticket.user_id));
    setDrawDetail(null);
    navigate("players");
  };

  if (checking) return <main className="boot">K-LOTO // ПРОВЕРКА СЕССИИ</main>;
  if (!session) return <Login onAuthenticated={setSession} />;

  const visibleLotteries = lotteries.filter(l => scope === "all" || ["flash", "shadow", "pulse"].includes(l.code) === (scope === "fast"));
  const title = navigation.find((item) => item.id === view)?.label ?? "Управление";
  return <div className={`admin-shell ${view === "fast" ? "fast-admin" : ""}`}>
    <aside><div className="brand"><span>K</span><div>Kasper Loto<small>Панель владельца</small></div></div><nav>{navigation.map((item) => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => navigate(item.id)}><small>{item.code}</small>{item.label}</button>)}</nav><div className="operator"><small>ВЛАДЕЛЕЦ</small><b>{session.username}</b><button onClick={() => void adminApi.logout().finally(() => setSession(null))}>ЗАВЕРШИТЬ СЕАНС</button></div></aside>
    <main className="workspace"><header className="topbar"><div><small>Kasper Loto · управление</small><h1>{title}</h1></div><div className="refresh-control"><span>{loadedAt ? `Обновлено ${date(new Date(loadedAt).toISOString())} МСК` : "Загружаем данные"}</span><button disabled={loading || refreshing} onClick={() => void load(view, true)}>{refreshing ? "Обновляем…" : "Обновить данные"}</button></div></header>
      {["lotteries", "schedule", "draws", "analytics"].includes(view) && <div className="scope-toolbar"><SectionTabs label="Тип игр" value={scope} items={[{ id: "standard", label: "Лотереи" }, { id: "fast", label: "Fast" }, { id: "all", label: "Всё" }]} onChange={setScope} /><p>{scope === "standard" ? "Обычные лотереи. Быстрые тиражи и их выигрыши — в Fast." : scope === "fast" ? "Только быстрые игры: FLASH, SHADOW и PULSE." : "Полная картина: обычные лотереи и Fast вместе."} Игроки и Фонд Каспера общие.</p></div>}
      {error && <div className="error banner">{error}</div>}{loading && <div className="loading">ЗАГРУЖАЕМ ДАННЫЕ…</div>}
      {!loading && view === "dashboard" && dashboard && ticketAnalytics && <DashboardView data={dashboard} analytics={ticketAnalytics} refreshedAt={loadedAt} onOpen={openDraw} onNavigate={navigate} />}
      {!loading && view === "fast" && dashboard && ticketAnalytics && <FastDashboard data={dashboard} analytics={ticketAnalytics} refreshedAt={loadedAt} onOpen={openDraw} />}
      {!loading && view === "players" && <PlayersView players={players} search={playerSearch} onSearch={setPlayerSearch} onResults={applyPlayerResults} onReload={() => load("players")} />}
      {!loading && view === "lotteries" && <section className="stack">{visibleLotteries.filter((lottery) => lottery.is_active).map((lottery) => <LotteryCard key={lottery.id} lottery={lottery} onSaved={() => load("lotteries")} />)}</section>}
      {!loading && view === "schedule" && <ScheduleView key={scope} entries={scheduleEntries} lotteries={visibleLotteries} loadedAt={scheduleLoadedAt} />}
      {!loading && view === "draws" && <DrawsView key={scope} scope={scope} lotteries={visibleLotteries} onOpen={openDraw} />}
      {!loading && view === "analytics" && dashboard && ticketAnalytics && <AnalyticsView tab={analyticsTab} onTab={setAnalyticsTab} dashboard={dashboard} analytics={ticketAnalytics} lotteries={visibleLotteries} statistics={statistics} selectedLotteryId={statisticsLotteryId} windowSize={statisticsWindow} onLottery={setStatisticsLotteryId} onWindow={setStatisticsWindow} />}
      {!loading && view === "facts" && <InterestingFactsView facts={interestingFacts} lotteries={lotteries} onStatus={async (fact, factStatus) => { try { const updated = await adminApi.setInterestingFactStatus(fact.id, factStatus); setInterestingFacts((current) => current.map((item) => item.id === updated.id ? updated : item)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось изменить статус факта."); } }} />}
      {!loading && view === "broadcast" && <BroadcastTestView lotteries={lotteries} miniappUrl={session.miniapp_url} />}
      {!loading && view === "system" && <SystemView dashboard={dashboard} releaseNotes={releaseNotes} tab={systemTab} onTab={setSystemTab} transactions={transactions} notifications={notifications} audit={audit} onTransactions={(query) => void adminApi.transactions(query).then(setTransactions).catch((reason: Error) => setError(reason.message))} />}
    </main>{drawDetail && <DrawDetailPanel detail={drawDetail} onClose={() => setDrawDetail(null)} onOpenPlayer={openPlayerFromTicket} />}
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
      <div><span>История выпадений</span><h2>{report.lottery_name}</h2><p>Статистика начата заново с 1 сентября 2026 года. История тиражей и их номера не изменялись.</p></div>
      <article><small>УЧТЕНО ТИРАЖЕЙ</small><strong>{report.draw_count}</strong><span>{windowLabel}</span></article>
      <article><small>ЧАЩЕ ВСЕГО</small><strong>{hottest?.appearances ? numberLabel(hottest.number) : "—"}</strong><span>{hottest?.appearances ? `${hottest.appearances} выпадений` : "данные накапливаются"}</span></article>
      <article><small>РЕЖЕ ВСЕГО</small><strong>{coldest?.appearances || report.draw_count ? coldest ? numberLabel(coldest.number) : "—" : "—"}</strong><span>{coldest ? `${coldest.appearances} выпадений` : "данные накапливаются"}</span></article>
    </section>
    <section className="panel statistics-panel"><header><div><h2>Выпавшие числа</h2><span>{report.draw_count ? `${date(report.first_draw_at)} — ${date(report.last_draw_at)}` : "ПОКА НЕТ ЗАВЕРШЁННЫХ ТИРАЖЕЙ В ПЕРИОДЕ"}</span></div><div className="statistics-controls"><select aria-label="Лотерея" value={selectedLotteryId} onChange={(e) => onLottery(e.target.value)}>{eligibleLotteries.map((lottery) => <option value={lottery.id} key={lottery.id}>{lottery.name}</option>)}</select><select aria-label="Количество тиражей" value={windowSize} onChange={(e) => onWindow(Number(e.target.value))}><option value={0}>Все</option><option value={10}>10 тиражей</option><option value={20}>20 тиражей</option><option value={50}>50 тиражей</option><option value={100}>100 тиражей</option></select></div></header><div className="stat-grid">{report.numbers.map((row) => <article key={row.number}><i>{numberLabel(row.number)}</i><strong>{row.appearances}</strong><small>выпадений</small><div style={{ "--value": `${row.draw_percentage}%` } as CSSProperties}><span /></div><em>{row.draw_percentage}% тиражей</em><b>{row.draws_since_last === null ? "ещё не выпадало" : row.draws_since_last === 0 ? "в последнем тираже" : `${row.draws_since_last} тир. назад`}</b></article>)}</div><p className="source-note">Для Kasper Grand символ ★ обозначает специальное поле. Bingo здесь не показывается: в нём важен порядок закрытия строк, а не частота почти всех 60 шаров. Частота чисел нужна только для наблюдения за историей и не повышает вероятность следующего результата.</p></section>
  </>;
}
