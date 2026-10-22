import { tr, getLocale } from "./i18n";
import { useEffect, useRef, useState } from "react";
import type { PointerEvent } from "react";
import { ApiError, miniAppApi } from "./api";
import { recoveredEvent } from "./purchaseJournal";
import type { PurchaseResolution } from "./purchaseJournal";
import { logoSymbol } from "./brand";
import { Money } from "./components";
import { LiveSymbol } from "./LiveSymbol";
import { liveSymbolDefinitions } from "./liveSymbols";
import { errorHaptic, selectionHaptic, successHaptic } from "./telegram";
import type { InstantPurchaseResult, InstantTicket } from "./types";
import "./kasper-live.css";
import { disableTelegramVerticalSwipes, lockInteractionViewport } from "./interactionLock";

function ScratchCover({ ticket, onReveal }: { ticket: InstantTicket; onReveal: () => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const gesture = useRef<{ x: number; y: number; distance: number; total: number } | null>(null);
  const dragged = useRef(false);
  const scratchedDistance = useRef(0);
  const releaseViewport = useRef<(() => void) | null>(null);
  const finishGesture = () => {
    gesture.current = null;
    releaseViewport.current?.(); releaseViewport.current = null;
  };
  useEffect(() => () => { releaseViewport.current?.(); }, []);
  useEffect(() => {
    const node = canvas.current;
    const context = node?.getContext("2d");
    if (!context) return;
    const gradient = context.createLinearGradient(0, 0, 600, 160);
    gradient.addColorStop(0, "#c99b48"); gradient.addColorStop(.35, "#f5db97"); gradient.addColorStop(.6, "#b48639"); gradient.addColorStop(1, "#e6c477");
    context.fillStyle = gradient; context.fillRect(0, 0, 600, 160);
    if (node) node.style.background = "transparent";
    context.strokeStyle = "#5a391d22";
    for (let x = -160; x < 600; x += 12) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x + 160, 160); context.stroke(); }
  }, []);
  const scratch = (event: PointerEvent<HTMLButtonElement>) => {
    const node = canvas.current; const state = gesture.current;
    if (!node || !state || !(event.buttons & 1)) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const context = node.getContext("2d");
    if (context) {
      context.globalCompositeOperation = "destination-out"; context.lineWidth = 62; context.lineCap = "round";
      context.beginPath(); context.moveTo((state.x - rect.left) * 600 / rect.width, (state.y - rect.top) * 160 / rect.height); context.lineTo((event.clientX - rect.left) * 600 / rect.width, (event.clientY - rect.top) * 160 / rect.height); context.stroke();
    }
    const distance = Math.hypot(event.clientX - state.x, event.clientY - state.y);
    state.x = event.clientX; state.y = event.clientY; state.distance += distance; state.total += distance;
    dragged.current = state.distance > 8;
    if (dragged.current) event.currentTarget.dataset.scratched = "true";
    scratchedDistance.current = state.total;
    if (state.total > rect.width * 1.8) { finishGesture(); onReveal(); }
  };
  return <button className="live-scratch-cover" type="button" aria-label={tr("Открыть билет № {0}", ticket.public_number)} onClick={event => { if (!dragged.current || event.detail === 0) onReveal(); }}
    onPointerDown={event => { if (event.button !== 0 || gesture.current) return; releaseViewport.current = lockInteractionViewport(); event.currentTarget.setPointerCapture?.(event.pointerId); dragged.current = false; gesture.current = { x: event.clientX, y: event.clientY, distance: 0, total: scratchedDistance.current }; }}
    onPointerMove={scratch} onPointerUp={finishGesture} onPointerCancel={() => { dragged.current = true; finishGesture(); }} onLostPointerCapture={finishGesture}>
    <canvas ref={canvas} width="600" height="160" aria-hidden="true" /><span><img src={logoSymbol} alt="" /><strong>{tr("Сотрите покрытие")}</strong><small>{tr("или коснитесь, чтобы открыть")}</small></span>
  </button>;
}

function Ticket({ ticket, revealed = true, onReveal, compact = false }: { ticket: InstantTicket; revealed?: boolean; onReveal?: () => void; compact?: boolean }) {
  return <article className={`kasper-live-ticket ${revealed ? "revealed" : "sealed"}${revealed && ticket.prize_amount > 0 ? " winner" : ""}${compact ? " compact" : ""}`} aria-label={tr("Билет № {0}", ticket.public_number)}>
    <header><span>CASPER <b>LIVE</b></span><small>№ {tr(ticket.public_number.toLocaleString(getLocale()))}</small><img src={logoSymbol} alt="" /></header>
    <div className="live-ticket-field"><div className="kasper-live-symbols" aria-hidden={!revealed}>{ticket.symbols.map((value, index) => <i key={index} style={{ animationDelay: `${index * 70}ms` }}><LiveSymbol value={value} /></i>)}</div>{!revealed && onReveal && <ScratchCover ticket={ticket} onReveal={onReveal} />}</div>
    <footer>{revealed ? <><span>{ticket.prize_amount > 0 ? tr("ВАШ ВЫИГРЫШ") : tr("БЕЗ ВЫИГРЫША")}</span><strong>{ticket.prize_amount > 0 ? <Money value={ticket.prize_amount} /> : tr("В этот раз не совпало")}</strong></> : <><span>{tr("ТРИ ОДИНАКОВЫХ СИМВОЛА")}</span><strong>{tr("Откройте свой результат")}</strong></>}</footer>
  </article>;
}

