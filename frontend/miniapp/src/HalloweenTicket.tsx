import { Icon, Money } from "./components";
import type { Lottery } from "./types";
import { HalloweenPumpkin } from "./HalloweenPumpkin";

export function HalloweenTicket({ lottery, selected, purchasing, drawCount, onToggle, onRandomize }: { lottery: Lottery; selected: number[]; purchasing: boolean; drawCount: 1 | 5; onToggle: (number: number) => void; onRandomize: () => void }) {
  return <section className="halloween-ticket" aria-label={`Билет Casper Halloween ${lottery.numbers_to_pick} из ${lottery.max_number}`}>
    <header><div><span>ВАШ ПРАЗДНИЧНЫЙ БИЛЕТ</span><h2>Выберите {lottery.numbers_to_pick} числа из {lottery.max_number}</h2></div><button type="button" aria-label="Случайные числа" disabled={purchasing} onClick={onRandomize}><Icon name="spark" /></button></header>
    <div className="ticket-number-grid halloween-number-grid" aria-label="Числа">
      {Array.from({ length: lottery.max_number }, (_, index) => index + 1).map(value => <button type="button" key={value} className="halloween-number" aria-label={String(value)} aria-pressed={selected.includes(value)} disabled={purchasing} onClick={() => onToggle(value)}>{selected.includes(value) && <HalloweenPumpkin id={`halloween-number-${value}`} />}<span>{value}</span></button>)}
    </div>
    <div className="halloween-selected"><span>Ваша комбинация</span><div aria-label="Выбранная комбинация">{Array.from({ length: lottery.numbers_to_pick }, (_, index) => selected[index] !== undefined ? <button key={index} type="button" className="halloween-lantern lit" disabled={purchasing} aria-label={`Убрать число ${selected[index]}`} onClick={() => onToggle(selected[index])}><HalloweenPumpkin id={`halloween-selected-${index}`} /><span>{selected[index]}</span></button> : <i className="halloween-lantern" key={index} aria-hidden="true">·</i>)}</div><small role="status">{selected.length} из {lottery.numbers_to_pick}</small></div>
    <footer>{drawCount === 5 ? "Одна комбинация · 5 тиражей" : "Одна комбинация · 1 тираж"}</footer>
    {lottery.fixed_payouts && <div className="halloween-prizes" aria-label="Выигрыши">{Object.entries(lottery.fixed_payouts).filter(([, amount]) => amount > 0).map(([matches, amount]) => <span key={matches}>{matches} совпадения <strong><Money value={amount} /></strong></span>)}<span>{lottery.numbers_to_pick} совпадения <strong>Джекпот</strong></span></div>}
  </section>;
}
