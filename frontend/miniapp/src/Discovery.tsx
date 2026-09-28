import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { miniAppApi } from "./api";
import { logoHorizontal, logoSymbolArt } from "./brand";
import { countdown, formatCas, formatMoscow } from "./format";
import { LotteryVisual } from "./LotteryVisuals";
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
  const mood: Record<string, string> = { pll: "ВРЕМЯ НЕИЗБЕЖНО", september: "У КАЖДОГО ЧИСЛА СВОЯ ИСТОРИЯ", pss: "ТАМ, ГДЕ НАЧИНАЕТСЯ ТИШИНА", khan: "КЛАССИКА БОЛЬШОЙ ИГРЫ", weekly: "СОБЫТИЕ НЕДЕЛИ", grob: "ТИШИНА. ТИРАЖ НАЧИНАЕТСЯ." };
  return <div className={`lottery-room room-${lottery.code}`}>
    <header className="room-topbar"><button type="button" onClick={onClose} aria-label="Вернуться к лотереям">←</button><img src={logoHorizontal} alt="Casper Loto" />{balance !== undefined && <span>{formatCas(balance)}</span>}</header>
    <section className="room-masthead">{lottery.code !== "dual" && <LotteryVisual code={lottery.code} context="hero" />}<div className="room-masthead-copy">{lottery.code === "dual" && <img className="dual-hero-logo" src={logoSymbolArt} alt="Casper Loto" />}<span>{lottery.code === "dual" ? lottery.draw_number ? `БЛИЖАЙШИЙ ТИРАЖ №${lottery.draw_number}` : "БЛИЖАЙШИЙ ТИРАЖ" : mood[lottery.code]}</span><h1>{lottery.name}</h1><p>{lottery.code === "dual" ? "NIGHT 00:30 · DAWN 07:30 · МСК" : lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Следующий тираж готовится"}</p></div><div className="room-prize"><span>{lottery.code === "dual" ? "ДЖЕКПОТ CASPER DUAL" : "ДЖЕКПОТ"}</span><strong>{lottery.code === "dual" ? `${new Intl.NumberFormat("ru-RU").format(lottery.jackpot)} CAS` : formatCas(lottery.jackpot)}</strong>{lottery.code === "dual" ? <small><span>Ваших билетов: {lottery.player_ticket_count}</span><span>До тиража <b>{countdown(lottery.scheduled_at, now)}</b></span></small> : <small>{lottery.player_ticket_count > 0 ? `Ваших билетов: ${lottery.player_ticket_count}` : "Ваш следующий шанс"}<b>{countdown(lottery.scheduled_at, now)}</b></small>}</div></section>
    <nav aria-label="Разделы лотереи"><button type="button" aria-pressed={tab === "tickets"} onClick={() => setTab("tickets")}>Выбрать числа</button><button type="button" aria-pressed={tab === "live"} onClick={() => setTab("live")}>Эфир и результаты <span aria-hidden="true">↗</span></button></nav>
    {error && <p role="alert">{error}</p>}{tab === "tickets" ? children : <LiveView feed={feed} now={now} loading={!feed} onPlay={() => setTab("tickets")} onTickets={onTickets} />}
  </div>;
}
