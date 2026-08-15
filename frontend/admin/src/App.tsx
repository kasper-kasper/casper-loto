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
  Player,
  Transaction,
} from "./types";

type View = "dashboard" | "players" | "lotteries" | "draws" | "ledger" | "statistics" | "audit";

const navigation: { id: View; label: string; code: string }[] = [
  { id: "dashboard", label: "Overview", code: "01" },
  { id: "players", label: "Players", code: "02" },
  { id: "lotteries", label: "Lotteries", code: "03" },
  { id: "draws", label: "Draw archive", code: "04" },
  { id: "ledger", label: "CAS ledger", code: "05" },
  { id: "statistics", label: "Number intel", code: "06" },
  { id: "audit", label: "Admin audit", code: "07" },
];

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
      setError(reason instanceof Error ? reason.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand"><span>K</span><div>K-LOTO<small>CONTROL SYSTEM</small></div></div>
        <div className="secure-line"><i /> RESTRICTED ADMINISTRATIVE AREA</div>
        <h1>System access</h1>
        <p>Authenticate to inspect immutable history and execute audited changes.</p>
        <form onSubmit={(event) => void submit(event)}>
          <label>OPERATOR ID<input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} /></label>
          <label>PASSPHRASE<input autoComplete="current-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "VERIFYING…" : "ENTER CONTROL"}</button>
        </form>
      </section>
    </main>
  );
}

function DashboardView({ data }: { data: Dashboard }) {
  const metrics = [
    ["Players", data.counts.users],
    ["Tickets", data.counts.tickets],
    ["Completed draws", data.counts.completed_draws],
    ["Open / recovery", data.counts.pending_draws],
  ];
  return <>
    <div className="system-strip">
      <Status active={data.database_healthy}>DATABASE ONLINE</Status>
      <Status active={data.scheduler_enabled}>SCHEDULER {data.scheduler_enabled ? "ACTIVE" : "DISABLED"}</Status>
      <Status active={data.bot_configured}>BOT {data.bot_configured ? "CONFIGURED" : "NOT CONFIGURED"}</Status>
      <span>v{data.version} · uptime {Math.floor(data.uptime_seconds / 60)}m</span>
    </div>
    <section className="metric-grid">{metrics.map(([label, value]) => <article className="metric" key={label}><small>{label}</small><strong>{value}</strong><div className="scan" /></article>)}</section>
    <div className="split">
      <section className="panel"><header><h2>Funds monitor</h2><span>LIVE STATE</span></header>
        <div className="fund-list">{data.lotteries.map((lottery) => <article key={lottery.id}><div><b>{lottery.name}</b><small>DRAW {lottery.next_draw_number ? drawNumber(lottery.next_draw_number) : "—"}</small></div><dl><dt>JACKPOT</dt><dd>{cas(lottery.current_jackpot)}</dd><dt>DISTRIBUTION</dt><dd>{cas(lottery.distribution_fund)}</dd><dt>RESERVE</dt><dd>{cas(lottery.reserve)}</dd></dl></article>)}</div>
      </section>
      <section className="panel"><header><h2>Recent draws</h2><span>IMMUTABLE</span></header><DrawTable draws={data.recent_draws} /></section>
    </div>
    <section className="panel"><header><h2>Latest ledger movements</h2><span>TRACEABLE CAS</span></header><TransactionTable rows={data.recent_transactions} /></section>
  </>;
}

