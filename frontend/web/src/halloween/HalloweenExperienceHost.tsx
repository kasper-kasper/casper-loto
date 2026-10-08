import { useMemo } from "react";
import { HalloweenHeader } from "../../../miniapp/src/HalloweenHeader";
import { HalloweenTicket } from "../../../miniapp/src/HalloweenTicket";
import "../../../miniapp/src/play-room.css";
import type { Lottery } from "../types";
import { useGrobExperience } from "../grob/application/useGrobExperience";
import { createRandomCombination } from "../grob/application/random-ticket";
import { GrobBridge } from "../grob/bridge/GrobBridge";
import "./halloween-web.css";

export default function HalloweenExperienceHost({ lottery, balance, userId, onClose, onBalance }: { lottery: Lottery; balance: number; userId: string; onClose: () => void; onBalance: (balance: number) => void }) {
  const bridge = useMemo(() => new GrobBridge(), []);
  const snapshot = useGrobExperience({ bridge, initialLottery: lottery, initialBalance: balance, userId, onExit: onClose, onBalance });
  const busy = snapshot.purchase.status === "pending" || snapshot.purchase.status === "uncertain";
  const presentation = { ...snapshot.lottery, sales_open: snapshot.salesOpen, max_tickets_per_user_per_draw: snapshot.lottery.max_tickets_per_user_per_draw ?? snapshot.lottery.max_tickets_per_purchase };
  const toggle = (value: number) => bridge.emitIntent({ type: "TOGGLE_NUMBER", value });
  const randomize = () => {
    snapshot.selectedNumbers.forEach(toggle);
    createRandomCombination(presentation.primary_max_number, presentation.primary_numbers_to_pick).forEach(toggle);
  };
  const price = presentation.ticket_price ?? 0;
  return <main className="halloween-web play-room game-grob">
    <HalloweenHeader lottery={presentation} balance={snapshot.balance} now={snapshot.serverNow} onClose={onClose} />
    <HalloweenTicket lottery={presentation} selected={snapshot.selectedNumbers} purchasing={busy || !snapshot.salesOpen} drawCount={1} onToggle={toggle} onRandomize={randomize} />
    <section className="play-quick" aria-label="Быстрая покупка"><div><strong>Быстрая покупка</strong><small>Случайные билеты</small></div><div>{([1, 5, 25] as const).map(quantity => <button type="button" key={quantity} aria-label={`Купить ${quantity} случайных билетов`} disabled={busy || !snapshot.salesOpen || snapshot.balance < quantity * price || quantity > presentation.max_tickets_per_purchase || quantity + presentation.player_ticket_count > presentation.max_tickets_per_user_per_draw} onClick={() => bridge.emitIntent({ type: "BUY_QUICK", quantity })}>×{quantity}</button>)}</div></section>
    {snapshot.purchase.message && <p role="status" className="halloween-web-message">{snapshot.purchase.message}</p>}
    {snapshot.purchase.status === "uncertain" && <button className="secondary" onClick={() => bridge.emitIntent({ type: "RETRY_PURCHASE" })}>Повторить тот же запрос</button>}
    <footer className="play-checkout"><div><small>Стоимость билета</small><strong>{price.toLocaleString("ru-RU")} CAS</strong></div><button type="button" disabled={busy || !snapshot.salesOpen || snapshot.selectedNumbers.length !== presentation.primary_numbers_to_pick || snapshot.balance < price} onClick={() => bridge.emitIntent({ type: "BUY_MANUAL" })}>{busy ? "Оформляем…" : "Купить билет"}</button></footer>
  </main>;
}
