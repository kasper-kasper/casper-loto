import { tr } from "./i18n";
import { Icon } from "./components";
import type { Lottery } from "./types";
import "./classic-ticket.css";

/** Paper coupon and tactile balls are presentation; selection remains in TicketComposer. */
export function ClassicTicket({ lottery, selected, purchasing, drawCount, onToggle, onRandomize }: { lottery: Lottery; selected: number[]; purchasing: boolean; drawCount: 1 | 5; onToggle: (number: number) => void; onRandomize: () => void }) {
  const ready = selected.length === lottery.numbers_to_pick;
  return <section className="classic-coupon" aria-label={tr("Классический билет {0} из {1}", lottery.numbers_to_pick, lottery.max_number)}>
    <div className="classic-paper">
      <header className="classic-paper-heading"><div><span>{lottery.code === "mini" ? "♣ CASPER MINI ♣" : tr("КЛАССИЧЕСКАЯ ЛОТЕРЕЯ")}</span><h2>{tr("Ваш билет")}</h2></div><button type="button" aria-label={tr("Случайные числа")} disabled={purchasing} onClick={onRandomize}><Icon name="spark" /><span>{tr("Случайно")}</span></button></header>
      <div className="classic-field-heading"><span>{tr("Отметьте свои числа")}</span><span role="status" aria-live="polite">{selected.length}  {tr("из")} {lottery.numbers_to_pick}</span></div>
      <div className="ticket-number-grid classic-number-grid" aria-label={tr("Числа")}>
        {Array.from({ length: lottery.max_number }, (_, i) => i + 1).map(value => <button key={value} type="button" className="classic-number" aria-label={tr(String(value))} aria-pressed={selected.includes(value)} disabled={purchasing} onClick={() => onToggle(value)}><span>{tr(value.toString().padStart(2, "0"))}</span></button>)}
      </div>
    </div>
    <div className="classic-ticket-stub">
      <div className="classic-stub-label"><span>{tr("ВАША КОМБИНАЦИЯ")}</span><span>{tr(ready ? tr("Готов к покупке") : tr("Отметьте ещё ") + (lottery.numbers_to_pick - selected.length))}</span></div>
      <div className="classic-ball-tray" aria-label={tr("Выбранная комбинация")}>{Array.from({ length: lottery.numbers_to_pick }, (_, index) => {
        const value = selected[index];
        return value !== undefined ? <button className="classic-ball" key={index} type="button" disabled={purchasing} aria-label={tr("Убрать число {0}", value)} onClick={() => onToggle(value)}><span>{value}</span></button> : <span className="classic-ball-empty" key={index} aria-hidden="true">·</span>;
      })}</div>
      <footer><span>{drawCount === 5 ? tr("Одна комбинация · 5 тиражей") : tr("Одна комбинация · 1 тираж")}</span><span className="classic-paper-seal" aria-hidden="true">{lottery.numbers_to_pick} / {lottery.max_number}</span></footer>
    </div>
  </section>;
}
