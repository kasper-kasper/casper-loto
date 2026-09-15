import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, miniAppApi } from "./api";
import { countdown, formatCas, formatMoscow } from "./format";
import type { Lottery, PurchaseResult, Ticket } from "./types";
import "./bingo.css";

export interface BingoResult { moves: number[]; amounts: number[] }
interface PrintedTicket { id: string; public_number?: number; pool_position?: number; numbers: number[]; price?: number; result?: BingoResult | null }
export interface BingoInventory { draw_id: string; draw_number: number; scheduled_at: string; price: number; has_more: boolean; kasper_set_available: boolean; tickets: PrintedTicket[] }
export interface BingoFeed { rules: { total_moves: number; jackpot_move: number; tour_moves: number[]; tour_prizes: number[]; pool_size: number }; server_time: string; draw: null | { draw_number: number; scheduled_at: string; complete: boolean; numbers: number[]; total_moves: number; jackpot_move: number; tour_prizes: number[]; stages: { move: number | null; winners: number }[]; tickets: PrintedTicket[] } }

function serial(ticket: number) { return `KB-${String(ticket).padStart(6, "0")}`; }

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
    <footer><span><small>{ticket.public_number ? "СЕРИЙНЫЙ НОМЕР" : "ДО ПОКУПКИ"}</small><b>{ticket.public_number ? serial(ticket.public_number) : "ВАРИАНТ БИЛЕТА"}</b></span><span><small>СТОИМОСТЬ</small><b>{formatCas(price)}</b></span></footer>
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

