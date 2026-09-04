import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

import flashScene from "./assets/lotteries/flash-scene.webp";
import pulseScene from "./assets/lotteries/pulse-scene.webp";
import shadowScene from "./assets/lotteries/shadow-scene.webp";
import { Icon, PrimaryButton } from "./components";
import { countdown, formatCas, formatDrawLabel, formatMoscowTime } from "./format";
import { fastLivePresentation } from "./live";
import { randomCombination } from "./random";
import { liveStartHaptic, selectionHaptic } from "./telegram";
import type { LiveFeed, Lottery } from "./types";

type FastCode = "flash" | "shadow" | "pulse";

const fastScene = (code: string) => code === "flash" ? flashScene : code === "pulse" ? pulseScene : shadowScene;
const fastTagline = (code: string) => code === "flash" ? "Соберите сигнал" : code === "pulse" ? "Поймайте ритм" : "Выберите тени";
const fastAction = (code: string) => code === "flash" ? "Собрать сигнал" : code === "pulse" ? "Поймать импульс" : "Выбрать тени";

function displayFastNumber(code: string, value: number): string {
  return code === "pulse" && value > 10 ? `P${value - 10}` : String(value).padStart(2, "0");
}

function displayFastMatches(code: string, matches: number): string {
  return code === "pulse" ? `${Math.floor(matches / 10)}+${matches % 10}` : `${matches}/3`;
}

function PulseTrace({ className }: { className: string }) {
  return <div className={className} aria-hidden="true"><svg viewBox="0 0 120 48"><path d="M0 25H24L31 21L37 25L44 7L53 41L61 25H120" pathLength="120" /><circle cx="44" cy="7" r="2" /></svg></div>;
}

function SignalPreview({ code }: { code: string }) {
  if (code === "pulse") return <PulseTrace className="fast-pulse-preview" />;
  const active = code === "flash" ? [1, 7, 12] : [2, 8, 14];
  return <div className="fast-signal-preview" aria-hidden="true">{Array.from({ length: 15 }, (_, index) => <i className={active.includes(index) ? "active" : ""} key={index} />)}</div>;
}

function FastCard({ lottery, now, primary, onOpen }: { lottery: Lottery; now: number; primary: boolean; onOpen: () => void }) {
  return <motion.article className={`fast-card fast-${lottery.code} ${primary ? "primary" : ""}`} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .34 }}>
    <img src={fastScene(lottery.code)} alt="" />
    <div className="fast-card-sheen" aria-hidden="true" />
    <header><span><i /> БЫСТРАЯ ЛОТЕРЕЯ</span><small>{formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</small></header>
    <div className="fast-card-main"><div><h2>{lottery.name}</h2><p>{fastTagline(lottery.code)}</p><span>Следующий раунд через</span><strong>{countdown(lottery.scheduled_at, now)}</strong></div><SignalPreview code={lottery.code} /></div>
    <div className="fast-card-bottom"><div><span>Стоимость</span><strong>{formatCas(lottery.ticket_price ?? 0)}</strong></div><button disabled={!lottery.purchase_available} onClick={onOpen} type="button"><Icon name="fast" />{lottery.purchase_available ? fastAction(lottery.code) : "Продажи закрыты"}<small>{lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "—"}</small></button></div>
  </motion.article>;
}

