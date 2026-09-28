import { useState } from "react";
import type { CSSProperties } from "react";
import { Icon, Money } from "./components";
import { ClassicTicket } from "./ClassicTicket";
import { isGrandLottery, lotteryCombination } from "./grand";
import { selectionHaptic } from "./telegram";
import type { Favorite, Lottery } from "./types";

export function TicketComposer({ lottery, balance, now, purchasing, initialNumbers = [], favorites, onBuy, onBuyMany, onSaveFavorite, onDeleteFavorite }: { lottery: Lottery; balance: number; now: number; purchasing: boolean; initialNumbers?: number[]; favorites: Favorite[]; onBuy: (numbers: number[], drawCount: 1 | 5) => Promise<boolean>; onBuyMany: (numbers: number[][], drawCount: 1 | 5) => Promise<boolean>; onSaveFavorite: (numbers: number[]) => void; onDeleteFavorite: (id: string) => void }) {
  const [selected, setSelected] = useState<number[]>(initialNumbers);
  const [drawCount, setDrawCount] = useState<1 | 5>(1);
  const dual = lottery.code === "dual";
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
    lottery.max_tickets_per_purchase,
    Math.max(0, lottery.max_tickets_per_user_per_draw - lottery.player_ticket_count),
    ticketCost > 0 ? Math.floor(balance / (ticketCost * drawCount)) : 0,
  );
  const saved = favorites.some((favorite) => favorite.numbers.length === selected.length && favorite.numbers.every((value, index) => value === selected[index]));
  const toggle = (value: number) => {
    if (purchasing) return;
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
  };
  const buy = async () => {
    if (dualSalesClosed) return;
    if (await onBuy(selected, drawCount)) setSelected([]);
  };
  const closed = dualSalesClosed || !lottery.purchase_available;
  const field = (label: string, max: number, limit: number, values: number[], offset = 0, phase?: "night" | "dawn") => <section className={`ticket-field ${offset ? "ticket-special" : ""}`}>
    <div className="ticket-field-label"><span>{label}</span><small>{values.length} из {limit}</small></div>
    <div className="ticket-number-grid" style={{ "--columns": max <= 8 ? max : max <= 16 ? 4 : max <= 25 ? 5 : 6 } as CSSProperties} aria-label={label}>
      {Array.from({ length: max }, (_, index) => index + 1).map(value => <button className="ticket-number" type="button" aria-label={phase ? `${phase.toUpperCase()} ${value}` : String(value)} aria-pressed={values.includes(value)} disabled={purchasing} onClick={() => phase ? toggleDual(value, phase) : toggle(value + offset)} key={value}>{value}</button>)}
    </div>
  </section>;

  return <div className="ticket-composer">
    {lottery.code === "khan" ? <ClassicTicket lottery={lottery} selected={selected} purchasing={purchasing} drawCount={drawCount} onToggle={toggle} onRandomize={randomize} /> : <div className="ticket-surface">
      <header className="ticket-surface-heading"><div><span>ВАША КОМБИНАЦИЯ</span><h2>Ваш билет</h2></div><button type="button" aria-label="Случайные числа" className="ticket-shuffle" disabled={purchasing} onClick={randomize}><Icon name="spark" />Случайно</button></header>
      {dual ? <div className="ticket-dual-fields">{field("NIGHT · 00:30", 12, 2, dualNight, 0, "night")}{field("DAWN · 07:30", 12, 2, dualDawn, 12, "dawn")}</div> : grand ? <>
        {field("Основные числа", lottery.primary_max_number ?? 35, grandMainCount, mainSelected)}
        {field(lottery.code === "pss" ? "Casper Ball" : "Звёзды", lottery.secondary_max_number ?? 5, grandSpecialCount, specialSelected.map(value => value - grandOffset), grandOffset)}
      </> : field("Числа", lottery.max_number, lottery.numbers_to_pick, selected)}
      <div className="ticket-surface-footer"><span>{dual ? "Два раунда · один билет" : drawCount === 5 ? "Одна комбинация · 5 тиражей" : "Одна комбинация · 1 тираж"}</span><span>{ready ? "Готов к покупке" : `${selected.length} / ${lottery.numbers_to_pick}`}</span></div>
    </div>}
    <section className="play-quick" aria-label="Быстрая покупка"><div><strong>Быстрая покупка</strong><small>Случайные билеты</small></div><div>{[1, 5, 25].map(count => <button key={count} type="button" aria-label={`Купить ${count} ${count === 1 ? "случайный билет" : "случайных билетов"}`} disabled={purchasing || closed || count > quickLimit} onClick={() => void onBuyMany(Array.from({ length: count }, () => lotteryCombination(lottery)), drawCount)}>×{count}</button>)}</div></section>
    {!dual && <details className="ticket-options"><summary>Повторы и избранное <span>＋</span></summary><div className="ticket-options-body">
      <div className="ticket-repeat"><span>Участие в тиражах</span><div><button type="button" disabled={purchasing} aria-pressed={drawCount === 1} onClick={() => setDrawCount(1)}>1 тираж</button><button type="button" disabled={purchasing} aria-pressed={drawCount === 5} onClick={() => setDrawCount(5)}>5 тиражей</button></div></div>
      {drawCount === 5 && <p>Эти числа участвуют в текущем и следующих 4 тиражах. Полная сумма оплачивается сейчас. Без автопродления.</p>}
      <button type="button" className="ticket-save" disabled={!ready || saved || purchasing} onClick={() => onSaveFavorite(selected)}>{saved ? "Комбинация сохранена" : "Сохранить комбинацию"}</button>
      {favorites.length > 0 && <div className="ticket-favorites">{favorites.map(favorite => <div key={favorite.id}><button disabled={purchasing} type="button" onClick={() => setSelected(favorite.numbers)}>{grand ? `${favorite.numbers.filter(n => n <= grandOffset).join(" · ")} + ${favorite.numbers.filter(n => n > grandOffset).map(n => n - grandOffset).join(" · ")}` : favorite.numbers.join(" · ")}</button><button type="button" disabled={purchasing} aria-label="Удалить из избранного" onClick={() => onDeleteFavorite(favorite.id)}>×</button></div>)}</div>}
    </div></details>}
    {closed && <p className="play-message">Продажи закрыты. Ожидаем следующий тираж.</p>}
    <footer className="play-checkout"><div><small>{drawCount === 5 ? "Билет на 5 тиражей" : "Стоимость билета"}</small><strong><Money value={ticketCost * drawCount} /></strong></div><button type="button" aria-label={drawCount === 5 ? "Купить на 5 тиражей" : "Купить билет"} disabled={!ready || purchasing || closed} onClick={() => void buy()}>{purchasing ? "Оформляем…" : "Купить билет"}<span aria-hidden="true">↗</span></button></footer>
  </div>;
}