export function KasperLiveView({ initData, balance, onClose, onSettled }: { initData: string; balance: number; onClose: () => void; onSettled: (result: InstantPurchaseResult) => void }) {
  const [history, setHistory] = useState<InstantTicket[]>([]);
  const [result, setResult] = useState<InstantPurchaseResult | null>(null);
  const [opened, setOpened] = useState<string[]>([]);
  const [quantity, setQuantity] = useState<1 | 3>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [retryQuantity, setRetryQuantity] = useState<1 | 3 | null>(null);
  const pending = useRef<{ key: string; quantity: 1 | 3 } | null>(null);
  const historyRequest = useRef(0);
  useEffect(() => {
    const resolved = (event: Event) => {
      const detail = (event as CustomEvent<PurchaseResolution>).detail;
      if (!detail.path.endsWith("/kasper-live/purchases")) return;
      pending.current = null; setRetryQuantity(null); setError("");
      if (detail.receipt && "tickets" in detail.receipt) {
        const receipt = detail.receipt;
        historyRequest.current += 1; setResult(receipt); setOpened([]);
        setHistory(current => [...receipt.tickets, ...current.filter(item => !receipt.tickets.some(ticket => ticket.id === item.id))].slice(0, 30));
      }
    };
    window.addEventListener(recoveredEvent, resolved);
    return () => window.removeEventListener(recoveredEvent, resolved);
  }, []);
  const buying = useRef(false);
  const root = useRef<HTMLElement>(null);
  useEffect(() => disableTelegramVerticalSwipes(), []);
  useEffect(() => {
    const version = ++historyRequest.current;
    let active = true;
    void miniAppApi.kasperLiveHistory(initData).then(tickets => { if (active && version === historyRequest.current) setHistory(tickets); }).catch(() => undefined);
    return () => { active = false; };
  }, [initData]);
  const buy = async () => {
    if (buying.current) return;
    buying.current = true; selectionHaptic(); setError(""); setBusy(true);
    const request = pending.current ?? { key: crypto.randomUUID(), quantity }; pending.current = request;
    try {
      const purchase = await miniAppApi.kasperLivePurchase(initData, request.quantity, request.key);
      pending.current = null; setRetryQuantity(null);
      historyRequest.current += 1;
      setResult(purchase); setOpened([]);
      root.current?.scrollIntoView?.({ block: "start", behavior: "instant" });
      setHistory(current => [...purchase.tickets, ...current.filter(item => !purchase.tickets.some(ticket => ticket.id === item.id))].slice(0, 30));
      onSettled(purchase);
    } catch (reason) { if (reason instanceof ApiError && reason.status < 500) { pending.current = null; setRetryQuantity(null); } else setRetryQuantity(request.quantity); setError(reason instanceof ApiError ? reason.message : tr("Нет связи. Повторите запрос — повторного списания не будет.")); errorHaptic(); }
    finally { buying.current = false; setBusy(false); }
  };
  const reveal = (ids: string[]) => {
    setOpened(current => Array.from(new Set([...current, ...ids])));
    if (result?.tickets.some(ticket => ids.includes(ticket.id) && ticket.prize_amount > 0)) successHaptic(); else selectionHaptic();
  };
  const complete = !!result && result.tickets.every(ticket => opened.includes(ticket.id));
  const previous = history.filter(ticket => !result?.tickets.some(current => current.id === ticket.id));
  return <main ref={root} className="kasper-live-page">
    <header className="kasper-live-header"><button disabled={busy} onClick={onClose} type="button" aria-label={tr("Закрыть")}>←</button><div><small>{tr("МГНОВЕННАЯ ЛОТЕРЕЯ")}</small><strong>Casper <em>LIVE</em></strong></div><span><small>{tr("БАЛАНС")}</small><Money value={balance} compact /></span></header>
    {!result && <section className="kasper-live-hero"><div className="live-hero-copy"><span className="live-kicker"><i /> CASPER LIVE</span><h1>{tr("Ваша удача.")}<br /><em>{tr("Под золотом.")}</em></h1><p>{tr("Один билет. Три символа.")}<br />{tr("Ваш результат — сразу.")}</p></div><div className="live-hero-art" aria-hidden="true"><img src="/assets/casper-live-casino-v1.webp" alt="" width="768" height="512" /><i /></div><div className="live-hero-bottom"><span>{tr("МГНОВЕННАЯ ЛОТЕРЕЯ")}</span><span>{tr("✦ МОМЕНТ УДАЧИ")}</span></div></section>}
    {!result && <section className="kasper-live-buy"><div className="live-buy-heading"><span>{tr("Ваш выпуск")}</span><small>{tr("Билет")} <Money value={2_000} /></small></div><div className="live-quantity" role="group" aria-label={tr("Количество билетов")}><button type="button" aria-pressed={quantity === 1} disabled={busy || retryQuantity !== null} onClick={() => { selectionHaptic(); setQuantity(1); }}><b>{tr("1 билет")}</b><small>{tr("Один момент удачи")}</small></button><button type="button" aria-pressed={quantity === 3} disabled={busy || retryQuantity !== null} onClick={() => { selectionHaptic(); setQuantity(3); }}><b>{tr("3 билета")}</b><small>{tr("Открывайте вместе")}</small></button></div><button className="live-gold-button" disabled={busy || balance < (retryQuantity ?? quantity) * 2_000} onClick={() => void buy()} type="button"><span>{busy ? tr("Печатаем ваш выпуск…") : retryQuantity !== null ? tr("Повторить запрос") : tr("Купить {0}", quantity === 1 ? tr("билет") : tr("3 билета"))}</span><b><Money value={(retryQuantity ?? quantity) * 2_000} /></b></button>{balance < quantity * 2_000 && <p className="live-balance-note">{tr("Недостаточно CAS для этого выпуска")}</p>}{error && <p role="alert">{tr(error)}</p>}<p className="live-rule"><span>✦ ✦ ✦</span>  {tr("Три одинаковых символа — выигрыш")}</p></section>}
    {result && <section className="kasper-live-result"><header><span className="live-kicker">{complete ? tr("ВЫПУСК ОТКРЫТ") : tr("ВАШ ВЫПУСК ГОТОВ")}</span><h1>{complete ? result.total_prize > 0 ? tr("Золотой момент.") : tr("До следующего совпадения.") : tr("Удача под печатью.")}</h1><p>{complete ? tr("Все результаты этого выпуска перед вами.") : tr("Сотрите покрытие или откройте все билеты одним нажатием.")}</p></header><div className="kasper-live-ticket-grid">{result.tickets.map(ticket => <Ticket key={ticket.id} ticket={ticket} revealed={opened.includes(ticket.id)} onReveal={() => reveal([ticket.id])} />)}</div><div className="live-result-actions">{complete ? <><div className="live-total" role="status"><span>{result.total_prize > 0 ? tr("Общий выигрыш") : tr("В этот раз без выигрыша")}</span>{result.total_prize > 0 && <strong><Money value={result.total_prize} /></strong>}</div><button className="live-gold-button" type="button" disabled={busy || balance < (retryQuantity ?? quantity) * 2_000} onClick={() => void buy()}><span>{busy ? tr("Печатаем ваш выпуск…") : retryQuantity !== null ? tr("Повторить запрос") : quantity === 3 ? tr("Купить ещё 3 билета") : tr("Купить ещё")}</span><Money value={(retryQuantity ?? quantity) * 2_000} /></button>{balance < (retryQuantity ?? quantity) * 2_000 && <p className="live-balance-note">{tr("Недостаточно CAS для этого выпуска")}</p>}</> : <button className="live-gold-button" type="button" onClick={() => reveal(result.tickets.map(ticket => ticket.id))}>{result.tickets.length === 1 ? tr("Открыть билет") : tr("Открыть все")}<span aria-hidden="true">✦</span></button>}{error && <p role="alert">{tr(error)}</p>}</div></section>}
    <details className="live-prize-guide"><summary>{tr("Символы и выигрыши")} <span aria-hidden="true">＋</span></summary><p>{tr("Три одинаковых символа открывают приз.")}</p><ul>{liveSymbolDefinitions.map(symbol => "prize" in symbol && <li key={symbol.id}><LiveSymbol value={symbol.id} /><span>{tr(symbol.name)}<small>{tr("Три совпадения")}</small></span><strong><Money value={symbol.prize} /></strong></li>)}</ul></details>
    {previous.length > 0 && <details className="kasper-live-history"><summary><span>{tr("Ваши предыдущие билеты")}</span><small>{previous.length} <span aria-hidden="true">＋</span></small></summary><div>{previous.slice(0, 6).map(ticket => <Ticket key={ticket.id} ticket={ticket} compact />)}</div></details>}
    <footer className="live-page-footer">CASPER LIVE <i>✦</i>  {tr("Результат сохраняется в истории билетов")}</footer>
  </main>;
}
