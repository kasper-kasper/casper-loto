import { useEffect, useMemo, useRef } from "react";

import { NumberSet, PrimaryButton } from "./components";
import { countdown, formatCas, formatDraw, formatMoscow } from "./format";
import { livePresentation } from "./live";
import { liveStartHaptic } from "./telegram";
import type { LiveFeed } from "./types";

interface LiveViewProps {
  feed: LiveFeed | null;
  now: number;
  loading: boolean;
  onPlay: (lotteryCode: string) => void;
  onTickets: () => void;
}

export function LiveView({ feed, now, loading, onPlay, onTickets }: LiveViewProps) {
  const state = useMemo(() => livePresentation(feed, now), [feed, now]);
  const signalledDraw = useRef<string | null>(null);
  const draw = state.draw;

  useEffect(() => {
    if (!draw || (state.phase !== "starting" && state.phase !== "revealing")) return;
    const drawKey = `${draw.lottery_code}:${draw.draw_number}`;
    if (signalledDraw.current === drawKey) return;
    signalledDraw.current = drawKey;
    liveStartHaptic();
  }, [draw, state.phase]);

  if (loading && !feed) return <section className="live-stage live-loading" aria-label="Загружаем эфир"><div className="live-grid" /><div className="skeleton live-title-skeleton" /><div className="skeleton live-clock-skeleton" /><div className="skeleton live-panel-skeleton" /></section>;
  if (!draw) return <section className="live-stage live-idle"><div className="live-grid" /><span className="live-label"><i /> ЭФИР</span><h1>Расписание готовится</h1><p>Следующий тираж появится здесь автоматически.</p><button className="secondary-button" onClick={onTickets} type="button">Мои билеты</button></section>;

  const winner = draw.player_total_prize > 0;
  const canBuy = state.nextDraw?.lottery_code ?? (state.phase === "waiting" ? draw.lottery_code : null);
  return <section className={`live-stage phase-${state.phase}`}>
    <div className="live-grid" aria-hidden="true" />
    <div className="live-ambient" aria-hidden="true" />
    <header className="live-heading"><span className="live-label"><i /> {state.phase === "waiting" ? "СКОРО В ЭФИРЕ" : state.phase === "result" ? "ТИРАЖ ЗАВЕРШЁН" : "ЭФИР"}</span><span>Тираж #{formatDraw(draw.draw_number)}</span></header>
    <div className="live-identity"><span>{draw.lottery_kind === "WEEKLY" ? "WEEKLY" : "DAILY"}</span><h1>{draw.lottery_name}</h1><time>{formatMoscow(draw.scheduled_at)} МСК</time></div>

    {state.phase === "waiting" && <>
      <div className="live-countdown"><span>До начала тиража</span><strong>{countdown(draw.scheduled_at, now)}</strong><small>Время синхронизировано с сервером</small></div>
      <div className="live-facts"><div><span>Джекпот</span><strong>{formatCas(draw.jackpot)}</strong></div><div><span>Ваши билеты</span><strong>{draw.player_ticket_count}</strong></div></div>
    </>}

    {state.phase === "starting" && <div className="live-start"><span>Тираж начинается</span><strong>Результат фиксируется на сервере</strong><i /></div>}

    {state.phase === "revealing" && <div className="live-reveal" aria-live="polite">
      <span>Выпадает число</span>
      <strong key={state.currentNumber}>{state.currentNumber}</strong>
      <div className="live-sequence">{draw.winning_numbers?.map((number, index) => <i className={index < state.revealedNumbers.length ? "shown" : ""} key={`${number}-${index}`}>{index < state.revealedNumbers.length ? number : "·"}</i>)}</div>
    </div>}

    {state.phase === "result" && <div className={`live-result ${winner ? "winner" : "neutral"}`}>
      <span>Итог тиража</span>
      <div className="live-final-numbers">{state.revealedNumbers.map((number) => <i key={number}>{number}</i>)}</div>
      {draw.player_ticket_count === 0 ? <div className="personal-result"><strong>Вы не участвовали в этом тираже</strong><p>Новый билет можно выбрать для ближайшего розыгрыша.</p></div> : winner ? <div className="personal-result win"><span>Ваш выигрыш</span><strong>+{formatCas(draw.player_total_prize)}</strong><p>Выигрышных билетов: {draw.player_winning_ticket_count}</p></div> : <div className="personal-result"><strong>В этот раз без выигрыша</strong><p>{draw.player_best_matches ? `Лучший результат — ${draw.player_best_matches} совпадения.` : "Совпадений нет."} Следующий шанс уже близко.</p></div>}
      {draw.highlighted_tickets.map((ticket) => <article className="live-ticket" key={ticket.public_number}><div><span>Билет #{formatDraw(ticket.public_number)}</span><strong>{ticket.prize_amount > 0 ? `+${formatCas(ticket.prize_amount)}` : "Без выигрыша"}</strong></div><NumberSet values={ticket.numbers} winning={draw.winning_numbers} animate={ticket.prize_amount > 0} /></article>)}
    </div>}

    {state.nextDraw && <div className="live-next"><span>Следующий тираж</span><strong>{state.nextDraw.lottery_name}</strong><small>{formatMoscow(state.nextDraw.scheduled_at)} МСК · {countdown(state.nextDraw.scheduled_at, now)}</small></div>}
    <div className="live-actions"><button className="secondary-button" onClick={onTickets} type="button">Мои билеты</button>{canBuy && <PrimaryButton onClick={() => onPlay(canBuy)}>Купить билет</PrimaryButton>}</div>
  </section>;
}
