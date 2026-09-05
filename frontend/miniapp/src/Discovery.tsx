import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { miniAppApi } from "./api";
import { Icon } from "./components";
import { countdown, formatCas, formatMoscow } from "./format";
import { LotteryVisual } from "./LotteryVisuals";
import { LiveView } from "./LiveView";
import type { LiveFeed, Lottery } from "./types";
import "./discovery.css";

export interface Highlights { next_event?: { lottery_code: string; scheduled_at: string; draw_number: number; player_ticket_count: number; jackpot: number; phase: string } | null; last_jackpot: null | { lottery_code: string; lottery_name: string; draw_number: number; jackpot_amount: number; occurred_at: string } }

function compactPrize(value: number): string {
  const unit = value >= 1e9 ? 1e9 : value >= 1e6 ? 1e6 : 1;
  return `${(value / unit).toLocaleString("ru-RU", { maximumFractionDigits: unit === 1 ? 0 : 2 })}${unit === 1e9 ? " млрд" : unit === 1e6 ? " млн" : ""}`;
}

export function LotteryCatalog({ lotteries, onOpen }: { lotteries: Lottery[]; onOpen: (code: string) => void }) {
  const [filter, setFilter] = useState("all");
  const largest = Math.max(0, ...lotteries.map(l => l.jackpot));
  const visible = [...lotteries].filter(l => filter === "all" || l.kind === filter).sort((a, b) => b.jackpot - a.jackpot);
  return <><div className="discovery-heading"><span>КОЛЛЕКЦИЯ ИГР KASPER</span><h1>Найдите свою удачу.</h1><p>Выберите лотерею. Билеты, правила и эфир — внутри.</p></div><div className="discovery-filters" aria-label="Каталог лотерей">{[["all", "Все"], ["DAILY", "Каждый день"], ["WEEKLY", "Раз в неделю"]].map(([id, label]) => <button key={id} type="button" aria-pressed={filter === id} onClick={() => setFilter(id)}>{label}</button>)}</div><div className="lottery-catalog" aria-label="Витрина лотерей">{visible.map(lottery => <button className={`catalog-game lottery-${lottery.code} ${lottery.jackpot === largest ? "largest-prize" : ""}`} key={lottery.code} type="button" onClick={() => onOpen(lottery.code)} aria-label={`Открыть ${lottery.name}`}>
      <div className="catalog-art">{lottery.code === "bingo" ? <img src="/brand/kasper-symbol.svg" alt="" /> : <LotteryVisual code={lottery.code} animated={false} />}<span>{lottery.jackpot === largest ? "САМЫЙ БОЛЬШОЙ ДЖЕКПОТ" : lottery.kind === "WEEKLY" ? "СОБЫТИЕ НЕДЕЛИ" : "ЕЖЕДНЕВНАЯ"}</span></div>
      <div className="catalog-game-body"><h2>{lottery.name}</h2><small>ДЖЕКПОТ</small><strong title={formatCas(lottery.jackpot)}>{compactPrize(lottery.jackpot)} <em>CAS</em></strong><time>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Расписание внутри"}</time><footer><span>{lottery.ticket_price === null ? "Скоро" : formatCas(lottery.ticket_price)}</span><i>↗</i></footer></div>
    </button>)}</div></>;
}

