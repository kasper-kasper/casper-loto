import { tr } from "./i18n";
import { useLayoutEffect, useState } from "react";
import { Money } from "./components";
import { NewYearTitle } from "./NewYear";
import { formatCas, formatMoscow, formatMoscowTime } from "./format";
import type { Lottery } from "./types";
import vault from "./assets/lotteries/vault-treasury-v1.webp";
import aurora from "./assets/lotteries/aurora-crystal-v1.webp";
import grand from "./assets/lotteries/grand-hall-v1.webp";
import classic from "./assets/lotteries/classic-drum-v1.webp";
import mini from "./assets/lotteries/mini-clover.svg";
import september from "./assets/lotteries/september-embankment.jpg";
import portal from "./assets/lotteries/pll-portal.jpg";
import nature from "./assets/lotteries/pss-nature-scene.webp";
import grob from "./assets/lotteries/halloween-pumpkins-v1.webp";
import { HalloweenBrand } from "./HalloweenBrand";
import "./halloween.css";
import dual from "./assets/lotteries/casper-dual-scene.webp";
import bingo from "./assets/lotteries/bingo-edition-v1.webp";
import flash from "./assets/lotteries/fast-flash-device-v1.webp";
import pulse from "./assets/lotteries/fast-pulse-device-v1.webp";
import code from "./assets/lotteries/fast-code-device-v1.webp";
import "./lottery-catalog.css";

const newYearScene = new URL("./assets/newyear/preview.webp", import.meta.url).href;

const identities: Record<string, { image: string; label: string }> = {
  vault: { image: vault, label: "Золотой сейф" },
  aurora: { image: aurora, label: "Кристалл сияния" },
  weekly: { image: grand, label: "Раз в неделю" },
  khan: { image: classic, label: "Классика" },
  mini: { image: mini, label: "Классика" },
  newyear2027: { image: newYearScene, label: "Праздничная" },
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
const order = ["newyear2027", "kasper-live", "aurora", "vault", "khan", "mini", "bingo", "dual", "weekly", "pll", "pss", "september", "grob", "flash", "pulse", "shadow"];
const filters = [["all", "Все"], ["instant", "Моментальные"], ["draw", "Тиражные"], ["holiday", "Праздничные"]] as const;
export type CatalogFilter = typeof filters[number][0];

function drawTime(lottery: Lottery, now: number): string {
  if (!lottery.scheduled_at) return tr("Расписание внутри");
  const remaining = new Date(lottery.scheduled_at).getTime() - now;
  if (remaining <= 0) return lottery.sales_status === "COMPLETED" ? tr("Результаты внутри") : lottery.sales_status === "DRAWING" ? tr("Розыгрыш идёт") : tr("Обновляем тираж");
  if (remaining < 60 * 60 * 1000) return tr("Через {0} мин", Math.max(1, Math.ceil(remaining / 60000)));
  const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Moscow" });
  if (today.format(new Date(now)) === today.format(new Date(lottery.scheduled_at))) return tr("Сегодня, {0}", formatMoscowTime(lottery.scheduled_at));
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
  const visible = lotteries.filter(lottery => lottery.code !== "kasper-live" && (filter === "all" || filter === "draw" || (filter === "holiday" && ["grob", "newyear2027"].includes(lottery.code))));
  const entries: (Lottery | string)[] = filter === "all" || filter === "instant" ? ["kasper-live", "aurora", "vault", ...visible] : visible;
  const entryCode = (e: Lottery | string) => typeof e === "string" ? e : e.code;
  const rank = (code: string) => order.includes(code) ? order.indexOf(code) : order.length;
  entries.sort((a, b) => rank(entryCode(a)) - rank(entryCode(b)) || entryCode(a).localeCompare(entryCode(b)));

  return <section className="lottery-collection">
    <header className="collection-heading"><div><h1>{tr("Лотереи")}</h1><p>{tr("Выберите свою игру")}</p></div><span className="collection-count" aria-label={tr("{0} игр", lotteries.filter(item => item.code !== "kasper-live").length + 3)}>{lotteries.filter(item => item.code !== "kasper-live").length + 3}<small>{tr("игр")}</small></span></header>
    <nav className="collection-filters" aria-label={tr("Каталог лотерей")}>
      {filters.map(([id, label]) => <button key={id} type="button" aria-pressed={filter === id} onClick={() => { setFilter(id);onFilterChange?.(id); }}>{tr(label)}</button>)}
    </nav>
    <div className="collection-list" aria-label={tr("Витрина лотерей")}>
      {entries.map((entry, index) => {
        const lottery = typeof entry === "string" ? null : entry;
        const code = entryCode(entry);
        const name = lottery?.name ?? (code === "vault" ? "Casper Vault" : code === "aurora" ? "Casper Aurora" : "Casper LIVE");
        const identity = identities[code];
        const image = identity?.image ?? (lottery ? undefined : "/assets/casper-live-casino-v1.webp");
        return <button className={`collection-card collection-${code}`} key={code} type="button" onClick={() => onOpen(code)} aria-label={tr("Открыть {0}", tr(name))}>
          <div className="collection-art" aria-hidden="true">
            {image ? <img className="collection-scene" src={image} alt="" width="600" height="400" loading={index < 4 ? "eager" : "lazy"} decoding="async" /> : <span className="collection-art-fallback">✦</span>}
            <span className="collection-tag">{tr(identity?.label ?? (lottery ? tr("Тиражная") : tr("Сотрите билет")))}</span><span className="collection-art-arrow">↗</span>
          </div>
          <div className="collection-card-content">
            <h2 aria-label={tr(name)}>{tr(code === "grob" ? <HalloweenBrand /> : code === "newyear2027" ? <NewYearTitle /> : name)}</h2>
            <div className="collection-prize">{lottery?.code === "newyear2027" ? <small>{tr("3 символа из 12")}</small> : lottery ? <><small>{lottery.code === "dual" ? tr("Максимальный выигрыш") : tr("Джекпот")}</small><strong title={tr(formatCas(lottery.jackpot))}><Money value={lottery.jackpot} compact /></strong></> : <><small>{tr("Моментальная игра")}</small><strong className="collection-instant-prize">{code === "vault" ? tr("До 5 млн") : code === "aurora" ? tr("До 1 млн") : tr("Выигрыш по символам")}</strong></>}</div>
            <div className="collection-price">{lottery?.ticket_price === null ? tr("Цена скоро") : <>{tr("Билет")} <Money value={lottery?.ticket_price ?? (code === "vault" ? 30_000 : code === "aurora" ? 3_000 : 2_000)} compact /></>}</div>
            <div className="collection-time"><span aria-hidden="true">{lottery ? "◷" : "ϟ"}</span>{lottery ? <time dateTime={lottery.scheduled_at ?? undefined} title={tr(lottery.scheduled_at ? tr("{0} МСК", formatMoscow(lottery.scheduled_at)) : undefined)}>{tr(drawTime(lottery, now))}</time> : <span>{tr("Результат сразу")}</span>}</div>
          </div>
        </button>;
      })}
      {entries.length === 0 && <p className="collection-empty">{tr("В этой категории пока нет лотерей.")}</p>}
    </div>
    <p className="collection-footnote">{filter === "holiday" ? tr("Праздничное настроение — круглый год") : tr("Время розыгрышей указано по Москве")}</p>
  </section>;
}
