import { logoSymbol } from "./brand";
import { formatCas, formatMoscow } from "./format";
import type { BingoResult } from "./BingoView";
import "./bingo-edition.css";

export function BingoEdition({ ticket, draw, date, price, revealed = [], result, compact = false }: { ticket: { public_number?: number; numbers: number[] }; draw: number; date: string; price: number; revealed?: number[]; result?: BingoResult | null; compact?: boolean }) {
  const hits = new Set(revealed);
  return <article className={`bingo-edition ${compact ? "edition-compact" : ""}`}>
    <header className="edition-heading"><span className="edition-medallion" aria-hidden="true"><img src={logoSymbol} alt="" /></span><span className="edition-brand">CASPER<strong>BINGO</strong></span><span className="edition-draw">ТИРАЖ<b>№ {String(draw).padStart(4, "0")}</b></span></header>
    {!compact && <div className="edition-date"><time dateTime={date}>{formatMoscow(date)} МСК</time><span>12 чисел · 3 строки</span></div>}
    <div className="edition-face"><div className="edition-spine" aria-hidden="true"><span>CASPER</span><i>✦</i><span>BINGO</span></div><div className="bingo-grid edition-grid">{[0, 1, 2].map(row => <div className={ticket.numbers.slice(row * 4, row * 4 + 4).every(n => hits.has(n)) ? "closed-row" : ""} key={row}>{ticket.numbers.slice(row * 4, row * 4 + 4).map(n => <span key={n} className={hits.has(n) ? "hit" : ""} aria-label={`${n}${hits.has(n) ? ", совпало" : ""}`}><b>{String(n).padStart(2, "0")}</b>{hits.has(n) && <i aria-hidden="true">✓</i>}</span>)}</div>)}</div></div>
    <footer className="edition-footer"><span><small>{ticket.public_number ? "СЕРИЙНЫЙ НОМЕР" : "ДО ПОКУПКИ"}</small><b>{ticket.public_number ? `KB-${String(ticket.public_number).padStart(6, "0")}` : "ВАРИАНТ БИЛЕТА"}</b></span><span><small>СТОИМОСТЬ</small><b>{formatCas(price)}</b></span></footer>
    {!compact && <div className="edition-imprint"><span aria-hidden="true">✦</span> CASPER BINGO <span aria-hidden="true">✦</span></div>}
    {result && <div className="edition-result"><strong>{result.amounts.some(Boolean) ? `Ваш выигрыш · ${formatCas(result.amounts.reduce((a, b) => a + b, 0))}` : "В этот раз без выигрыша"}</strong><small>Совпало {ticket.numbers.filter(n => hits.has(n)).length} из 12</small>{result.amounts.map((amount, i) => amount > 0 && <p key={i}>{["Одна строка", "Две строки", "Джекпот", "Полная карточка"][i]} <b>{formatCas(amount)}</b></p>)}</div>}
  </article>;
}
