import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { motion } from "motion/react";

import { GrandNumberSet, Icon, Money, NumberSet, PrimaryButton } from "./components";
import { MINIAPP_TEXTS as copy } from "./content";
import { countdown, formatCas, formatDrawLabel, formatMoscow, formatTicketLabel } from "./format";
import { livePresentation, replayPresentation } from "./live";
import { LotteryVisual } from "./LotteryVisuals";
import { isGrandLottery, matchLabel, splitGrandNumbers } from "./grand";
import { liveStartHaptic, selectionHaptic } from "./telegram";
import type { LiveDraw, LiveFeed, LiveTicket } from "./types";

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

function lotteryFormat(draw: LiveDraw): string {
  if (draw.lottery_code === "khan") return "ЕЖЕДНЕВНАЯ · 6 ИЗ 36";
  if (draw.lottery_code === "september") return "DAILY · 3 ИЗ 33";
  if (draw.lottery_code === "grob") return "DAILY · 3 ИЗ 16";
  return draw.lottery_kind === "WEEKLY" ? "ЕЖЕНЕДЕЛЬНАЯ · 5 ИЗ 35 + 2 ИЗ 5" : "DAILY · 4 ИЗ 15";
}

const drumBalls = [
  [4, 18, 27], [13, 36, 18], [22, 57, 26], [31, 73, 43], [8, 63, 66], [17, 42, 72],
  [26, 22, 61], [35, 47, 45], [10, 79, 23], [19, 29, 42], [28, 55, 57], [36, 76, 68],
];

function khanBallBand(number: number): string {
  if (number < 10) return "band-yellow";
  if (number < 20) return "band-blue";
  if (number < 30) return "band-red";
  return "band-green";
}

function KhanLototron({ revealedNumbers, currentNumber, mixing }: { revealedNumbers: number[]; currentNumber: number | null; mixing: boolean }) {
  return <div className={`khan-lototron ${mixing ? "is-mixing" : "is-drawing"}`} aria-live="polite">
    <header><span><i />{mixing ? "ЛОТОТРОН ЗАПУЩЕН" : `ШАР ${revealedNumbers.length} ИЗ 6`}</span><strong>{mixing ? "Перемешиваем шары" : currentNumber === null ? "Механизм готов" : "Шар зафиксирован"}</strong></header>
    <div className="khan-machine" aria-hidden="true">
      <div className="khan-drum"><i className="khan-drum-ring" /><i className="khan-glass-glare" />{drumBalls.map(([number, left, top], index) => <b className={`khan-ball ${khanBallBand(number)}`} key={number} style={{ "--ball-left": `${left}%`, "--ball-top": `${top}%`, "--ball-delay": `${index * -0.17}s` } as CSSProperties}>{number}</b>)}<span className="khan-rotor"><i /><i /><i /></span></div>
      <div className={`khan-chute ${currentNumber !== null ? "releasing" : ""}`}><i /><b /></div>
      <div className={`khan-output ${currentNumber !== null ? "has-ball" : ""}`}>{currentNumber !== null ? <motion.strong className={khanBallBand(currentNumber)} animate={{ opacity: 1, scale: 1, y: 0, rotate: 0 }} initial={{ opacity: 0, scale: .45, y: -28, rotate: -35 }} key={currentNumber} transition={{ type: "spring", stiffness: 240, damping: 17 }}>{currentNumber}</motion.strong> : <span />}</div>
      <div className="khan-base"><span>KASPER</span><i /><b>6 / 36</b></div>
    </div>
    <div className="khan-ball-rack">{Array.from({ length: 6 }, (_, index) => { const number = revealedNumbers[index]; return <i className={number ? `filled ${khanBallBand(number)}` : ""} key={index}>{number ?? "·"}</i>; })}</div>
  </div>;
}

