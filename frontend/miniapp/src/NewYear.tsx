import { tr } from "./i18n";
import type { CSSProperties, ReactNode } from "react";
import { useId } from "react";
import atlas from "./assets/newyear/symbols.webp";
import champagne from "./assets/newyear/champagne.webp";
import sparklers from "./assets/newyear/sparklers.webp";
import { Icon, Money } from "./components";
import { countdown, formatMoscow, formatTicketLabel, formatDrawLabel } from "./format";
import type { Lottery, Ticket } from "./types";
import "./new-year.css";
import { NEW_YEAR_SYMBOLS } from "./newYearSymbols";

// The illustration has uneven row spacing. Explicit source windows prevent a
// neighbouring object from leaking into a receipt or a non-square thumbnail.
const objectWindows = [
  [0, 0, 380, 355], [400, 0, 260, 355], [706, 0, 380, 358],
  [0, 357, 360, 355], [390, 365, 315, 350], [735, 365, 351, 348],
  [0, 717, 380, 320], [365, 717, 365, 320], [724, 730, 362, 304],
  [0, 1038, 370, 410], [370, 1040, 355, 408], [738, 1040, 348, 408],
];

export function NewYearSymbol({ value }: { value: number }) {
  const clip = useId();
  const area = objectWindows[value - 1];
  if (!area) return null;
  if (value === 2 || value === 7) return <img className="ny-object" src={value === 2 ? champagne : sparklers} alt={tr(NEW_YEAR_SYMBOLS[value - 1])} draggable={false} />;
  const [x, y, width, height] = area;
  return <svg className="ny-object" role="img" aria-label={tr(NEW_YEAR_SYMBOLS[value - 1])} viewBox={area.join(" ")} preserveAspectRatio="xMidYMid meet"><defs><clipPath id={clip}><rect x={x} y={y} width={width} height={height} /></clipPath></defs><image href={atlas} width="1086" height="1448" clipPath={`url(#${clip})`} /></svg>;
}

export function NewYearTitle() {
  return <>{tr("Новогоднее лото")} <em>2027</em></>;
}

export function NewYearPurchaseNotice({ error, notice }: { error: string | null; notice: string | null }) {
  if (!error && !notice) return null;
  return <div className={`ny-purchase-notice${error ? " is-error" : ""}`} role={error ? "alert" : "status"}>{tr(error ?? notice)}</div>;
}

export function NewYearSymbols({ values, slots = 3 }: { values: number[]; slots?: number }) {
  return <div className="ny-symbols">{Array.from({ length: slots }, (_, index) => <span className="ny-symbol-slot" key={index}>{values[index] ? <NewYearSymbol key={values[index]} value={values[index]} /> : <span aria-hidden="true">✧</span>}</span>)}</div>;
}

export function NewYearEnvironment() {
  const lights = [8, 17, 27, 38, 50, 62, 74, 85, 94];
  return <div className="ny-environment" aria-hidden="true"><div className="ny-wire" />{["top", "bottom"].map(row => <div className={`ny-lights ny-lights-${row}`} key={row}>{lights.map((left, index) => <i key={left} style={{ left: `${left}%`, "--delay": `${-index * 0.73}s`, "--light": ["#ffd078", "#f18058", "#99c68f", "#ffe2a8"][index % 4] } as CSSProperties} />)}</div>)}<div className="ny-room-lighting"><div className="ny-tree-lights">{[[8.6,3.6],[32.9,3.3],[35.8,5.6],[21.4,11.5],[14.6,21.4],[8.5,25.2],[43.9,24.4],[20.4,32.8]].map(([left, top], i) => <i key={i} style={{ left: `${left}%`, top: `${top}%`, "--delay": `${-i * 0.63}s`, "--light": ["#ffd078", "#ff9468", "#8df0ad"][i % 3] } as CSSProperties} />)}</div><div className="ny-candle"><b /><i /></div></div></div>;
}

export function NewYearHeader({ lottery, balance, onClose, children }: { lottery: Lottery; balance?: number; now: number; onClose: () => void; children?: ReactNode }) {
  return <header className="ny-header"><div className="ny-topbar"><button type="button" onClick={onClose}>{tr("← К лотереям")}</button>{balance !== undefined && <span><Money value={balance} compact /></span>}</div><h1><NewYearTitle /></h1><div className="ny-title-rule" aria-hidden="true">✥</div><p>{lottery.scheduled_at ? tr("{0} МСК · {1}", formatMoscow(lottery.scheduled_at), formatDrawLabel("newyear2027", lottery.draw_number ?? 0)) : tr("Расписание готовится")}</p><nav>{tr(children)}</nav></header>;
}

