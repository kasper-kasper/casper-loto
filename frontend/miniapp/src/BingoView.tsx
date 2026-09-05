import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, miniAppApi } from "./api";
import { countdown, formatCas, formatMoscow } from "./format";
import type { Lottery, Ticket } from "./types";
import "./bingo.css";

export interface BingoResult { moves: number[]; amounts: number[] }
interface PrintedTicket { id: string; public_number: number; numbers: number[]; price?: number; result?: BingoResult | null }
export interface BingoInventory { draw_id: string; draw_number: number; scheduled_at: string; price: number; has_more: boolean; tickets: PrintedTicket[] }
export interface BingoFeed { rules: { total_moves: number; jackpot_move: number; tour_prizes: number[]; pool_size: number }; server_time: string; draw: null | { draw_number: number; scheduled_at: string; complete: boolean; numbers: number[]; total_moves: number; jackpot_move: number; tour_prizes: number[]; stages: { move: number | null; winners: number }[]; tickets: PrintedTicket[] } }

function serial(draw: number, ticket: number) { return `KB-${String(draw).padStart(6, "0")}-${String(ticket).padStart(6, "0")}`; }

function BingoMark() { return <span className="bingo-mark" aria-hidden="true"><img src="/brand/kasper-symbol.svg" alt="" /></span>; }

