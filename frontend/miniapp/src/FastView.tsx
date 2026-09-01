import { useState } from "react";
import { motion } from "motion/react";

import flashScene from "./assets/lotteries/flash-scene.webp";
import shadowScene from "./assets/lotteries/shadow-scene.webp";
import { Icon, PrimaryButton } from "./components";
import { countdown, formatCas, formatDrawLabel, formatMoscowTime } from "./format";
import { randomCombination } from "./random";
import { selectionHaptic } from "./telegram";
import type { Lottery } from "./types";

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

export function FastView({ lotteries, now, onOpen }: { lotteries: Lottery[]; now: number; onOpen: (code: string) => void }) {
  const ordered = [...lotteries].sort((left, right) => new Date(left.scheduled_at ?? 0).getTime() - new Date(right.scheduled_at ?? 0).getTime());
  return <section className="fast-view">
    <header className="fast-heading"><div><span>Ритм Каспера</span><h1>Fast</h1></div><p>Новый раунд каждые 10 минут.<br />FLASH и SHADOW чередуются.</p></header>
    {ordered.map((lottery, index) => <div key={lottery.code}><FastCard lottery={lottery} now={now} primary={index === 0} onOpen={() => onOpen(lottery.code)} />{index === 0 && ordered.length > 1 && <div className="fast-divider"><span><b>{lottery.scheduled_at ? formatMoscowTime(lottery.scheduled_at) : "—"}</b>{lottery.name}</span><i><Icon name="fast" /></i><span><b>{ordered[1].scheduled_at ? formatMoscowTime(ordered[1].scheduled_at) : "—"}</b>{ordered[1].name}</span></div>}</div>)}
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
