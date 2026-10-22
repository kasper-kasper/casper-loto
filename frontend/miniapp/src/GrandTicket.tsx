import { tr } from "./i18n";
import { Icon, Money } from "./components";
import type { Lottery } from "./types";
import "./grand-hall.css";

export function GrandTicket({ lottery, selected, purchasing, onToggle, onRandomize }: { lottery: Pick<Lottery, "fixed_payouts" | "primary_max_number" | "primary_numbers_to_pick" | "secondary_max_number" | "secondary_numbers_to_pick" | "secondary_storage_offset">; selected: number[]; purchasing: boolean; onToggle: (n: number) => void; onRandomize: () => void }) {
  const offset = lottery.secondary_storage_offset ?? 35;
  const fields = [{ label: tr("Основные числа"), max: lottery.primary_max_number ?? 35, pick: lottery.primary_numbers_to_pick ?? 5, offset: 0 }, { label: tr("Золотые шары"), max: lottery.secondary_max_number ?? 5, pick: lottery.secondary_numbers_to_pick ?? 2, offset }];
  return <section className="grand-ticket" aria-label={tr("Билет Casper Grand")}>
    <header><div><span>{tr("ВАШ ПРОПУСК В БОЛЬШОЙ ЗАЛ")}</span><h2>{tr("Выберите свою комбинацию")}</h2></div><button aria-label={tr("Случайные числа")} type="button" disabled={purchasing} onClick={onRandomize}><Icon name="spark" /></button></header>
    {fields.map(field => { const values = selected.filter(n => field.offset ? n > offset : n <= offset); return <section className={`grand-field ${field.offset ? "grand-stars" : ""}`} key={field.label} aria-label={tr(field.label)}>
      <header><h3>{tr(field.label)} <small>{field.pick}  {tr("из")} {field.max}</small></h3><span role="status">{values.length} / {field.pick}</span></header>
      <div className="grand-grid" style={field.offset ? { gridTemplateColumns: `repeat(${field.max},minmax(0,1fr))` } : undefined}>{Array.from({ length: field.max }, (_, i) => i + 1).map(n => <button className="grand-token" type="button" key={n} disabled={purchasing} aria-label={tr(`${field.label} ${n}`)} aria-pressed={selected.includes(n + field.offset)} onClick={() => onToggle(n + field.offset)}><i aria-hidden="true" /><span>{n}</span></button>)}</div>
      <div className="grand-rack" aria-label={tr("Выбранные {0}", field.label.toLowerCase())}>{Array.from({ length: field.pick }, (_, i) => values[i] === undefined ? <i key={i} aria-hidden="true">·</i> : <button type="button" key={values[i]} disabled={purchasing} onClick={() => onToggle(values[i])} aria-label={tr("Убрать {0} {1}", field.label.toLowerCase(), values[i] - field.offset)}>{values[i] - field.offset}</button>)}</div>
    </section>; })}
    {lottery.fixed_payouts && Object.keys(lottery.fixed_payouts).length > 0 && <details className="grand-prizes"><summary>{tr("Таблица выигрышей")} <span>＋</span></summary><dl>{Object.entries(lottery.fixed_payouts).sort(([a],[b]) => Number(a)-Number(b)).map(([tier, value]) => <div key={tier}><dt>{Math.floor(Number(tier)/10)} + {Number(tier)%10}</dt><dd><Money value={value} /></dd></div>)}<div><dt>5 + 2</dt><dd>{tr("Джекпот")}</dd></div></dl></details>}
    <p className="grand-ticket-note">{tr("Пять основных чисел и два золотых шара — один билет")}</p>
  </section>;
}
