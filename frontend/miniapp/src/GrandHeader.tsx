import { DistributionBadge } from "./DistributionBadge";
import type { ReactNode } from "react";
import type { Lottery } from "./types";
import { Money } from "./components";
import { countdown, formatDrawLabel, formatMoscow } from "./format";
import scene from "./assets/lotteries/grand-hall-v1.webp";
import "./grand-hall.css";

export function GrandHeader({ lottery, balance, now, onClose, children }: { lottery: Lottery; balance?: number; now: number; onClose: () => void; children?: ReactNode }) {
  return <header className="grand-header"><div className="play-topbar"><button type="button" className="play-back" aria-label="Вернуться к лотереям" onClick={onClose}>←</button><div><span className="grand-eyebrow">ВОСКРЕСНЫЙ БОЛЬШОЙ ТИРАЖ</span><h1>Casper Grand</h1><small>{formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</small></div>{balance !== undefined && <span className="play-balance" aria-label="Баланс"><Money value={balance} compact /></span>}</div>
    <div className="grand-hall-art"><img src={scene} alt="Большой зал со львами и двумя стеклянными лототронами" /><span>Воскресенье · 20:00 МСК</span></div>
    <div className="grand-prize-band"><div><small>Джекпот</small><strong><Money value={lottery.jackpot} compact /></strong></div><div><small>До тиража</small><time>{countdown(lottery.scheduled_at, now)}</time></div></div>
    <DistributionBadge active={lottery.is_distribution} /><div className="play-context"><time>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Расписание готовится"}</time><div className="play-links">{children}</div></div></header>;
}
