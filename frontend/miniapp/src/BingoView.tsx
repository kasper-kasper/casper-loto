import { tr } from "./i18n";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, miniAppApi } from "./api";
import { logoSymbol } from "./brand";
import { Money } from "./components";
import { GameHeader } from "./GameHeader";
import { BingoEdition } from "./BingoEdition";
import { BingoTicketDeck } from "./BingoTicketDeck";
import editionArt from "./assets/lotteries/bingo-edition-v1.webp";
import "./bingo-play.css";
import { countdown, formatCas, formatMoscow } from "./format";
import type { Lottery, PurchaseResult, Ticket } from "./types";
import "./bingo.css";
import { broadcastPreviewConfig } from "./broadcastPreview";

export interface BingoResult { moves: number[]; amounts: number[] }
interface PrintedTicket { id: string; public_number?: number; pool_position?: number; numbers: number[]; price?: number; result?: BingoResult | null }
export interface BingoInventory { draw_id: string; draw_number: number; scheduled_at: string; price: number; has_more: boolean; kasper_set_available: boolean; tickets: PrintedTicket[] }
export interface BingoFeed { rules: { total_moves: number; jackpot_move: number; tour_moves: number[]; tour_prizes: number[]; stage_moves?: number[]; fixed_per_card?: boolean; pool_size: number }; server_time: string; draw: null | { draw_number: number; scheduled_at: string; complete: boolean; numbers: number[]; total_moves: number; jackpot_move: number; tour_prizes: number[]; stages: { move: number | null; winners: number }[]; tickets: PrintedTicket[] } }

function serial(ticket: number) { return `KB-${String(ticket).padStart(6, "0")}`; }

function BingoMark() { return <span className="bingo-mark" aria-hidden="true"><img src={logoSymbol} alt="" /></span>; }

export function BingoInvitation({ lottery, now, onOpen }: { lottery: Lottery; now: number; onOpen: () => void }) {
  return <button className="bingo-invitation" type="button" onClick={onOpen}>
    <span className="bingo-invite-top"><span>{tr("КАЖДЫЙ ВЕЧЕР · 22:00 МСК")}</span><span>{tr("ДЖЕКПОТ ВЕЧЕРА")}</span></span>
    <span className="bingo-invite-main"><span><strong>Casper <em>Bingo</em></strong><small>{tr("Ваш вечерний ритуал")}</small></span><BingoMark /></span>
    <span className="bingo-invite-bottom"><span><small>{tr("ДЖЕКПОТ")}</small><b><Money value={lottery.jackpot} compact /></b></span><span className="bingo-arrow">↗</span></span>
    <span className="bingo-invite-date">{lottery.scheduled_at ? tr("{0} МСК · {1}", formatMoscow(lottery.scheduled_at), countdown(lottery.scheduled_at, now)) : tr("Открыть билеты и эфир")}</span>
  </button>;
}

function Paper({ ticket, draw, date, price, revealed = [], current, result, compact = false }: { ticket: PrintedTicket; draw: number; date: string; price: number; revealed?: number[]; current?: number; result?: BingoResult | null; compact?: boolean }) {
  const hits = new Set(revealed);
  const missingRows = [0, 1, 2].map(row => ticket.numbers.slice(row * 4, row * 4 + 4).filter(n => !hits.has(n)).length).sort((a, b) => a - b);
  return <article className={`bingo-paper ${compact ? "is-compact" : ""}`}>
    <header><BingoMark /><span>CASPER<strong>BINGO</strong></span><small>{tr("ТИРАЖ")}<b>№{tr(String(draw).padStart(4, "0"))}</b></small></header>
    {!compact && <div className="bingo-paper-date">{tr(formatMoscow(date))}  {tr("МСК")} <span>{tr("12 чисел · 3 строки")}</span></div>}
    <div className="bingo-grid">{[0, 1, 2].map(row => <div className={ticket.numbers.slice(row * 4, row * 4 + 4).every(n => hits.has(n)) ? "closed-row" : ""} key={row}>{ticket.numbers.slice(row * 4, row * 4 + 4).map(n => <span key={n} className={`${hits.has(n) ? "hit" : ""} ${current === n ? "current" : ""}`} aria-label={tr(`${n}${hits.has(n) ? tr(", совпало") : ""}${current === n ? tr(", текущее число") : ""}`)}><b>{tr(String(n).padStart(2, "0"))}</b>{hits.has(n) && <i aria-hidden="true">✓</i>}</span>)}</div>)}</div>
    <footer><span><small>{ticket.public_number ? tr("СЕРИЙНЫЙ НОМЕР") : tr("ДО ПОКУПКИ")}</small><b>{tr(ticket.public_number ? serial(ticket.public_number) : tr("ВАРИАНТ БИЛЕТА"))}</b></span><span><small>{tr("СТОИМОСТЬ")}</small><b>{tr(formatCas(price))}</b></span></footer>
    {!compact && <div className="bingo-paper-seal"><span>✦</span>  {tr("Счастье любит присутствие")} <span>✦</span></div>}
    {!compact && !result && revealed.length > 0 && <div className="bingo-ticket-progress"><span>{tr("До строки")} <b>{missingRows[0]}</b></span><span>{tr("До двух")} <b>{missingRows[0] + missingRows[1]}</b></span><span>{tr("До полного")} <b>{missingRows.reduce((a, b) => a + b, 0)}</b></span></div>}
    {result && <div className="bingo-ticket-result"><strong>{result.amounts.some(Boolean) ? tr("Ваш выигрыш · {0}", formatCas(result.amounts.reduce((a, b) => a + b, 0))) : tr("В этот раз без выигрыша")}</strong><small>{tr("Совпало")} {ticket.numbers.filter(n => hits.has(n)).length}  {tr("из 12")}</small>{result.amounts.map((amount, i) => amount > 0 && <p key={i}>{tr([tr("Одна строка"), tr("Две строки"), tr("Джекпот"), tr("Полная карточка")][i])} <b>{tr(formatCas(amount))}</b></p>)}</div>}
  </article>;
}

