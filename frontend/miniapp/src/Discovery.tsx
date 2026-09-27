import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { miniAppApi } from "./api";
import { logoHorizontal, logoSymbolArt } from "./brand";
import { Money } from "./components";
import { countdown, formatCas, formatMoscow } from "./format";
import { LotteryVisual } from "./LotteryVisuals";
import { LiveView } from "./LiveView";
import type { LiveFeed, Lottery } from "./types";
import "./discovery.css";

export function LotteryCatalog({ lotteries, onOpen }: { lotteries: Lottery[]; onOpen: (code: string) => void }) {
  const [filter, setFilter] = useState("all");
  const largest = Math.max(0, ...lotteries.map(l => l.jackpot));
  const visible = [...lotteries].filter(l => filter === "all" || l.kind === filter).sort((a, b) => b.jackpot - a.jackpot);
  return <><div className="discovery-heading"><span>КОЛЛЕКЦИЯ ИГР KASPER</span><h1>Найдите свою удачу.</h1><p>Выберите лотерею. Билеты, правила и эфир — внутри.</p></div><div className="discovery-filters" aria-label="Каталог лотерей">{[["all", "Все"], ["DAILY", "Каждый день"], ["WEEKLY", "Раз в неделю"]].map(([id, label]) => <button key={id} type="button" aria-pressed={filter === id} onClick={() => setFilter(id)}>{label}</button>)}</div><div className="lottery-catalog" aria-label="Витрина лотерей">{filter === "all" && <button className="catalog-game lottery-kasper-live" type="button" onClick={() => onOpen("kasper-live")} aria-label="Открыть Kasper LIVE"><div className="catalog-art"><b>LIVE</b><span>ЗДЕСЬ И СЕЙЧАС</span></div><div className="catalog-game-body"><h2>Kasper LIVE</h2><small>МГНОВЕННЫЙ РЕЗУЛЬТАТ</small><strong>до 1 млн</strong><time>Без тиражей и ожидания</time><footer><span><Money value={2_000} /></span><i>↗</i></footer></div></button>}{visible.map(lottery => <button className={`catalog-game lottery-${lottery.code} ${lottery.jackpot === largest ? "largest-prize" : ""}`} key={lottery.code} type="button" onClick={() => onOpen(lottery.code)} aria-label={`Открыть ${lottery.name}`}>
      <div className="catalog-art">{lottery.code === "bingo" ? <img loading="lazy" src={logoSymbolArt} alt="" /> : <LotteryVisual code={lottery.code} context="catalog" animated={false} />}{lottery.code === "dual" && <img loading="lazy" className="dual-catalog-logo" src={logoSymbolArt} alt="" />}<span>{lottery.code === "dual" ? "NIGHT 00:30 · DAWN 07:30" : lottery.jackpot === largest ? "САМЫЙ БОЛЬШОЙ ДЖЕКПОТ" : lottery.kind === "WEEKLY" ? "СОБЫТИЕ НЕДЕЛИ" : "ЕЖЕДНЕВНАЯ"}</span></div>
      <div className="catalog-game-body"><h2>{lottery.name}</h2><small>ДЖЕКПОТ</small><strong title={formatCas(lottery.jackpot)}><Money value={lottery.jackpot} compact /></strong><time>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Расписание внутри"}</time><footer><span>{lottery.ticket_price === null ? "Скоро" : <Money value={lottery.ticket_price} />}</span><i>↗</i></footer></div>
    </button>)}</div></>;
}

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
