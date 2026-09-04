import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

import flashScene from "./assets/lotteries/flash-scene.webp";
import shadowScene from "./assets/lotteries/shadow-scene.webp";
import { Icon, PrimaryButton } from "./components";
import { countdown, formatCas, formatDrawLabel, formatMoscowTime } from "./format";
import { fastLivePresentation } from "./live";
import { randomCombination } from "./random";
import { liveStartHaptic, selectionHaptic } from "./telegram";
import type { LiveFeed, Lottery } from "./types";

function SignalPreview({ code }: { code: string }) {
  const active = code === "flash" ? [1, 7, 12] : [2, 8, 14];
  return <div className="fast-signal-preview" aria-hidden="true">{Array.from({ length: 15 }, (_, index) => <i className={active.includes(index) ? "active" : ""} key={index} />)}</div>;
}

function FastCard({ lottery, now, primary, onOpen }: { lottery: Lottery; now: number; primary: boolean; onOpen: () => void }) {
  const flash = lottery.code === "flash";
  return <motion.article className={`fast-card fast-${lottery.code} ${primary ? "primary" : ""}`} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .34 }}>
    <img src={flash ? flashScene : shadowScene} alt="" />
    <div className="fast-card-sheen" aria-hidden="true" />
    <header><span>{flash ? "ϟ" : "☾"} БЫСТРАЯ ЛОТЕРЕЯ</span><small>{formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</small></header>
    <div className="fast-card-main"><div><h2>{lottery.name}</h2><p>{flash ? "Соберите сигнал" : "Выберите тени"}</p><span>Следующий раунд через</span><strong>{countdown(lottery.scheduled_at, now)}</strong></div><SignalPreview code={lottery.code} /></div>
    <div className="fast-card-bottom"><div><span>Стоимость</span><strong>{formatCas(lottery.ticket_price ?? 0)}</strong></div><button disabled={!lottery.purchase_available} onClick={onOpen} type="button"><Icon name="fast" />{lottery.purchase_available ? (flash ? "Собрать сигнал" : "Выбрать тени") : "Продажи закрыты"}<small>{lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "—"}</small></button></div>
  </motion.article>;
}

function FastLiveCard({ feed, now }: { feed: LiveFeed; now: number }) {
  const state = fastLivePresentation(feed, now);
  const signalled = useRef<string | null>(null);
  const draw = state?.draw;
  const code = draw?.lottery_code === "shadow" ? "shadow" : "flash";
  const revealed = state ? [...state.revealedNumbers] : [];
  if (state?.phase === "revealing" && state.currentNumber !== null) revealed.push(state.currentNumber);

  useEffect(() => {
    if (!draw || !state || (state.phase !== "starting" && state.phase !== "revealing")) return;
    const key = `${draw.lottery_code}:${draw.draw_number}`;
    if (signalled.current === key) return;
    signalled.current = key;
    liveStartHaptic();
  }, [draw, state]);

  if (!draw || !state) return null;
  const waiting = state.phase === "waiting";
  const result = state.phase === "result";
  const winner = draw.player_total_prize > 0;
  return <motion.article animate={{ opacity: 1, scale: 1 }} className={`fast-live-card fast-${code} phase-${state.phase}`} initial={{ opacity: 0, scale: .985 }} transition={{ duration: .28 }}>
    <img src={code === "flash" ? flashScene : shadowScene} alt="" />
    <div className="fast-live-veil" aria-hidden="true" />
    <header><span><i /> {waiting ? "СКОРО В ЭФИРЕ" : result ? "РАУНД ЗАВЕРШЁН" : "ПРЯМОЙ ЭФИР"}</span><small>{formatDrawLabel(draw.lottery_code, draw.draw_number)}</small></header>
    <div className="fast-live-title"><div><small>{draw.lottery_name}</small><h2>{waiting ? `Старт через ${countdown(draw.scheduled_at, now)}` : result ? "Сигнал принят" : "Каспер выбирает числа"}</h2></div><b>{formatMoscowTime(draw.scheduled_at)} МСК</b></div>
    <section className="fast-live-ticket" aria-live="polite">
      <div className="fast-live-ticket-head"><span>БИЛЕТ РОЗЫГРЫША</span><small>{revealed.length} / 3</small></div>
      <div className="fast-live-slots">{Array.from({ length: 3 }, (_, index) => <motion.i animate={revealed[index] ? { opacity: 1, scale: [0.82, 1.08, 1] } : { opacity: .55, scale: 1 }} className={revealed[index] ? "lit" : ""} key={`${index}-${revealed[index] ?? "empty"}`} transition={{ duration: .36 }}>{revealed[index] ?? "·"}</motion.i>)}</div>
      {!waiting && !result && <div className="fast-live-scan"><i /><span>{state.phase === "starting" ? "Подготовка сигнала" : `Выпадает число ${state.currentNumber ?? ""}`}</span></div>}
    </section>
    {waiting && <p className="fast-live-note">Оставайтесь здесь — числа появятся автоматически.</p>}
    {result && <motion.div animate={{ opacity: 1, y: 0 }} className={`fast-live-result ${winner ? "winner" : ""}`} initial={{ opacity: 0, y: 6 }}><span>ИТОГ</span><strong>{draw.player_ticket_count === 0 ? "Вы не участвовали" : winner ? `+${formatCas(draw.player_total_prize)}` : "Без выигрыша"}</strong><small>{draw.player_ticket_count ? `Ваших билетов: ${draw.player_ticket_count}${draw.player_best_matches !== null ? ` · лучший результат: ${draw.player_best_matches}/3` : ""}` : "Следующий раунд уже близко"}</small></motion.div>}
  </motion.article>;
}

