import { tr } from "./i18n";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { miniAppApi } from "./api";
import { GameHeader } from "./GameHeader";
import { ClassicHeader } from "./ClassicHeader";
import { NewYearHeader, NewYearEnvironment } from "./NewYear";
import { MiniHeader } from "./MiniIdentity";
import { GrandHeader } from "./GrandHeader";
import { HalloweenHeader } from "./HalloweenHeader";
import { LiveView } from "./LiveView";
import type { LiveFeed, Lottery } from "./types";
import "./discovery.css";

export { LotteryCatalog } from "./LotteryCatalog";

export function LotteryRoom({ lottery, initData, now, children, onClose, onTickets, onLiveModeChange, initialLive = false, balance }: { balance?: number; initialLive?: boolean; lottery: Lottery; initData: string; now: number; children: ReactNode; onClose: () => void; onTickets: () => void; onLiveModeChange?: (active: boolean) => void }) {
  const [tab, setTab] = useState<"tickets" | "live">(initialLive ? "live" : "tickets");
  const [feed, setFeed] = useState<LiveFeed | null>(null);
  const [error, setError] = useState("");
  useEffect(() => onLiveModeChange?.(tab === "live"), [onLiveModeChange, tab]);
  useEffect(() => {
    if (tab !== "live") return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      if (!document.hidden) {
        try { const next = await miniAppApi.live(initData, "standard", lottery.code); if (active) { setFeed(next); setError(""); } }
        catch { if (active) setError(tr("Не удалось обновить эфир. Переподключаемся…")); }
      }
      if (active) timer = setTimeout(() => void poll(), 2000);
    };
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [initData, lottery.code, tab]);
  const classicTicket = lottery.code === "khan" && tab === "tickets";
  const Header = lottery.code === "newyear2027" ? NewYearHeader : lottery.code === "mini" ? MiniHeader : classicTicket ? ClassicHeader : lottery.code === "grob" ? HalloweenHeader : lottery.code === "weekly" && (lottery.secondary_numbers_to_pick ?? 0) > 0 ? GrandHeader : GameHeader;
  return <div className={`play-room game-${lottery.code}${classicTicket ? " classic-room" : ""}`}>
    {lottery.code === "newyear2027" && <NewYearEnvironment />}
    <Header lottery={lottery} balance={balance} now={now} onClose={onClose}>
      {tab === "live" && <button type="button" onClick={() => setTab("tickets")}>{tr("К билетам")}</button>}
      <button type="button" onClick={onTickets}>{tr("Мои билеты")}</button>
      {tab === "tickets" && <button type="button" aria-label={tr("Эфир и результаты")} onClick={() => setTab("live")}>{tr("Эфир ↗")}</button>}
    </Header>
    {error && <p className="play-message is-error" role="alert">{tr(error)}</p>}{tr(tab === "tickets" ? children : <LiveView feed={feed} now={now} loading={!feed} onPlay={() => setTab("tickets")} onTickets={onTickets} />)}
  </div>;
}
