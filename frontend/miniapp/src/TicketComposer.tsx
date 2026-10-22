import { tr } from "./i18n";
import { useState } from "react";
import type { CSSProperties } from "react";
import { Icon, Money } from "./components";
import { ClassicTicket } from "./ClassicTicket";
import { MiniRules } from "./MiniTicket";
import { NewYearCoupon, NewYearRules, NewYearSymbols } from "./NewYear";
import { MiniCoupon } from "./MiniIdentity";
import { GrandTicket } from "./GrandTicket";
import { HalloweenTicket } from "./HalloweenTicket";
import { isGrandLottery, lotteryCombination } from "./grand";
import { selectionHaptic } from "./telegram";
import type { Favorite, Lottery } from "./types";

function DualDial({ phase, selected, purchasing, onToggle }: { phase: "night" | "dawn"; selected: number[]; purchasing: boolean; onToggle: (value: number, phase: "night" | "dawn") => void }) {
  const label = phase.toUpperCase();
  return <section className={`dual-dial-panel dual-dial-${phase}`} aria-label={tr("{0} · выбор чисел", label)}>
    <header className="dual-dial-heading"><strong>{tr(label)}</strong><small>{phase === "night" ? "00:30" : "07:30"}</small></header>
    <div className="dual-dial-face" role="group" aria-label={tr("{0}: выберите 2 числа из 12", label)}>
      <span className="dual-dial-center" aria-hidden="true">{phase === "night" ? "☾" : "☀"}</span>
      {Array.from({ length: 12 }, (_, index) => index + 1).map((value) => {
        const angle = value * Math.PI / 6;
        const active = selected.includes(value);
        return <span className="dual-dial-position" key={value} style={{ left: `${50 + 35 * Math.sin(angle)}%`, top: `${50 - 35 * Math.cos(angle)}%` }}>
          <button type="button" className="dual-dial-number" aria-label={tr(`${label} ${value}`)} aria-pressed={active} disabled={purchasing} onClick={() => onToggle(value, phase)}><span>{value}</span></button>
        </span>;
      })}
    </div>
    <div className="dual-dial-count" aria-live="polite"><span>{selected.length} / 2</span><small>{tr("выбрано")}</small></div>
  </section>;
}

