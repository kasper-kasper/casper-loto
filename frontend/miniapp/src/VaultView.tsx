import { useEffect, useRef, useState } from "react";
import { ApiError, miniAppApi } from "./api";
import { Money } from "./components";
import { disableTelegramVerticalSwipes, lockInteractionViewport } from "./interactionLock";
import { errorHaptic, selectionHaptic, successHaptic } from "./telegram";
import type { InstantPurchaseResult, InstantTicket } from "./types";
import artwork from "./assets/lotteries/vault-treasury-v1.webp";
import "./vault.css";

function VaultWheel({ ticket, onReveal }: { ticket: InstantTicket; onReveal: () => void }) {
  const [progress, setProgress] = useState(0);
  const amount = useRef(0);
  const pointer = useRef<{ id: number; angle: number } | null>(null);
  const release = useRef<(() => void) | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const finish = () => { pointer.current = null; if (timer.current) clearInterval(timer.current); timer.current = null; release.current?.(); release.current = null; };
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); release.current?.(); }, []);
  const advance = (degrees: number) => { const next = amount.current + degrees / 540; amount.current = next >= 1 - 1e-9 ? 1 : next; setProgress(amount.current); if (amount.current >= 1) { finish(); onReveal(); } };
  const angle = (e: React.PointerEvent<HTMLButtonElement>) => { const r = e.currentTarget.querySelector(".vault-wheel")!.getBoundingClientRect(); return Math.atan2(e.clientY - r.top - r.height / 2, e.clientX - r.left - r.width / 2) * 180 / Math.PI; };
  return <button className="vault-wheel-control" type="button" aria-label={`Повернуть колесо сейфа № ${ticket.public_number}`} style={{ "--turn": `${progress * 540}deg` } as React.CSSProperties}
    onPointerDown={e => { if (e.button !== 0 || pointer.current || timer.current) return; pointer.current = { id: e.pointerId, angle: angle(e) }; release.current = lockInteractionViewport(); e.currentTarget.setPointerCapture?.(e.pointerId); }}
    onPointerMove={e => { const p = pointer.current; if (!p || p.id !== e.pointerId) return; const next = angle(e); const delta = (next - p.angle + 540) % 360 - 180; p.angle = next; advance(Math.abs(delta)); }} onPointerUp={finish} onPointerCancel={finish} onLostPointerCapture={finish} onBlur={finish}
    onKeyDown={e => { if (["ArrowLeft","ArrowRight"," ","Enter"].includes(e.key)) { e.preventDefault(); if (e.key.startsWith("Arrow")) advance(90); else if (!timer.current && !e.repeat) { release.current = lockInteractionViewport(); let last = performance.now(); timer.current = setInterval(() => { const now = performance.now(); advance((now-last) * 540 / 1800); last = now; },40); } } }} onKeyUp={e => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); finish(); } }}>
    <span className="vault-door" aria-hidden="true"><span className="vault-door-inside" /><span className="vault-wheel"><i /><i /><i /><i /><i /><i /><b /></span><span className="vault-bolts">{Array.from({length:5},(_,i) => <i key={i} className={progress >= (i+1)/5 ? "unlocked" : ""} style={{ "--bolt": `${i*72}deg` } as React.CSSProperties} />)}</span></span>
    <strong>Поверните колесо</strong><small>{Math.floor(progress * 5)} из 5 замков открыто</small><span className="vault-locks" aria-hidden="true">{Array.from({length:5},(_,i) => <i key={i} className={progress >= (i+1)/5 ? "unlocked" : ""} />)}</span>
  </button>;
}

function VaultTicket({ ticket, revealed, onReveal }: { ticket: InstantTicket; revealed: boolean; onReveal?: () => void }) {
  return <article className={`vault-ticket ${revealed ? "revealed" : "sealed"} ${revealed && ticket.prize_amount > 0 ? "winner" : ""}`} aria-label={`Билет № ${ticket.public_number}`}>
    <header><span>CASPER <b>VAULT</b></span><small>№ {ticket.public_number.toLocaleString("ru-RU")}</small></header>
    {revealed ? <div className="vault-reveal" role="status"><span aria-hidden="true">✧</span><small>{ticket.prize_amount > 0 ? "ВАШ ВЫИГРЫШ" : "БЕЗ ВЫИГРЫША"}</small><strong>{ticket.prize_amount > 0 ? <Money value={ticket.prize_amount} /> : "В этот раз без приза"}</strong><p>{ticket.prize_amount > 0 ? "Уже зачислен на баланс" : "Результат сохранён в истории"}</p></div> : onReveal && <VaultWheel ticket={ticket} onReveal={onReveal} />}
  </article>;
}

