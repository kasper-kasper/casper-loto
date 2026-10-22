import { tr } from "./i18n";
import { DistributionBadge } from "./DistributionBadge";
import type { ReactNode } from "react";
import { Money } from "./components";
import { countdown, formatDrawLabel, formatMoscow } from "./format";
import type { Lottery } from "./types";
import grand from "./assets/lotteries/grand-hall-v1.webp";
import classic from "./assets/lotteries/khan-scene.webp";
import mini from "./assets/lotteries/mini-clover.svg";
import september from "./assets/lotteries/september-embankment.jpg";
import portal from "./assets/lotteries/pll-portal.jpg";
import nature from "./assets/lotteries/pss-nature-scene.webp";
import grob from "./assets/lotteries/halloween-pumpkins-v1.webp";
import dual from "./assets/lotteries/casper-dual-scene.webp";
import bingo from "./assets/lotteries/weekly-scene.webp";
import "./play-room.css";

const artwork: Record<string, string> = { weekly: grand, khan: classic, mini, september, pll: portal, pss: nature, grob, dual, bingo };

export function GameHeader({ lottery, balance, now, onClose, children, artworkOverride }: { lottery: Lottery; balance?: number; now: number; onClose: () => void; children?: ReactNode; artworkOverride?: string }) {
  return <header className="play-header">
    <div className="play-topbar"><button className="play-back" type="button" onClick={onClose} aria-label={tr("Вернуться к лотереям")}>←</button><div><h1>{tr(lottery.name)}</h1><small>{tr(formatDrawLabel(lottery.code, lottery.draw_number ?? 0))}</small></div>{balance !== undefined && <span className="play-balance" aria-label={tr("Баланс")}><Money value={balance} compact /></span>}</div>
    <div className="play-prize-band">
      {(artworkOverride ?? artwork[lottery.code]) && <img src={artworkOverride ?? artwork[lottery.code]} alt="" decoding="async" />}
      <div><small>{lottery.code === "dual" ? tr("Максимальный выигрыш") : tr("Джекпот")}</small><strong><Money value={lottery.jackpot} compact /></strong></div>
      <div className="play-countdown"><small>{tr("До тиража")}</small><time>{tr(countdown(lottery.scheduled_at, now))}</time></div>
    </div>
    <DistributionBadge active={lottery.is_distribution} /><div className="play-context"><time dateTime={lottery.scheduled_at ?? undefined}>{lottery.scheduled_at ? tr("{0} МСК", formatMoscow(lottery.scheduled_at)) : tr("Расписание готовится")}</time><div className="play-links">{tr(children)}</div></div>
  </header>;
}
