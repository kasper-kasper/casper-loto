import { useLayoutEffect, useState } from "react";
import { Money } from "./components";
import { formatCas, formatMoscow, formatMoscowTime } from "./format";
import type { Lottery } from "./types";
import grand from "./assets/lotteries/kasper-grand-scene.webp";
import classic from "./assets/lotteries/classic-drum-v1.webp";
import september from "./assets/lotteries/september-embankment.jpg";
import portal from "./assets/lotteries/pll-portal.jpg";
import nature from "./assets/lotteries/pss-nature-scene.webp";
import grob from "./assets/lotteries/grob-scene.webp";
import dual from "./assets/lotteries/casper-dual-scene.webp";
import bingo from "./assets/lotteries/bingo-edition-v1.webp";
import flash from "./assets/lotteries/fast-flash-device-v1.webp";
import pulse from "./assets/lotteries/fast-pulse-device-v1.webp";
import code from "./assets/lotteries/fast-code-device-v1.webp";
import "./lottery-catalog.css";

const identities: Record<string, { image: string; label: string }> = {
  weekly: { image: grand, label: "Раз в неделю" },
  khan: { image: classic, label: "Классика" },
  september: { image: september, label: "3 СЕНТЯБРЯ" },
  pll: { image: portal, label: "2:22" },
  pss: { image: nature, label: "Выберите числа" },
  grob: { image: grob, label: "Праздничная" },
  dual: { image: dual, label: "NIGHT / DAWN" },
  bingo: { image: bingo, label: "Готовый билет" },
  flash: { image: flash, label: "FLASH" },
  pulse: { image: pulse, label: "PULSE" },
  shadow: { image: code, label: "CODE" },
};
const order = ["kasper-live", "khan", "bingo", "dual", "weekly", "pll", "pss", "september", "grob", "flash", "pulse", "shadow"];
const filters = [["all", "Все"], ["instant", "Моментальные"], ["draw", "Тиражные"], ["holiday", "Праздничные"]] as const;
export type CatalogFilter = typeof filters[number][0];

function drawTime(lottery: Lottery, now: number): string {
  if (!lottery.scheduled_at) return "Расписание внутри";
  const remaining = new Date(lottery.scheduled_at).getTime() - now;
  if (remaining <= 0) return lottery.sales_status === "COMPLETED" ? "Результаты внутри" : lottery.sales_status === "DRAWING" ? "Розыгрыш идёт" : "Обновляем тираж";
  if (remaining < 60 * 60 * 1000) return `Через ${Math.max(1, Math.ceil(remaining / 60000))} мин`;
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Moscow" });
  if (today.format(new Date(now)) === today.format(new Date(lottery.scheduled_at))) return `Сегодня, ${formatMoscowTime(lottery.scheduled_at)}`;
  return formatMoscow(lottery.scheduled_at);
}

export function LotteryCatalog({ lotteries, onOpen, now, selectedFilter, onFilterChange, restoreScroll = 0 }: { lotteries: Lottery[]; onOpen: (code: string) => void; now: number; selectedFilter?: CatalogFilter; onFilterChange?: (filter: CatalogFilter) => void; restoreScroll?: number }) {
  const [localFilter, setFilter] = useState<CatalogFilter>("all");
  const filter = selectedFilter ?? localFilter;
  useLayoutEffect(() => {
    // The lazy catalogue must exist before restoring its scrollable height.
    const frame = window.requestAnimationFrame(() => { if (restoreScroll > 0) window.scrollTo({ top: restoreScroll, behavior: "instant" }); });
    return () => window.cancelAnimationFrame(frame);
  }, [restoreScroll]);
  const visible = lotteries.filter(lottery => lottery.code !== "kasper-live" && (filter === "all" || filter === "draw" || (filter === "holiday" && lottery.code === "grob")));
  const entries: (Lottery | null)[] = filter === "all" || filter === "instant" ? [null, ...visible] : visible;
  const rank = (code: string) => order.includes(code) ? order.indexOf(code) : order.length;
  entries.sort((a, b) => rank(a?.code ?? "kasper-live") - rank(b?.code ?? "kasper-live") || (a?.code ?? "").localeCompare(b?.code ?? ""));

  return <section className="lottery-collection">
    <header className="collection-heading"><div><h1>Лотереи</h1><p>Выберите свою игру</p></div><span className="collection-count" aria-label={`${lotteries.filter(item => item.code !== "kasper-live").length + 1} игр`}>{lotteries.filter(item => item.code !== "kasper-live").length + 1}<small>игр</small></span></header>
    <nav className="collection-filters" aria-label="Каталог лотерей">
      {filters.map(([id, label]) => <button key={id} type="button" aria-pressed={filter === id} onClick={() => { setFilter(id);onFilterChange?.(id); }}>{label}</button>)}
    </nav>
    <div className="collection-list" aria-label="Витрина лотерей">
      {entries.map((lottery, index) => {
        const code = lottery?.code ?? "kasper-live";
        const name = lottery?.name ?? "Casper LIVE";
        const identity = identities[code];
        const image = identity?.image ?? (lottery ? undefined : "/assets/casper-live-casino-v1.webp");
        return <button className={`collection-card collection-${code}`} key={code} type="button" onClick={() => onOpen(code)} aria-label={`Открыть ${name}`}>
          <div className="collection-art" aria-hidden="true">
            {image ? <img className="collection-scene" src={image} alt="" width="600" height="400" loading={index < 4 ? "eager" : "lazy"} decoding="async" /> : <span className="collection-art-fallback">✦</span>}
            <span className="collection-tag">{identity?.label ?? (lottery ? "Тиражная" : "Сотрите билет")}</span><span className="collection-art-arrow">↗</span>
          </div>
          <div className="collection-card-content">
            <h2>{name}</h2>
            <div className="collection-prize">{lottery ? <><small>Джекпот</small><strong title={formatCas(lottery.jackpot)}><Money value={lottery.jackpot} compact /></strong></> : <><small>Моментальная игра</small><strong className="collection-instant-prize">Выигрыш по символам</strong></>}</div>
            <div className="collection-price">{lottery?.ticket_price === null ? "Цена скоро" : <>Билет <Money value={lottery?.ticket_price ?? 2_000} compact /></>}</div>
            <div className="collection-time"><span aria-hidden="true">{lottery ? "◷" : "ϟ"}</span>{lottery ? <time dateTime={lottery.scheduled_at ?? undefined} title={lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : undefined}>{drawTime(lottery, now)}</time> : <span>Результат сразу</span>}</div>
          </div>
        </button>;
      })}
      {entries.length === 0 && <p className="collection-empty">В этой категории пока нет лотерей.</p>}
    </div>
    <p className="collection-footnote">{filter === "holiday" ? "Праздничное настроение — круглый год" : "Время розыгрышей указано по Москве"}</p>
  </section>;
}
