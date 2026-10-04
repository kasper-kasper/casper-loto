import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

import { FastArtifact } from "./FastArtifact";
import "./fast-premium.css";
import { Icon, Money, PrimaryButton } from "./components";
import { countdown, formatCas, formatDrawLabel, formatMoscowTime } from "./format";
import { fastLivePresentation } from "./live";
import { randomCombination } from "./random";
import { liveStartHaptic, selectionHaptic } from "./telegram";
import type { LiveFeed, Lottery } from "./types";

type FastCode = "flash" | "shadow" | "pulse" | "code";

const presentationCode = (lottery: Pick<Lottery, "code" | "name" | "ruleset_code">): FastCode => lottery.ruleset_code?.startsWith("code_") || lottery.name === "CODE" ? "code" : lottery.code === "pulse" ? "pulse" : lottery.code === "shadow" ? "shadow" : "flash";
const fastTagline = (code: FastCode) => code === "flash" ? "Соберите сигнал" : code === "pulse" ? "Поймайте ритм" : code === "code" ? "Взломайте комбинацию" : "Выберите тени";
const fastAction = (code: FastCode) => code === "flash" ? "Собрать сигнал" : code === "pulse" ? "Поймать импульс" : code === "code" ? "Ввести код" : "Выбрать тени";

function displayFastNumber(code: string, value: number, pulseOffset = 12): string {
  if (code === "pulse" && value > 1_000) return `ШИФР ${String(value - 1_000).padStart(3, "0")}`;
  return code === "pulse" && value > pulseOffset ? `P${value - pulseOffset}` : String(value).padStart(2, "0");
}

function displayFastMatches(code: string, matches: number, total: number): string {
  if (code === "pulse" && matches >= 100) return `${Math.floor(matches / 100)}+${Math.floor(matches / 10) % 10} · шифр ${matches % 10 ? "да" : "нет"}`;
  return code === "pulse" ? `${Math.floor(matches / 10)}+${matches % 10}` : `${matches}/${total}`;
}

function secureCode(length: number): number[] {
  const values = new Uint32Array(length);
  crypto.getRandomValues(values);
  return Array.from(values, (value) => value % 10);
}

function PulseTrace({ className }: { className: string }) {
  return <div className={className} aria-hidden="true"><svg viewBox="0 0 120 48"><path d="M0 25H24L31 21L37 25L44 7L53 41L61 25H120" pathLength="120" /><circle cx="44" cy="7" r="2" /></svg></div>;
}

function SignalTelemetry({ code, maxNumber, pickCount }: { code: string; maxNumber: number; pickCount: number }) {
  if (code === "pulse") return <PulseTrace className="fast-pulse-preview" />;
  if (code === "code") return <div className="code-preview" aria-hidden="true">{Array.from({ length: pickCount }, (_, index) => <span key={index}>•</span>)}<i /></div>;
  const active = code === "flash" ? [1, 7, 12] : [2, 8, 14];
  return <div className="fast-signal-preview" aria-hidden="true">{Array.from({ length: maxNumber }, (_, index) => <i className={active.includes(index) ? "active" : ""} key={index} />)}</div>;
}

function randomFastTicket(lottery: Lottery): number[] {
  const code = presentationCode(lottery);
  const primaryMax = lottery.primary_max_number ?? lottery.max_number;
  const primaryPick = lottery.primary_numbers_to_pick ?? lottery.numbers_to_pick;
  const secondaryMax = lottery.secondary_max_number ?? 0;
  const secondaryPick = lottery.secondary_numbers_to_pick ?? 0;
  const secondaryOffset = lottery.secondary_storage_offset ?? primaryMax;
  return code === "code"
    ? secureCode(lottery.numbers_to_pick)
    : code === "pulse"
      ? [...randomCombination(primaryMax, primaryPick), ...randomCombination(secondaryMax, secondaryPick).map((value) => value + secondaryOffset)]
      : randomCombination(lottery.max_number, lottery.numbers_to_pick);
}