function PlayerCard({ player, onSaved }: { player: Player; onSaved: () => Promise<void> }) {
  const [amount, setAmount] = useState(String(player.balance));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [webUsername, setWebUsername] = useState("");
  const [webPassword, setWebPassword] = useState("");
  const save = async () => {
    setBusy(true);
    try {
      await adminApi.setBalance(player.id, Number(amount), reason);
      setReason("");
      await onSaved();
    } finally { setBusy(false); }
  };
  const saveWeb = async () => {
    setBusy(true);
    try {
      await adminApi.configureWebAccount(player.id, webUsername, webPassword, reason);
      setWebPassword("");
      await onSaved();
    } finally { setBusy(false); }
  };
  return <article className="player-card">
    <div className="player-head"><div className="avatar">{player.display_name.slice(0, 1)}</div><div><h3>{player.display_name}</h3><small>@{player.username ?? "no_username"} · TG {player.telegram_id ?? "—"}</small></div><Status active={player.is_active}>{player.is_active ? "ACTIVE" : "DISABLED"}</Status></div>
    <div className="player-stats"><span><small>BALANCE</small><b>{cas(player.balance)}</b></span><span><small>TICKETS</small><b>{player.ticket_count}</b></span><span><small>SPENT</small><b>{cas(player.spent)}</b></span><span><small>WON</small><b>{cas(player.won)}</b></span><span><small>NET</small><b className={player.net >= 0 ? "positive" : "negative"}>{cas(player.net)}</b></span></div>
    <div className="adjust"><label>New balance<input min="0" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} /></label><label>Mandatory reason<input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why is this adjustment needed?" /></label><button disabled={busy || !reason.trim()} onClick={() => void save()}>SET VIA LEDGER</button></div>
    <div className="adjust"><label>Web username<input value={webUsername} onChange={(e) => setWebUsername(e.target.value)} /></label><label>New Web password<input type="password" value={webPassword} onChange={(e) => setWebPassword(e.target.value)} /></label><button disabled={busy || !reason.trim() || webUsername.length < 3 || webPassword.length < 12} onClick={() => void saveWeb()}>SET WEB ACCESS</button></div>
  </article>;
}

function LotteryCard({ lottery, onSaved }: { lottery: Lottery; onSaved: () => Promise<void> }) {
  const [price, setPrice] = useState(String(lottery.ticket_price ?? 0));
  const [base, setBase] = useState(String(lottery.base_jackpot));
  const [reserve, setReserve] = useState(String(lottery.reserve));
  const [reason, setReason] = useState("");
  const configure = async () => { await adminApi.configureLottery(lottery.id, Number(price), Number(base), reason); setReason(""); await onSaved(); };
  const fundReserve = async () => { await adminApi.setReserve(lottery.id, Number(reserve), reason); setReason(""); await onSaved(); };
  return <article className="lottery-card">
    <header><div><small>{lottery.kind}</small><h2>{lottery.name}</h2></div><Status active={lottery.is_active}>{lottery.is_active ? "ACTIVE" : "INACTIVE"}</Status></header>
    <div className="fund-matrix"><span><small>CURRENT JACKPOT</small><b>{cas(lottery.current_jackpot)}</b></span><span><small>DISTRIBUTION</small><b>{cas(lottery.distribution_fund)}</b></span><span><small>NEXT DRAW</small><b>{lottery.next_draw_number ? `#${drawNumber(lottery.next_draw_number)}` : "—"}</b><em>{date(lottery.next_draw_at)}</em></span></div>
    <div className="config-grid"><label>Ticket price, CAS<input type="number" min="1" value={price} onChange={(e) => setPrice(e.target.value)} /></label><label>Base jackpot, CAS<input type="number" min="0" value={base} onChange={(e) => setBase(e.target.value)} /></label><label>Reserve, CAS<input type="number" min="0" value={reserve} onChange={(e) => setReserve(e.target.value)} /></label></div>
    <label className="reason">Mandatory audit reason<input value={reason} onChange={(e) => setReason(e.target.value)} /></label>
    <div className="actions"><button disabled={!reason.trim()} onClick={() => void configure()}>SAVE CONFIGURATION</button><button disabled={!reason.trim()} onClick={() => void fundReserve()}>ADJUST RESERVE VIA LEDGER</button></div>
    <footer>Schedule: <code>{JSON.stringify(lottery.schedule)}</code> · cutoff {lottery.sales_cutoff_minutes ?? "—"} min. Schedule and payout editing are locked pending approved rules.</footer>
  </article>;
}