export function NewYearCoupon({ selected, purchasing, onToggle, onRandomize }: { selected: number[]; purchasing: boolean; onToggle: (value: number) => void; onRandomize: () => void }) {
  return <section className="ny-coupon" aria-label={tr("Новогодний билет: 3 символа из 12")}><header className="ny-paper ny-prompt"><div><h2>{tr("Ваша тройка")}</h2><p>{tr("Выберите 3 символа")}</p></div><div><strong role="status" aria-live="polite">{selected.length} / 3</strong><button type="button" aria-label={tr("Случайные символы")} onClick={onRandomize} disabled={purchasing}>{tr("⤨ Случайно")}</button></div></header><div className="ny-object-grid" role="group" aria-label={tr("Игровые символы")}>{NEW_YEAR_SYMBOLS.map((name, index) => <button type="button" key={name} aria-label={tr(name)} aria-pressed={selected.includes(index + 1)} disabled={purchasing} onClick={() => onToggle(index + 1)}><NewYearSymbol value={index + 1} /><span className="ny-object-name">{tr(name)}</span><span className="ny-object-check" aria-hidden="true">✓</span></button>)}</div><div className="ny-paper ny-ticket-strip"><strong>{tr("Ваш билет")}</strong><NewYearSymbols values={selected} /></div><div className="ny-coupon-lights" aria-hidden="true">{[0, 1, 2, 3, 4, 5, 6, 7, 8].map(i => <i key={i} style={{ "--delay": `${-i * .71}s`, "--light": ["#ffd078", "#ef8860", "#a5d2a0"][i % 3] } as CSSProperties} />)}</div></section>;
}

export function NewYearRules() {
  return <details className="ticket-options ny-rules"><summary>{tr("Правила и выплаты")} <span aria-hidden="true">＋</span></summary><div className="ny-rules-body"><p>{tr("Выберите 3 разных символа из 12. Порядок не важен. Один билет стоит 10 000 CAS. Тиражи ежедневно в 21:15 по Москве (Europe/Moscow), продажи закрываются в 21:13.")}</p><dl><div><dt>{tr("Совпадений")}</dt><dd>{tr("Полная выплата")}</dd></div><div><dt>0</dt><dd>0 CAS</dd></div><div><dt>1</dt><dd>5 000 CAS</dd></div><div><dt>2</dt><dd>30 000 CAS</dd></div><div><dt>3</dt><dd>{tr("Доля от 1 000 000 CAS")}</dd></div></dl><p>{tr("Общий приз 1 000 000 CAS делится поровну между всеми билетами с тремя совпадениями. Один такой билет получает весь миллион. Неделимый остаток по 1 CAS получают билеты с меньшими номерами. Без полных совпадений миллион не переносится; накопительного джекпота нет. Выплаты за одно и два совпадения фиксированы для каждого билета. Категории не суммируются; стоимость билета включена в выплату.")}</p><p>{tr("Не более 101 билета от игрока на один тираж суммарно во всех покупках. При отмене тиража возвращается полная стоимость билета.")}</p></div></details>;
}

export function NewYearTicketDetail({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const pending = ticket.status === "PURCHASED";
  const refunded = ticket.status === "REFUNDED";
  return <div className="ny-receipt-backdrop" role="presentation" onClick={onClose}><article className={`ny-paper ny-receipt${!pending && !refunded ? " has-result" : ""}`} role="dialog" aria-modal="true" aria-label={tr("Новогоднее лото 2027 · {0}", formatTicketLabel(ticket.lottery_code, ticket.public_number))} onClick={event => event.stopPropagation()}><button type="button" className="ny-receipt-close" onClick={onClose} aria-label={tr("Закрыть билет")}><Icon name="close" /></button><header><span className="ny-receipt-snow" aria-hidden="true">✥</span><h1><NewYearTitle /></h1><h2>{tr(formatTicketLabel(ticket.lottery_code, ticket.public_number))}</h2><p>{tr(formatDrawLabel(ticket.lottery_code, ticket.draw_number))} · {tr(formatMoscow(ticket.scheduled_at))}  {tr("МСК")}</p><b>{pending ? tr("Ожидает тиража") : refunded ? tr("Стоимость возвращена") : ticket.prize_amount ? tr("Выигрыш зачислен") : tr("Тираж завершён")}</b></header><section className="ny-receipt-choice"><h3>{tr("Ваша тройка")}</h3><NewYearSymbols values={ticket.numbers} /><div className="ny-receipt-names">{ticket.numbers.map(value => <span key={value}>{tr(NEW_YEAR_SYMBOLS[value - 1])}</span>)}</div></section>{!pending && !refunded && <section className="ny-receipt-result"><span>{tr("Символы тиража · совпадений")} {ticket.matches ?? 0}</span><NewYearSymbols values={ticket.winning_numbers ?? []} /><strong>{ticket.prize_amount ? <Money value={ticket.prize_amount} /> : tr("Без выигрыша")}</strong></section>}<footer><span>{refunded ? tr("Возвращено") : tr("Стоимость")}<small>CAS · CASPER LOTO</small></span><strong><Money value={ticket.purchase_price} /></strong></footer></article></div>;
}

export function NewYearLiveScene({ scheduledAt, now, values, phase }: { scheduledAt: string; now: number; values: number[]; phase: string }) {
  return <div className={`ny-live-scene ny-live-${phase}`}>{phase === "waiting" && <div className="ny-live-clock"><span>{tr("До тиража")}</span><strong>{tr(countdown(scheduledAt, now))}</strong></div>}{phase === "starting" && <p className="ny-live-clock">{tr("Тираж начинается…")}</p>}<ol className="ny-timeline" aria-label={tr("Этапы тиража")}>{[tr("Ожидание"), tr("Розыгрыш"), tr("Итог")].map((label, index) => <li key={label} aria-current={(phase === "waiting" ? 0 : phase === "result" ? 2 : 1) === index ? "step" : undefined}><i />{tr(label)}</li>)}</ol><section className="ny-paper"><h2>{tr("Символы тиража")}</h2><NewYearSymbols values={values} /></section></div>;
}