export function Today({ lotteries, now, highlights, onOpen, onCatalog, onTickets, onFast }: { lotteries: Lottery[]; now: number; highlights: Highlights | null; onOpen: (code: string, live?: boolean) => void; onCatalog: () => void; onTickets: () => void; onFast: () => void }) {
  const fallback = [...lotteries].filter(l => l.scheduled_at).sort((a, b) => Date.parse(a.scheduled_at!) - Date.parse(b.scheduled_at!))[0];
  const event = highlights?.next_event;
  const eventLottery = lotteries.find(l => l.code === event?.lottery_code);
  const next = event && eventLottery ? { ...eventLottery, ...event } : fallback;
  const phase = eventLottery ? event?.phase ?? "waiting" : "waiting";
  const participation = lotteries.filter(l => l.player_ticket_count > 0);
  const jackpot = highlights?.last_jackpot;
  return <><div className="discovery-heading today-heading"><span>ВАШ ДЕНЬ В KASPER</span><h1>Сегодня может повезти.</h1><p>Ближайший розыгрыш и всё, что важно для вас.</p></div>{next ? <section className={`today-event lottery-${next.code}`}><div className="today-event-art">{next.code === "bingo" ? <img src="/brand/kasper-symbol.svg" alt="" /> : <LotteryVisual code={next.code} animated={false} />}</div><span className="today-eyebrow">{phase === "live" ? "СЕЙЧАС В ЭФИРЕ" : phase === "result" ? "ТИРАЖ ЗАВЕРШЁН" : "БЛИЖАЙШИЙ ТИРАЖ"}</span><h2>{next.name}</h2><small>Джекпот</small><strong>{formatCas(next.jackpot)}</strong><div className="today-event-time"><span>{formatMoscow(next.scheduled_at!)} МСК</span><b>{phase === "waiting" ? countdown(next.scheduled_at, now) : phase === "live" ? "LIVE" : "Итоги"}</b></div>{next.player_ticket_count > 0 && <p className="today-participating">✓ У вас {next.player_ticket_count} билетов на этот тираж</p>}<button type="button" onClick={() => onOpen(next.code, phase !== "waiting")}>{phase === "live" ? "Смотреть эфир" : phase === "result" ? "Результаты тиража" : next.player_ticket_count ? "Моя лотерея" : "Открыть лотерею"}<span aria-hidden="true">↗</span></button></section> : <div className="today-empty">Готовим следующие тиражи. Все игры доступны в каталоге.</div>}
    <button className="today-personal" type="button" onClick={participation.length ? onTickets : onCatalog}><Icon name={participation.length ? "ticket" : "catalog"} /><span><strong>{participation.length ? `Вы участвуете в ${participation.length} лотереях` : "Какая лотерея ваша?"}</strong><small>{participation.length ? "Билеты и история — в разделе «Моё»" : "Посмотрите все игры в каталоге"}</small></span><b>→</b></button>
    {jackpot && <section className="today-jackpot"><span className="today-eyebrow">ПОСЛЕДНИЙ ДЖЕКПОТ · ЛОТЕРЕИ</span><h2>{formatCas(jackpot.jackpot_amount)}</h2><p>{jackpot.lottery_name} · тираж №{jackpot.draw_number}</p><small>{formatMoscow(jackpot.occurred_at)} МСК</small><button type="button" onClick={() => onOpen(jackpot.lottery_code)}>Открыть лотерею ↗</button></section>}
    <button className="today-fast-link" type="button" onClick={onFast}><Icon name="fast" /><span><b>Есть свободная минута?</b><small>Fast · быстрые игры и своя история</small></span><span aria-hidden="true">↗</span></button>
  </>;
}

export function LotteryRoom({ lottery, initData, now, children, onClose, onTickets, initialLive = false }: { initialLive?: boolean; lottery: Lottery; initData: string; now: number; children: ReactNode; onClose: () => void; onTickets: () => void }) {
  const [tab, setTab] = useState<"tickets" | "live">(initialLive ? "live" : "tickets");
  const [feed, setFeed] = useState<LiveFeed | null>(null);
  const [error, setError] = useState("");
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
  return <div className="lottery-room"><header><button type="button" onClick={onClose} aria-label="Вернуться к лотереям"><Icon name="arrow" /></button><strong>{lottery.name}</strong></header><nav aria-label="Разделы лотереи"><button type="button" aria-pressed={tab === "tickets"} onClick={() => setTab("tickets")}>Билеты</button><button type="button" aria-pressed={tab === "live"} onClick={() => setTab("live")}>Эфир и результаты</button></nav>{error && <p role="alert">{error}</p>}{tab === "tickets" ? children : <LiveView feed={feed} now={now} loading={!feed} onPlay={() => setTab("tickets")} onTickets={onTickets} />}</div>;
}
