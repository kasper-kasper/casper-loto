import { logoSymbolArt } from "./brand";
import { Icon } from "./components";
import { countdown, formatCas, formatCompactAmount, formatMoscow, formatMoscowTime } from "./format";
import { LotteryVisual } from "./LotteryVisuals";
import type { Lottery } from "./types";
import "./discovery.css";

export interface Highlights { next_event?: { lottery_code: string; scheduled_at: string; draw_number: number; player_ticket_count: number; jackpot: number; phase: string } | null; last_jackpot: null | { lottery_code: string; lottery_name: string; draw_number: number; jackpot_amount: number; occurred_at: string } }

const compactPrize = formatCompactAmount;

function moscowDay(value: string | number): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Moscow", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(value));
}

function ticketsWaiting(count: number): string {
  const ending = count % 100;
  const word = ending >= 11 && ending <= 14 ? "билетов" : count % 10 === 1 ? "билет" : count % 10 >= 2 && count % 10 <= 4 ? "билета" : "билетов";
  const action = word === "билет" ? "ждёт" : "ждут";
  return `${count} ${word} ${action} тиража`;
}

export function Today({ lotteries, now, highlights, totalTicketCount, totalWinningTicketCount, monthlyTotalPayout, onOpen, onCatalog, onTickets }: { lotteries: Lottery[]; now: number; highlights: Highlights | null; totalTicketCount: number; totalWinningTicketCount: number; monthlyTotalPayout: number; onOpen: (code: string, live?: boolean) => void; onCatalog: () => void; onTickets: () => void }) {
  const scheduled = [...lotteries].filter(lottery => lottery.scheduled_at).sort((left, right) => Date.parse(left.scheduled_at!) - Date.parse(right.scheduled_at!));
  const fallback = scheduled[0];
  const event = highlights?.next_event;
  const eventLottery = lotteries.find(lottery => lottery.code === event?.lottery_code);
  const next = event && eventLottery ? { ...eventLottery, ...event } : fallback;
  const phase = eventLottery ? event?.phase ?? "waiting" : "waiting";
  const today = moscowDay(now);
  const rest = scheduled.filter(lottery => !(lottery.code === next?.code && lottery.draw_number === next?.draw_number));
  const todayRest = rest.filter(lottery => moscowDay(lottery.scheduled_at!) === today);
  const agenda = (todayRest.length ? todayRest : rest).slice(0, 3);
  const participation = scheduled.filter(lottery => lottery.player_ticket_count > 0);
  const activeTicketCount = participation.reduce((total, lottery) => total + lottery.player_ticket_count, 0);
  const nextPersonal = participation[0];
  const jackpot = highlights?.last_jackpot;
  const currentJackpots = lotteries.reduce((total, lottery) => total + lottery.jackpot, 0);
  const ticker = [
    ["БИЛЕТОВ В ИСТОРИИ", totalTicketCount.toLocaleString("ru-RU")],
    ["ВЫИГРЫШНЫХ БИЛЕТОВ", totalWinningTicketCount.toLocaleString("ru-RU")],
    ["ВЫПЛАЧЕНО ЗА МЕСЯЦ", formatCas(monthlyTotalPayout)],
    ["ДЖЕКПОТЫ СЕЙЧАС", formatCas(currentJackpots)],
  ];

  return <>
    <div className="discovery-heading today-heading"><span>ВАШ ДЕНЬ В KASPER</span><h1>Сегодня может повезти.</h1><p>Вся игра дня — перед вами.</p></div>
    {next ? <section className={`today-event lottery-${next.code}`}><div className="today-event-art">{next.code === "bingo" ? <img src={logoSymbolArt} alt="" /> : <LotteryVisual code={next.code} animated={false} />}</div><span className="today-eyebrow">{phase === "live" ? "СЕЙЧАС В ЭФИРЕ" : phase === "result" ? "ТИРАЖ ЗАВЕРШЁН" : "БЛИЖАЙШИЙ ТИРАЖ"}</span><h2>{next.name}</h2><small>Джекпот</small><strong>{formatCas(next.jackpot)}</strong><div className="today-event-time"><span>{formatMoscow(next.scheduled_at!)} МСК</span><b>{phase === "waiting" ? countdown(next.scheduled_at, now) : phase === "live" ? "LIVE" : "Итоги"}</b></div>{next.player_ticket_count > 0 && <p className="today-participating">✓ У вас {next.player_ticket_count} билетов на этот тираж</p>}<button type="button" onClick={() => onOpen(next.code, phase !== "waiting")}>{phase === "live" ? "Смотреть эфир" : phase === "result" ? "Результаты тиража" : next.player_ticket_count ? "Моя лотерея" : "Открыть лотерею"}<span aria-hidden="true">↗</span></button></section> : <div className="today-empty">Готовим следующие тиражи. Все игры доступны в каталоге.</div>}

    <div className="today-ticker" aria-label="Статистика Kasper"><div>{[...ticker, ...ticker].map(([label, value], index) => <span aria-hidden={index >= ticker.length} key={`${label}-${index}`}><small>{label}</small><b>{value}</b><i>◆</i></span>)}</div></div>

    <section className="today-agenda"><header><div><span>АФИША ДНЯ</span><h2>{todayRest.length ? "Дальше сегодня" : "Следующие события"}</h2></div><button type="button" onClick={onCatalog}>Все лотереи ↗</button></header>{agenda.length ? <div>{agenda.map((lottery, index) => <button className={`lottery-${lottery.code}`} key={lottery.code} onClick={() => onOpen(lottery.code)} type="button"><i><b>{formatMoscowTime(lottery.scheduled_at!)}</b><small>МСК</small></i><span><small>{index === 0 ? "СЛЕДОМ" : `ПОСЛЕ · ${index + 1}`}</small><strong>{lottery.name}</strong>{lottery.player_ticket_count > 0 && <em>✓ {lottery.player_ticket_count} бил.</em>}</span><span><small>ДЖЕКПОТ</small><b>{compactPrize(lottery.jackpot)}</b></span><strong aria-hidden="true">→</strong></button>)}</div> : <p>Новые события скоро появятся.</p>}</section>

    <section className={`today-player ${activeTicketCount ? "in-game" : "empty"}`}><div className="today-player-mark"><Icon name={activeTicketCount ? "ticket" : "spark"} /><i /></div><div className="today-player-copy"><span>ВЫ В ИГРЕ</span><h2>{activeTicketCount ? ticketsWaiting(activeTicketCount) : "Ваше место свободно"}</h2><p>{nextPersonal ? `Ближайший ваш — ${nextPersonal.name}, ${formatMoscowTime(nextPersonal.scheduled_at!)} МСК` : "Выберите игру — и здесь появится ваш ближайший тираж."}</p>{participation.length > 0 && <div>{participation.slice(0, 3).map(lottery => <i key={lottery.code}>{lottery.name}<b>{lottery.player_ticket_count}</b></i>)}</div>}</div><button type="button" onClick={activeTicketCount ? onTickets : onCatalog}>{activeTicketCount ? "Мои билеты" : "Выбрать игру"}<span>↗</span></button></section>

    {jackpot && <section className="today-jackpot"><span className="today-eyebrow">ПОСЛЕДНИЙ ДЖЕКПОТ · ЛОТЕРЕИ</span><h2>{formatCas(jackpot.jackpot_amount)}</h2><p>{jackpot.lottery_name} · тираж №{jackpot.draw_number}</p><small>{formatMoscow(jackpot.occurred_at)} МСК</small><button type="button" onClick={() => onOpen(jackpot.lottery_code)}>Открыть лотерею ↗</button></section>}
  </>;
}

