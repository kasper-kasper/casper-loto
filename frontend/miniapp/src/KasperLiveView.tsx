import { useEffect, useState } from "react";

import { ApiError, miniAppApi } from "./api";
import { Money } from "./components";
import { errorHaptic, selectionHaptic, successHaptic } from "./telegram";
import type { InstantPurchaseResult, InstantTicket } from "./types";

import "./kasper-live.css";

const symbols = ["★", "◆", "●", "✦", "☾", "⚡", "♣", "7"];
const wait = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

function Ticket({ ticket }: { ticket: InstantTicket }) {
  return <article className={ticket.prize_amount > 0 ? "kasper-live-ticket winner" : "kasper-live-ticket"}>
    <header><span>CASPER LIVE</span><b>№ {ticket.public_number.toLocaleString("ru-RU")}</b></header>
    <div className="kasper-live-symbols">{ticket.symbols.map((value, index) => <i key={`${value}:${index}`}>{symbols[value - 1] ?? "●"}</i>)}</div>
    <footer><span>{ticket.prize_amount > 0 ? "ОДИНАКОВЫЕ СИМВОЛЫ · ВЫИГРЫШ" : "РАЗНЫЕ СИМВОЛЫ · БЕЗ ВЫИГРЫША"}</span><strong><Money value={ticket.prize_amount} /></strong></footer>
  </article>;
}

export function KasperLiveView({ initData, balance, onClose, onSettled }: { initData: string; balance: number; onClose: () => void; onSettled: (result: InstantPurchaseResult) => void }) {
  const [history, setHistory] = useState<InstantTicket[]>([]);
  const [result, setResult] = useState<InstantPurchaseResult | null>(null);
  const [phase, setPhase] = useState<"idle" | "creating" | "numbering" | "generating" | "result">("idle");
  const [error, setError] = useState("");
  const busy = phase !== "idle" && phase !== "result";

  useEffect(() => {
    void miniAppApi.kasperLiveHistory(initData).then(setHistory).catch(() => undefined);
  }, [initData]);

  const buy = async (quantity: 1 | 3) => {
    selectionHaptic();
    setError("");
    setResult(null);
    setPhase("creating");
    try {
      const purchase = await miniAppApi.kasperLivePurchase(initData, quantity, crypto.randomUUID());
      await wait(650);
      setPhase("numbering");
      await wait(650);
      setPhase("generating");
      await wait(1_200);
      setResult(purchase);
      setHistory((current) => [...purchase.tickets, ...current.filter((item) => !purchase.tickets.some((ticket) => ticket.id === item.id))].slice(0, 30));
      setPhase("result");
      onSettled(purchase);
      successHaptic();
    } catch (reason) {
      setPhase("idle");
      setError(reason instanceof ApiError ? reason.message : "Не удалось создать билет. Попробуйте ещё раз.");
      errorHaptic();
    }
  };

  const phaseLabel = phase === "creating" ? "Создаём билет" : phase === "numbering" ? "Присваиваем номер" : "Casper генерирует комбинацию";
  return <main className="kasper-live-page">
    <header className="kasper-live-header"><button disabled={busy} onClick={onClose} type="button" aria-label="Закрыть">←</button><div><small>НОВОСТЬ В ПРЯМОМ ЭФИРЕ</small><strong>Casper LIVE</strong></div><span><Money value={balance} compact /></span></header>
    <section className="kasper-live-hero"><span>LIVE</span><h1>Результат.<br />Здесь и сейчас.</h1><p>Билет создаётся и рассчитывается сразу. Никаких тиражей и ожидания.</p><small className="kasper-live-rule">Три одинаковых символа — выигрыш. Разные символы — без выигрыша.</small></section>

    {busy && <section className="kasper-live-processing" aria-live="polite"><i /><strong>{phaseLabel}</strong><span>Выпуск в эфир готовится…</span></section>}
    {phase === "result" && result && <section className="kasper-live-result" aria-live="polite"><header><span>ЭФИР ЗАВЕРШЁН</span><strong>{result.total_prize > 0 ? <>Выигрыш <Money value={result.total_prize} /></> : "В этот раз без выигрыша"}</strong></header><div className={result.tickets.length === 3 ? "kasper-live-ticket-grid triple" : "kasper-live-ticket-grid"}>{result.tickets.map((ticket) => <Ticket key={ticket.id} ticket={ticket} />)}</div><button type="button" onClick={() => { setResult(null); setPhase("idle"); }}>Купить ещё</button></section>}

    {phase === "idle" && <section className="kasper-live-buy"><div><small>СТОИМОСТЬ БИЛЕТА</small><strong><Money value={2_000} /></strong></div><button disabled={balance < 2_000} onClick={() => void buy(1)} type="button"><span>1 билет</span><b>2 000 CAS</b></button><button disabled={balance < 6_000} onClick={() => void buy(3)} type="button"><span>3 билета</span><b>6 000 CAS</b></button>{error && <p role="alert">{error}</p>}</section>}

    {!busy && history.length > 0 && <section className="kasper-live-history"><header><span>ВАШИ БИЛЕТЫ</span><small>Последние результаты</small></header><div>{history.map((ticket) => <Ticket key={ticket.id} ticket={ticket} />)}</div></section>}
  </main>;
}
