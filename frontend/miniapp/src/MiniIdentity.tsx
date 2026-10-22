import { tr } from "./i18n";
import type { ReactNode } from "react";
import { DistributionBadge } from "./DistributionBadge";
import { Icon, Money } from "./components";
import { countdown, formatMoscow } from "./format";
import type { Lottery } from "./types";
import clover from "./assets/lotteries/mini-clover.svg";
import "./mini.css";

export function MiniHeader({ lottery, balance, now, onClose, children }: { lottery: Lottery; balance?: number; now: number; onClose: () => void; children?: ReactNode }) {
  return <header className="mini-header">
    <div className="mini-topbar"><button type="button" onClick={onClose} aria-label={tr("Вернуться к лотереям")}>←</button><div><h1>Casper Mini</h1><span>{tr("КЛАССИКА")} <i />  {tr("6 ИЗ 30")}</span></div>{balance !== undefined && <span className="mini-balance" aria-label={tr("Баланс")}><Money value={balance} compact /></span>}</div>
    <div className="mini-jackpot-band"><div><span>{tr("Джекпот")}</span><strong><Money value={lottery.jackpot} /></strong></div><img src={clover} alt="" aria-hidden="true" /><div className="mini-clock"><span>{tr("До тиража")}</span><time>{tr(countdown(lottery.scheduled_at, now))}</time></div></div>
    <div className="mini-context"><time dateTime={lottery.scheduled_at ?? undefined}>{lottery.scheduled_at ? tr("{0} МСК", formatMoscow(lottery.scheduled_at)) : tr("Расписание готовится")}</time><div>{tr(children)}</div></div>
    <DistributionBadge active={lottery.is_distribution} />
  </header>;
}

/** Mini owns its visual coupon; the shared composer still owns every action. */
export function MiniCoupon({ lottery, selected, purchasing, drawCount, onToggle, onRandomize }: { lottery: Lottery; selected: number[]; purchasing: boolean; drawCount: 1 | 5; onToggle: (number: number) => void; onRandomize: () => void }) {
  return <section className="mini-coupon" aria-label={tr("Классический билет {0} из {1}", lottery.numbers_to_pick, lottery.max_number)}>
    <div className="mini-coupon-engraving" aria-hidden="true"><span>✥</span><span>✥</span><span>✥</span><span>✥</span></div>
    <header className="mini-coupon-heading"><div><span>{tr("CASPER MINI · КЛАССИКА")}</span><h2>{tr("Ваш билет")}</h2></div><button type="button" aria-label={tr("Случайные числа")} disabled={purchasing} onClick={onRandomize}><Icon name="spark" /><span>{tr("Случайно")}</span></button></header>
    <div className="mini-field-label"><span>{tr("Выберите")} {lottery.numbers_to_pick}  {tr("чисел")}</span><span role="status" aria-live="polite">{selected.length}  {tr("из")} {lottery.numbers_to_pick}</span></div>
    <div className="mini-number-grid" aria-label={tr("Числа")}>{Array.from({ length: lottery.max_number }, (_, index) => index + 1).map(number => <button type="button" key={number} aria-label={tr(String(number))} aria-pressed={selected.includes(number)} disabled={purchasing} onClick={() => onToggle(number)}><span>{tr(String(number).padStart(2, "0"))}</span></button>)}</div>
    <div className="mini-coupon-stub"><div className="mini-stub-label"><span>{tr("ВАША КОМБИНАЦИЯ")}</span><span>{selected.length === lottery.numbers_to_pick ? tr("Билет готов") : tr("Ещё {0}", lottery.numbers_to_pick - selected.length)}</span></div><div className="mini-chosen" aria-label={tr("Выбранная комбинация")}>{Array.from({ length: lottery.numbers_to_pick }, (_, index) => selected[index] !== undefined ? <button key={index} type="button" disabled={purchasing} aria-label={tr("Убрать число {0}", selected[index])} onClick={() => onToggle(selected[index])}>{tr(String(selected[index]).padStart(2, "0"))}</button> : <span key={index} aria-hidden="true">·</span>)}</div><footer><span>{tr("Одна комбинация ·")} {drawCount === 5 ? tr("5 тиражей") : tr("1 тираж")}</span><span>6 / 30</span></footer></div>
  </section>;
}