function DrawTable({ draws, onOpen }: { draws: Draw[]; onOpen?: (id: string) => void }) {
  return <div className="table-wrap"><table><thead><tr><th>Lottery / Draw</th><th>Status</th><th>Schedule</th><th>Numbers</th><th>Tickets</th><th>Sales / Payout</th></tr></thead><tbody>{draws.map((draw) => <tr key={draw.id} onClick={() => onOpen?.(draw.id)} className={onOpen ? "clickable" : ""}><td><b>{draw.lottery_code.toUpperCase()}</b> #{drawNumber(draw.public_number)}</td><td><span className={`tag ${draw.status.toLowerCase()}`}>{draw.status}</span></td><td>{date(draw.scheduled_at)}</td><td><div className="number-line">{draw.winning_numbers?.map((n) => <i key={n}>{n}</i>) ?? "—"}</div></td><td>{draw.ticket_count}</td><td>{cas(draw.total_sales)}<small>{cas(draw.total_payout)}</small></td></tr>)}</tbody></table></div>;
}

function TransactionTable({ rows }: { rows: Transaction[] }) {
  return <div className="table-wrap"><table><thead><tr><th>Timestamp</th><th>Type</th><th>Account</th><th>Delta</th><th>Before → After</th><th>Trace</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{date(row.created_at)}</td><td><span className="tag">{row.type}</span></td><td>{row.account_kind}</td><td className={row.amount >= 0 ? "positive" : "negative"}>{row.amount > 0 ? "+" : ""}{cas(row.amount)}</td><td>{cas(row.balance_before)} → {cas(row.balance_after)}</td><td><code>{row.operation_id.slice(0, 8)}</code></td></tr>)}</tbody></table></div>;
}

function DrawDetailPanel({ detail, onClose }: { detail: DrawDetail; onClose: () => void }) {
  const draw = detail.draw;
  return <div className="drawer"><button className="close" onClick={onClose}>×</button><small>IMMUTABLE DRAW RECORD</small><h2>{draw.lottery_code.toUpperCase()} #{drawNumber(draw.public_number)}</h2><div className="winning">{draw.winning_numbers?.map((n) => <i key={n}>{n}</i>) ?? "NO RESULT"}</div><dl className="detail-list"><dt>Status</dt><dd>{draw.status}</dd><dt>Scheduled</dt><dd>{date(draw.scheduled_at)}</dd><dt>Executed</dt><dd>{date(draw.executed_at)}</dd><dt>Sales</dt><dd>{cas(draw.total_sales)}</dd><dt>Payout</dt><dd>{cas(draw.total_payout)}</dd><dt>Reserve used</dt><dd>{cas(draw.reserve_used)}</dd><dt>Correlation</dt><dd><code>{draw.correlation_id}</code></dd></dl><h3>Tickets ({detail.tickets.length})</h3>{detail.tickets.map((ticket) => <div className="ticket-row" key={ticket.id}><b>#{drawNumber(ticket.public_number)}</b><span>{ticket.numbers.join(" · ")}</span><span>{ticket.matches ?? "—"} match</span><strong>{cas(ticket.prize_amount)}</strong></div>)}</div>;
}

export default function App() {
  const [session, setSession] = useState<AdminSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [view, setView] = useState<View>("dashboard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [lotteries, setLotteries] = useState<Lottery[]>([]);
  const [draws, setDraws] = useState<Draw[]>([]);
  const [drawDetail, setDrawDetail] = useState<DrawDetail | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [statistics, setStatistics] = useState<NumberStatistic[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);

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
      if (target === "statistics") {
        const available = await adminApi.lotteries();
        setLotteries(available);
        if (available[0]) setStatistics(await adminApi.statistics(available[0].id));
      }
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) setSession(null);
      setError(reason instanceof Error ? reason.message : "Admin request failed.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!session) return;
    const task = window.setTimeout(() => void load(view), 0);
    return () => window.clearTimeout(task);
  }, [session, view, load]);

  if (checking) return <main className="boot">K-LOTO // VERIFYING SESSION</main>;
  if (!session) return <Login onAuthenticated={setSession} />;

  const title = navigation.find((item) => item.id === view)?.label ?? "Control";
  return <div className="admin-shell">
    <aside><div className="brand"><span>K</span><div>K-LOTO<small>CONTROL SYSTEM</small></div></div><nav>{navigation.map((item) => <button className={view === item.id ? "active" : ""} key={item.id} onClick={() => setView(item.id)}><small>{item.code}</small>{item.label}</button>)}</nav><div className="operator"><small>AUTHENTICATED OPERATOR</small><b>{session.username}</b><button onClick={() => void adminApi.logout().finally(() => setSession(null))}>TERMINATE SESSION</button></div></aside>
    <main className="workspace"><header className="topbar"><div><small>K-LOTO / ADMIN / {view.toUpperCase()}</small><h1>{title}</h1></div><span className="utc">UTC {new Date().toISOString().slice(11, 19)}</span></header>
      {error && <div className="error banner">{error}</div>}{loading && <div className="loading">QUERYING SYSTEM…</div>}
      {!loading && view === "dashboard" && dashboard && <DashboardView data={dashboard} />}
      {!loading && view === "players" && <section className="stack">{players.map((player) => <PlayerCard key={player.id} player={player} onSaved={() => load("players")} />)}</section>}
      {!loading && view === "lotteries" && <section className="stack">{lotteries.map((lottery) => <LotteryCard key={lottery.id} lottery={lottery} onSaved={() => load("lotteries")} />)}</section>}
      {!loading && view === "draws" && <section className="panel"><header><h2>Permanent draw archive</h2><span>READ ONLY</span></header><DrawTable draws={draws} onOpen={(id) => void adminApi.draw(id).then(setDrawDetail)} /></section>}
      {!loading && view === "ledger" && <><TransactionFilters onApply={(query) => void adminApi.transactions(query).then(setTransactions).catch((reason: Error) => setError(reason.message))} /><section className="panel"><header><h2>Immutable CAS ledger</h2><span>{transactions.length} RECORDS</span></header><TransactionTable rows={transactions} /></section></>}
      {!loading && view === "statistics" && <StatisticsView lotteries={lotteries} rows={statistics} onLottery={(id) => void adminApi.statistics(id).then(setStatistics)} />}
      {!loading && view === "audit" && <section className="panel"><header><h2>Administrator audit</h2><span>PERMANENT</span></header><div className="audit-list">{audit.map((item) => <article key={item.id}><time>{date(item.created_at)}</time><b>{item.action} · {item.entity_type}</b><p>{item.reason ?? "No reason"}</p><code>{JSON.stringify(item.old_values)} → {JSON.stringify(item.new_values)}</code></article>)}</div></section>}
    </main>{drawDetail && <DrawDetailPanel detail={drawDetail} onClose={() => setDrawDetail(null)} />}
  </div>;
}

