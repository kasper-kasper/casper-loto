import { tr } from "./i18n";
import { NewYearLiveScene, NewYearSymbols } from "./NewYear";
import { DistributionBadge } from "./DistributionBadge";
import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "motion/react";

import { GrandNumberSet, Icon, Money, NumberSet, PrimaryButton } from "./components";
import { MINIAPP_TEXTS as copy } from "./content";
import { countdown, formatCas, formatDrawLabel, formatMoscow, formatTicketLabel } from "./format";
import { livePresentation, replayPresentation } from "./live";
import { LotteryVisual } from "./LotteryVisuals";
import { GrandDrawScene } from "./GrandDrawScene";
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
  if (draw.lottery_code === "dual") {
    const slot = new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Moscow", hour: "2-digit", minute: "2-digit" }).format(new Date(draw.scheduled_at));
    return tr("РАУНД {0} · 2 ИЗ 12", slot === "00:30" ? "NIGHT" : "DAWN");
  }
  if (draw.lottery_code === "pss") return tr("ЕЖЕДНЕВНАЯ · 5 ИЗ 36 + CASPER BALL 1 ИЗ 8");
  if (draw.lottery_code === "mini") return tr("КЛАССИКА · 6 ИЗ 30");
  if (draw.lottery_code === "khan") return tr("ЕЖЕДНЕВНАЯ · 6 ИЗ 36");
  if (draw.lottery_code === "september") return tr("DAILY · 3 ИЗ 33");
  if (draw.lottery_code === "grob") return tr("ПРАЗДНИЧНАЯ · 3 ИЗ {0}", draw.primary_max_number || 16);
  return draw.lottery_kind === "WEEKLY" ? tr("ЕЖЕНЕДЕЛЬНАЯ · 5 ИЗ 35 + 2 ИЗ 5") : tr("DAILY · 4 ИЗ 15");
}

function khanBallBand(number: number): string {
  if (number < 10) return "band-yellow";
  if (number < 20) return "band-blue";
  if (number < 30) return "band-red";
  return "band-green";
}

function KhanLototron({ revealedNumbers, currentNumber, mixing }: { revealedNumbers: number[]; currentNumber: number | null; mixing: boolean }) {
  const shown = currentNumber ?? revealedNumbers.at(-1) ?? null;
  return <div className="khan-draw-console" aria-live="polite">
    <header><span><i />{mixing ? tr("ПОДГОТОВКА ТИРАЖА") : tr("ШАР {0} ИЗ 6", revealedNumbers.length)}</span><strong>{mixing ? tr("Синхронизируем результат") : shown === null ? tr("Механизм готов") : tr("Число зафиксировано")}</strong></header>
    <div className="khan-current-wrap"><div className={`khan-current-ball ${shown !== null ? "has-number" : ""} ${shown !== null ? khanBallBand(shown) : ""}`} key={shown ?? "empty"}>{tr(shown ?? "—")}</div><span>{mixing ? tr("Эфир начнётся через несколько секунд") : tr("Результат тиража обновляется автоматически")}</span></div>
    <div className="khan-progress"><i style={{ width: `${(revealedNumbers.length / 6) * 100}%` }} /></div>
    <div className="khan-ball-rack">{Array.from({ length: 6 }, (_, index) => { const number = revealedNumbers[index]; return <i className={number ? `filled ${khanBallBand(number)}` : ""} key={index}>{number ?? "·"}</i>; })}</div>
  </div>;
}

