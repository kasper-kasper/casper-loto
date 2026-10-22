import { useEffect, useRef, useState } from "react";
import { GrandHeader } from "../../miniapp/src/GrandHeader";
import { GrandTicket } from "../../miniapp/src/GrandTicket";
import { lotteryCombination } from "../../miniapp/src/grand";
import type { Lottery as MiniLottery } from "../../miniapp/src/types";
import "../../miniapp/src/play-room.css";
import { ApiError, webApi } from "./api";
import type { Lottery } from "./types";
import "./grand-web.css";

export default function GrandPicker({ lottery, onClose, onBought }: { lottery: Lottery; onClose: () => void; onBought: (message: string) => void }) {
  const [selected, setSelected] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const pending = useRef<{ fingerprint: string; key: string } | null>(null);
  const inFlight = useRef(false);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const game: MiniLottery = { ...lottery, sales_open: lottery.purchase_available, max_tickets_per_user_per_draw: lottery.max_tickets_per_user_per_draw ?? 5000 };
  const offset = lottery.secondary_storage_offset;
  const closed = !lottery.purchase_available || (lottery.sales_close_at !== null && Date.parse(lottery.sales_close_at) <= now);
  const mainCount = selected.filter(n => n <= offset).length;
  const specialCount = selected.filter(n => n > offset).length;
  const ready = mainCount === lottery.primary_numbers_to_pick && specialCount === lottery.secondary_numbers_to_pick;
  const toggle = (n: number) => { if (busy) return; setSelected(old => old.includes(n) ? old.filter(v => v !== n) : old.filter(v => (v > offset) === (n > offset)).length >= (n > offset ? lottery.secondary_numbers_to_pick : lottery.primary_numbers_to_pick) ? old : [...old,n].sort((a,b) => a-b)); };
  const purchase = async (combinations: number[][]) => {
    if (closed || inFlight.current) return;
    inFlight.current = true;
    setBusy(true); setError("");
    const fingerprint = JSON.stringify([lottery.code,combinations]);
    if (pending.current?.fingerprint !== fingerprint) pending.current = { fingerprint, key: crypto.randomUUID() };
    try { const result = await webApi.purchase(lottery.code,combinations,pending.current.key); onBought(`Куплено билетов: ${result.ticket_ids.length}. Списано ${result.total_cost.toLocaleString("ru-RU")} CAS.`); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "Покупка не выполнена. Повторите запрос."); }
    finally { inFlight.current = false; setBusy(false); }
  };
  return <div className="modal-backdrop"><section className="picker-panel grand-web game-weekly" aria-label="Casper Grand"><GrandHeader lottery={game} now={now} onClose={onClose} /><GrandTicket lottery={game} selected={selected} purchasing={busy} onToggle={toggle} onRandomize={() => setSelected(lotteryCombination(game))} />
    <section className="play-quick" aria-label="Быстрая покупка"><strong>Случайные билеты</strong><div>{[1,5,25].map(count => <button type="button" key={count} disabled={busy || closed || count > lottery.max_tickets_per_purchase || count + lottery.player_ticket_count > game.max_tickets_per_user_per_draw} onClick={() => void purchase(Array.from({ length: count }, () => lotteryCombination(game)))}>×{count}</button>)}</div></section>
    {error && <p role="alert">{error}</p>}{closed && <p>Продажи закрыты. Ожидаем следующий тираж.</p>}
    <footer className="play-checkout"><div><small>Стоимость билета</small><strong>{lottery.ticket_price?.toLocaleString("ru-RU")} CAS</strong></div><button type="button" disabled={!ready || busy || closed} onClick={() => void purchase([selected])}>{busy ? "Оформляем…" : "Купить билет"}</button></footer>
  </section></div>;
}