export function FastView({ lotteries, feed, now, onOpen }: { lotteries: Lottery[]; feed: LiveFeed | null; now: number; onOpen: (code: string) => void }) {
  const ordered = [...lotteries].sort((left, right) => new Date(left.scheduled_at ?? 0).getTime() - new Date(right.scheduled_at ?? 0).getTime());
  const liveState = useMemo(() => fastLivePresentation(feed, now), [feed, now]);
  const liveCode = liveState?.draw?.lottery_code;
  return <section className="fast-view">
    <header className="fast-heading"><div><span>Ритм Каспера</span><h1>Fast</h1></div><p>Новый раунд каждые 10 минут.<br />FLASH и SHADOW чередуются.</p></header>
    {ordered.map((lottery, index) => <div key={lottery.code}><AnimatePresence mode="wait">{liveCode === lottery.code && feed ? <FastLiveCard feed={feed} key={`live-${lottery.code}`} now={now} /> : <FastCard lottery={lottery} now={now} primary={index === 0} onOpen={() => onOpen(lottery.code)} key={`card-${lottery.code}`} />}</AnimatePresence>{index === 0 && ordered.length > 1 && <div className="fast-divider"><span><b>{lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "—"}</b>{lottery.name}</span><i><Icon name="fast" /></i><span><b>{ordered[1].scheduled_at ? formatMoscowTime(ordered[1].scheduled_at) : "—"}</b>{ordered[1].name}</span></div>}</div>)}
    {!ordered.length && <div className="fast-unavailable"><Icon name="fast" /><strong>Расписание Fast готовится</strong><p>Экран обновится автоматически.</p></div>}
  </section>;
}

export function FastPicker({ lottery, purchasing, success, onClose, onBuy }: { lottery: Lottery; purchasing: boolean; success: boolean; onClose: () => void; onBuy: (numbers: number[]) => void }) {
  const [selected, setSelected] = useState<number[]>([]);
  const flash = lottery.code === "flash";
  const toggle = (value: number) => {
    selectionHaptic();
    setSelected((current) => current.includes(value) ? current.filter((item) => item !== value) : current.length < 3 ? [...current, value].sort((a, b) => a - b) : current);
  };
  const randomize = () => { selectionHaptic(); setSelected(randomCombination(15, 3)); };
  return <div className={`fast-picker fast-${lottery.code}`}>
    <img className="fast-picker-scene" src={flash ? flashScene : shadowScene} alt="" />
    <div className="fast-picker-overlay" aria-hidden="true" />
    <button className="fast-picker-close" onClick={onClose} type="button" aria-label="Закрыть"><Icon name="arrow" /></button>
    <header><span>{lottery.name} · {formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</span><h1>{flash ? "Соберите сигнал" : "Выберите 3 тени"}</h1><p>Отметьте 3 позиции из 15</p></header>
    <section className="fast-grid-panel"><div><strong>{flash ? "ПОЛЕ ИМПУЛЬСОВ" : "ПОЛЕ ТЕНЕЙ"}</strong><span>Выбрано <b>{selected.length}</b> / 3</span></div><div className="fast-grid">{Array.from({ length: 15 }, (_, index) => index + 1).map((value) => <motion.button aria-label={`Позиция ${value}`} aria-pressed={selected.includes(value)} className={selected.includes(value) ? "selected" : ""} key={value} onClick={() => toggle(value)} type="button" whileTap={{ scale: .86 }}><i /><small>{String(value).padStart(2, "0")}</small></motion.button>)}</div></section>
    <section className="fast-selection"><div><span>{flash ? "Ваш сигнал" : "Ваши тени"}</span><div>{Array.from({ length: 3 }, (_, index) => <i className={selected[index] ? "filled" : ""} key={index}>{selected[index] ? String(selected[index]).padStart(2, "0") : "—"}</i>)}</div></div><button onClick={randomize} type="button"><Icon name="spark" />Случайный выбор</button></section>
    <div className="fast-purchase"><div><span>Стоимость</span><strong>{formatCas(lottery.ticket_price ?? 0)}</strong></div><PrimaryButton disabled={selected.length !== 3} loading={purchasing} success={success} onClick={() => onBuy(selected)}><Icon name="fast" />{success ? "Билет куплен" : flash ? "Активировать" : "Купить сигнал"}</PrimaryButton></div>
    <p className="fast-picker-note">Билет участвует в ближайшем раунде · без эфира в Telegram</p>
  </div>;
}