export function TicketComposer({ lottery, balance, now, purchasing, initialNumbers = [], favorites, onBuy, onBuyMany, onSaveFavorite, onDeleteFavorite }: { lottery: Lottery; balance: number; now: number; purchasing: boolean; initialNumbers?: number[]; favorites: Favorite[]; onBuy: (numbers: number[], drawCount: 1 | 5, mode: "manual" | "random") => Promise<boolean>; onBuyMany: (numbers: number[][], drawCount: 1 | 5) => Promise<boolean>; onSaveFavorite: (numbers: number[]) => void; onDeleteFavorite: (id: string) => void }) {
  const [selected, setSelected] = useState<number[]>(initialNumbers);
  const [manualNumbers, setManualNumbers] = useState<number[]>([]);
  const [drawCount, setDrawCount] = useState<1 | 5>(1);
  const dual = lottery.code === "dual";
  const newYear = lottery.code === "newyear2027";
  const dualSalesClosed = dual && (!lottery.purchase_available || (lottery.sales_close_at !== null && Date.parse(lottery.sales_close_at) <= now));
  const grand = isGrandLottery(lottery);
  const grandOffset = lottery.secondary_storage_offset ?? 35;
  const grandMainCount = lottery.primary_numbers_to_pick ?? 5;
  const grandSpecialCount = lottery.secondary_numbers_to_pick ?? 2;
  const mainSelected = selected.filter((value) => value <= grandOffset);
  const specialSelected = selected.filter((value) => value > grandOffset);
  const dualNight = dual ? selected.filter((value) => value <= 12) : [];
  const dualDawn = dual ? selected.filter((value) => value > 12).map((value) => value - 12) : [];
  const ready = dual ? dualNight.length === 2 && dualDawn.length === 2 : grand
    ? mainSelected.length === grandMainCount && specialSelected.length === grandSpecialCount
    : selected.length === lottery.numbers_to_pick;
  const ticketCost = lottery.ticket_price ?? 0;
  const quickLimit = Math.min(
    Math.floor(lottery.max_tickets_per_purchase / (lottery.code === "mini" ? drawCount : 1)),
    Math.max(0, lottery.max_tickets_per_user_per_draw - lottery.player_ticket_count),
    ticketCost > 0 ? Math.floor(balance / (ticketCost * drawCount)) : 0,
  );
  const saved = favorites.some((favorite) => favorite.numbers.length === selected.length && favorite.numbers.every((value, index) => value === selected[index]));
  const toggle = (value: number) => {
    if (purchasing) return;
    setManualNumbers(current => selected.includes(value) ? current.filter(n => n !== value) : [...current, value]);
    setSelected((current) => {
      const inSpecialField = grand && value > grandOffset;
      const fieldCount = grand
        ? current.filter((item) => inSpecialField ? item > grandOffset : item <= grandOffset).length
        : current.length;
      const fieldLimit = inSpecialField ? grandSpecialCount : grand ? grandMainCount : lottery.numbers_to_pick;
      if (!current.includes(value) && fieldCount >= fieldLimit) return current;
      selectionHaptic();
      return current.includes(value) ? current.filter((item) => item !== value) : [...current, value].sort((left, right) => left - right);
    });
  };
  const toggleDual = (value: number, phase: "night" | "dawn") => {
    if (purchasing) return;
    const stored = phase === "night" ? value : value + 12;
    setManualNumbers(current => selected.includes(stored) ? current.filter(n => n !== stored) : [...current, stored]);
    setSelected((current) => {
      const field = current.filter((item) => phase === "night" ? item <= 12 : item > 12);
      if (!current.includes(stored) && field.length >= 2) return current;
      selectionHaptic();
      return current.includes(stored) ? current.filter((item) => item !== stored) : [...current, stored].sort((left, right) => left - right);
    });
  };
  const randomize = () => {
    selectionHaptic();
    setSelected(lotteryCombination(lottery));
    setManualNumbers([]);
  };
  const buy = async () => {
    if (dualSalesClosed) return;
    if (await onBuy(selected, drawCount, selected.every(n => manualNumbers.includes(n)) ? "manual" : "random")) { setSelected([]); setManualNumbers([]); }
  };
  const closed = dualSalesClosed || !lottery.purchase_available;
  const field = (label: string, max: number, limit: number, values: number[], offset = 0) => <section className={`ticket-field ${offset ? "ticket-special" : ""}`}>
    <div className="ticket-field-label"><span>{tr(label)}</span><small>{values.length}  {tr("из")} {limit}</small></div>
    <div className="ticket-number-grid" style={{ "--columns": max <= 8 ? max : max <= 16 ? 4 : max <= 25 ? 5 : 6 } as CSSProperties} aria-label={tr(label)}>
      {Array.from({ length: max }, (_, index) => index + 1).map(value => <button className="ticket-number" type="button" aria-label={tr(String(value))} aria-pressed={values.includes(value)} disabled={purchasing} onClick={() => toggle(value + offset)} key={value}>{value}</button>)}
    </div>
  </section>;

  return <div className="ticket-composer">
    {newYear ? <NewYearCoupon selected={selected} purchasing={purchasing} onToggle={toggle} onRandomize={randomize} /> : lottery.code === "mini" ? <MiniCoupon lottery={lottery} selected={selected} purchasing={purchasing} drawCount={drawCount} onToggle={toggle} onRandomize={randomize} /> : lottery.code === "khan" ? <ClassicTicket lottery={lottery} selected={selected} purchasing={purchasing} drawCount={drawCount} onToggle={toggle} onRandomize={randomize} /> : lottery.code === "grob" ? <HalloweenTicket lottery={lottery} selected={selected} purchasing={purchasing} drawCount={drawCount} onToggle={toggle} onRandomize={randomize} /> : lottery.code === "weekly" && grand ? <GrandTicket lottery={lottery} selected={selected} purchasing={purchasing} onToggle={toggle} onRandomize={randomize} /> : <div className={`ticket-surface${dual ? " dual-ticket-surface" : ""}`}>
      <header className="ticket-surface-heading"><div><span>{tr("ВАША КОМБИНАЦИЯ")}</span><h2>{tr("Ваш билет")}</h2></div><button type="button" aria-label={tr("Случайные числа")} className="ticket-shuffle" disabled={purchasing} onClick={randomize}><Icon name="spark" />{tr("Случайно")}</button></header>
      {dual ? <div className="dual-dial-pair"><DualDial phase="night" selected={dualNight} purchasing={purchasing} onToggle={toggleDual} /><DualDial phase="dawn" selected={dualDawn} purchasing={purchasing} onToggle={toggleDual} /></div> : grand ? <>
        {field(tr("Основные числа"), lottery.primary_max_number ?? 35, grandMainCount, mainSelected)}
        {field(lottery.code === "pss" ? "Casper Ball" : tr("Звёзды"), lottery.secondary_max_number ?? 5, grandSpecialCount, specialSelected.map(value => value - grandOffset), grandOffset)}
      </> : field(tr("Числа"), lottery.max_number, lottery.numbers_to_pick, selected)}
      <div className="ticket-surface-footer"><span>{dual ? tr("Два раунда · один билет") : drawCount === 5 ? tr("Одна комбинация · 5 тиражей") : tr("Одна комбинация · 1 тираж")}</span><span>{tr(ready ? tr("Готов к покупке") : `${selected.length} / ${lottery.numbers_to_pick}`)}</span></div>
    </div>}
    <section className="play-quick" aria-label={tr("Быстрая покупка")}><div><strong>{tr("Быстрая покупка")}</strong><small>{tr("Случайные билеты")}</small></div><div>{[1, 5, 25].map(count => <button key={count} type="button" aria-label={tr("Купить {0} {1}", count, count === 1 ? tr("случайный билет") : tr("случайных билетов"))} disabled={purchasing || closed || count > quickLimit} onClick={() => void onBuyMany(Array.from({ length: count }, () => lotteryCombination(lottery)), drawCount)}>×{count}</button>)}</div></section>
    {<details className="ticket-options"><summary>{dual ? tr("Избранное") : tr("Повторы и избранное")} <span>＋</span></summary><div className="ticket-options-body">
      {!dual && <div className="ticket-repeat"><span>{tr("Участие в тиражах")}</span><div><button type="button" disabled={purchasing} aria-pressed={drawCount === 1} onClick={() => setDrawCount(1)}>{tr("1 тираж")}</button><button type="button" disabled={purchasing} aria-pressed={drawCount === 5} onClick={() => setDrawCount(5)}>{tr("5 тиражей")}</button></div></div>}
      {drawCount === 5 && <p>{tr("Эти числа участвуют в текущем и следующих 4 тиражах. Полная сумма оплачивается сейчас. Без автопродления.")}</p>}
      <button type="button" className="ticket-save" disabled={!ready || saved || purchasing} onClick={() => onSaveFavorite(selected)}>{saved ? tr("Комбинация сохранена") : tr("Сохранить комбинацию")}</button>
      {favorites.length > 0 && <div className="ticket-favorites">{favorites.map(favorite => <div key={favorite.id}><button disabled={purchasing} type="button" aria-label={tr(newYear ? tr("Выбрать сохранённую тройку") : undefined)} onClick={() => { setSelected(favorite.numbers); setManualNumbers([]); }}>{tr(newYear ? <NewYearSymbols values={favorite.numbers} /> : dual ? `NIGHT: ${favorite.numbers.filter(n => n <= 12).join(" · ")} / DAWN: ${favorite.numbers.filter(n => n > 12).map(n => n - 12).join(" · ")}` : grand ? `${favorite.numbers.filter(n => n <= grandOffset).join(" · ")} + ${favorite.numbers.filter(n => n > grandOffset).map(n => n - grandOffset).join(" · ")}` : favorite.numbers.join(" · "))}</button><button type="button" disabled={purchasing} aria-label={tr("Удалить из избранного")} onClick={() => onDeleteFavorite(favorite.id)}>×</button></div>)}</div>}
    </div></details>}
    {lottery.code === "mini" && <MiniRules lottery={lottery} />}
    {newYear && <NewYearRules />}
    {closed && <p className="play-message">{tr("Продажи закрыты. Ожидаем следующий тираж.")}</p>}
    <footer className="play-checkout"><div><small>{drawCount === 5 ? tr("Билет на 5 тиражей") : tr("Стоимость билета")}</small><strong><Money value={ticketCost * drawCount} /></strong></div><button type="button" aria-label={drawCount === 5 ? tr("Купить на 5 тиражей") : tr("Купить билет")} disabled={!ready || purchasing || closed} onClick={() => void buy()}>{purchasing ? tr("Оформляем…") : tr("Купить билет")}<span aria-hidden="true">↗</span></button></footer>
  </div>;
}
