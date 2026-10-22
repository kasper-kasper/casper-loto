import { tr, getLocale, getLanguage } from "./i18n";
import { DimensionalIcon } from "./DimensionalIcon";
import { Money } from "./components";
import { NewYearTitle } from "./NewYear";
import { countdown, formatCas, formatMoscow } from "./format";
import type { Lottery } from "./types";
import type { ReactNode } from "react";
import ticketArt from "./assets/account/account-tickets-v1.webp";
import orbitArt from "./assets/home/lottery-orbit-v1.webp";
import miniClover from "./assets/lotteries/mini-clover.svg";
import "./discovery.css";
import "./home-hub.css";

export interface Highlights { next_event?: { lottery_code: string; scheduled_at: string; draw_number: number; player_ticket_count: number; jackpot: number; phase: string } | null; last_jackpot: null | { lottery_code: string; lottery_name: string; draw_number: number; jackpot_amount: number; occurred_at: string } }

function ticketsWaiting(count: number): string {
  if (getLanguage() === "en") return `${count} ${count === 1 ? "ticket" : "tickets"} awaiting a draw`;
  const ending = count % 100;
  const word = ending >= 11 && ending <= 14 ? tr("билетов") : count % 10 === 1 ? tr("билет") : count % 10 >= 2 && count % 10 <= 4 ? tr("билета") : tr("билетов");
  return tr("{0} {1} {2} тиража", count, word, word === "билет" ? tr("ждёт") : tr("ждут"));
}