export function BingoInvitation({ lottery, now, onOpen }: { lottery: Lottery; now: number; onOpen: () => void }) {
  return <button className="bingo-invitation" type="button" onClick={onOpen}>
    <span className="bingo-invite-top"><span>КАЖДЫЙ ВЕЧЕР · 22:00 МСК</span><span>ДЖЕКПОТ ВЕЧЕРА</span></span>
    <span className="bingo-invite-main"><span><strong>Kasper <em>Bingo</em></strong><small>Ваш вечерний ритуал</small></span><BingoMark /></span>
    <span className="bingo-invite-bottom"><span><small>ДЖЕКПОТ</small><b>{formatCas(lottery.jackpot)}</b></span><span className="bingo-arrow">↗</span></span>
    <span className="bingo-invite-date">{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК · ${countdown(lottery.scheduled_at, now)}` : "Открыть билеты и эфир"}</span>
  </button>;
}

function Paper({ ticket, draw, date, price, revealed = [], current, result, compact = false }: { ticket: PrintedTicket; draw: number; date: string; price: number; revealed?: number[]; current?: number; result?: BingoResult | null; compact?: boolean }) {
  const hits = new Set(revealed);
  const missingRows = [0, 1, 2].map(row => ticket.numbers.slice(row * 4, row * 4 + 4).filter(n => !hits.has(n)).length).sort((a, b) => a - b);
  return <article className={`bingo-paper ${compact ? "is-compact" : ""}`}>
    <header><BingoMark /><span>KASPER<strong>BINGO</strong></span><small>ТИРАЖ<b>№{String(draw).padStart(4, "0")}</b></small></header>
    {!compact && <div className="bingo-paper-date">{formatMoscow(date)} МСК <span>12 чисел · 3 строки</span></div>}
    <div className="bingo-grid">{[0, 1, 2].map(row => <div className={ticket.numbers.slice(row * 4, row * 4 + 4).every(n => hits.has(n)) ? "closed-row" : ""} key={row}>{ticket.numbers.slice(row * 4, row * 4 + 4).map(n => <span key={n} className={`${hits.has(n) ? "hit" : ""} ${current === n ? "current" : ""}`} aria-label={`${n}${hits.has(n) ? ", совпало" : ""}${current === n ? ", текущее число" : ""}`}><b>{String(n).padStart(2, "0")}</b>{hits.has(n) && <i aria-hidden="true">✓</i>}</span>)}</div>)}</div>
    <footer><span><small>СЕРИЙНЫЙ НОМЕР</small><b>{serial(draw, ticket.public_number)}</b></span><span><small>СТОИМОСТЬ</small><b>{formatCas(price)}</b></span></footer>
    {!compact && <div className="bingo-paper-seal"><span>✦</span> Счастье любит присутствие <span>✦</span></div>}
    {!compact && !result && revealed.length > 0 && <div className="bingo-ticket-progress"><span>До строки <b>{missingRows[0]}</b></span><span>До двух <b>{missingRows[0] + missingRows[1]}</b></span><span>До полного <b>{missingRows.reduce((a, b) => a + b, 0)}</b></span></div>}
    {result && <div className="bingo-ticket-result"><strong>{result.amounts.some(Boolean) ? `Ваш выигрыш · ${formatCas(result.amounts.reduce((a, b) => a + b, 0))}` : "В этот раз без выигрыша"}</strong><small>Совпало {ticket.numbers.filter(n => hits.has(n)).length} из 12</small>{result.amounts.map((amount, i) => amount > 0 && <p key={i}>{["Одна строка", "Две строки", "Джекпот"][i]} <b>{formatCas(amount)}</b></p>)}</div>}
  </article>;
}

export function BingoTicketDetail({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  return <PaperDialog onClose={onClose}><Paper ticket={ticket} draw={ticket.draw_number} date={ticket.scheduled_at} price={ticket.purchase_price} revealed={ticket.winning_numbers ?? []} result={ticket.bingo_result} /></PaperDialog>;
}

function PaperDialog({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const prior = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const key = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); if (event.key === "Tab") { event.preventDefault(); ref.current?.focus(); } };
    document.addEventListener("keydown", key);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", key); document.body.style.overflow = overflow; prior?.focus(); };
  }, [onClose]);
  return <div className="bingo-dialog-backdrop" role="presentation" onClick={onClose}><section className="bingo-dialog" role="dialog" aria-modal="true" aria-label="Билет Kasper Bingo" onClick={e => e.stopPropagation()}><button ref={ref} type="button" className="bingo-dialog-close" onClick={onClose} aria-label="Закрыть билет">×</button>{children}</section></div>;
}

export function BingoView({ lottery, initData, now, balance, onClose, onPurchased, initialTab = "choose" }: { initialTab?: "choose" | "live"; lottery: Lottery; initData: string; now: number; balance: number; onClose: () => void; onPurchased: () => Promise<unknown> }) {
  const [tab, setTab] = useState<"choose" | "live" | "mine">(initialTab);
  const [inventory, setInventory] = useState<BingoInventory | null>(null);
  const [selected, setSelected] = useState<PrintedTicket[]>([]);
  const [offset, setOffset] = useState(0);
  const [revision, setRevision] = useState(0);
  const [retry, setRetry] = useState(false);
  const inventoryDraw = useRef("");
  const [feed, setFeed] = useState<BingoFeed | null>(null);
  const [mine, setMine] = useState<Ticket[]>([]);
  const [opened, setOpened] = useState<PrintedTicket | null>(null);
  const [liveIndex, setLiveIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const pending = useRef<{ key: string; ids: string[]; draw: string } | null>(null);
  const refreshMine = useCallback(async () => { const page = await miniAppApi.tickets(initData, "active", "bingo"); setMine(page.tickets); }, [initData]);
  useEffect(() => {
    let active = true;
    void miniAppApi.bingoInventory(initData, offset).then(data => { if (active) { setInventory(data); if (inventoryDraw.current && inventoryDraw.current !== data.draw_id) setSelected([]); inventoryDraw.current = data.draw_id; } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты"); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [initData, offset, revision]);
  useEffect(() => { const timer = window.setTimeout(() => void refreshMine().catch(() => undefined), 0); return () => window.clearTimeout(timer); }, [refreshMine, feed?.draw?.complete]);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      if (!document.hidden) {
        try { const data = await miniAppApi.bingoLive(initData); if (active) setFeed(data); }
        catch { if (active && tab === "live") setError("Эфир переподключается. Выпавшие числа сохраняются."); }
      }
      if (active) timer = setTimeout(() => void poll(), tab === "live" ? 2000 : 10000);
    };
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [initData, tab]);
  const live = feed?.draw;
  const rules = feed?.rules;
  const liveTicket = live?.tickets[Math.min(liveIndex, live.tickets.length - 1)];
  const price = inventory?.price ?? lottery.ticket_price ?? 0;
  const total = selected.length * price;
  const available = Math.max(0, lottery.max_tickets_per_user_per_draw - lottery.player_ticket_count);
  const toggle = (ticket: PrintedTicket) => {
    if (busy || pending.current) return;
    setSelected(current => current.some(t => t.id === ticket.id) ? current.filter(t => t.id !== ticket.id) : current.length < available ? [...current, ticket] : current);
  };
  const buy = async () => {
    if (!inventory || !selected.length || busy) return;
    pending.current ??= { key: crypto.randomUUID(), ids: selected.map(t => t.id), draw: inventory.draw_id };
    setBusy(true); setError("");
    try {
      const result = await miniAppApi.bingoPurchase(initData, pending.current.draw, pending.current.ids, pending.current.key);
      pending.current = null; setRetry(false); setSelected([]);
      setNotice(`Ваши билеты готовы · ${result.ticket_ids.length} шт. · ${formatCas(result.total_cost)}`);
      await onPurchased(); await refreshMine(); setTab("mine");
      setInventory(await miniAppApi.bingoInventory(initData, 0)); setOffset(0);
    } catch (reason) {
      if (reason instanceof ApiError && reason.status >= 400 && reason.status < 500) {
        pending.current = null; setRetry(false);
        if (reason.status === 409) { setSelected([]); setRevision(v => v + 1); }
      } else setRetry(true);
      setError(reason instanceof ApiError && reason.status === 409 ? "Один из билетов уже купили или продажи завершены. Подборка обновлена — выберите свободные билеты." : reason instanceof Error ? reason.message : "Не удалось подтвердить покупку. Нажмите ещё раз — повторного списания не будет.");
    } finally { setBusy(false); }
  };
  const best = () => {
    if (!live?.tickets.length) return;
    const hits = new Set(live.numbers);
    const category = live.stages[0]?.winners ? live.stages[1]?.winners ? 2 : 1 : 0;
    const score = (t: PrintedTicket) => [0, 1, 2].map(row => t.numbers.slice(row * 4, row * 4 + 4).filter(n => !hits.has(n)).length).sort((a, b) => a - b).slice(0, category + 1).reduce((a, b) => a + b, 0);
    setLiveIndex(live.tickets.reduce((winner, t, i) => score(t) < score(live.tickets[winner]) ? i : winner, 0));
  };
  return <main className="app-shell bingo-page">
    <header className="bingo-topbar"><button type="button" onClick={onClose} aria-label="Вернуться к лотереям">←</button><span>KASPER <b>BINGO</b></span><small>{formatCas(balance)}</small></header>
    <section className="bingo-hero"><div className="bingo-hero-kicker"><span>ВЕЧЕР ОСОБОГО ЗНАЧЕНИЯ</span><span>✦ DAILY</span></div><div className="bingo-hero-title"><h1>Kasper<br /><em>Bingo.</em></h1><BingoMark /></div><p>Один вечер. Ваш билет. Большая история.</p><div className="bingo-jackpot"><small>НАКОПИТЕЛЬНЫЙ ДЖЕКПОТ</small><strong>{formatCas(lottery.jackpot).replace(" CAS", "")}<span>CAS</span></strong><p>Все 12 чисел до {rules?.jackpot_move ?? "…"}-го хода включительно</p></div><footer><span><small>БЛИЖАЙШИЙ ТИРАЖ · №{lottery.draw_number}</small><b>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Готовим расписание"}</b></span><time>{countdown(lottery.scheduled_at, now)}</time></footer></section>
    <div className="bingo-prizes"><div><small>01 / ОДНА СТРОКА</small><strong>{rules ? formatCas(rules.tour_prizes[0]) : "…"}</strong></div><div><small>02 / ДВЕ СТРОКИ</small><strong>{rules ? formatCas(rules.tour_prizes[1]) : "…"}</strong></div><div><small>03 / ПОЛНЫЙ БИЛЕТ</small><strong>Джекпот до хода {rules?.jackpot_move ?? "…"}</strong></div></div>
    <nav className="bingo-tabs" aria-label="Kasper Bingo"><button type="button" aria-pressed={tab === "choose"} onClick={() => setTab("choose")}>Выбрать билеты</button><button type="button" aria-pressed={tab === "mine"} onClick={() => setTab("mine")}>Мои · {mine.length}</button><button type="button" aria-pressed={tab === "live"} onClick={() => setTab("live")}>{live && !live.complete ? "● " : ""}Эфир</button></nav>
    {error && <div className="bingo-message is-error" role="alert">{error}<button type="button" onClick={() => setError("")} aria-label="Закрыть сообщение">×</button></div>}
    {notice && <div className="bingo-message" role="status">{notice}</div>}
    {tab === "choose" && <section className="bingo-selection"><div className="bingo-section-title"><span className="bingo-eyebrow">ВАША КОЛЛЕКЦИЯ УДАЧИ</span><h2>Найдите свой билет.</h2><p>Готовые числа. Настоящее предвкушение.</p></div><div className="bingo-selection-meta"><span>До {lottery.max_tickets_per_user_per_draw} билетов на тираж · осталось {available}</span><button type="button" disabled={loading || busy} onClick={() => { setLoading(true); setOffset(inventory?.has_more ? offset + 6 : 0); setRevision(v => v + 1); setError(""); }}>Другие билеты ↻</button></div>{loading ? <div className="bingo-loading">Печатаем вашу подборку…</div> : inventory?.tickets.length ? <div className="bingo-ticket-list">{inventory.tickets.map(ticket => <div className={`bingo-choice ${selected.some(t => t.id === ticket.id) ? "chosen" : ""}`} key={ticket.id}><button className="bingo-ticket-preview" type="button" onClick={() => toggle(ticket)} aria-pressed={selected.some(t => t.id === ticket.id)} aria-label={`Выбрать билет ${ticket.public_number}`}><Paper ticket={ticket} draw={inventory.draw_number} date={inventory.scheduled_at} price={price} compact /></button><button className="bingo-inspect" type="button" onClick={() => setOpened(ticket)}>Рассмотреть ↗</button><button className="bingo-select-button" type="button" disabled={busy || (!selected.some(t => t.id === ticket.id) && selected.length >= available)} aria-pressed={selected.some(t => t.id === ticket.id)} onClick={() => toggle(ticket)}>{selected.some(t => t.id === ticket.id) ? "✓ Билет выбран" : "+ Выбрать билет"}</button></div>)}</div> : <div className="bingo-empty">Свободные билеты появятся после открытия продаж.</div>}{selected.length > 0 && <div className="bingo-selected-chips" aria-label="Выбранные билеты">{selected.map(t => <button key={t.id} type="button" disabled={busy || retry} onClick={() => toggle(t)}>№{String(t.public_number).padStart(6, "0")} ×</button>)}</div>}{selected.length > 0 && <div className="bingo-checkout"><span><small>ВЫБРАНО · {selected.length}</small><strong>{formatCas(total)}</strong></span><button type="button" disabled={busy || total > balance} onClick={() => void buy()}>{busy ? "Оформляем…" : total > balance ? "Недостаточно CAS" : retry ? "Проверить покупку" : "Купить билеты ↗"}</button></div>}</section>}
    {tab === "mine" && <section className="bingo-mine"><div className="bingo-section-title"><span className="bingo-eyebrow">МЕСТО В ПЕРВОМ РЯДУ</span><h2>Ваши билеты.</h2><p>Во время эфира совпадения отметятся сами.</p></div>{mine.length ? mine.map(ticket => <button type="button" className="bingo-owned-row" key={ticket.id} onClick={() => setOpened({ ...ticket, price: ticket.purchase_price })}><span>✦</span><span><b>{serial(ticket.draw_number, ticket.public_number)}</b><small>{formatMoscow(ticket.scheduled_at)} МСК</small></span><span>↗</span></button>) : <div className="bingo-empty">Активных билетов пока нет. Выберите билет или посмотрите последний эфир.</div>}</section>}
    {tab === "live" && <section className="bingo-live"><div className="bingo-section-title"><span className="bingo-eyebrow">{live?.complete ? "ИТОГИ РОЗЫГРЫША" : "В ПРЯМОМ ЭФИРЕ"}</span><h2>{live ? `Тираж №${live.draw_number}` : "Встретимся в 22:00."}</h2></div>{live ? <><div className="bingo-draw-stage"><span className="bingo-live-status">{live.complete ? "ТИРАЖ ЗАВЕРШЁН" : "● ЭФИР"}</span><div className="bingo-current-ball" key={live.numbers.length}>{live.numbers.at(-1) ?? "✦"}</div><p>ХОД <strong>{live.numbers.length}</strong> / {live.total_moves}</p><div className="bingo-live-progress"><i style={{ width: `${live.numbers.length / live.total_moves * 100}%` }} /></div><div className="bingo-last-balls">{live.numbers.slice(-6).reverse().map((n, i) => <span className={i === 0 ? "latest" : ""} key={n}>{String(n).padStart(2, "0")}</span>)}</div></div><div className="bingo-stage-results">{live.stages.map((stage, i) => <div key={i}><span>{["Одна строка", "Две строки", "Джекпот"][i]}</span><b>{stage.winners ? `${stage.winners} бил. · ход ${stage.move}` : i === 2 && live.numbers.length >= live.jackpot_move ? "Переносится" : live.complete ? "Без победителя" : "Разыгрывается"}</b></div>)}</div>{liveTicket ? <><div className="bingo-live-controls"><button type="button" onClick={() => setLiveIndex(i => Math.max(0, i - 1))} disabled={liveIndex === 0} aria-label="Предыдущий билет">←</button><span>Билет {Math.min(liveIndex + 1, live.tickets.length)} / {live.tickets.length}</span><button type="button" onClick={best}>Лучший</button><button type="button" onClick={() => setLiveIndex(i => Math.min(live.tickets.length - 1, i + 1))} disabled={liveIndex >= live.tickets.length - 1} aria-label="Следующий билет">→</button></div><Paper ticket={liveTicket} draw={live.draw_number} date={live.scheduled_at} price={liveTicket.price ?? price} revealed={live.numbers} current={live.numbers.at(-1)} result={liveTicket.result} /></> : <div className="bingo-empty">В этом тираже у вас нет билетов. Наблюдать за эфиром можно без покупки.</div>}<details className="bingo-all-balls"><summary>Все выпавшие числа · {live.numbers.length}</summary><div>{live.numbers.map(n => <span key={n}>{n}</span>)}</div>{live.complete && <p>Не выпали: {Array.from({ length: 60 }, (_, i) => i + 1).filter(n => !live.numbers.includes(n)).join(" и ")}</p>}</details></> : <div className="bingo-empty">Первый эфир начнётся по расписанию. Здесь появятся выпавшие числа и ваши билеты.</div>}</section>}
    <details className="bingo-rules"><summary>Маленькие правила большого вечера <span>+</span></summary><p>В билете 12 уникальных чисел: 3 строки по 4. В эфире выпадают {rules?.total_moves ?? "…"} чисел из 60 без повторений. Два числа остаются невыпавшими.</p><p>Первый билет с любой закрытой строкой выигрывает первый тур. С любыми двумя — второй. Первый полностью закрытый билет до {rules?.jackpot_move ?? "…"}-го хода включительно выигрывает джекпот. После {rules?.jackpot_move ?? "…"}-го хода за полный билет приза нет.</p><p>На одном ходе приз делится между выигравшими билетами. Один билет может выиграть несколько туров. Остаток целых CAS распределяется по возрастанию серийных номеров. Непроданные билеты не участвуют.</p><p>Если победителя тура нет, его приз остаётся в фонде Каспера. Джекпот без победителя переносится. Вся стоимость билета пополняет джекпот; обычные призы и восстановление минимума оплачивает фонд Каспера.</p><p>Продажи закрываются за 2 минуты до начала. Тираж проводится при любом количестве билетов. Выбор билета не резервирует его до оплаты.</p></details>
    <footer className="bingo-page-footer">KASPER BINGO <span>✦</span> ВАШЕ ЛИЧНОЕ СОБЫТИЕ</footer>
    {opened && <PaperDialog onClose={() => setOpened(null)}><Paper ticket={opened} draw={mine.find(t => t.id === opened.id)?.draw_number ?? inventory?.draw_number ?? lottery.draw_number ?? 0} date={mine.find(t => t.id === opened.id)?.scheduled_at ?? inventory?.scheduled_at ?? lottery.scheduled_at ?? new Date().toISOString()} price={opened.price ?? price} /></PaperDialog>}
  </main>;
}