function FastLiveCard({ feed, now }: { feed: LiveFeed; now: number }) {
  const state = fastLivePresentation(feed, now);
  const signalled = useRef<string | null>(null);
  const draw = state?.draw;
  const code: FastCode = draw?.lottery_code === "shadow" ? "shadow" : draw?.lottery_code === "pulse" ? "pulse" : "flash";
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
    <img src={fastScene(code)} alt="" />
    <div className="fast-live-veil" aria-hidden="true" />
    {code === "pulse" && <PulseTrace className="pulse-live-ecg" />}
    <header><span><i /> {waiting ? "СКОРО В ЭФИРЕ" : result ? "РАУНД ЗАВЕРШЁН" : "ПРЯМОЙ ЭФИР"}</span><small>{formatDrawLabel(draw.lottery_code, draw.draw_number)}</small></header>
    <div className="fast-live-title"><div><small>{draw.lottery_name}</small><h2>{waiting ? `Старт через ${countdown(draw.scheduled_at, now)}` : result ? (code === "pulse" ? "Ритм зафиксирован" : "Сигнал принят") : "Каспер выбирает числа"}</h2></div><b>{formatMoscowTime(draw.scheduled_at)} МСК</b></div>
    <section className="fast-live-ticket" aria-live="polite">
      <div className="fast-live-ticket-head"><span>БИЛЕТ РОЗЫГРЫША</span><small>{revealed.length} / 3</small></div>
      <div className={`fast-live-slots ${code === "pulse" ? "pulse-slots" : ""}`}>{Array.from({ length: 3 }, (_, index) => <motion.i animate={revealed[index] ? { opacity: 1, scale: [0.82, 1.08, 1] } : { opacity: .55, scale: 1 }} className={`${revealed[index] ? "lit" : ""} ${code === "pulse" && index === 2 ? "special" : ""}`} key={`${index}-${revealed[index] ?? "empty"}`} transition={{ duration: .36 }}>{revealed[index] ? displayFastNumber(code, revealed[index]) : "·"}</motion.i>)}</div>
      {!waiting && !result && <div className="fast-live-scan"><i /><span>{state.phase === "starting" ? (code === "pulse" ? "Синхронизация ритма" : "Подготовка сигнала") : `Выпадает число ${state.currentNumber ? displayFastNumber(code, state.currentNumber) : ""}`}</span></div>}
    </section>
    {waiting && <p className="fast-live-note">Оставайтесь здесь — числа появятся автоматически.</p>}
    {result && <motion.div animate={{ opacity: 1, y: 0 }} className={`fast-live-result ${winner ? "winner" : ""}`} initial={{ opacity: 0, y: 6 }}><span>ИТОГ</span><strong>{draw.player_ticket_count === 0 ? "Вы не участвовали" : winner ? `+${formatCas(draw.player_total_prize)}` : "Без выигрыша"}</strong><small>{draw.player_ticket_count ? `Ваших билетов: ${draw.player_ticket_count}${draw.player_best_matches !== null ? ` · лучший результат: ${displayFastMatches(code, draw.player_best_matches)}` : ""}` : "Следующий раунд уже близко"}</small></motion.div>}
  </motion.article>;
}

export function FastView({ lotteries, feed, now, onOpen }: { lotteries: Lottery[]; feed: LiveFeed | null; now: number; onOpen: (code: string) => void }) {
  const liveState = useMemo(() => fastLivePresentation(feed, now), [feed, now]);
  const liveCode = liveState?.draw?.lottery_code;
  const ordered = [...lotteries].sort((left, right) => {
    if (left.code === liveCode) return -1;
    if (right.code === liveCode) return 1;
    return new Date(left.scheduled_at ?? 0).getTime() - new Date(right.scheduled_at ?? 0).getTime();
  });
  return <section className="fast-view">
    <header className="fast-heading"><div><span>Ритм Каспера</span><h1>Fast</h1></div><p>Новый раунд каждые 3 минуты.<br />Каждая лотерея возвращается через 9.</p></header>
    {ordered.map((lottery, index) => <motion.div key={lottery.code} layout transition={{ layout: { duration: .42, ease: [0.2, 0.75, 0.25, 1] } }}><AnimatePresence mode="wait">{liveCode === lottery.code && feed ? <FastLiveCard feed={feed} key={`live-${lottery.code}`} now={now} /> : <FastCard lottery={lottery} now={now} primary={index === 0} onOpen={() => onOpen(lottery.code)} key={`card-${lottery.code}`} />}</AnimatePresence>{index === 0 && ordered.length > 1 && <div className="fast-divider"><span><b>{lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "—"}</b>{lottery.name}</span><i><Icon name="fast" /></i><span><b>{ordered[1].scheduled_at ? formatMoscowTime(ordered[1].scheduled_at) : "—"}</b>{ordered[1].name}</span></div>}</motion.div>)}
    {!ordered.length && <div className="fast-unavailable"><Icon name="fast" /><strong>Расписание Fast готовится</strong><p>Экран обновится автоматически.</p></div>}
  </section>;
}