function KhanBestTicket({ ticket, revealedNumbers }: { ticket: LiveTicket; revealedNumbers: number[] }) {
  const matches = ticket.numbers.filter((number) => revealedNumbers.includes(number)).length;
  return <article className="khan-best-ticket"><header><div><span>ВАШ ЛУЧШИЙ БИЛЕТ СЕЙЧАС</span><strong>{formatTicketLabel("khan", ticket.public_number)}</strong></div><b>{matches} / 6</b></header><div className="number-row">{ticket.numbers.map((number) => <span className={`number ${khanBallBand(number)} ${revealedNumbers.includes(number) ? "won" : ""}`} key={number}>{number}</span>)}</div></article>;
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
  const grand = isGrandLottery(draw.lottery_code) && (draw.winning_numbers?.length ?? 7) === 7;
  const resultSize = draw.lottery_code === "september" || draw.lottery_code === "grob" ? 3 : draw.lottery_code === "khan" ? 6 : draw.lottery_kind === "WEEKLY" ? 7 : 4;
  const khanShownNumbers = state.currentNumber === null ? state.revealedNumbers : [...state.revealedNumbers, state.currentNumber];

  return <div className="live-experience">
    <section className={`live-stage lottery-${draw.lottery_code} phase-${state.phase} ${finalMinute ? "final-minute" : ""} ${isReplay ? "is-replay" : "is-live"}`}>
      <div className="live-grid" aria-hidden="true" />
      <div className="live-ambient" aria-hidden="true" />
      <div className="live-lottery-scene"><LotteryVisual code={draw.lottery_code} context="live" animated={!isReplay} /></div>
      {draw.lottery_code === "september" && <div className="live-september-mark" aria-hidden="true"><small>{copy.september.liveMood}</small><strong>03</strong><span>сентября</span></div>}
      <header className="live-heading">
        <span className="live-label"><i /> {isReplay ? "ПОВТОР ТИРАЖА" : state.phase === "waiting" ? "СКОРО В ЭФИРЕ" : state.phase === "result" ? "ТИРАЖ ЗАВЕРШЁН" : "ПРЯМОЙ ЭФИР"}</span>
        {isReplay ? <button className="replay-close" onClick={() => setReplayKey(null)} type="button"><Icon name="close" /> К эфиру</button> : <span>{formatDrawLabel(draw.lottery_code, draw.draw_number)}</span>}
      </header>
      <div className="live-identity"><span>{lotteryFormat(draw)}</span><h1>{draw.lottery_name}</h1><time>{formatMoscow(draw.scheduled_at)} МСК · {formatDrawLabel(draw.lottery_code, draw.draw_number)}</time></div>

      {state.phase === "waiting" && <>
        <div className="live-countdown"><span>{finalMinute ? "Тираж начнётся через" : "До начала тиража"}</span><strong>{countdown(draw.scheduled_at, now)}</strong><small><i /> Синхронизировано с сервером</small><div className="live-signal" aria-hidden="true"><i /><span /></div>{finalMinute && <div className="last-minute-progress"><span style={{ width: `${finalMinuteProgress}%` }} /></div>}</div>
        <div className="live-timeline" aria-label="Этапы тиража"><div className="active"><i /><span>Ожидание</span></div><b /><div><i /><span>Выбор чисел</span></div><b /><div><i /><span>Результат</span></div></div>
        <div className="result-preview"><span>{finalMinute ? "Готовим экран результата" : "Здесь появятся выпавшие числа"}</span><div>{Array.from({ length: resultSize }, (_, index) => <i key={index}>{index + 1}</i>)}</div></div>
        <div className="live-facts"><div><span>Джекпот</span><strong><Money value={draw.jackpot} compact /></strong></div><div><span>Ваши билеты</span><strong>{draw.player_ticket_count}</strong></div></div>
      </>}

      {state.phase === "starting" && (draw.lottery_code === "khan" ? <KhanLototron revealedNumbers={[]} currentNumber={null} mixing /> : <div className="live-start"><span>{isReplay ? "Возвращаемся к моменту тиража" : "Тираж начинается"}</span><strong>{isReplay ? "Восстанавливаем последовательность чисел" : copy.live.choosingNumbers}</strong><p>{isReplay ? "Это цифровой повтор сохранённого результата." : copy.live.stayOnScreen}</p><i /></div>)}

      {state.phase === "revealing" && (draw.lottery_code === "khan" ? <><KhanLototron revealedNumbers={khanShownNumbers} currentNumber={state.currentNumber} mixing={false} />{draw.highlighted_tickets[0] && <KhanBestTicket ticket={draw.highlighted_tickets[0]} revealedNumbers={khanShownNumbers} />}</> : <div className="live-reveal" aria-live="polite">
        <span>{isReplay ? "В записи выпало число" : "Выпадает число"}</span>
        <motion.strong animate={{ opacity: 1, scale: 1, y: 0 }} initial={{ opacity: 0, scale: .76, y: 12 }} key={state.currentNumber} transition={{ type: "spring", stiffness: 280, damping: 22 }}>{grand && (state.currentNumber ?? 0) > 35 ? (state.currentNumber ?? 0) - 35 : state.currentNumber}</motion.strong>
        <div className={`live-sequence ${grand ? "grand-live-sequence" : ""}`}>{draw.winning_numbers?.map((number, index) => <i className={`${grand && number > 35 ? "special" : ""} ${index < state.revealedNumbers.length ? `shown ${index === state.revealedNumbers.length - 1 ? "recent" : ""}` : ""}`} key={`${number}-${index}`}>{index < state.revealedNumbers.length ? (grand && number > 35 ? number - 35 : number) : "·"}</i>)}</div>
      </div>)}

      {state.phase === "result" && <motion.div animate={{ opacity: 1, y: 0 }} className={`live-result ${winner ? "winner" : "neutral"}`} initial={{ opacity: 0, y: 10 }}>
        <span>{isReplay ? "Результат записи" : "Итог тиража"}</span>
        {grand ? <GrandNumberSet values={state.revealedNumbers} /> : <div className="live-final-numbers">{state.revealedNumbers.map((number) => <i key={number}>{number}</i>)}</div>}
        {draw.player_ticket_count === 0 ? <div className="personal-result"><strong>Вы не участвовали в этом тираже</strong><p>Новый билет можно выбрать для ближайшего розыгрыша.</p></div> : winner ? <div className="personal-result win"><span>Ваш выигрыш</span><strong>+{formatCas(draw.player_total_prize)}</strong><p>Выигрышных билетов: {draw.player_winning_ticket_count}</p></div> : <div className="personal-result"><strong>В этот раз без выигрыша</strong><p>{draw.player_best_matches ? `Лучший результат — ${matchLabel(draw.lottery_code, draw.player_best_matches, grand)}.` : "Совпадений нет."} Следующий шанс уже близко.</p></div>}
        {draw.highlighted_tickets.map((ticket) => <article className="live-ticket" key={ticket.public_number}><div><span>{formatTicketLabel(draw.lottery_code, ticket.public_number)}</span><strong>{ticket.prize_amount > 0 ? `+${formatCas(ticket.prize_amount)}` : "Без выигрыша"}</strong></div>{grand ? <GrandNumberSet values={ticket.numbers} winning={draw.winning_numbers} animate={ticket.prize_amount > 0} /> : <NumberSet values={ticket.numbers} winning={draw.winning_numbers} animate={ticket.prize_amount > 0} />}</article>)}
      </motion.div>}

      {!isReplay && state.nextDraw && <div className="live-next"><span>Следующий тираж</span><strong>{state.nextDraw.lottery_name}</strong><small>{formatMoscow(state.nextDraw.scheduled_at)} МСК · {countdown(state.nextDraw.scheduled_at, now)}</small></div>}
      <div className="live-actions"><button className="secondary-button" onClick={onTickets} type="button">Мои билеты</button>{isReplay ? <button className="secondary-button" onClick={() => { setReplayStartedAt(now); selectionHaptic(); }} type="button">Повторить ещё раз</button> : canBuy && <PrimaryButton onClick={() => onPlay(canBuy)}>Выбрать числа</PrimaryButton>}</div>
    </section>

    {!isReplay && feed && <section className="replay-library">
      <div className="section-heading"><div><span className="eyebrow">Цифровой архив</span><h2>Последние розыгрыши</h2></div><span className="section-count">По 2 каждой лотереи</span></div>
      <div className="replay-list">{feed.recent_completed.map((item) => { const parts = splitGrandNumbers(item.winning_numbers ?? []); return <button className={`replay-row lottery-${item.lottery_code}`} key={drawKey(item)} onClick={() => startReplay(item)} type="button"><span className="replay-symbol"><Icon name="replay" /></span><span><strong>{item.lottery_name}</strong><small>{formatMoscow(item.scheduled_at)} МСК · {formatDrawLabel(item.lottery_code, item.draw_number)}</small></span><span className="replay-numbers">{isGrandLottery(item.lottery_code) && (item.winning_numbers?.length ?? 0) === 7 ? `${parts.main.join(" · ")} + ${parts.special.join(" · ")}` : item.winning_numbers?.join(" · ")}</span><b>Смотреть</b></button>; })}</div>
    </section>}
  </div>;
}
