import { tr, getLocale } from "./i18n";
import { useEffect, useRef, useState } from "react";
import { ApiError, miniAppApi } from "./api";
import { recoveredEvent } from "./purchaseJournal";
import type { PurchaseResolution } from "./purchaseJournal";
import { Money } from "./components";
import { disableTelegramVerticalSwipes, lockInteractionViewport } from "./interactionLock";
import { errorHaptic, selectionHaptic, successHaptic } from "./telegram";
import type { InstantPurchaseResult, InstantTicket } from "./types";
import artwork from "./assets/lotteries/aurora-crystal-v1.webp";
import "./aurora.css";

function Crystal({ ticket, onReveal }: { ticket: InstantTicket; onReveal: () => void }) {
  const [progress, setProgress] = useState(0);
  const accumulated = useRef(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const release = useRef<(() => void) | null>(null);
  const stop = () => { if (timer.current) clearInterval(timer.current); timer.current = null; release.current?.(); release.current = null; };
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); release.current?.(); }, []);
  const start = () => {
    if (timer.current) return;
    release.current = lockInteractionViewport();
    let last = performance.now();
    timer.current = setInterval(() => {
      const now = performance.now(); accumulated.current = Math.min(1, accumulated.current + (now - last) / 1600); last = now;
      setProgress(accumulated.current);
      if (accumulated.current >= 1) { stop(); onReveal(); }
    }, 40);
  };
  return <button className={`aurora-crystal ${progress > 0 ? "charged" : ""}`} type="button" aria-label={tr("Удерживать кристалл билета № {0}", ticket.public_number)} style={{ "--charge": progress } as React.CSSProperties}
    onPointerDown={e => { if (e.button !== 0) return; e.currentTarget.setPointerCapture?.(e.pointerId); start(); }} onPointerMove={e => { if (!timer.current) return; const rect = e.currentTarget.getBoundingClientRect(); e.currentTarget.style.setProperty("--tilt", `${Math.max(-8,Math.min(8,(e.clientX - rect.left - rect.width / 2) / 15))}deg`); }} onPointerUp={stop} onPointerCancel={stop} onLostPointerCapture={stop} onBlur={stop}
    onKeyDown={e => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); if (!e.repeat) start(); } }} onKeyUp={e => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); stop(); } }}>
    <span className="aurora-crystal-orbit" aria-hidden="true" /><span className="aurora-gem" aria-hidden="true"><i /><i /><i /><i /></span>
    <strong>{tr("Удерживайте кристалл")}</strong><small>{progress > 0 ? tr("{0}% · можно продолжить", Math.round(progress * 100)) : tr("Соберите свет и откройте результат")}</small><span className="aurora-charge" aria-hidden="true"><i style={{ width: `${progress * 100}%` }} /></span>
  </button>;
}

function AuroraTicket({ ticket, revealed, onReveal }: { ticket: InstantTicket; revealed: boolean; onReveal?: () => void }) {
  return <article className={`aurora-ticket ${revealed ? "revealed" : "sealed"} ${revealed && ticket.prize_amount > 0 ? "winner" : ""}`} aria-label={tr("Билет № {0}", ticket.public_number)}>
    <header><span>CASPER <b>AURORA</b></span><small>№ {tr(ticket.public_number.toLocaleString(getLocale()))}</small></header>
    {revealed ? <div className="aurora-reveal" role="status"><span aria-hidden="true">✧</span><small>{ticket.prize_amount > 0 ? tr("ВАШ ВЫИГРЫШ") : tr("БЕЗ ВЫИГРЫША")}</small><strong>{ticket.prize_amount > 0 ? <Money value={ticket.prize_amount} /> : tr("В этот раз без приза")}</strong><p>{ticket.prize_amount > 0 ? tr("Уже зачислен на баланс") : tr("Результат сохранён в истории")}</p></div> : onReveal && <Crystal ticket={ticket} onReveal={onReveal} />}
  </article>;
}

