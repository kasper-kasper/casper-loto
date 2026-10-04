import { DimensionalIcon } from "./DimensionalIcon";
import { Money } from "./components";
import { countdown, formatCas, formatMoscow } from "./format";
import type { Lottery } from "./types";
import ticketArt from "./assets/account/account-tickets-v1.webp";
import orbitArt from "./assets/home/lottery-orbit-v1.webp";
import "./discovery.css";
import "./home-hub.css";

export interface Highlights { next_event?: { lottery_code: string; scheduled_at: string; draw_number: number; player_ticket_count: number; jackpot: number; phase: string } | null; last_jackpot: null | { lottery_code: string; lottery_name: string; draw_number: number; jackpot_amount: number; occurred_at: string } }

function ticketsWaiting(count: number): string {
  const ending = count % 100;
  const word = ending >= 11 && ending <= 14 ? "билетов" : count % 10 === 1 ? "билет" : count % 10 >= 2 && count % 10 <= 4 ? "билета" : "билетов";
  return `${count} ${word} ${word === "билет" ? "ждёт" : "ждут"} тиража`;
}

export function Today({ lotteries, now, highlights, totalTicketCount, totalWinningTicketCount, monthlyTotalPayout, onOpen, onCatalog, onTickets, onArchive }: { lotteries: Lottery[]; now: number; highlights: Highlights | null; totalTicketCount: number; totalWinningTicketCount: number; monthlyTotalPayout: number; onOpen: (code: string, live?: boolean) => void; onCatalog: () => void; onTickets: () => void; onArchive: () => void }) {
  const scheduled = [...lotteries].filter(lottery => lottery.scheduled_at).sort((left, right) => Date.parse(left.scheduled_at!) - Date.parse(right.scheduled_at!));
  const event = highlights?.next_event;
  const eventLottery = lotteries.find(lottery => lottery.code === event?.lottery_code);
  const next = event && eventLottery ? { ...eventLottery, ...event } : scheduled[0];
  const phase = eventLottery ? event?.phase ?? "waiting" : "waiting";
  const agenda = scheduled.filter(lottery => !(lottery.code === next?.code && lottery.draw_number === next?.draw_number)).slice(0, 3);
  const participation = scheduled.filter(lottery => lottery.player_ticket_count > 0);
  const activeTicketCount = participation.reduce((total, lottery) => total + lottery.player_ticket_count, 0);
  const nextPersonal = participation[0];
  const jackpot = highlights?.last_jackpot;
  const date = new Intl.DateTimeFormat("ru-RU", { timeZone: "Europe/Moscow", day: "numeric", month: "long", weekday: "short" }).format(new Date(now));

  return <div className="home-hub">
    <header className="home-heading"><div><span>ВАШ ДЕНЬ В CASPER</span><h1>Сегодня</h1></div><time dateTime={new Date(now).toISOString()}>{date}</time></header>
    {next ? <section className={`home-feature home-phase-${phase}`} aria-label="Ближайший тираж">
      <div className="home-feature-top"><span><i />{phase === "live" ? "Сейчас в эфире" : phase === "result" ? "Тираж завершён" : "Ближайший тираж"}</span><small>№ {next.draw_number}</small></div>
      <div className="home-feature-art" aria-hidden="true"><img src={orbitArt} alt="" width="512" height="362" decoding="async" fetchPriority="high" /></div>
      <div className="home-feature-copy"><h2>{next.name}</h2><span>Джекпот</span><strong><Money value={next.jackpot} compact /></strong></div>
      <div className="home-feature-time"><time dateTime={next.scheduled_at!}>{formatMoscow(next.scheduled_at!)} МСК</time><strong>{phase === "waiting" ? countdown(next.scheduled_at, now) : phase === "live" ? "LIVE" : "Итоги"}</strong></div>
      <button type="button" onClick={() => onOpen(next.code, phase !== "waiting")}><span>{phase === "live" ? "Смотреть эфир" : phase === "result" ? "Результаты тиража" : next.player_ticket_count ? "Моя лотерея" : "Открыть лотерею"}</span><span aria-hidden="true">↗</span></button>
    </section> : <section className="home-no-draw"><DimensionalIcon name="history" /><h2>Новые тиражи скоро</h2><p>Расписание появится здесь. Все игры доступны в каталоге.</p><button type="button" onClick={onCatalog}>Все лотереи ↗</button></section>}

    <nav className="home-actions" aria-label="Мои игры">
      <button className="home-my-tickets" type="button" onClick={onTickets}><img src={ticketArt} alt="" width="512" height="414" decoding="async" /><span className="home-action-arrow" aria-hidden="true">↗</span><span className="home-action-copy"><strong>Мои билеты</strong><small>{activeTicketCount ? ticketsWaiting(activeTicketCount) : "Пока нет активных"}</small></span></button>
      <button className="home-catalog-link" type="button" onClick={onCatalog}><DimensionalIcon name="catalog" /><span className="home-action-arrow" aria-hidden="true">↗</span><span className="home-action-copy"><strong>Все лотереи</strong><small>Найдите свою игру</small></span></button>
    </nav>
    {nextPersonal && <button className="home-participation" type="button" onClick={onTickets}><span className="home-participation-dot" /><span><small>Ближайший с вашим билетом</small><strong>{nextPersonal.name} · {formatMoscow(nextPersonal.scheduled_at!)} МСК</strong></span><span aria-hidden="true">↗</span></button>}

    <section className="home-schedule"><header><h2>Дальше по расписанию</h2><span>МСК</span></header>{agenda.length ? <div className="home-schedule-list">{agenda.map(lottery => <button key={lottery.code} onClick={() => onOpen(lottery.code)} type="button"><span className="home-schedule-icon"><DimensionalIcon name={lottery.code === "bingo" ? "ticket" : "history"} /></span><span className="home-schedule-copy"><strong>{lottery.name}</strong><time dateTime={lottery.scheduled_at!}>{formatMoscow(lottery.scheduled_at!)}</time></span><span className="home-schedule-prize"><small>Джекпот</small><Money value={lottery.jackpot} compact /></span><span className="home-schedule-arrow" aria-hidden="true">↗</span></button>)}</div> : <p>Следующие события скоро появятся.</p>}</section>

    {jackpot && <section className="home-latest-win"><DimensionalIcon name="profile" /><div><small>Последний джекпот · лотереи</small><strong><Money value={jackpot.jackpot_amount} compact /></strong><p>{jackpot.lottery_name} · № {jackpot.draw_number}</p><time dateTime={jackpot.occurred_at}>{formatMoscow(jackpot.occurred_at)} МСК</time></div><button type="button" aria-label={`Открыть ${jackpot.lottery_name}`} onClick={() => onOpen(jackpot.lottery_code)}>↗</button></section>}
    <button className="home-archive-link" type="button" onClick={onArchive}><DimensionalIcon name="history" /><span><strong>Архив тиражей</strong><small>Результаты и сорванные джекпоты</small></span><b aria-hidden="true">↗</b></button>
    <details className="home-statistics"><summary>Статистика Casper<span aria-hidden="true">＋</span></summary><dl><div><dt>Билетов в истории</dt><dd>{totalTicketCount.toLocaleString("ru-RU")}</dd></div><div><dt>Выигрышных билетов</dt><dd>{totalWinningTicketCount.toLocaleString("ru-RU")}</dd></div><div><dt>Выплачено за месяц</dt><dd>{formatCas(monthlyTotalPayout)}</dd></div></dl></details>
  </div>;
}