function KhanBestTicket({ ticket, revealedNumbers }: { ticket: LiveTicket; revealedNumbers: number[] }) {
  const matches = ticket.numbers.filter((number) => revealedNumbers.includes(number)).length;
  return <article className="khan-best-ticket"><header><div><span>{tr("ВАШ ЛУЧШИЙ БИЛЕТ СЕЙЧАС")}</span><strong>{tr(formatTicketLabel("khan", ticket.public_number))}</strong></div><b>{matches} / 6</b></header><div className="number-row">{ticket.numbers.map((number) => <span className={`number ${khanBallBand(number)} ${revealedNumbers.includes(number) ? "won" : ""}`} key={number}>{number}</span>)}</div></article>;
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

  if (loading && !feed) return <section className="live-stage live-loading" aria-label={tr("Загружаем эфир")}><div className="live-grid" /><div className="skeleton live-title-skeleton" /><div className="skeleton live-clock-skeleton" /><div className="skeleton live-panel-skeleton" /></section>;
  if (!draw) return <section className="live-stage live-idle"><div className="live-grid" /><span className="live-label"><i />  {tr("ЭФИР")}</span><h1>{tr("Расписание готовится")}</h1><p>{tr("Следующий тираж появится здесь автоматически.")}</p><button className="secondary-button" onClick={onTickets} type="button">{tr("Мои билеты")}</button></section>;

  const isReplay = Boolean(replayDraw);
  const winner = draw.player_total_prize > 0;
  const canBuy = liveState.nextDraw?.lottery_code ?? (liveState.phase === "waiting" ? liveState.draw?.lottery_code : null);
  const startsIn = Math.max(0, new Date(draw.scheduled_at).getTime() - now);
  const finalMinute = !isReplay && state.phase === "waiting" && startsIn <= 60_000;
  const finalMinuteProgress = finalMinute ? Math.max(0, Math.min(100, ((60_000 - startsIn) / 60_000) * 100)) : 0;
  const grand = isGrandLottery(draw.lottery_code);
  const newYear = draw.lottery_code === "newyear2027";
  const dual = draw.lottery_code === "dual";
  const grandOffset = draw.secondary_storage_offset ?? (draw.lottery_code === "pss" ? 36 : 35);
  const resultSize = draw.winning_numbers?.length ?? (dual ? 2 : draw.lottery_code === "september" || draw.lottery_code === "grob" ? 3 : (draw.lottery_code === "khan" || draw.lottery_code === "mini") ? 6 : draw.lottery_kind === "WEEKLY" ? 7 : 4);
  const khanShownNumbers = state.currentNumber === null ? state.revealedNumbers : [...state.revealedNumbers, state.currentNumber];

  return <div className="live-experience">
    <DistributionBadge active={draw.is_distribution} />
    <section className={`live-stage lottery-${draw.lottery_code} phase-${state.phase} ${finalMinute ? "final-minute" : ""} ${isReplay ? "is-replay" : "is-live"}`}>
      <div className="live-grid" aria-hidden="true" />
      <div className="live-ambient" aria-hidden="true" />
      <div className="live-lottery-scene"><LotteryVisual code={draw.lottery_code} context="live" animated={!isReplay && draw.lottery_code !== "khan" && draw.lottery_code !== "mini"} /></div>
      {draw.lottery_code === "september" && <div className="live-september-mark" aria-hidden="true"><small>{tr(copy.september.liveMood)}</small><strong>03</strong><span>{tr("сентября")}</span></div>}
      <header className="live-heading">
        <span className="live-label"><i /> {isReplay ? tr("ПОВТОР ТИРАЖА") : state.phase === "waiting" ? tr("СКОРО В ЭФИРЕ") : state.phase === "result" ? tr("ТИРАЖ ЗАВЕРШЁН") : tr("ПРЯМОЙ ЭФИР")}</span>
        {isReplay ? <button className="replay-close" onClick={() => setReplayKey(null)} type="button"><Icon name="close" />  {tr("К эфиру")}</button> : <span>{tr(formatDrawLabel(draw.lottery_code, draw.draw_number))}</span>}
      </header>
      <div className="live-identity"><span>{tr(lotteryFormat(draw))}</span><h1>{tr(draw.lottery_name)}</h1><time>{tr(formatMoscow(draw.scheduled_at))}  {tr("МСК ·")} {tr(formatDrawLabel(draw.lottery_code, draw.draw_number))}</time></div>

      {draw.lottery_code === "weekly" && <GrandDrawScene active={state.phase === "starting" || state.phase === "revealing"} revealed={state.revealedNumbers} />}
      {newYear && <NewYearLiveScene scheduledAt={draw.scheduled_at} now={now} values={state.currentNumber === null ? state.revealedNumbers : [...state.revealedNumbers, state.currentNumber]} phase={state.phase} />}
      {!newYear && state.phase === "waiting" && <>
        <div className="live-countdown"><span>{finalMinute ? tr("Тираж начнётся через") : tr("До начала тиража")}</span><strong>{tr(countdown(draw.scheduled_at, now))}</strong><small><i />  {tr("Синхронизировано с сервером")}</small><div className="live-signal" aria-hidden="true"><i /><span /></div>{finalMinute && <div className="last-minute-progress"><span style={{ width: `${finalMinuteProgress}%` }} /></div>}</div>
        <div className="live-timeline" aria-label={tr("Этапы тиража")}><div className="active"><i /><span>{tr("Ожидание")}</span></div><b /><div><i /><span>{tr("Выбор чисел")}</span></div><b /><div><i /><span>{tr("Результат")}</span></div></div>
        <div className="result-preview"><span>{finalMinute ? tr("Готовим экран результата") : tr("Здесь появятся выпавшие числа")}</span><div>{Array.from({ length: resultSize }, (_, index) => <i key={index}>{index + 1}</i>)}</div></div>
        <div className="live-facts"><div><span>{tr("Джекпот")}</span><strong><Money value={draw.jackpot} compact /></strong></div><div><span>{tr("Ваши билеты")}</span><strong>{draw.player_ticket_count}</strong></div></div>
      </>}

      {!newYear && state.phase === "starting" && ((draw.lottery_code === "khan" || draw.lottery_code === "mini") ? <KhanLototron revealedNumbers={[]} currentNumber={null} mixing /> : <div className="live-start"><span>{isReplay ? tr("Возвращаемся к моменту тиража") : tr("Тираж начинается")}</span><strong>{tr(isReplay ? tr("Восстанавливаем последовательность чисел") : copy.live.choosingNumbers)}</strong><p>{tr(isReplay ? tr("Это цифровой повтор сохранённого результата.") : copy.live.stayOnScreen)}</p><i /></div>)}

      {!newYear && state.phase === "revealing" && ((draw.lottery_code === "khan" || draw.lottery_code === "mini") ? <><KhanLototron revealedNumbers={khanShownNumbers} currentNumber={state.currentNumber} mixing={false} />{draw.highlighted_tickets[0] && <KhanBestTicket ticket={draw.highlighted_tickets[0]} revealedNumbers={khanShownNumbers} />}</> : <div className="live-reveal" aria-live="polite">
        <span>{isReplay ? tr("В записи выпало число") : tr("Выпадает число")}</span>
        <motion.strong animate={{ opacity: 1, scale: 1, y: 0 }} initial={{ opacity: 0, scale: .76, y: 12 }} key={state.currentNumber} transition={{ type: "spring", stiffness: 280, damping: 22 }}>{grand && (state.currentNumber ?? 0) > grandOffset ? (state.currentNumber ?? 0) - grandOffset : state.currentNumber}</motion.strong>
        <div className={`live-sequence ${grand ? "grand-live-sequence" : ""}`}>{draw.winning_numbers?.map((number, index) => <i className={`${grand && number > grandOffset ? "special" : ""} ${index < state.revealedNumbers.length ? `shown ${index === state.revealedNumbers.length - 1 ? "recent" : ""}` : ""}`} key={`${number}-${index}`}>{tr(index < state.revealedNumbers.length ? (grand && number > grandOffset ? number - grandOffset : number) : "·")}</i>)}</div>
      </div>)}

      {state.phase === "result" && <motion.div animate={{ opacity: 1, y: 0 }} className={`live-result ${winner ? "winner" : "neutral"}`} initial={{ opacity: 0, y: 10 }}>
        <span>{isReplay ? tr("Результат записи") : dual ? tr("Результат раунда") : tr("Итог тиража")}</span>
        {newYear ? <NewYearSymbols values={state.revealedNumbers} /> : grand ? <GrandNumberSet values={state.revealedNumbers} offset={grandOffset} specialLabel={tr(draw.lottery_code === "pss" ? "Casper Ball" : undefined)} /> : <div className="live-final-numbers">{state.revealedNumbers.map((number) => <i key={number}>{number}</i>)}</div>}
        {draw.player_ticket_count === 0 ? <div className="personal-result"><strong>{tr("Вы не участвовали в этом")} {dual ? tr("раунде") : tr("тираже")}</strong><p>{tr("Новый билет можно выбрать для ближайшего розыгрыша.")}</p></div> : winner ? <div className="personal-result win"><span>{tr("Ваш выигрыш")}</span><strong>+{tr(formatCas(draw.player_total_prize))}</strong><p>{tr("Выигрышных билетов:")} {draw.player_winning_ticket_count}</p></div> : dual ? <div className="personal-result"><strong>{tr("Результат раунда сохранён")}</strong><p>{tr("Проверьте свой билет: после первого раунда он остаётся активным, итог и выплата появятся после второго.")}</p></div> : <div className="personal-result"><strong>{tr("В этот раз без выигрыша")}</strong><p>{draw.player_best_matches ? tr("Лучший результат — {0}.", matchLabel(draw.lottery_code, draw.player_best_matches, grand)) : tr("Совпадений нет.")}  {tr("Следующий шанс уже близко.")}</p></div>}
        {!dual && draw.highlighted_tickets.map((ticket) => <article className="live-ticket" key={ticket.public_number}><div><span>{tr(formatTicketLabel(draw.lottery_code, ticket.public_number))}</span><strong>{tr(ticket.prize_amount > 0 ? `+${formatCas(ticket.prize_amount)}` : tr("Без выигрыша"))}</strong></div>{newYear ? <NewYearSymbols values={ticket.numbers} /> : grand ? <GrandNumberSet values={ticket.numbers} offset={grandOffset} specialLabel={tr(draw.lottery_code === "pss" ? "Casper Ball" : undefined)} winning={draw.winning_numbers} animate={ticket.prize_amount > 0} /> : <NumberSet values={ticket.numbers} winning={draw.winning_numbers} animate={ticket.prize_amount > 0} />}</article>)}
      </motion.div>}

      {!isReplay && state.nextDraw && <div className="live-next"><span>{tr("Следующий тираж")}</span><strong>{tr(state.nextDraw.lottery_name)}</strong><small>{tr(formatMoscow(state.nextDraw.scheduled_at))}  {tr("МСК ·")} {tr(countdown(state.nextDraw.scheduled_at, now))}</small></div>}
      <div className="live-actions"><button className="secondary-button" onClick={onTickets} type="button">{tr("Мои билеты")}</button>{isReplay ? <button className="secondary-button" onClick={() => { setReplayStartedAt(now); selectionHaptic(); }} type="button">{tr("Повторить ещё раз")}</button> : canBuy && <PrimaryButton onClick={() => onPlay(canBuy)}>{newYear ? tr("Выбрать символы") : tr("Выбрать числа")}</PrimaryButton>}</div>
    </section>

    {!isReplay && feed && <section className="replay-library">
      <div className="section-heading"><div><span className="eyebrow">{tr("Цифровой архив")}</span><h2>{tr("Последние розыгрыши")}</h2></div><span className="section-count">{tr("По 2 каждой лотереи")}</span></div>
      <div className="replay-list">{feed.recent_completed.map((item) => { const parts = splitGrandNumbers(item.winning_numbers ?? [], item.secondary_storage_offset ?? (item.lottery_code === "pss" ? 36 : 35)); return <button className={`replay-row lottery-${item.lottery_code}`} key={drawKey(item)} onClick={() => startReplay(item)} type="button"><span className="replay-symbol"><Icon name="replay" /></span><span><strong>{tr(item.lottery_name)}</strong><small>{tr(formatMoscow(item.scheduled_at))}  {tr("МСК ·")} {tr(formatDrawLabel(item.lottery_code, item.draw_number))}</small></span><span className="replay-numbers">{tr(item.lottery_code === "newyear2027" ? <NewYearSymbols values={item.winning_numbers ?? []} /> : isGrandLottery(item.lottery_code) ? `${parts.main.join(" · ")} + ${parts.special.join(" · ")}` : item.winning_numbers?.join(" · "))}</span><b>{tr("Смотреть")}</b></button>; })}</div>
    </section>}
  </div>;
}