export function AuroraView({ initData, balance, onClose, onSettled }: { initData: string; balance: number; onClose: () => void; onSettled: (result: InstantPurchaseResult) => void }) {
  const [history, setHistory] = useState<InstantTicket[]>([]);
  const [result, setResult] = useState<InstantPurchaseResult | null>(null);
  const [opened, setOpened] = useState<string[]>([]);
  const [quantity, setQuantity] = useState<1 | 3>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [retryQuantity, setRetryQuantity] = useState<1 | 3 | null>(null);
  const buying = useRef(false);
  const pending = useRef<{ key: string; quantity: 1 | 3 } | null>(null);
  const historyRequest = useRef(0);
  useEffect(() => {
    const resolved = (event: Event) => {
      const detail = (event as CustomEvent<PurchaseResolution>).detail;
      if (!detail.path.endsWith("/aurora/purchases")) return;
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
  const root = useRef<HTMLElement>(null);
  useEffect(() => disableTelegramVerticalSwipes(), []);
  useEffect(() => { const version = ++historyRequest.current; let active = true; void miniAppApi.auroraHistory(initData).then(tickets => { if (active && version === historyRequest.current) setHistory(tickets); }).catch(() => undefined); return () => { active = false; }; }, [initData]);
  const buy = async () => {
    if (buying.current) return;
    buying.current = true; setBusy(true); setError(""); selectionHaptic();
    const request = pending.current ?? { key: crypto.randomUUID(), quantity }; pending.current = request;
    try {
      const purchase = await miniAppApi.auroraPurchase(initData, request.quantity, request.key);
      pending.current = null; setRetryQuantity(null); historyRequest.current += 1; setResult(purchase); setOpened([]);
      setHistory(current => [...purchase.tickets, ...current.filter(item => !purchase.tickets.some(ticket => ticket.id === item.id))].slice(0, 30));
      onSettled(purchase); root.current?.scrollIntoView?.({ block: "start", behavior: "instant" });
    } catch (reason) { if (reason instanceof ApiError && reason.status < 500) { pending.current = null; setRetryQuantity(null); } else setRetryQuantity(request.quantity); setError(reason instanceof ApiError ? reason.message : tr("Нет связи. Повторите запрос — повторного списания не будет.")); errorHaptic(); }
    finally { buying.current = false; setBusy(false); }
  };
  const reveal = (ids: string[]) => { setOpened(current => Array.from(new Set([...current, ...ids]))); if (result?.tickets.some(t => ids.includes(t.id) && t.prize_amount > 0)) successHaptic(); else selectionHaptic(); };
  const complete = !!result && result.tickets.every(t => opened.includes(t.id));
  const previous = history.filter(t => !result?.tickets.some(current => current.id === t.id));
  return <main ref={root} className="aurora-page">
    <header className="aurora-header"><button type="button" aria-label={tr("Закрыть")} disabled={busy} onClick={onClose}>←</button><div><small>{tr("МОМЕНТАЛЬНАЯ ЛОТЕРЕЯ")}</small><strong>Casper <em>Aurora</em></strong></div><span><small>{tr("БАЛАНС")}</small><Money value={balance} compact /></span></header>
    {!result && <><section className="aurora-hero"><img src={artwork} alt={tr("Кристалл на ледяном озере под северным сиянием")} /><div><span>{tr("СЕВЕРНОЕ СИЯНИЕ В ВАШИХ РУКАХ")}</span><h1>{tr("Свет внутри.")}<br /><em>{tr("Момент — ваш.")}</em></h1><p>{tr("Удержите кристалл.")}<br />{tr("Откройте свою Aurora.")}</p></div><footer><span>{tr("До")} <Money value={1_000_000} compact /></span><span>{tr("Результат сразу")}</span></footer></section>
    <section className="aurora-buy"><header><strong>{tr("Ваши кристаллы")}</strong><small>{tr("Билет")} <Money value={3_000} /></small></header><div className="aurora-quantity" role="group" aria-label={tr("Количество билетов")}>{([1,3] as const).map(n => <button type="button" key={n} aria-pressed={quantity === n} disabled={busy || retryQuantity !== null} onClick={() => { setQuantity(n); selectionHaptic(); }}><b>{n === 1 ? tr("1 билет") : tr("3 билета")}</b><small>{n === 1 ? tr("Один кристалл") : tr("Открыть вместе или по одному")}</small></button>)}</div>
    <button className="aurora-primary" type="button" disabled={busy || balance < (retryQuantity ?? quantity) * 3_000} onClick={() => void buy()}><span>{busy ? tr("Готовим кристаллы…") : retryQuantity !== null ? tr("Повторить запрос") : quantity === 1 ? tr("Купить билет") : tr("Купить 3 билета")}</span><Money value={(retryQuantity ?? quantity) * 3_000} /></button>{error && <p role="alert">{tr(error)}</p>}{balance < quantity * 3_000 && <p>{tr("Недостаточно CAS для покупки")}</p>}<p className="aurora-buy-note">{tr("Раскрывайте удержанием или одним нажатием")}</p></section></>}
    {result && <section className="aurora-results"><header><span>{complete ? tr("СИЯНИЕ РАСКРЫТО") : tr("ВАШИ КРИСТАЛЛЫ ГОТОВЫ")}</span><h1>{complete ? tr("Ваш момент Aurora.") : tr("Соберите свет.")}</h1><p>{complete ? tr("Результаты сохранены в истории.") : tr("Удерживайте каждый кристалл или откройте все сразу.")}</p></header><div className="aurora-tickets">{result.tickets.map(t => <AuroraTicket key={t.id} ticket={t} revealed={opened.includes(t.id)} onReveal={() => reveal([t.id])} />)}</div>{complete ? <><div className="aurora-total" role="status"><span>{tr("Общий выигрыш")}</span><strong><Money value={result.total_prize} /></strong></div><button className="aurora-primary" type="button" disabled={busy || balance < (retryQuantity ?? quantity) * 3000} onClick={() => void buy()}><span>{busy ? tr("Готовим билеты…") : retryQuantity !== null ? tr("Повторить запрос") : quantity === 3 ? tr("Купить ещё 3 билета") : tr("Купить ещё")}</span><Money value={(retryQuantity ?? quantity) * 3000} /></button>{balance < (retryQuantity ?? quantity) * 3000 && <p>{tr("Недостаточно CAS для покупки")}</p>}</> : <button className="aurora-primary" type="button" onClick={() => reveal(result.tickets.map(t => t.id))}>{result.tickets.length === 1 ? tr("Открыть билет") : tr("Открыть все")} ✧</button>}{error && <p role="alert">{tr(error)}</p>}</section>}
    <details className="aurora-guide"><summary>{tr("Выигрыши и вероятности")} <span>＋</span></summary><dl>{[[0,60],[2000,20],[3000,10],[6000,7],[25000,2.8],[200000,.19],[1000000,.01]].map(([prize,chance]) => <div key={prize}><dt>{prize ? <Money value={prize} /> : tr("Без выигрыша")}{prize === 3000 && <small>{tr("Стоимость билета")}</small>}</dt><dd>{tr(chance.toLocaleString(getLocale()))}%</dd></div>)}</dl><p>{tr("Каждый билет независим. Длительность удержания не меняет результат.")}</p></details>
    {previous.length > 0 && <details className="aurora-history"><summary>{tr("Ваши предыдущие билеты")} <span>＋</span></summary>{previous.slice(0,6).map(t => <AuroraTicket key={t.id} ticket={t} revealed />)}</details>}
    <footer className="aurora-footer">CASPER AURORA <i>✧</i>  {tr("Момент северного сияния")}</footer>
  </main>;
}
