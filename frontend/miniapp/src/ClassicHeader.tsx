import { DistributionBadge } from "./DistributionBadge";
import type { ReactNode } from "react";
import { Money } from "./components";
import { countdown, formatDrawLabel, formatMoscow } from "./format";
import type { Lottery } from "./types";
import drum from "./assets/lotteries/classic-drum-v1.webp";
import "./classic-ticket.css";

export function ClassicHeader({ lottery, balance, now, onClose, children }: { lottery: Lottery; balance?: number; now: number; onClose: () => void; children?: ReactNode }) {
  return <header className="classic-header">
    <div className="classic-topbar"><button type="button" onClick={onClose} aria-label="Вернуться к лотереям">←</button><div><h1>{lottery.name}</h1><small>{formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</small></div>{balance !== undefined && <span className="classic-balance" aria-label="Баланс"><Money value={balance} compact /></span>}</div>
    <div className="classic-draw"><div><small>Джекпот</small><strong><Money value={lottery.jackpot} compact /></strong></div><div className="classic-machine" aria-hidden="true"><img src={drum} alt="" decoding="async" /></div><div className="classic-draw-clock"><small>До тиража</small><time>{countdown(lottery.scheduled_at, now)}</time></div></div>
    <div className="classic-context"><time dateTime={lottery.scheduled_at ?? undefined}>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Расписание готовится"}</time><div>{children}</div></div>
  <DistributionBadge active={lottery.is_distribution} /></header>;
}