function FastCard({ lottery, now, primary, balance, purchasing, onOpen, onQuickBuy }: { lottery: Lottery; now: number; primary: boolean; balance: number; purchasing: boolean; onOpen: () => void; onQuickBuy: (combinations: number[][]) => void }) {
  const code = presentationCode(lottery);
  const remaining = Math.max(0, lottery.max_tickets_per_user_per_draw - lottery.player_ticket_count);
  const affordable = lottery.ticket_price ? Math.floor(balance / lottery.ticket_price) : 0;
  const quickLimit = Math.min(remaining, affordable, lottery.max_tickets_per_purchase);
  return <motion.article className={`fast-card fast-${code} ${primary ? "primary" : ""}`} initial={false} animate={{ opacity: 1, y: 0 }} transition={{ duration: .34 }}>
    <div className="fast-card-sheen" aria-hidden="true" />
    <header><span><i /> БЫСТРАЯ ЛОТЕРЕЯ</span><small>{formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</small></header>
    <div className="fast-card-main"><div><h2>{lottery.name}</h2><p>{fastTagline(code)}</p><span>Следующий раунд через</span><strong>{countdown(lottery.scheduled_at, now)}</strong></div><div className="fast-display"><FastArtifact kind={code} /><div className="fast-telemetry"><SignalTelemetry code={code} maxNumber={lottery.max_number} pickCount={lottery.numbers_to_pick} /></div></div></div>
    <div className="fast-card-jackpot"><span>ТЕКУЩИЙ ДЖЕКПОТ</span><strong><Money value={lottery.jackpot} /></strong></div>
    <div className="fast-card-bottom"><div><span>Стоимость</span><strong><Money value={lottery.ticket_price ?? 0} /></strong></div><button disabled={purchasing || !lottery.purchase_available} onClick={onOpen} type="button"><Icon name="fast" />{lottery.purchase_available ? fastAction(code) : "Продажи закрыты"}<small>{lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "—"}</small></button></div>
    <div className="fast-card-quick"><span>КУПИТЬ СЛУЧАЙНЫЕ</span>{[1, 5, 10].map((quantity) => <button aria-label={`Купить ${quantity} случайных билетов ${lottery.name}`} disabled={purchasing || !lottery.purchase_available || quantity > quickLimit} key={quantity} onClick={() => onQuickBuy(Array.from({ length: quantity }, () => randomFastTicket(lottery)))} type="button">{quantity}</button>)}</div>
  </motion.article>;
}

function FastLiveCard({ feed, now }: { feed: LiveFeed; now: number }) {
  const state = fastLivePresentation(feed, now);
  const signalled = useRef<string | null>(null);
  const draw = state?.draw;
  const code: FastCode = draw?.lottery_name === "CODE" ? "code" : draw?.lottery_code === "shadow" ? "shadow" : draw?.lottery_code === "pulse" ? "pulse" : "flash";
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
  const slotCount = draw.winning_numbers?.length || draw.reveal_at.length || (code === "code" ? 5 : code === "pulse" ? 5 : 5);
  const pulseOffset = draw.secondary_storage_offset || 12;
  return <motion.article animate={{ opacity: 1, scale: 1 }} className={`fast-live-card fast-${code} phase-${state.phase}`} initial={false} transition={{ duration: .28 }}>
    <FastArtifact kind={code} className="fast-live-art" />
    <div className="fast-live-veil" aria-hidden="true" />
    {code === "pulse" && <PulseTrace className="pulse-live-ecg" />}
    <header><span><i /> {waiting ? "СКОРО В ЭФИРЕ" : result ? "РАУНД ЗАВЕРШЁН" : "ПРЯМОЙ ЭФИР"}</span><small>{formatDrawLabel(draw.lottery_code, draw.draw_number)}</small></header>
    <div className="fast-live-title"><div><small>{draw.lottery_name}</small><h2>{waiting ? `Старт через ${countdown(draw.scheduled_at, now)}` : result ? (code === "pulse" ? "Ритм зафиксирован" : "Сигнал принят") : "Каспер выбирает числа"}</h2></div><b>{formatMoscowTime(draw.scheduled_at)} МСК</b></div>
    <section className="fast-live-ticket" aria-live="polite">
      <div className="fast-live-ticket-head"><span>{code === "code" ? "КОД РОЗЫГРЫША" : "БИЛЕТ РОЗЫГРЫША"}</span><small>{revealed.length} / {slotCount}</small></div>
      <div className={`fast-live-slots ${code === "pulse" ? `pulse-slots ${slotCount === 5 ? "has-cipher" : ""}` : ""} ${code === "code" ? "code-slots" : ""}`}>{Array.from({ length: slotCount }, (_, index) => <motion.i animate={revealed[index] !== undefined ? { opacity: 1, scale: [0.82, 1.08, 1] } : { opacity: .55, scale: 1 }} className={`${revealed[index] !== undefined ? "lit" : ""} ${code === "pulse" && index >= 2 && index < 4 ? "special" : ""} ${code === "pulse" && index === 4 ? "cipher" : ""}`} key={`${index}-${revealed[index] ?? "empty"}`} transition={{ duration: .36 }}>{revealed[index] !== undefined ? displayFastNumber(code, revealed[index], pulseOffset) : "·"}</motion.i>)}</div>
      {!waiting && !result && <div className="fast-live-scan"><i /><span>{state.phase === "starting" ? (code === "pulse" ? "Синхронизация ритма" : code === "code" ? "Проверка шифра" : "Подготовка сигнала") : `Выпадает число ${state.currentNumber !== null ? displayFastNumber(code, state.currentNumber, pulseOffset) : ""}`}</span></div>}
    </section>
    {waiting && <p className="fast-live-note">Оставайтесь здесь — числа появятся автоматически.</p>}
    {result && <motion.div animate={{ opacity: 1, y: 0 }} className={`fast-live-result ${winner ? "winner" : ""}`} initial={{ opacity: 0, y: 6 }}><span>ИТОГ</span><strong>{draw.player_ticket_count === 0 ? "Вы не участвовали" : winner ? `+${formatCas(draw.player_total_prize)}` : "Без выигрыша"}</strong><small>{draw.player_ticket_count ? `Ваших билетов: ${draw.player_ticket_count}${draw.player_best_matches !== null ? ` · лучший результат: ${displayFastMatches(code, draw.player_best_matches, slotCount)}` : ""}` : "Следующий раунд уже близко"}</small></motion.div>}
  </motion.article>;
}

export function FastView({ lotteries, feed, now, balance = Number.MAX_SAFE_INTEGER, purchasing = false, onOpen, onQuickBuy = () => undefined }: { lotteries: Lottery[]; feed: LiveFeed | null; now: number; balance?: number; purchasing?: boolean; onOpen: (code: string) => void; onQuickBuy?: (code: string, combinations: number[][]) => void }) {
  const liveState = useMemo(() => fastLivePresentation(feed, now), [feed, now]);
  const liveCode = liveState?.draw?.lottery_code;
  const ordered = [...lotteries].sort((left, right) => {
    if (left.code === liveCode) return -1;
    if (right.code === liveCode) return 1;
    return new Date(left.scheduled_at ?? 0).getTime() - new Date(right.scheduled_at ?? 0).getTime();
  });
  return <section className="fast-view">
    <header className="fast-heading"><div><h1>Casper Fast</h1></div><p>Новый раунд каждые 3 минуты.<br />Каждая игра возвращается через 9.</p></header>
    {ordered.map((lottery, index) => <motion.div key={lottery.code} layout transition={{ layout: { duration: .42, ease: [0.2, 0.75, 0.25, 1] } }}><AnimatePresence mode="wait">{liveCode === lottery.code && feed ? <FastLiveCard feed={feed} key={`live-${lottery.code}`} now={now} /> : <FastCard lottery={lottery} now={now} primary={index === 0} balance={balance} purchasing={purchasing} onOpen={() => onOpen(lottery.code)} onQuickBuy={(combinations) => onQuickBuy(lottery.code, combinations)} key={`card-${lottery.code}`} />}</AnimatePresence>{index === 0 && ordered.length > 1 && <div className="fast-divider"><span><b>{lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "—"}</b>{lottery.name}</span><i><Icon name="fast" /></i><span><b>{ordered[1].scheduled_at ? formatMoscowTime(ordered[1].scheduled_at) : "—"}</b>{ordered[1].name}</span></div>}</motion.div>)}
    {!ordered.length && <div className="fast-unavailable"><Icon name="fast" /><strong>Расписание готовится</strong><p>Экран обновится автоматически.</p></div>}
  </section>;
}

export function FastPicker({ lottery, purchasing, success, error, onClose, onBuy }: { error?: string | null; lottery: Lottery; purchasing: boolean; success: boolean; onClose: () => void; onBuy: (numbers: number[]) => Promise<boolean> }) {
  const [selected, setSelected] = useState<number[]>([]);
  const code = presentationCode(lottery);
  const pulse = code === "pulse";
  const codeMode = code === "code";
  const codePick = codeMode ? lottery.numbers_to_pick : 0;
  const primaryMax = pulse ? (lottery.primary_max_number ?? 10) : codeMode ? 9 : lottery.max_number;
  const primaryPick = pulse ? (lottery.primary_numbers_to_pick ?? 2) : codeMode ? codePick : lottery.numbers_to_pick;
  const secondaryPick = lottery.secondary_numbers_to_pick ?? 0;
  const secondaryMax = lottery.secondary_max_number ?? 0;
  const secondaryOffset = lottery.secondary_storage_offset ?? primaryMax;
  const secondaryValues = pulse ? Array.from({ length: secondaryMax }, (_, index) => index + 1 + secondaryOffset) : [];
  const primarySelected = codeMode ? selected : selected.filter((value) => value <= primaryMax);
  const secondarySelected = selected.filter((value) => value > secondaryOffset);
  const toggle = (value: number, limit = primaryPick) => {
    if (purchasing) return;
    selectionHaptic();
    setSelected((current) => {
      if (codeMode) return current.length < codePick ? [...current, value] : current;
      if (current.includes(value)) return current.filter((item) => item !== value);
      const sameField = current.filter((item) => pulse && value > secondaryOffset ? item > secondaryOffset : item <= primaryMax);
      return sameField.length < limit ? [...current, value].sort((a, b) => a - b) : current;
    });
  };
  const randomize = () => {
    if (purchasing) return;
    selectionHaptic();
    setSelected(codeMode ? secureCode(codePick) : pulse ? [...randomCombination(primaryMax, primaryPick), ...randomCombination(secondaryMax, secondaryPick).map((value) => value + secondaryOffset)] : randomCombination(lottery.max_number, lottery.numbers_to_pick));
  };
  const buy = async () => {
    if (purchasing || !complete || !lottery.purchase_available) return;
    if (await onBuy([...selected])) setSelected([]);
  };
  const complete = codeMode ? selected.length === codePick : pulse ? primarySelected.length === primaryPick && secondarySelected.length === secondaryPick : selected.length === lottery.numbers_to_pick;
  const primaryValues = codeMode ? [...Array.from({ length: 9 }, (_, index) => index + 1), 0] : Array.from({ length: primaryMax }, (_, index) => index + 1);
  return <div className={`fast-picker fast-${code}`}>
    <FastArtifact kind={code} className="fast-picker-art" />
    <button className="fast-picker-close" onClick={onClose} type="button" aria-label="Закрыть"><Icon name="arrow" /></button>
    <span className="fast-picker-mode">CASPER <b>FAST</b><i /> БЫСТРЫЕ РАУНДЫ</span>
    <header><span>{lottery.name} · {formatDrawLabel(lottery.code, lottery.draw_number ?? 0)}</span><h1>{pulse ? "Соберите пульс" : code === "flash" ? "Соберите сигнал" : codeMode ? "Введите код" : `Выберите ${lottery.numbers_to_pick} тени`}</h1><p>{pulse ? `${primaryPick} основных числа + ${secondaryPick} Pulse-числа · шифр назначит сервер` : codeMode ? `${codePick} цифр · порядок важен · повторы разрешены` : `Ваш выбор: ${lottery.numbers_to_pick} из ${lottery.max_number}`}</p></header>
    <section className={`fast-grid-panel ${codeMode ? "code-keypad-panel" : ""}`}><div><strong>{pulse ? `ОСНОВНОЙ РИТМ · ${primaryPick} ИЗ ${primaryMax}` : code === "flash" ? "ПОЛЕ ИМПУЛЬСОВ" : codeMode ? "ЦИФРОВАЯ КЛАВИАТУРА" : "ПОЛЕ ТЕНЕЙ"}</strong><span>{codeMode ? "Введено" : "Выбрано"} <b>{primarySelected.length}</b> / {primaryPick}</span></div><div className={`fast-grid ${pulse ? "pulse-main-grid" : ""} ${codeMode ? "code-keypad" : ""}`}>{primaryValues.map((value) => <motion.button aria-label={`${codeMode ? "Цифра" : "Позиция"} ${value}`} aria-pressed={codeMode ? undefined : selected.includes(value)} className={!codeMode && selected.includes(value) ? "selected" : ""} key={value} disabled={purchasing} onClick={() => toggle(value)} type="button" whileTap={{ scale: .86 }}><i /><small>{codeMode ? value : String(value).padStart(2, "0")}</small></motion.button>)}{codeMode && <button className="code-backspace" aria-label="Удалить последнюю цифру" disabled={purchasing || !selected.length} onClick={() => setSelected((current) => current.slice(0, -1))} type="button">⌫</button>}</div></section>
    {pulse && <section className="pulse-special-panel"><div><strong>PULSE-ПОЛЕ · {secondaryPick} ИЗ {secondaryMax}</strong><span>Выбрано <b>{secondarySelected.length}</b> / {secondaryPick}</span></div><div>{secondaryValues.map((value) => <motion.button aria-label={`Pulse-число ${value - secondaryOffset}`} aria-pressed={selected.includes(value)} className={selected.includes(value) ? "selected" : ""} key={value} disabled={purchasing} onClick={() => toggle(value, secondaryPick)} type="button" whileTap={{ scale: .84 }}>{value - secondaryOffset}</motion.button>)}</div></section>}
    <section className="fast-selection"><div><span>{pulse ? "Ваш ритм" : code === "flash" ? "Ваш сигнал" : codeMode ? "Ваш код" : "Ваши тени"}</span><div>{pulse ? <>{Array.from({ length: primaryPick }, (_, index) => <i className={primarySelected[index] ? "filled" : ""} key={`primary-${index}`}>{primarySelected[index] ? String(primarySelected[index]).padStart(2, "0") : "—"}</i>)}<b>+</b>{Array.from({ length: secondaryPick }, (_, index) => <i className={`pulse-chip ${secondarySelected[index] ? "filled" : ""}`} key={`secondary-${index}`}>{secondarySelected[index] ? `P${secondarySelected[index] - secondaryOffset}` : "—"}</i>)}</> : Array.from({ length: codeMode ? codePick : lottery.numbers_to_pick }, (_, index) => <i className={selected[index] !== undefined ? "filled" : ""} key={index}>{selected[index] !== undefined ? String(selected[index]).padStart(codeMode ? 1 : 2, "0") : "—"}</i>)}</div></div><button disabled={purchasing} onClick={randomize} type="button"><Icon name="spark" />{codeMode ? "Случайный код" : "Случайный выбор"}</button></section>
    {error && <p className="fast-picker-error" role="alert">{error}</p>}
    <div className="fast-purchase"><div><span>Стоимость</span><strong>{formatCas(lottery.ticket_price ?? 0)}</strong></div><PrimaryButton disabled={!complete || !lottery.purchase_available} loading={purchasing} success={success} onClick={() => void buy()}><Icon name="fast" />{success ? "Билет куплен" : pulse ? "Запустить пульс" : code === "flash" ? "Активировать" : codeMode ? "Подтвердить код" : "Купить сигнал"}</PrimaryButton></div>
    <p className="fast-picker-note">Билет участвует в ближайшем раунде</p>
  </div>;
}