export function FastPicker({ lottery, purchasing, success, onClose, onBuy }: { lottery: Lottery; purchasing: boolean; success: boolean; onClose: () => void; onBuy: (numbers: number[]) => void }) {
  const [selected, setSelected] = useState<number[]>([]);
  const pulse = lottery.code === "pulse";
  const primaryMax = pulse ? 10 : 15;
  const primaryPick = pulse ? 2 : 3;
  const secondaryValues = pulse ? Array.from({ length: 5 }, (_, index) => index + 11) : [];
  const primarySelected = selected.filter((value) => value <= primaryMax);
  const secondarySelected = selected.filter((value) => value > primaryMax);
  const toggle = (value: number, limit = primaryPick) => {
    selectionHaptic();
    setSelected((current) => {
      if (current.includes(value)) return current.filter((item) => item !== value);
      const sameField = current.filter((item) => pulse && value > 10 ? item > 10 : item <= primaryMax);
      return sameField.length < limit ? [...current, value].sort((a, b) => a - b) : current;
    });
  };
  const randomize = () => {
    selectionHaptic();
    setSelected(pulse ? [...randomCombination(10, 2), randomCombination(5, 1)[0] + 10] : randomCombination(15, 3));
  };
  const complete = pulse ? primarySelected.length === 2 && secondarySelected.length === 1 : selected.length === 3;
  return <div className={`fast-picker fast-${lottery.code}`}>
    <img className="fast-picker-scene" src={fastScene(lottery.code)} alt="" />
    <div className="fast-picker-overlay" aria-hidden="true" />
    {pulse && <PulseTrace className="pulse-picker-beat" />}
    <button className="fast-picker-close" onClick={onClose} type="button" aria-label="Закрыть"><Icon name="arrow" /></button>
    <header><span>{lottery.name} · {formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</span><h1>{pulse ? "Соберите пульс" : lottery.code === "flash" ? "Соберите сигнал" : "Выберите 3 тени"}</h1><p>{pulse ? "2 основных числа + 1 Pulse-число" : "Отметьте 3 позиции из 15"}</p></header>
    <section className="fast-grid-panel"><div><strong>{pulse ? "ОСНОВНОЙ РИТМ · 2 ИЗ 10" : lottery.code === "flash" ? "ПОЛЕ ИМПУЛЬСОВ" : "ПОЛЕ ТЕНЕЙ"}</strong><span>Выбрано <b>{primarySelected.length}</b> / {primaryPick}</span></div><div className={`fast-grid ${pulse ? "pulse-main-grid" : ""}`}>{Array.from({ length: primaryMax }, (_, index) => index + 1).map((value) => <motion.button aria-label={`Позиция ${value}`} aria-pressed={selected.includes(value)} className={selected.includes(value) ? "selected" : ""} key={value} onClick={() => toggle(value)} type="button" whileTap={{ scale: .86 }}><i /><small>{String(value).padStart(2, "0")}</small></motion.button>)}</div></section>
    {pulse && <section className="pulse-special-panel"><div><strong>PULSE-ПОЛЕ · 1 ИЗ 5</strong><span>Выбрано <b>{secondarySelected.length}</b> / 1</span></div><div>{secondaryValues.map((value) => <motion.button aria-label={`Pulse-число ${value - 10}`} aria-pressed={selected.includes(value)} className={selected.includes(value) ? "selected" : ""} key={value} onClick={() => toggle(value, 1)} type="button" whileTap={{ scale: .84 }}><i />P{value - 10}</motion.button>)}</div></section>}
    <section className="fast-selection"><div><span>{pulse ? "Ваш ритм" : lottery.code === "flash" ? "Ваш сигнал" : "Ваши тени"}</span><div>{pulse ? <><i className={primarySelected[0] ? "filled" : ""}>{primarySelected[0] ? String(primarySelected[0]).padStart(2, "0") : "—"}</i><i className={primarySelected[1] ? "filled" : ""}>{primarySelected[1] ? String(primarySelected[1]).padStart(2, "0") : "—"}</i><b>+</b><i className={`pulse-chip ${secondarySelected[0] ? "filled" : ""}`}>{secondarySelected[0] ? `P${secondarySelected[0] - 10}` : "—"}</i></> : Array.from({ length: 3 }, (_, index) => <i className={selected[index] ? "filled" : ""} key={index}>{selected[index] ? String(selected[index]).padStart(2, "0") : "—"}</i>)}</div></div><button onClick={randomize} type="button"><Icon name="spark" />Случайный выбор</button></section>
    <div className="fast-purchase"><div><span>Стоимость</span><strong>{formatCas(lottery.ticket_price ?? 0)}</strong></div><PrimaryButton disabled={!complete} loading={purchasing} success={success} onClick={() => onBuy(selected)}><Icon name="fast" />{success ? "Билет куплен" : pulse ? "Запустить пульс" : lottery.code === "flash" ? "Активировать" : "Купить сигнал"}</PrimaryButton></div>
    <p className="fast-picker-note">Билет участвует в ближайшем раунде · без эфира в Telegram</p>
  </div>;
}