export function VaultView({ initData, balance, onClose, onSettled }: { initData: string; balance: number; onClose: () => void; onSettled: (result: InstantPurchaseResult) => void }) {
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
  const root = useRef<HTMLElement>(null);
  useEffect(() => disableTelegramVerticalSwipes(), []);
  useEffect(() => { const version = ++historyRequest.current; let active = true; void miniAppApi.vaultHistory(initData).then(tickets => { if (active && version === historyRequest.current) setHistory(tickets); }).catch(() => undefined); return () => { active = false; }; }, [initData]);
  const buy = async () => {
    if (buying.current) return;
    buying.current = true; setBusy(true); setError(""); selectionHaptic();
    const request = pending.current ?? { key: crypto.randomUUID(), quantity }; pending.current = request;
    try {
      const purchase = await miniAppApi.vaultPurchase(initData, request.quantity, request.key);
      pending.current = null; setRetryQuantity(null); historyRequest.current += 1; setResult(purchase); setOpened([]);
      setHistory(current => [...purchase.tickets, ...current.filter(item => !purchase.tickets.some(ticket => ticket.id === item.id))].slice(0, 30));
      onSettled(purchase); root.current?.scrollIntoView?.({ block: "start", behavior: "instant" });
    } catch (reason) { if (reason instanceof ApiError && reason.status < 500) { pending.current = null; setRetryQuantity(null); } else setRetryQuantity(request.quantity); setError(reason instanceof ApiError ? reason.message : "Нет связи. Повторите запрос — повторного списания не будет."); errorHaptic(); }
    finally { buying.current = false; setBusy(false); }
  };
  const reveal = (ids: string[]) => { setOpened(current => Array.from(new Set([...current, ...ids]))); if (result?.tickets.some(t => ids.includes(t.id) && t.prize_amount > 0)) successHaptic(); else selectionHaptic(); };
  const complete = !!result && result.tickets.every(t => opened.includes(t.id));
  const previous = history.filter(t => !result?.tickets.some(current => current.id === t.id));
  return <main ref={root} className="vault-page">
    <header className="vault-header"><button type="button" aria-label="Закрыть" disabled={busy} onClick={onClose}>←</button><div><small>МОМЕНТАЛЬНАЯ ЛОТЕРЕЯ</small><strong>Casper <em>Vault</em></strong></div><span><small>БАЛАНС</small><Money value={balance} compact /></span></header>
    {!result && <><section className="vault-hero"><img src={artwork} alt="Золотой сейф с массивным колесом в тёмной сокровищнице" /><div><span>ЗОЛОТОЙ СЕЙФ. ВАШ КЛЮЧ К МОМЕНТУ.</span><h1>За этой дверью.<br /><em>Ваш момент.</em></h1><p>Поверните колесо.<br />Откройте свой Vault.</p></div><footer><span>До <Money value={5_000_000} compact /></span><span>Результат сразу</span></footer></section>
    <section className="vault-buy"><header><strong>Ваши сейфы</strong><small>Билет <Money value={5_000} /></small></header><div className="vault-quantity" role="group" aria-label="Количество билетов">{([1,3] as const).map(n => <button type="button" key={n} aria-pressed={quantity === n} disabled={busy || retryQuantity !== null} onClick={() => { setQuantity(n); selectionHaptic(); }}><b>{n === 1 ? "1 билет" : "3 билета"}</b><small>{n === 1 ? "Один сейф" : "Открыть вместе или по одному"}</small></button>)}</div>
    <button className="vault-primary" type="button" disabled={busy || balance < (retryQuantity ?? quantity) * 5_000} onClick={() => void buy()}><span>{busy ? "Готовим сейфы…" : retryQuantity !== null ? "Повторить запрос" : quantity === 1 ? "Купить билет" : "Купить 3 билета"}</span><Money value={(retryQuantity ?? quantity) * 5_000} /></button>{error && <p role="alert">{error}</p>}{balance < quantity * 5_000 && <p>Недостаточно CAS для покупки</p>}<p className="vault-buy-note">Открывайте колесом или одним нажатием</p></section></>}
    {result && <section className="vault-results"><header><span>{complete ? "СЕЙФЫ ОТКРЫТЫ" : "ВАШИ СЕЙФЫ ГОТОВЫ"}</span><h1>{complete ? "Ваш момент Vault." : "Откройте замки."}</h1><p>{complete ? "Результаты сохранены в истории." : "Поверните колесо каждого сейфа или откройте все сразу."}</p></header><div className="vault-tickets">{result.tickets.map(t => <VaultTicket key={t.id} ticket={t} revealed={opened.includes(t.id)} onReveal={() => reveal([t.id])} />)}</div>{complete ? <><div className="vault-total" role="status"><span>Общий выигрыш</span><strong><Money value={result.total_prize} /></strong></div><button className="vault-primary" type="button" disabled={busy || balance < (retryQuantity ?? quantity) * 5000} onClick={() => void buy()}><span>{busy ? "Готовим билеты…" : retryQuantity !== null ? "Повторить запрос" : quantity === 3 ? "Купить ещё 3 билета" : "Купить ещё"}</span><Money value={(retryQuantity ?? quantity) * 5000} /></button>{balance < (retryQuantity ?? quantity) * 5000 && <p>Недостаточно CAS для покупки</p>}</> : <button className="vault-primary" type="button" onClick={() => reveal(result.tickets.map(t => t.id))}>{result.tickets.length === 1 ? "Открыть билет" : "Открыть все"} ✧</button>}{error && <p role="alert">{error}</p>}</section>}
    <details className="vault-guide"><summary>Выигрыши и вероятности <span>＋</span></summary><dl>{[[0,21.99],[3000,35],[5000,25],[10000,10],[50000,5],[300000,2],[1000000,1],[5000000,.01]].map(([prize,chance]) => <div key={prize}><dt>{prize ? <Money value={prize} /> : "Без выигрыша"}{prize === 5000 && <small>Стоимость билета</small>}</dt><dd>{chance.toLocaleString("ru-RU")}%</dd></div>)}</dl><p>Каждый билет независим. Вращение колеса не меняет результат.</p></details>
    {previous.length > 0 && <details className="vault-history"><summary>Ваши предыдущие билеты <span>＋</span></summary>{previous.slice(0,6).map(t => <VaultTicket key={t.id} ticket={t} revealed />)}</details>}
    <footer className="vault-footer">CASPER VAULT <i>✧</i> Ваш момент за золотой дверью</footer>
  </main>;
}
