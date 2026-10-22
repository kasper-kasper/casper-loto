import { tr } from "./i18n";
import { Icon, Money } from "./components";
import type { Lottery } from "./types";
import { HalloweenPumpkin } from "./HalloweenPumpkin";

export function HalloweenTicket({ lottery, selected, purchasing, drawCount, onToggle, onRandomize }: { lottery: Lottery; selected: number[]; purchasing: boolean; drawCount: 1 | 5; onToggle: (number: number) => void; onRandomize: () => void }) {
  return <section className="halloween-ticket" aria-label={tr("Билет Casper Halloween {0} из {1}", lottery.numbers_to_pick, lottery.max_number)}>
    <header><div><span>{tr("ВАШ ПРАЗДНИЧНЫЙ БИЛЕТ")}</span><h2>{tr("Выберите")} {lottery.numbers_to_pick}  {tr("числа из")} {lottery.max_number}</h2></div><button type="button" aria-label={tr("Случайные числа")} disabled={purchasing} onClick={onRandomize}><Icon name="spark" /></button></header>
    <div className="ticket-number-grid halloween-number-grid" aria-label={tr("Числа")}>
      {Array.from({ length: lottery.max_number }, (_, index) => index + 1).map(value => <button type="button" key={value} className="halloween-number" aria-label={tr(String(value))} aria-pressed={selected.includes(value)} disabled={purchasing} onClick={() => onToggle(value)}>{selected.includes(value) && <HalloweenPumpkin id={`halloween-number-${value}`} />}<span>{value}</span></button>)}
    </div>
    <div className="halloween-selected"><span>{tr("Ваша комбинация")}</span><div aria-label={tr("Выбранная комбинация")}>{Array.from({ length: lottery.numbers_to_pick }, (_, index) => selected[index] !== undefined ? <button key={index} type="button" className="halloween-lantern lit" disabled={purchasing} aria-label={tr("Убрать число {0}", selected[index])} onClick={() => onToggle(selected[index])}><HalloweenPumpkin id={`halloween-selected-${index}`} /><span>{selected[index]}</span></button> : <i className="halloween-lantern" key={index} aria-hidden="true">·</i>)}</div><small role="status">{selected.length}  {tr("из")} {lottery.numbers_to_pick}</small></div>
    <footer>{drawCount === 5 ? tr("Одна комбинация · 5 тиражей") : tr("Одна комбинация · 1 тираж")}</footer>
    {lottery.fixed_payouts && <div className="halloween-prizes" aria-label={tr("Выигрыши")}>{Object.entries(lottery.fixed_payouts).filter(([, amount]) => amount > 0).map(([matches, amount]) => <span key={matches}>{tr(matches)}  {tr("совпадения")} <strong><Money value={amount} /></strong></span>)}<span>{lottery.numbers_to_pick}  {tr("совпадения")} <strong>{tr("Джекпот")}</strong></span></div>}
  </section>;
}
