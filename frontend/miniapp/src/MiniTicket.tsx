import { tr } from "./i18n";
import { Icon, Money } from "./components";
import { formatDrawLabel, formatMoscow, formatTicketLabel } from "./format";
import type { Lottery, Ticket } from "./types";
import clover from "./assets/lotteries/mini-clover.svg";
import "./mini.css";

export function MiniRules({ lottery }: { lottery: Lottery }) {
  return <details className="mini-rules"><summary>{tr("Правила и выигрыши")} <span aria-hidden="true">＋</span></summary>
    <p>{tr("Выберите")} {lottery.numbers_to_pick}  {tr("различных чисел от 1 до")} {lottery.max_number}{tr(". Порядок чисел не важен.")}</p>
    <p>{tr("Ежедневно в 10:30 и 19:15 МСК (Europe/Moscow). Продажи закрываются за 2 минуты до тиража.")}</p>
    <dl><div><dt>{tr("Совпадений")}</dt><dd>{tr("Полная выплата")}</dd></div><div><dt>0–1</dt><dd>{tr("Без выигрыша")}</dd></div>
      {Object.entries(lottery.fixed_payouts ?? {}).sort(([a], [b]) => Number(a) - Number(b)).map(([matches, amount]) => <div key={matches}><dt>{tr(matches)}</dt><dd><Money value={amount} /></dd></div>)}
      <div><dt>{lottery.numbers_to_pick}</dt><dd>{tr("Джекпот")}</dd></div>
    </dl>
    <p>{tr("Выплачивается одна категория по числу совпадений. Суммы включают стоимость билета.")}</p>
    <p>{tr("Базовый джекпот — 20 000 000 CAS. С каждого билета в него поступает 4 000 CAS (40%). Без победителей он переносится дальше. При нескольких выигравших билетах делится поровну; остаток по 1 CAS получают билеты с меньшими номерами. После выигрыша восстанавливается базовый джекпот.")}</p>
    <p>{tr("До")} {lottery.max_tickets_per_purchase}  {tr("билетов за покупку и до")} {lottery.max_tickets_per_user_per_draw}  {tr("от игрока на один тираж. Отмена тиража возвращает полную стоимость билета.")}</p>
  </details>;
}

/** The receipt uses the stored ticket and draw result, never a client-side payout. */
export function MiniTicketDetail({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const selected = new Set(ticket.numbers);
  const winning = new Set(ticket.winning_numbers ?? []);
  const pending = ticket.status === "PURCHASED";
  const refunded = ticket.status === "REFUNDED";
  return <div className="ticket-detail-backdrop mini-ticket-backdrop" onClick={onClose} role="presentation">
    <article className={`mini-receipt${!pending && !refunded ? " has-result" : ""}`} role="dialog" aria-modal="true" aria-label={tr(`Casper Mini · ${formatTicketLabel("mini", ticket.public_number)}`)} onClick={event => event.stopPropagation()}>
      <button type="button" className="mini-receipt-close" aria-label={tr("Закрыть билет")} onClick={onClose}><Icon name="close" /></button>
      <header><img className="mini-receipt-crest" src={clover} alt="" aria-hidden="true" /><span>CASPER MINI</span><small>{tr("— 6 ИЗ 30 —")}</small><h2>{tr(formatTicketLabel("mini", ticket.public_number))}</h2><p>{tr(formatDrawLabel("mini", ticket.draw_number))} · {tr(formatMoscow(ticket.scheduled_at))}  {tr("МСК")}</p><b className="mini-receipt-status">{pending ? tr("Ожидает тиража") : refunded ? tr("Стоимость возвращена") : ticket.prize_amount > 0 ? tr("Выигрыш зачислен") : tr("Тираж завершён")}</b></header>
      <section className="mini-receipt-combination"><span>{tr("ВАША КОМБИНАЦИЯ")}</span><div>{ticket.numbers.map(number => <i key={number}>{tr(String(number).padStart(2, "0"))}</i>)}</div></section>
      <div className="mini-receipt-grid" aria-label={tr("Поле билета 6 из 30")}>{Array.from({ length: 30 }, (_, index) => index + 1).map(number => <i key={number} className={`${selected.has(number) ? "selected" : ""} ${selected.has(number) && winning.has(number) ? "matched" : ""}`}>{tr(String(number).padStart(2, "0"))}</i>)}</div>
      {!pending && !refunded && <section className="mini-receipt-result"><div><span>{tr("Выпавшие числа")}</span><strong>{tr(ticket.winning_numbers?.join(" · "))}</strong></div><div><span>{tr("Совпадений:")} {ticket.matches ?? 0}</span><b>{ticket.prize_amount > 0 ? <Money value={ticket.prize_amount} /> : tr("Без выигрыша")}</b></div></section>}
      <footer><span>{refunded ? tr("Возвращено") : tr("Стоимость")}</span><strong><Money value={ticket.purchase_price} /></strong><small>CAS · CASPER LOTO <span aria-hidden="true">♣</span></small></footer>
    </article>
  </div>;
}