function TransactionFilters({ onApply }: { onApply: (query: string) => void }) {
  const [values, setValues] = useState({ type: "", user_id: "", lottery_id: "", draw_id: "", ticket_id: "", date_from: "", date_to: "" });
  const apply = (event: FormEvent) => { event.preventDefault(); const params = new URLSearchParams(); Object.entries(values).forEach(([key, value]) => { if (value) params.set(key, key.startsWith("date_") ? new Date(value).toISOString() : value); }); onApply(params.toString()); };
  return <form className="filters" onSubmit={apply}><select aria-label="Transaction type" value={values.type} onChange={(e) => setValues({ ...values, type: e.target.value })}><option value="">All transaction types</option>{["ADMIN_BALANCE_ADJUSTMENT", "TICKET_PURCHASE", "PRIZE_PAYOUT", "JACKPOT_PAYOUT", "RESERVE_ADJUSTMENT", "SYSTEM_ADJUSTMENT"].map((type) => <option key={type}>{type}</option>)}</select>{["user_id", "lottery_id", "draw_id", "ticket_id"].map((key) => <input key={key} placeholder={key} value={values[key as keyof typeof values]} onChange={(e) => setValues({ ...values, [key]: e.target.value })} />)}<input aria-label="From date" type="datetime-local" value={values.date_from} onChange={(e) => setValues({ ...values, date_from: e.target.value })} /><input aria-label="To date" type="datetime-local" value={values.date_to} onChange={(e) => setValues({ ...values, date_to: e.target.value })} /><button>APPLY FILTERS</button></form>;
}

function StatisticsView({ lotteries, rows, onLottery }: { lotteries: Lottery[]; rows: NumberStatistic[]; onLottery: (id: string) => void }) {
  return <section className="panel"><header><h2>Number appearance intelligence</h2><select aria-label="Lottery" onChange={(e) => onLottery(e.target.value)}>{lotteries.map((lottery) => <option value={lottery.id} key={lottery.id}>{lottery.name}</option>)}</select></header><div className="stat-grid">{rows.map((row) => <article key={row.number}><i>{row.number}</i><strong>{row.appearances}</strong><small>appearances</small><div style={{ "--value": `${row.draw_percentage}%` } as CSSProperties}><span /></div><em>{row.draw_percentage}% · since last: {row.draws_since_last ?? "never"}</em></article>)}</div><p className="source-note">Calculated from immutable completed draw history. This view is not a stored source of truth.</p></section>;
}
