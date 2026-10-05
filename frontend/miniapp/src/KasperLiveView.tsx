import { useEffect, useRef, useState } from "react";
import type { PointerEvent } from "react";
import { ApiError, miniAppApi } from "./api";
import { logoSymbol } from "./brand";
import { Money } from "./components";
import { LiveSymbol } from "./LiveSymbol";
import { liveSymbolDefinitions } from "./liveSymbols";
import { errorHaptic, selectionHaptic, successHaptic } from "./telegram";
import type { InstantPurchaseResult, InstantTicket } from "./types";
import "./kasper-live.css";

function ScratchCover({ ticket, onReveal }: { ticket: InstantTicket; onReveal: () => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const gesture = useRef<{ x: number; y: number; distance: number; total: number } | null>(null);
  const dragged = useRef(false);
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
    if (state.total > rect.width * 1.8) { gesture.current = null; onReveal(); }
  };
  return <button className="live-scratch-cover" type="button" aria-label={`Открыть билет № ${ticket.public_number}`} onClick={event => { if (!dragged.current || event.detail === 0) onReveal(); }}
    onPointerDown={event => { event.currentTarget.setPointerCapture?.(event.pointerId); dragged.current = false; gesture.current = { x: event.clientX, y: event.clientY, distance: 0, total: gesture.current?.total ?? 0 }; }}
    onPointerMove={scratch} onPointerCancel={() => { gesture.current = null; }}>
    <canvas ref={canvas} width="600" height="160" aria-hidden="true" /><span><img src={logoSymbol} alt="" /><strong>Сотрите покрытие</strong><small>или коснитесь, чтобы открыть</small></span>
  </button>;
}

function Ticket({ ticket, revealed = true, onReveal, compact = false }: { ticket: InstantTicket; revealed?: boolean; onReveal?: () => void; compact?: boolean }) {
  return <article className={`kasper-live-ticket ${revealed ? "revealed" : "sealed"}${revealed && ticket.prize_amount > 0 ? " winner" : ""}${compact ? " compact" : ""}`} aria-label={`Билет № ${ticket.public_number}`}>
    <header><span>CASPER <b>LIVE</b></span><small>№ {ticket.public_number.toLocaleString("ru-RU")}</small><img src={logoSymbol} alt="" /></header>
    <div className="live-ticket-field"><div className="kasper-live-symbols" aria-hidden={!revealed}>{ticket.symbols.map((value, index) => <i key={index} style={{ animationDelay: `${index * 70}ms` }}><LiveSymbol value={value} /></i>)}</div>{!revealed && onReveal && <ScratchCover ticket={ticket} onReveal={onReveal} />}</div>
    <footer>{revealed ? <><span>{ticket.prize_amount > 0 ? "ВАШ ВЫИГРЫШ" : "БЕЗ ВЫИГРЫША"}</span><strong>{ticket.prize_amount > 0 ? <Money value={ticket.prize_amount} /> : "В этот раз не совпало"}</strong></> : <><span>ТРИ ОДИНАКОВЫХ СИМВОЛА</span><strong>Откройте свой результат</strong></>}</footer>
  </article>;
}

