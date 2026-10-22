import { tr } from "./i18n";
import { DistributionBadge } from "./DistributionBadge";
import type { ReactNode } from "react";
import { Money } from "./components";
import { HalloweenBrand } from "./HalloweenBrand";
import { countdown, formatDrawLabel, formatMoscow } from "./format";
import type { Lottery } from "./types";
import scene from "./assets/lotteries/halloween-pumpkins-v1.webp";
import "./halloween.css";

export function HalloweenHeader({ lottery, balance, now, onClose, children }: { lottery: Lottery; balance?: number; now: number; onClose: () => void; children?: ReactNode }) {
  return <header className="halloween-header">
    <div className="play-topbar"><button className="play-back" type="button" onClick={onClose} aria-label={tr("Вернуться к лотереям")}>←</button><div><h1 aria-label={tr(lottery.name)}><HalloweenBrand /></h1><small>{tr(formatDrawLabel(lottery.code, lottery.draw_number ?? 0))}</small></div>{balance !== undefined && <span className="play-balance" aria-label={tr("Баланс")}><Money value={balance} compact /></span>}</div>
    <div className="halloween-scene"><img src={scene} alt="" width="1536" height="1024" decoding="async" /><span className="halloween-scene-caption">{tr("Праздничная магия — круглый год")}</span></div>
    <div className="halloween-draw"><div><small>{tr("Джекпот")}</small><strong><Money value={lottery.jackpot} compact /></strong></div><div className="play-countdown"><small>{tr("До тиража")}</small><time>{tr(countdown(lottery.scheduled_at, now))}</time></div></div>
    <DistributionBadge active={lottery.is_distribution} /><div className="play-context"><time dateTime={lottery.scheduled_at ?? undefined}>{lottery.scheduled_at ? tr("{0} МСК", formatMoscow(lottery.scheduled_at)) : tr("Расписание готовится")}</time><div className="play-links">{tr(children)}</div></div>
  </header>;
}
