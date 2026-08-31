import { useEffect, useMemo, useRef, useState } from "react";

import { Icon, NumberSet, PrimaryButton } from "./components";
import { countdown, formatCas, formatDraw, formatMoscow } from "./format";
import { livePresentation, replayPresentation } from "./live";
import { liveStartHaptic, selectionHaptic } from "./telegram";
import type { LiveDraw, LiveFeed } from "./types";

interface LiveViewProps {
  feed: LiveFeed | null;
  now: number;
  loading: boolean;
  onPlay: (lotteryCode: string) => void;
  onTickets: () => void;
}

function drawKey(draw: LiveDraw): string {
  return `${draw.lottery_code}:${draw.draw_number}`;
}

export function LiveView({ feed, now, loading, onPlay, onTickets }: LiveViewProps) {
  const liveState = useMemo(() => livePresentation(feed, now), [feed, now]);
  const [replayKey, setReplayKey] = useState<string | null>(null);
  const [replayStartedAt, setReplayStartedAt] = useState(0);
  const replayDraw = feed?.recent_completed.find((item) => drawKey(item) === replayKey) ?? null;
  const state = replayDraw ? replayPresentation(replayDraw, now - replayStartedAt) : liveState;
  const signalledDraw = useRef<string | null>(null);
  const draw = state.draw;

  useEffect(() => {
    if (!draw || (state.phase !== "starting" && state.phase !== "revealing")) return;
    const key = `${replayDraw ? "replay" : "live"}:${drawKey(draw)}`;
    if (signalledDraw.current === key) return;
    signalledDraw.current = key;
    liveStartHaptic();
  }, [draw, replayDraw, state.phase]);

  const startReplay = (item: LiveDraw) => {
    selectionHaptic();
    setReplayKey(drawKey(item));
    setReplayStartedAt(now);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (loading && !feed) return <section className="live-stage live-loading" aria-label="Загружаем эфир"><div className="live-grid" /><div className="skeleton live-title-skeleton" /><div className="skeleton live-clock-skeleton" /><div className="skeleton live-panel-skeleton" /></section>;
  if (!draw) return <section className="live-stage live-idle"><div className="live-grid" /><span className="live-label"><i /> ЭФИР</span><h1>Расписание готовится</h1><p>Следующий тираж появится здесь автоматически.</p><button className="secondary-button" onClick={onTickets} type="button">Мои билеты</button></section>;

  const isReplay = Boolean(replayDraw);
  const winner = draw.player_total_prize > 0;
  const canBuy = liveState.nextDraw?.lottery_code ?? (liveState.phase === "waiting" ? liveState.draw?.lottery_code : null);
  const startsIn = Math.max(0, new Date(draw.scheduled_at).getTime() - now);
  const finalMinute = !isReplay && state.phase === "waiting" && startsIn <= 60_000;
  const finalMinuteProgress = finalMinute ? Math.max(0, Math.min(100, ((60_000 - startsIn) / 60_000) * 100)) : 0;
  const resultSize = draw.lottery_kind === "WEEKLY" ? 5 : 4;

  return <div className="live-experience">
    <section className={`live-stage lottery-${draw.lottery_code} phase-${state.phase} ${finalMinute ? "final-minute" : ""} ${isReplay ? "is-replay" : "is-live"}`}>
      <div className="live-grid" aria-hidden="true" />
      <div className="live-ambient" aria-hidden="true" />
      <header className="live-heading">
        <span className="live-label"><i /> {isReplay ? "ПОВТОР ТИРАЖА" : state.phase === "waiting" ? "СКОРО В ЭФИРЕ" : state.phase === "result" ? "ТИРАЖ ЗАВЕРШЁН" : "ПРЯМОЙ ЭФИР"}</span>
        {isReplay ? <button className="replay-close" onClick={() => setReplayKey(null)} type="button"><Icon name="close" /> К эфиру</button> : <span>Тираж #{formatDraw(draw.draw_number)}</span>}
      </header>
      <div className="live-identity"><span>{draw.lottery_kind === "WEEKLY" ? "WEEKLY · 5 ИЗ 20" : "DAILY · 4 ИЗ 15"}</span><h1>{draw.lottery_name}</h1><time>{formatMoscow(draw.scheduled_at)} МСК · тираж #{formatDraw(draw.draw_number)}</time></div>

      {state.phase === "waiting" && <>
        <div className="live-countdown"><span>{finalMinute ? "Тираж начнётся через" : "До начала тиража"}</span><strong>{countdown(draw.scheduled_at, now)}</strong><small><i /> Синхронизировано с сервером</small><div className="live-signal" aria-hidden="true"><i /><span /></div>{finalMinute && <div className="last-minute-progress"><span style={{ width: `${finalMinuteProgress}%` }} /></div>}</div>
        <div className="result-preview"><span>{finalMinute ? "Готовим экран результата" : "Здесь появятся выпавшие числа"}</span><div>{Array.from({ length: resultSize }, (_, index) => <i key={index}>{index + 1}</i>)}</div></div>
        <div className="live-facts"><div><span>Джекпот</span><strong>{formatCas(draw.jackpot)}</strong></div><div><span>Ваши билеты</span><strong>{draw.player_ticket_count}</strong></div></div>
      </>}

      {state.phase === "starting" && <div className="live-start"><span>{isReplay ? "Возвращаемся к моменту тиража" : "Тираж начинается"}</span><strong>{isReplay ? "Восстанавливаем последовательность чисел" : "Сервер готовит результат"}</strong><p>{isReplay ? "Это цифровой повтор сохранённого результата." : "Оставайтесь на экране — числа появятся автоматически."}</p><i /></div>}

      {state.phase === "revealing" && <div className="live-reveal" aria-live="polite">
        <span>{isReplay ? "В записи выпало число" : "Выпадает число"}</span>
        <strong key={state.currentNumber}>{state.currentNumber}</strong>
        <div className="live-sequence">{draw.winning_numbers?.map((number, index) => <i className={index < state.revealedNumbers.length ? `shown ${index === state.revealedNumbers.length - 1 ? "recent" : ""}` : ""} key={`${number}-${index}`}>{index < state.revealedNumbers.length ? number : "·"}</i>)}</div>
      </div>}

      {state.phase === "result" && <div className={`live-result ${winner ? "winner" : "neutral"}`}>
        <span>{isReplay ? "Результат записи" : "Итог тиража"}</span>
        <div className="live-final-numbers">{state.revealedNumbers.map((number) => <i key={number}>{number}</i>)}</div>
        {draw.player_ticket_count === 0 ? <div className="personal-result"><strong>Вы не участвовали в этом тираже</strong><p>Новый билет можно выбрать для ближайшего розыгрыша.</p></div> : winner ? <div className="personal-result win"><span>Ваш выигрыш</span><strong>+{formatCas(draw.player_total_prize)}</strong><p>Выигрышных билетов: {draw.player_winning_ticket_count}</p></div> : <div className="personal-result"><strong>В этот раз без выигрыша</strong><p>{draw.player_best_matches ? `Лучший результат — ${draw.player_best_matches} совпадения.` : "Совпадений нет."} Следующий шанс уже близко.</p></div>}
        {draw.highlighted_tickets.map((ticket) => <article className="live-ticket" key={ticket.public_number}><div><span>Билет #{formatDraw(ticket.public_number)}</span><strong>{ticket.prize_amount > 0 ? `+${formatCas(ticket.prize_amount)}` : "Без выигрыша"}</strong></div><NumberSet values={ticket.numbers} winning={draw.winning_numbers} animate={ticket.prize_amount > 0} /></article>)}
      </div>}

      {!isReplay && state.nextDraw && <div className="live-next"><span>Следующий тираж</span><strong>{state.nextDraw.lottery_name}</strong><small>{formatMoscow(state.nextDraw.scheduled_at)} МСК · {countdown(state.nextDraw.scheduled_at, now)}</small></div>}
      <div className="live-actions"><button className="secondary-button" onClick={onTickets} type="button">Мои билеты</button>{isReplay ? <button className="secondary-button" onClick={() => { setReplayStartedAt(now); selectionHaptic(); }} type="button">Повторить ещё раз</button> : canBuy && <PrimaryButton onClick={() => onPlay(canBuy)}>Выбрать числа</PrimaryButton>}</div>
    </section>

    {!isReplay && feed && <section className="replay-library">
      <div className="section-heading"><div><span className="eyebrow">Цифровой архив</span><h2>Последние розыгрыши</h2></div><span className="section-count">По 2 каждой лотереи</span></div>
      <div className="replay-list">{feed.recent_completed.map((item) => <button className={`replay-row lottery-${item.lottery_code}`} key={drawKey(item)} onClick={() => startReplay(item)} type="button"><span className="replay-symbol"><Icon name="replay" /></span><span><strong>{item.lottery_name}</strong><small>{formatMoscow(item.scheduled_at)} МСК · тираж #{formatDraw(item.draw_number)}</small></span><span className="replay-numbers">{item.winning_numbers?.join(" · ")}</span><b>Смотреть</b></button>)}</div>
    </section>}
  </div>;
}