export function KasperLiveView({ initData, balance, onClose, onSettled }: { initData: string; balance: number; onClose: () => void; onSettled: (result: InstantPurchaseResult) => void }) {
  const [history, setHistory] = useState<InstantTicket[]>([]);
  const [result, setResult] = useState<InstantPurchaseResult | null>(null);
  const [opened, setOpened] = useState<string[]>([]);
  const [quantity, setQuantity] = useState<1 | 3>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const buying = useRef(false);
  const root = useRef<HTMLElement>(null);
  const historyRequest = useRef(0);
  useEffect(() => {
    const version = ++historyRequest.current;
    let active = true;
    void miniAppApi.kasperLiveHistory(initData).then(tickets => { if (active && version === historyRequest.current) setHistory(tickets); }).catch(() => undefined);
    return () => { active = false; };
  }, [initData]);
  const buy = async () => {
    if (buying.current) return;
    buying.current = true; selectionHaptic(); setError(""); setBusy(true);
    try {
      const purchase = await miniAppApi.kasperLivePurchase(initData, quantity, crypto.randomUUID());
      historyRequest.current += 1;
      setResult(purchase); setOpened([]);
      root.current?.scrollIntoView?.({ block: "start", behavior: "instant" });
      setHistory(current => [...purchase.tickets, ...current.filter(item => !purchase.tickets.some(ticket => ticket.id === item.id))].slice(0, 30));
      onSettled(purchase);
    } catch (reason) { setError(reason instanceof ApiError ? reason.message : "Не удалось получить результат. Проверьте историю билетов перед новой покупкой."); errorHaptic(); }
    finally { buying.current = false; setBusy(false); }
  };
  const reveal = (ids: string[]) => {
    setOpened(current => Array.from(new Set([...current, ...ids])));
    if (result?.tickets.some(ticket => ids.includes(ticket.id) && ticket.prize_amount > 0)) successHaptic(); else selectionHaptic();
  };
  const complete = !!result && result.tickets.every(ticket => opened.includes(ticket.id));
  const previous = history.filter(ticket => !result?.tickets.some(current => current.id === ticket.id));
  return <main ref={root} className="kasper-live-page">
    <header className="kasper-live-header"><button disabled={busy} onClick={onClose} type="button" aria-label="Закрыть">←</button><div><small>МГНОВЕННАЯ ЛОТЕРЕЯ</small><strong>Casper <em>LIVE</em></strong></div><span><small>БАЛАНС</small><Money value={balance} compact /></span></header>
    {!result && <section className="kasper-live-hero"><div className="live-hero-copy"><span className="live-kicker"><i /> CASPER LIVE</span><h1>Ваша удача.<br /><em>Под золотом.</em></h1><p>Один билет. Три символа.<br />Ваш результат — сразу.</p></div><div className="live-hero-art" aria-hidden="true"><img src="/assets/casper-live-casino-v1.webp" alt="" width="768" height="512" /><i /></div><div className="live-hero-bottom"><span>МГНОВЕННАЯ ЛОТЕРЕЯ</span><span>✦ МОМЕНТ УДАЧИ</span></div></section>}
    {!result && <section className="kasper-live-buy"><div className="live-buy-heading"><span>Ваш выпуск</span><small>Билет <Money value={2_000} /></small></div><div className="live-quantity" role="group" aria-label="Количество билетов"><button type="button" aria-pressed={quantity === 1} disabled={busy} onClick={() => { selectionHaptic(); setQuantity(1); }}><b>1 билет</b><small>Один момент удачи</small></button><button type="button" aria-pressed={quantity === 3} disabled={busy} onClick={() => { selectionHaptic(); setQuantity(3); }}><b>3 билета</b><small>Открывайте вместе</small></button></div><button className="live-gold-button" disabled={busy || balance < quantity * 2_000} onClick={() => void buy()} type="button"><span>{busy ? "Печатаем ваш выпуск…" : `Купить ${quantity === 1 ? "билет" : "3 билета"}`}</span><b><Money value={quantity * 2_000} /></b></button>{balance < quantity * 2_000 && <p className="live-balance-note">Недостаточно CAS для этого выпуска</p>}{error && <p role="alert">{error}</p>}<p className="live-rule"><span>✦ ✦ ✦</span> Три одинаковых символа — выигрыш</p></section>}
    {result && <section className="kasper-live-result"><header><span className="live-kicker">{complete ? "ВЫПУСК ОТКРЫТ" : "ВАШ ВЫПУСК ГОТОВ"}</span><h1>{complete ? result.total_prize > 0 ? "Золотой момент." : "До следующего совпадения." : "Удача под печатью."}</h1><p>{complete ? "Все результаты этого выпуска перед вами." : "Сотрите покрытие или откройте все билеты одним нажатием."}</p></header><div className="kasper-live-ticket-grid">{result.tickets.map(ticket => <Ticket key={ticket.id} ticket={ticket} revealed={opened.includes(ticket.id)} onReveal={() => reveal([ticket.id])} />)}</div><div className="live-result-actions">{complete ? <><div className="live-total" role="status"><span>{result.total_prize > 0 ? "Общий выигрыш" : "В этот раз без выигрыша"}</span>{result.total_prize > 0 && <strong><Money value={result.total_prize} /></strong>}</div><button className="live-gold-button" type="button" onClick={() => { setResult(null); setOpened([]); }}>Купить ещё <span aria-hidden="true">↗</span></button></> : <button className="live-gold-button" type="button" onClick={() => reveal(result.tickets.map(ticket => ticket.id))}>{result.tickets.length === 1 ? "Открыть билет" : "Открыть все"}<span aria-hidden="true">✦</span></button>}</div></section>}
    <details className="live-prize-guide"><summary>Символы и выигрыши <span aria-hidden="true">＋</span></summary><p>Три одинаковых символа открывают приз.</p><ul>{liveSymbolDefinitions.map(symbol => "prize" in symbol && <li key={symbol.id}><LiveSymbol value={symbol.id} /><span>{symbol.name}<small>Три совпадения</small></span><strong><Money value={symbol.prize} /></strong></li>)}</ul></details>
    {previous.length > 0 && <details className="kasper-live-history"><summary><span>Ваши предыдущие билеты</span><small>{previous.length} <span aria-hidden="true">＋</span></small></summary><div>{previous.slice(0, 6).map(ticket => <Ticket key={ticket.id} ticket={ticket} compact />)}</div></details>}
    <footer className="live-page-footer">CASPER LIVE <i>✦</i> Результат сохраняется в истории билетов</footer>
  </main>;
}