export function BingoView({ lottery, initData, now, balance, onClose, onPurchased, initialTab = "choose" }: { initialTab?: "choose" | "live"; lottery: Lottery; initData: string; now: number; balance: number; onClose: () => void; onPurchased: (result: PurchaseResult) => void }) {
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
  const [autoBest, setAutoBest] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [favoriteInputs, setFavoriteInputs] = useState(["", "", ""]);
  const [favoriteNumbers, setFavoriteNumbers] = useState<number[]>([]);
  const [favoriteError, setFavoriteError] = useState("");
  const [retrySelection, setRetrySelection] = useState<{ ticketIds?: string[]; quantity?: number; requiredNumbers?: number[] } | null>(null);
  const pending = useRef<{ key: string; selection: { ticketIds?: string[]; quantity?: number; requiredNumbers?: number[] }; draw: string } | null>(null);
  const refreshMine = useCallback(async () => { const page = await miniAppApi.tickets(initData, "active", "bingo"); setMine(page.tickets); }, [initData]);
  useEffect(() => {
    let active = true;
    void miniAppApi.bingoInventory(initData, offset, favoriteNumbers).then(data => { if (active) { setInventory(data); setFavoriteError(""); if (inventoryDraw.current && inventoryDraw.current !== data.draw_id) setSelected([]); inventoryDraw.current = data.draw_id; } }).catch((reason: unknown) => { if (active) { if (favoriteNumbers.length > 0) setFavoriteError("Поиск не сработал. Попробуйте ещё раз."); else setError(reason instanceof Error ? reason.message : "Не удалось загрузить билеты"); } }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [favoriteNumbers, initData, offset, revision]);
  useEffect(() => { const timer = window.setTimeout(() => void refreshMine().catch(() => undefined), 0); return () => window.clearTimeout(timer); }, [refreshMine, feed?.draw?.complete]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 2600);
    return () => window.clearTimeout(timer);
  }, [notice]);
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
  const bestIndex = useMemo(() => {
    if (!live?.tickets.length) return 0;
    const hits = new Set(live.numbers);
    const rowsToCount = live.numbers.length < 18 ? 1 : live.numbers.length < 34 ? 2 : 3;
    const score = (ticket: PrintedTicket) => [0, 1, 2].map(row => ticket.numbers.slice(row * 4, row * 4 + 4).filter(number => !hits.has(number)).length).sort((a, b) => a - b).slice(0, rowsToCount).reduce((a, b) => a + b, 0);
    return live.tickets.reduce((winner, ticket, index) => score(ticket) < score(live.tickets[winner]) ? index : winner, 0);
  }, [live]);
  const shownLiveIndex = autoBest ? bestIndex : Math.min(liveIndex, Math.max(0, (live?.tickets.length ?? 1) - 1));
  const liveTicket = live?.tickets[shownLiveIndex];
  const price = inventory?.price ?? lottery.ticket_price ?? 0;
  const total = selected.length * price;
  const available = Math.max(0, lottery.max_tickets_per_user_per_draw - lottery.player_ticket_count);
  const affordable = price > 0 ? Math.floor(balance / price) : 0;
  const quickAll = Math.min(available, affordable);
  const hasFavoriteNumber = favoriteInputs.some(value => value.trim() !== "");
  const toggle = (ticket: PrintedTicket) => {
    if (busy || pending.current) return;
    setSelected(current => current.some(t => t.id === ticket.id) ? current.filter(t => t.id !== ticket.id) : current.length < available ? [...current, ticket] : current);
  };
  const purchase = async (selection: { ticketIds?: string[]; quantity?: number; requiredNumbers?: number[] }) => {
    if (!inventory || busy) return;
    pending.current ??= { key: crypto.randomUUID(), selection, draw: inventory.draw_id };
    setBusy(true); setError("");
    try {
      const result = await miniAppApi.bingoPurchase(initData, pending.current.draw, pending.current.selection, pending.current.key);
      pending.current = null; setRetry(false); setRetrySelection(null); setSelected([]);
      setNotice(`Куплено: ${result.ticket_ids.length} · ${formatCas(result.total_cost)}`);
      onPurchased(result);
      void Promise.allSettled([refreshMine(), miniAppApi.bingoInventory(initData, 0, favoriteNumbers)]).then(([, inventoryRefresh]) => {
        if (inventoryRefresh.status === "fulfilled") { setInventory(inventoryRefresh.value); setOffset(0); }
      });
    } catch (reason) {
      if (reason instanceof ApiError && reason.status >= 400 && reason.status < 500) {
        pending.current = null; setRetry(false); setRetrySelection(null);
        if (reason.status === 409) { setSelected([]); setRevision(v => v + 1); }
      } else { setRetry(true); setRetrySelection(pending.current?.selection ?? selection); }
      setError(reason instanceof ApiError && reason.status === 409 ? "Один из билетов уже купили или продажи завершены. Подборка обновлена — выберите свободные билеты." : reason instanceof Error ? reason.message : "Не удалось подтвердить покупку. Нажмите ещё раз — повторного списания не будет.");
    } finally { setBusy(false); }
  };
  const buy = () => purchase({ ticketIds: selected.map(t => t.id) });
  const quickBuy = (quantity: number, requiredNumbers: number[] = []) => {
    if (quantity > 0) void purchase({ quantity, requiredNumbers });
  };
  const searchFavorites = () => {
    const values = favoriteInputs.filter(value => value.trim() !== "").map(Number);
    if (values.length === 0 || values.some(value => !Number.isInteger(value) || value < 1 || value > 60) || new Set(values).size !== values.length) {
      setFavoriteError("Введите до трёх разных чисел от 1 до 60.");
      return;
    }
    setFavoriteError(""); setError(""); setSelected([]); setOffset(0); setLoading(true); setFavoriteNumbers(values);
  };
  return <main className="app-shell bingo-page">
    <header className="bingo-topbar"><button type="button" onClick={onClose} aria-label="Вернуться к лотереям">←</button><span>KASPER <b>BINGO</b></span><small>{formatCas(balance)}</small></header>
    {tab !== "live" && <><section className="bingo-hero"><div className="bingo-hero-kicker"><span>ВЕЧЕР ОСОБОГО ЗНАЧЕНИЯ</span><span>✦ DAILY</span></div><div className="bingo-hero-title"><h1>Kasper<br /><em>Bingo.</em></h1><BingoMark /></div><p>Один вечер. Ваш билет. Большая история.</p><div className="bingo-jackpot"><small>НАКОПИТЕЛЬНЫЙ ДЖЕКПОТ</small><strong>{formatCas(lottery.jackpot).replace(" CAS", "")}<span>CAS</span></strong><p>Все 12 чисел до {rules?.jackpot_move ?? "…"}-го хода</p></div><footer><span><small>БЛИЖАЙШИЙ ТИРАЖ · №{lottery.draw_number}</small><b>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Готовим расписание"}</b></span><time>{countdown(lottery.scheduled_at, now)}</time></footer></section>
    <div className="bingo-prizes"><div><small>СТРОКА · ДО {rules?.tour_moves[0] ?? 18}</small><strong>{rules ? formatCas(rules.tour_prizes[0]) : "…"}</strong></div><div><small>ДВЕ · ДО {rules?.tour_moves[1] ?? 34}</small><strong>{rules ? formatCas(rules.tour_prizes[1]) : "…"}</strong></div><div><small>ПОЛНЫЙ · ДО {rules?.jackpot_move ?? 28}</small><strong>Джекпот</strong></div></div></>}
    <nav className="bingo-tabs" aria-label="Kasper Bingo"><button type="button" aria-pressed={tab === "choose"} onClick={() => setTab("choose")}>Выбрать билеты</button><button type="button" aria-pressed={tab === "mine"} onClick={() => setTab("mine")}>Мои · {mine.length}</button><button type="button" aria-pressed={tab === "live"} onClick={() => setTab("live")}>{live && !live.complete ? "● " : ""}Эфир</button></nav>
    {error && <div className="bingo-message is-error" role="alert"><span>{error}</span>{retry && retrySelection && <button type="button" onClick={() => void purchase(retrySelection)}>Проверить покупку</button>}<button type="button" onClick={() => setError("")} aria-label="Закрыть сообщение">×</button></div>}
    {notice && <div className="bingo-message" role="status"><span>{notice}</span><button type="button" onClick={() => { setNotice(""); setTab("mine"); }}>Мои билеты →</button></div>}
    {tab === "choose" && <section className="bingo-selection">
      <div className="bingo-section-title"><span className="bingo-eyebrow">БИЛЕТНАЯ КАССА</span><h2>Как играет удача?</h2><p>Мгновенно, по любимым числам или с личным выбором.</p></div>
      <div className="bingo-buy-studio">
        <div className="bingo-quick-buy">
          <span>БЫСТРЫЙ ВЫБОР</span>
          <div>{[1, 5, 10].map(quantity => <button key={quantity} type="button" disabled={busy || quantity > quickAll} onClick={() => quickBuy(quantity)}>Купить {quantity}</button>)}</div>
          <button className="bingo-buy-all" type="button" disabled={busy || quickAll < 1} onClick={() => quickBuy(quickAll)}>Купить все доступные · {quickAll}</button>
        </div>
        <button className="bingo-kasper-set" type="button" disabled={busy || available < 10 || affordable < 10 || !inventory?.kasper_set_available} onClick={() => quickBuy(10, [28, 16, 2, 9])}>
          <span>✦ НАБОР КАСПЕРА</span><strong>10 случайных билетов</strong><small>В каждом: 2 · 9 · 16 · 28</small><b>{inventory?.kasper_set_available ? formatCas(price * 10) : "Уже выбран"}</b>
        </button>
        <form className="bingo-favorite-search" onSubmit={event => { event.preventDefault(); searchFavorites(); }}>
          <span>ЛЮБИМЫЕ ЧИСЛА · ДО ТРЁХ</span>
          <div>{favoriteInputs.map((value, index) => <input key={index} type="number" min="1" max="60" inputMode="numeric" aria-label={`Любимое число ${index + 1}`} value={value} onChange={event => { setFavoriteError(""); setFavoriteInputs(current => current.map((item, itemIndex) => itemIndex === index ? event.target.value : item)); }} />)}</div>
          <button type="submit" disabled={busy || !hasFavoriteNumber}>Найти билеты</button>
          {favoriteError && <small className="bingo-search-feedback is-error" role="alert">{favoriteError}</small>}
          {favoriteNumbers.length > 0 && !loading && !favoriteError && <small className={`bingo-search-feedback ${inventory?.tickets.length ? "" : "is-error"}`}>{inventory?.tickets.length ? `Нашли варианты: ${inventory.tickets.length}` : "Свободных билетов с этими числами нет. Измените выбор."}</small>}
          {favoriteNumbers.length > 0 && <button className="bingo-search-reset" type="button" onClick={() => { setFavoriteError(""); setFavoriteNumbers([]); setFavoriteInputs(["", "", ""]); setOffset(0); setLoading(true); }}>Показать все</button>}
        </form>
      </div>
      <div className="bingo-selection-meta"><span>{favoriteNumbers.length ? `Билеты с числами ${favoriteNumbers.join(" · ")}` : `Можно купить ещё ${available}`}</span><button type="button" disabled={loading || busy} onClick={() => { setLoading(true); setOffset(inventory?.has_more ? offset + 6 : 0); setRevision(v => v + 1); setError(""); }}>Другие билеты ↻</button></div>
      {loading ? <div className="bingo-loading">Подбираем билеты…</div> : inventory?.tickets.length ? <div className="bingo-ticket-list">{inventory.tickets.map(ticket => <div className={`bingo-choice ${selected.some(t => t.id === ticket.id) ? "chosen" : ""}`} key={ticket.id}><button className="bingo-ticket-preview" type="button" onClick={() => toggle(ticket)} aria-pressed={selected.some(t => t.id === ticket.id)} aria-label="Выбрать вариант билета"><Paper ticket={ticket} draw={inventory.draw_number} date={inventory.scheduled_at} price={price} compact /></button><button className="bingo-inspect" type="button" onClick={() => setOpened(ticket)}>Рассмотреть ↗</button><button className="bingo-select-button" type="button" disabled={busy || (!selected.some(t => t.id === ticket.id) && selected.length >= available)} aria-pressed={selected.some(t => t.id === ticket.id)} onClick={() => toggle(ticket)}>{selected.some(t => t.id === ticket.id) ? "✓ Билет выбран" : "+ Выбрать билет"}</button></div>)}</div> : <div className="bingo-empty">Подходящих свободных билетов нет.</div>}
      {selected.length > 0 && <div className="bingo-selected-chips" aria-label="Выбранные билеты">{selected.map((ticket, index) => <button key={ticket.id} type="button" disabled={busy || retry} onClick={() => toggle(ticket)}>Вариант {index + 1} ×</button>)}</div>}
      {selected.length > 0 && <div className="bingo-checkout"><span><small>ВЫБРАНО · {selected.length}</small><strong>{formatCas(total)}</strong></span><button type="button" disabled={busy || total > balance} onClick={() => void buy()}>{busy ? "Оформляем…" : total > balance ? "Недостаточно CAS" : "Купить билеты ↗"}</button></div>}
    </section>}
    {tab === "mine" && <section className="bingo-mine"><div className="bingo-section-title"><span className="bingo-eyebrow">МЕСТО В ПЕРВОМ РЯДУ</span><h2>Ваши билеты.</h2><p>Во время эфира совпадения отметятся сами.</p></div>{mine.length ? mine.map(ticket => <button type="button" className="bingo-owned-row" key={ticket.id} onClick={() => setOpened({ ...ticket, price: ticket.purchase_price })}><span>✦</span><span><b>{serial(ticket.public_number)}</b><small>Тираж №{ticket.draw_number} · {formatMoscow(ticket.scheduled_at)} МСК</small></span><span>↗</span></button>) : <div className="bingo-empty">Активных билетов пока нет. Выберите билет или посмотрите последний эфир.</div>}</section>}
    {tab === "live" && <section className="bingo-live">
      <div className="bingo-section-title"><span className="bingo-eyebrow">{live?.complete ? "ИТОГИ РОЗЫГРЫША" : "В ПРЯМОМ ЭФИРЕ"}</span><h2>{live ? `Тираж №${live.draw_number}` : "Встретимся в 22:00."}</h2></div>
      {live ? <>
        <div className="bingo-draw-stage"><span className="bingo-live-status">{live.complete ? "ТИРАЖ ЗАВЕРШЁН" : "● ЭФИР"}</span><div className="bingo-current-ball" key={live.numbers.length}>{live.numbers.at(-1) ?? "✦"}</div><p>ХОД <strong>{live.numbers.length}</strong> / {live.total_moves}</p><div className="bingo-live-progress"><i style={{ width: `${live.numbers.length / live.total_moves * 100}%` }} /></div><div className="bingo-last-balls">{live.numbers.slice(-6).reverse().map((number, index) => <span className={index === 0 ? "latest" : ""} key={number}>{String(number).padStart(2, "0")}</span>)}</div></div>
        {liveTicket ? <><div className="bingo-live-controls"><button type="button" onClick={() => { setAutoBest(false); setLiveIndex(Math.max(0, shownLiveIndex - 1)); }} disabled={shownLiveIndex === 0} aria-label="Предыдущий билет">←</button><span>Билет {shownLiveIndex + 1} / {live.tickets.length}</span><button type="button" aria-pressed={autoBest} onClick={() => setAutoBest(value => !value)}>Авто</button><button type="button" onClick={() => { setAutoBest(false); setLiveIndex(Math.min(live.tickets.length - 1, shownLiveIndex + 1)); }} disabled={shownLiveIndex >= live.tickets.length - 1} aria-label="Следующий билет">→</button></div><Paper ticket={liveTicket} draw={live.draw_number} date={live.scheduled_at} price={liveTicket.price ?? price} revealed={live.numbers} current={live.numbers.at(-1)} result={liveTicket.result} /></> : <div className="bingo-empty">В этом тираже у вас нет билетов. Смотреть эфир можно без покупки.</div>}
        <div className="bingo-stage-results">{live.stages.map((stage, index) => { const cutoff = index === 2 ? live.jackpot_move : rules?.tour_moves[index] ?? [18, 34][index]; return <div key={index}><span>{["Строка", "Две строки", "Джекпот"][index]} · {cutoff}</span><b>{stage.winners ? `${stage.winners} бил.` : stage.move ? index === 2 ? "Перенос" : "Нет" : "В игре"}</b></div>; })}</div>
        <details className="bingo-all-balls"><summary>Все выпавшие числа · {live.numbers.length}</summary><div>{live.numbers.map(number => <span key={number}>{number}</span>)}</div>{live.complete && <p>Не выпали: {Array.from({ length: 60 }, (_, index) => index + 1).filter(number => !live.numbers.includes(number)).join(" и ")}</p>}</details>
      </> : <div className="bingo-empty">Эфир начнётся по расписанию.</div>}
    </section>}
    {tab !== "live" && <details className="bingo-rules"><summary>Коротко о правилах <span>+</span></summary><p>Строка до 18-го хода — 100 000 CAS. Две строки до 34-го — 500 000 CAS. Все подходящие билеты делят приз.</p><p>Полный билет до 28-го хода делит джекпот. Участвуют только купленные билеты.</p></details>}
    <footer className="bingo-page-footer">KASPER BINGO <span>✦</span> ВАШЕ ЛИЧНОЕ СОБЫТИЕ</footer>
    {opened && <PaperDialog onClose={() => setOpened(null)}><Paper ticket={opened} draw={mine.find(t => t.id === opened.id)?.draw_number ?? inventory?.draw_number ?? lottery.draw_number ?? 0} date={mine.find(t => t.id === opened.id)?.scheduled_at ?? inventory?.scheduled_at ?? lottery.scheduled_at ?? new Date().toISOString()} price={opened.price ?? price} /></PaperDialog>}
  </main>;
}
