import { DistributionBadge } from "./DistributionBadge";
import type { ReactNode } from "react";
import { Money } from "./components";
import { countdown, formatDrawLabel, formatMoscow } from "./format";
import type { Lottery } from "./types";
import grand from "./assets/lotteries/grand-hall-v1.webp";
import classic from "./assets/lotteries/khan-scene.webp";
import september from "./assets/lotteries/september-embankment.jpg";
import portal from "./assets/lotteries/pll-portal.jpg";
import nature from "./assets/lotteries/pss-nature-scene.webp";
import grob from "./assets/lotteries/halloween-pumpkins-v1.webp";
import dual from "./assets/lotteries/casper-dual-scene.webp";
import bingo from "./assets/lotteries/weekly-scene.webp";
import "./play-room.css";

const artwork: Record<string, string> = { weekly: grand, khan: classic, september, pll: portal, pss: nature, grob, dual, bingo };

export function GameHeader({ lottery, balance, now, onClose, children, artworkOverride }: { lottery: Lottery; balance?: number; now: number; onClose: () => void; children?: ReactNode; artworkOverride?: string }) {
  return <header className="play-header">
    <div className="play-topbar"><button className="play-back" type="button" onClick={onClose} aria-label="Вернуться к лотереям">←</button><div><h1>{lottery.name}</h1><small>{formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</small></div>{balance !== undefined && <span className="play-balance" aria-label="Баланс"><Money value={balance} compact /></span>}</div>
    <div className="play-prize-band">
      {(artworkOverride ?? artwork[lottery.code]) && <img src={artworkOverride ?? artwork[lottery.code]} alt="" decoding="async" />}
      <div><small>{lottery.code === "dual" ? "Максимальный выигрыш" : "Джекпот"}</small><strong><Money value={lottery.jackpot} compact /></strong></div>
      <div className="play-countdown"><small>До тиража</small><time>{countdown(lottery.scheduled_at, now)}</time></div>
    </div>
    <DistributionBadge active={lottery.is_distribution} /><div className="play-context"><time dateTime={lottery.scheduled_at ?? undefined}>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Расписание готовится"}</time><div className="play-links">{children}</div></div>
  </header>;
}
