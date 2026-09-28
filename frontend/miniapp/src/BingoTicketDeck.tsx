import { useRef, useState } from "react";
import { BingoEdition } from "./BingoEdition";
import type { BingoInventory } from "./BingoView";

type PoolTicket = BingoInventory["tickets"][number];
export function BingoTicketDeck({ inventory, selected, offset, price, busy, retry, available, onToggle, onInspect }: { inventory: BingoInventory; selected: PoolTicket[]; offset: number; price: number; busy: boolean; retry: boolean; available: number; onToggle: (ticket: PoolTicket) => void; onInspect: (ticket: PoolTicket) => void }) {
  const track = useRef<HTMLDivElement>(null);
  const [visibleIndex, setVisibleIndex] = useState(0);
  const move = (index: number) => {
    const node = track.current;
    const card = node?.children[index] as HTMLElement | undefined;
    if (node && card) node.scrollTo({ left: node.scrollLeft + card.getBoundingClientRect().left - node.getBoundingClientRect().left });
  };
  const observe = () => {
    const node = track.current;
    if (!node) return;
    const distances = Array.from(node.children).map(card => Math.abs(card.getBoundingClientRect().left - node.getBoundingClientRect().left));
    setVisibleIndex(distances.indexOf(Math.min(...distances)));
  };
  return <div className="bingo-deck">
    <div className="bingo-ticket-list bingo-deck-track" ref={track} onScroll={observe} aria-label="Варианты билетов Casper Bingo">{inventory.tickets.map((ticket, index) => {
      const chosen = selected.some(t => t.id === ticket.id);
      return <div className={`bingo-choice ${chosen ? "chosen" : ""}`} key={ticket.id}>
        <button className="bingo-ticket-preview" type="button" disabled={busy || retry || (!chosen && selected.length >= available)} onClick={() => onToggle(ticket)} aria-pressed={chosen} aria-label="Выбрать вариант билета">
          <span className="bingo-choice-label"><span>Вариант {String(offset + index + 1).padStart(2, "0")}</span><span className="bingo-choice-check">{chosen ? "Выбран" : "Выбрать"}<i aria-hidden="true">{chosen ? "✓" : "+"}</i></span></span>
          <BingoEdition ticket={ticket} draw={inventory.draw_number} date={inventory.scheduled_at} price={price} compact />
        </button>
        <button className="bingo-inspect" type="button" onClick={() => onInspect(ticket)}>Рассмотреть билет <span aria-hidden="true">↗</span></button>
      </div>;
    })}</div>
    <nav className="bingo-deck-controls" aria-label="Листать билеты"><button type="button" aria-label="Предыдущий вариант билета" disabled={visibleIndex <= 0} onClick={() => move(visibleIndex - 1)}>←</button><span>{visibleIndex + 1} <i>/ {inventory.tickets.length}</i><small>Листайте билеты</small></span><button type="button" aria-label="Следующий вариант билета" disabled={visibleIndex >= inventory.tickets.length - 1} onClick={() => move(visibleIndex + 1)}>→</button></nav>
  </div>;
}