export function BingoTicketDetail({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  return <PaperDialog onClose={onClose}><BingoEdition ticket={ticket} draw={ticket.draw_number} date={ticket.scheduled_at} price={ticket.purchase_price} revealed={ticket.winning_numbers ?? []} result={ticket.bingo_result} /></PaperDialog>;
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
  return <div className="bingo-dialog-backdrop" role="presentation" onClick={onClose}><section className="bingo-dialog" role="dialog" aria-modal="true" aria-label={tr("Билет Casper Bingo")} onClick={e => e.stopPropagation()}><button ref={ref} type="button" className="bingo-dialog-close" onClick={onClose} aria-label={tr("Закрыть билет")}>×</button>{tr(children)}</section></div>;
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
  const refreshMine = useCallback(async () => {
    const tickets: Ticket[] = [];
    let position: number | string = 0;
    while (true) {
      const page = await miniAppApi.tickets(initData, "active", "bingo", false, position);
      tickets.push(...page.tickets);
      if (!page.has_more || !page.tickets.length) break;
      position = page.next_cursor ?? tickets.length;
    }
    setMine(tickets);
  }, [initData]);
  useEffect(() => {
    const resolved = (event: Event) => {
      const detail = (event as CustomEvent<{ path: string }>).detail;
      if (!detail.path.endsWith("/bingo/purchases")) return;
      pending.current = null; setRetry(false); setRetrySelection(null); setSelected([]); setError("");
      setRevision(value => value + 1);
      void refreshMine().catch(() => undefined);
    };
    window.addEventListener(recoveredEvent, resolved);
    return () => window.removeEventListener(recoveredEvent, resolved);
  }, [refreshMine]);
  useEffect(() => {
    let active = true;
    void miniAppApi.bingoInventory(initData, offset, favoriteNumbers).then(data => { if (active) { setInventory(data); setFavoriteError(""); if (inventoryDraw.current && inventoryDraw.current !== data.draw_id) setSelected([]); inventoryDraw.current = data.draw_id; } }).catch((reason: unknown) => { if (active) { if (favoriteNumbers.length > 0) setFavoriteError(tr("Поиск не сработал. Попробуйте ещё раз.")); else setError(reason instanceof Error ? reason.message : tr("Не удалось загрузить билеты")); } }).finally(() => { if (active) setLoading(false); });
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
        catch { if (active && tab === "live") setError(tr("Эфир переподключается. Выпавшие числа сохраняются.")); }
      }
      if (active) timer = setTimeout(() => void poll(), broadcastPreviewConfig() ? 700 : tab === "live" ? 2000 : 10000);
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
  const quickAll = Math.min(available, affordable, lottery.max_tickets_per_purchase);
  const hasFavoriteNumber = favoriteInputs.some(value => value.trim() !== "");
  const toggle = (ticket: PrintedTicket) => {
    if (busy || pending.current) return;
    setSelected(current => current.some(t => t.id === ticket.id) ? current.filter(t => t.id !== ticket.id) : current.length < Math.min(available, lottery.max_tickets_per_purchase) ? [...current, ticket] : current);
  };
  const purchase = async (selection: { ticketIds?: string[]; quantity?: number; requiredNumbers?: number[] }) => {
    if (!inventory || busy) return;
    pending.current ??= { key: crypto.randomUUID(), selection, draw: inventory.draw_id };
    setBusy(true); setError("");
    try {
      const result = await miniAppApi.bingoPurchase(initData, pending.current.draw, pending.current.selection, pending.current.key);
      pending.current = null; setRetry(false); setRetrySelection(null); setSelected([]);
      setNotice(tr("Куплено: {0} · {1}", result.ticket_ids.length, formatCas(result.total_cost)));
      onPurchased(result);
      void Promise.allSettled([refreshMine(), miniAppApi.bingoInventory(initData, 0, favoriteNumbers)]).then(([, inventoryRefresh]) => {
        if (inventoryRefresh.status === "fulfilled") { setInventory(inventoryRefresh.value); setOffset(0); }
      });
    } catch (reason) {
      if (reason instanceof ApiError && reason.status >= 400 && reason.status < 500) {
        pending.current = null; setRetry(false); setRetrySelection(null);
        if (reason.status === 409) { setSelected([]); setRevision(v => v + 1); }
      } else { setRetry(true); setRetrySelection(pending.current?.selection ?? selection); }
      setError(reason instanceof ApiError && reason.status === 409 ? tr("Один из билетов уже купили или продажи завершены. Подборка обновлена — выберите свободные билеты.") : reason instanceof Error ? reason.message : tr("Не удалось подтвердить покупку. Нажмите ещё раз — повторного списания не будет."));
    } finally { setBusy(false); }
  };
  const buy = () => purchase({ ticketIds: selected.map(t => t.id) });
  const quickBuy = (quantity: number, requiredNumbers: number[] = []) => {
    if (quantity > 0) void purchase({ quantity, requiredNumbers });
  };
  const searchFavorites = () => {
    const values = favoriteInputs.filter(value => value.trim() !== "").map(Number);
    if (values.length === 0 || values.some(value => !Number.isInteger(value) || value < 1 || value > 60) || new Set(values).size !== values.length) {
      setFavoriteError(tr("Введите до трёх разных чисел от 1 до 60."));
      return;
    }
    setFavoriteError(""); setError(""); setSelected([]); setOffset(0); setLoading(true); setFavoriteNumbers(values);
  };
  return <main className={`app-shell bingo-page play-room play-bingo game-bingo${tab !== "live" ? " bingo-salon" : ""}`}>
    <GameHeader lottery={lottery} balance={balance} now={now} onClose={onClose} artworkOverride={tab !== "live" ? editionArt : undefined}>
      {tab !== "choose" && <button type="button" onClick={() => setTab("choose")}>{tr("К билетам")}</button>}
      {tab !== "mine" && <button type="button" onClick={() => setTab("mine")}>{tr("Мои билеты")}</button>}
      {tab !== "live" && <button type="button" onClick={() => setTab("live")}>{tr("Эфир ↗")}</button>}
    </GameHeader>
    {error && <div className="bingo-message is-error" role="alert"><span>{tr(error)}</span>{retry && retrySelection && <button type="button" onClick={() => void purchase(retrySelection)}>{tr("Проверить покупку")}</button>}<button type="button" onClick={() => setError("")} aria-label={tr("Закрыть сообщение")}>×</button></div>}
    {notice && <div className="bingo-message" role="status"><span>{tr(notice)}</span><button type="button" onClick={() => { setNotice(""); setTab("mine"); }}>{tr("Мои билеты →")}</button></div>}
    {tab === "choose" && <section className="bingo-selection">
      <section className="play-quick" aria-label={tr("Быстрая покупка")}><div><strong>{tr("Быстрая покупка")}</strong><small>{tr("Случайные билеты")}</small></div><div>{[1, 5, 25].map(quantity => <button key={quantity} type="button" aria-label={tr("Купить {0} {1}", quantity, quantity === 1 ? tr("случайный билет") : tr("случайных билетов"))} disabled={busy || loading || quantity > quickAll} onClick={() => quickBuy(quantity)}>×{quantity}</button>)}</div></section>
      <div className="bingo-selection-meta"><span>{favoriteNumbers.length ? tr("Билеты с числами {0}", favoriteNumbers.join(" · ")) : tr("Можно купить ещё {0}", available)}</span><button type="button" disabled={loading || busy} onClick={() => { setLoading(true); setOffset(inventory?.has_more ? offset + 6 : 0); setRevision(v => v + 1); setError(""); }}>{tr("Другие билеты ↻")}</button></div>
      {loading ? <div className="bingo-loading">{tr("Подбираем билеты…")}</div> : inventory?.tickets.length ? <BingoTicketDeck key={`${inventory.draw_id}:${offset}:${revision}:${favoriteNumbers.join(",")}`} inventory={inventory} selected={selected} offset={offset} price={price} busy={busy} retry={retry} available={available} onToggle={toggle} onInspect={setOpened} /> : <div className="bingo-empty">{tr("Подходящих свободных билетов нет.")}</div>}
      <details className="ticket-options bingo-more-options"><summary>{tr("Подбор по числам и наборы")} <span>＋</span></summary><div className="bingo-buy-studio">
        <button className="bingo-kasper-set" type="button" disabled={busy || available < 10 || affordable < 10 || !inventory?.kasper_set_available} onClick={() => quickBuy(10, [28, 16, 2, 9])}>
          <span>{tr("✦ НАБОР КАСПЕРА")}</span><strong>{tr("10 случайных билетов")}</strong><small>{tr("В каждом: 2 · 9 · 16 · 28")}</small><b>{tr(inventory?.kasper_set_available ? formatCas(price * 10) : tr("Уже выбран"))}</b>
        </button>
        <form className="bingo-favorite-search" onSubmit={event => { event.preventDefault(); searchFavorites(); }}>
          <span>{tr("ЛЮБИМЫЕ ЧИСЛА · ДО ТРЁХ")}</span>
          <div>{favoriteInputs.map((value, index) => <input key={index} type="number" min="1" max="60" inputMode="numeric" aria-label={tr("Любимое число {0}", index + 1)} value={value} onChange={event => { setFavoriteError(""); setFavoriteInputs(current => current.map((item, itemIndex) => itemIndex === index ? event.target.value : item)); }} />)}</div>
          <button type="submit" disabled={busy || !hasFavoriteNumber}>{tr("Найти билеты")}</button>
          {favoriteError && <small className="bingo-search-feedback is-error" role="alert">{tr(favoriteError)}</small>}
          {favoriteNumbers.length > 0 && !loading && !favoriteError && <small className={`bingo-search-feedback ${inventory?.tickets.length ? "" : "is-error"}`}>{inventory?.tickets.length ? tr("Нашли варианты: {0}", inventory.tickets.length) : tr("Свободных билетов с этими числами нет. Измените выбор.")}</small>}
          {favoriteNumbers.length > 0 && <button className="bingo-search-reset" type="button" onClick={() => { setFavoriteError(""); setFavoriteNumbers([]); setFavoriteInputs(["", "", ""]); setOffset(0); setLoading(true); }}>{tr("Показать все")}</button>}
        </form>
        <button className="bingo-buy-all" type="button" disabled={busy || quickAll < 1} onClick={() => quickBuy(quickAll)}>{tr("Купить все доступные ·")} {quickAll}</button>
      </div></details>
      {selected.length > 0 && <div className="bingo-selected-chips" aria-label={tr("Выбранные билеты")}>{selected.map((ticket, index) => <button key={ticket.id} type="button" disabled={busy || retry} onClick={() => toggle(ticket)}>{tr("Вариант")} {index + 1} ×</button>)}</div>}
      <footer className="play-checkout"><div><small>{selected.length ? tr("Выбрано билетов: {0}", selected.length) : tr("Стоимость билета")}</small><strong><Money value={selected.length ? total : price} /></strong></div><button type="button" disabled={!selected.length || busy || total > balance} onClick={() => void buy()}>{busy ? tr("Оформляем…") : total > balance ? tr("Недостаточно CAS") : selected.length ? tr("Купить билеты") : tr("Выберите билет")}<span aria-hidden="true">↗</span></button></footer>
    </section>}
    {tab === "mine" && <section className="bingo-mine"><div className="bingo-section-title"><h2>{tr("Мои билеты")}</h2><p>{tr("Во время эфира совпадения отметятся сами.")}</p></div>{mine.length ? mine.map(ticket => <button type="button" className="bingo-owned-row" key={ticket.id} onClick={() => setOpened({ ...ticket, price: ticket.purchase_price })}><span>✦</span><span><b>{tr(serial(ticket.public_number))}</b><small>{tr("Тираж №")}{ticket.draw_number} · {tr(formatMoscow(ticket.scheduled_at))}  {tr("МСК")}</small></span><span>↗</span></button>) : <div className="bingo-empty">{tr("Активных билетов пока нет. Выберите билет или посмотрите последний эфир.")}</div>}</section>}
    {tab === "live" && <section className="bingo-live">
      <div className="bingo-section-title"><span className="bingo-eyebrow">{live?.complete ? tr("ИТОГИ РОЗЫГРЫША") : tr("В ПРЯМОМ ЭФИРЕ")}</span><h2>{live ? tr("Тираж №{0}", live.draw_number) : tr("Встретимся в 22:00.")}</h2></div>
      {live ? <>
        <div className="bingo-draw-stage"><span className="bingo-live-status">{live.complete ? tr("ТИРАЖ ЗАВЕРШЁН") : tr("● ЭФИР")}</span><div className="bingo-current-ball" key={live.numbers.length}>{tr(live.numbers.at(-1) ?? "✦")}</div><p>{tr("ХОД")} <strong>{live.numbers.length}</strong> / {live.total_moves}</p><div className="bingo-live-progress"><i style={{ width: `${live.numbers.length / live.total_moves * 100}%` }} /></div><div className="bingo-last-balls">{live.numbers.slice(-6).reverse().map((number, index) => <span className={index === 0 ? "latest" : ""} key={number}>{tr(String(number).padStart(2, "0"))}</span>)}</div></div>
        {liveTicket ? <><div className="bingo-live-controls"><button type="button" onClick={() => { setAutoBest(false); setLiveIndex(Math.max(0, shownLiveIndex - 1)); }} disabled={shownLiveIndex === 0} aria-label={tr("Предыдущий билет")}>←</button><span>{tr("Билет")} {shownLiveIndex + 1} / {live.tickets.length}</span><button type="button" aria-pressed={autoBest} onClick={() => setAutoBest(value => !value)}>{tr("Авто")}</button><button type="button" onClick={() => { setAutoBest(false); setLiveIndex(Math.min(live.tickets.length - 1, shownLiveIndex + 1)); }} disabled={shownLiveIndex >= live.tickets.length - 1} aria-label={tr("Следующий билет")}>→</button></div><Paper ticket={liveTicket} draw={live.draw_number} date={live.scheduled_at} price={liveTicket.price ?? price} revealed={live.numbers} current={live.numbers.at(-1)} result={liveTicket.result} /></> : <div className="bingo-empty">{tr("В этом тираже у вас нет билетов. Смотреть эфир можно без покупки.")}</div>}
        <div className="bingo-stage-results">{live.stages.map((stage, index) => { const cutoff = rules?.stage_moves?.[index] ?? (index === 2 ? live.jackpot_move : [18, 34, 28, 58][index]); return <div key={index}><span>{tr([tr("Строка"), tr("Две строки"), tr("Джекпот"), tr("Полная карточка")][index])} · {cutoff}</span><b>{stage.winners ? tr("{0} бил.", stage.winners) : stage.move ? index === 2 ? tr("Перенос") : tr("Нет") : tr("В игре")}</b></div>; })}</div>
        <details className="bingo-all-balls"><summary>{tr("Все выпавшие числа ·")} {live.numbers.length}</summary><div>{live.numbers.map(number => <span key={number}>{number}</span>)}</div>{live.complete && <p>{tr("Не выпали:")} {tr(Array.from({ length: 60 }, (_, index) => index + 1).filter(number => !live.numbers.includes(number)).join(tr(" и ")))}</p>}</details>
      </> : <div className="bingo-empty">{tr("Эфир начнётся по расписанию.")}</div>}
    </section>}
    {tab !== "live" && <details className="bingo-rules"><summary>{tr("Коротко о правилах")} <span>+</span></summary>{lottery.ruleset_code === "bingo_12_60_economy_v2" ? <><p>{tr("Строка до 18-го хода включительно — 50 000 CAS. Две строки до 34-го — 100 000 CAS. Все 12 чисел до 58-го — 20 000 CAS.")}</p><p>{tr("Каждая выигравшая карточка получает полную фиксированную выплату. Выплаты по категориям суммируются. 40% стоимости карточки пополняют джекпот, 60% сгорают.")}</p></> : <p>{tr("Строка до 18-го хода — 100 000 CAS. Две строки до 34-го — 500 000 CAS. Все подходящие билеты делят приз.")}</p>}<p>{tr("Полный билет до 28-го хода делит джекпот. Участвуют только купленные билеты.")}</p></details>}
    {opened && <PaperDialog onClose={() => setOpened(null)}><BingoEdition ticket={opened} draw={mine.find(t => t.id === opened.id)?.draw_number ?? inventory?.draw_number ?? lottery.draw_number ?? 0} date={mine.find(t => t.id === opened.id)?.scheduled_at ?? inventory?.scheduled_at ?? lottery.scheduled_at ?? new Date().toISOString()} price={opened.price ?? price} /></PaperDialog>}
  </main>;
}
import { recoveredEvent } from "./purchaseJournal";
