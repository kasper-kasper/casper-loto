import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { miniAppApi } from "./api";
import { GameHeader } from "./GameHeader";
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
        catch { if (active) setError("Не удалось обновить эфир. Переподключаемся…"); }
      }
      if (active) timer = setTimeout(() => void poll(), 2000);
    };
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [initData, lottery.code, tab]);
  return <div className={`play-room game-${lottery.code}`}>
    <GameHeader lottery={lottery} balance={balance} now={now} onClose={onClose}>
      {tab === "live" && <button type="button" onClick={() => setTab("tickets")}>К билетам</button>}
      <button type="button" onClick={onTickets}>Мои билеты</button>
      {tab === "tickets" && <button type="button" aria-label="Эфир и результаты" onClick={() => setTab("live")}>Эфир ↗</button>}
    </GameHeader>
    {error && <p className="play-message is-error" role="alert">{error}</p>}{tab === "tickets" ? children : <LiveView feed={feed} now={now} loading={!feed} onPlay={() => setTab("tickets")} onTickets={onTickets} />}
  </div>;
}