export function Today({ stories, lotteries, now, highlights, totalTicketCount, totalWinningTicketCount, monthlyTotalPayout, onOpen, onCatalog, onTickets, onArchive }: { stories?: ReactNode; lotteries: Lottery[]; now: number; highlights: Highlights | null; totalTicketCount: number; totalWinningTicketCount: number; monthlyTotalPayout: number; onOpen: (code: string, live?: boolean) => void; onCatalog: () => void; onTickets: () => void; onArchive: () => void }) {
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
  const date = new Intl.DateTimeFormat(getLocale(), { timeZone: "Europe/Moscow", day: "numeric", month: "long", weekday: "short" }).format(new Date(now));

  return <div className="home-hub">
    <header className="home-heading"><div><span>{tr("ВАШ ДЕНЬ В CASPER")}</span><h1>{tr("Сегодня")}</h1></div><time dateTime={new Date(now).toISOString()}>{tr(date)}</time></header>
    {tr(stories)}
    {next ? <section className={`home-feature home-phase-${phase}${next.code === "mini" ? " home-feature-mini" : next.code === "newyear2027" ? " home-feature-newyear2027" : ""}`} aria-label={tr("Ближайший тираж")}>
      <div className="home-feature-top"><span><i />{phase === "live" ? tr("Сейчас в эфире") : phase === "result" ? tr("Тираж завершён") : tr("Ближайший тираж")}</span><small>№ {next.draw_number}</small></div>
      <div className="home-feature-art" aria-hidden="true"><img src={next.code === "mini" ? miniClover : orbitArt} alt="" width="512" height="362" decoding="async" fetchPriority="high" /></div>
      <div className="home-feature-copy"><h2>{tr(next.code === "newyear2027" ? <NewYearTitle /> : next.name)}</h2>{next.code === "newyear2027" ? <span>{tr("3 символа из 12 · билет 10 000 CAS")}</span> : <><span>{tr("Джекпот")}</span><strong><Money value={next.jackpot} compact /></strong></>}</div>
      <div className="home-feature-time"><time dateTime={next.scheduled_at!}>{tr(formatMoscow(next.scheduled_at!))}  {tr("МСК")}</time><strong>{tr(phase === "waiting" ? countdown(next.scheduled_at, now) : phase === "live" ? "LIVE" : tr("Итоги"))}</strong></div>
      <button type="button" onClick={() => onOpen(next.code, phase !== "waiting")}><span>{phase === "live" ? tr("Смотреть эфир") : phase === "result" ? tr("Результаты тиража") : next.code === "newyear2027" ? tr("Выбрать символы") : next.player_ticket_count ? tr("Моя лотерея") : tr("Открыть лотерею")}</span><span aria-hidden="true">↗</span></button>
    </section> : <section className="home-no-draw"><DimensionalIcon name="history" /><h2>{tr("Новые тиражи скоро")}</h2><p>{tr("Расписание появится здесь. Все игры доступны в каталоге.")}</p><button type="button" onClick={onCatalog}>{tr("Все лотереи ↗")}</button></section>}

    <nav className="home-actions" aria-label={tr("Мои игры")}>
      <button className="home-my-tickets" type="button" onClick={onTickets}><img src={ticketArt} alt="" width="512" height="414" decoding="async" /><span className="home-action-arrow" aria-hidden="true">↗</span><span className="home-action-copy"><strong>{tr("Мои билеты")}</strong><small>{tr(activeTicketCount ? ticketsWaiting(activeTicketCount) : tr("Пока нет активных"))}</small></span></button>
      <button className="home-catalog-link" type="button" onClick={onCatalog}><DimensionalIcon name="catalog" /><span className="home-action-arrow" aria-hidden="true">↗</span><span className="home-action-copy"><strong>{tr("Все лотереи")}</strong><small>{tr("Найдите свою игру")}</small></span></button>
    </nav>
    {nextPersonal && <button className="home-participation" type="button" onClick={onTickets}><span className="home-participation-dot" /><span><small>{tr("Ближайший с вашим билетом")}</small><strong>{tr(nextPersonal.name)} · {tr(formatMoscow(nextPersonal.scheduled_at!))}  {tr("МСК")}</strong></span><span aria-hidden="true">↗</span></button>}

    <section className="home-schedule"><header><h2>{tr("Дальше по расписанию")}</h2><span>{tr("МСК")}</span></header>{agenda.length ? <div className="home-schedule-list">{agenda.map(lottery => <button key={lottery.code} onClick={() => onOpen(lottery.code)} type="button"><span className="home-schedule-icon"><DimensionalIcon name={lottery.code === "bingo" ? "ticket" : "history"} /></span><span className="home-schedule-copy"><strong>{tr(lottery.name)}</strong><time dateTime={lottery.scheduled_at!}>{tr(formatMoscow(lottery.scheduled_at!))}</time></span>{lottery.code !== "newyear2027" && <span className="home-schedule-prize"><small>{lottery.code === "dual" ? tr("Макс. выигрыш") : tr("Джекпот")}</small><Money value={lottery.jackpot} compact /></span>}<span className="home-schedule-arrow" aria-hidden="true">↗</span></button>)}</div> : <p>{tr("Следующие события скоро появятся.")}</p>}</section>

    {jackpot && <section className="home-latest-win"><DimensionalIcon name="profile" /><div><small>{tr("Последний джекпот · лотереи")}</small><strong><Money value={jackpot.jackpot_amount} compact /></strong><p>{tr(jackpot.lottery_name)} · № {jackpot.draw_number}</p><time dateTime={jackpot.occurred_at}>{tr(formatMoscow(jackpot.occurred_at))}  {tr("МСК")}</time></div><button type="button" aria-label={tr("Открыть {0}", tr(jackpot.lottery_name))} onClick={() => onOpen(jackpot.lottery_code)}>↗</button></section>}
    <button className="home-archive-link" type="button" onClick={onArchive}><DimensionalIcon name="history" /><span><strong>{tr("Архив тиражей")}</strong><small>{tr("Результаты и сорванные джекпоты")}</small></span><b aria-hidden="true">↗</b></button>
    <details className="home-statistics"><summary>{tr("Статистика Casper")}<span aria-hidden="true">＋</span></summary><dl><div><dt>{tr("Билетов в истории")}</dt><dd>{tr(totalTicketCount.toLocaleString(getLocale()))}</dd></div><div><dt>{tr("Выигрышных билетов")}</dt><dd>{tr(totalWinningTicketCount.toLocaleString(getLocale()))}</dd></div><div><dt>{tr("Выплачено за месяц")}</dt><dd>{tr(formatCas(monthlyTotalPayout))}</dd></div></dl></details>
  </div>;
}
