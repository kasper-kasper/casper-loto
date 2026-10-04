import { useState } from "react";
import { Money } from "./components";
import { formatCas, formatMoscow } from "./format";
import type { Lottery } from "./types";
import grand from "./assets/lotteries/kasper-grand-scene.webp";
import classic from "./assets/lotteries/classic-drum-v1.webp";
import september from "./assets/lotteries/september-embankment.jpg";
import portal from "./assets/lotteries/pll-portal.jpg";
import nature from "./assets/lotteries/pss-nature-scene.webp";
import grob from "./assets/lotteries/grob-scene.webp";
import dual from "./assets/lotteries/casper-dual-scene.webp";
import bingo from "./assets/lotteries/bingo-edition-v1.webp";
import "./lottery-catalog.css";

const identities: Record<string, { image: string; caption: string }> = {
  weekly: { image: grand, caption: "Событие недели" },
  khan: { image: classic, caption: "Ваши числа. Большая классика." },
  september: { image: september, caption: "У каждого числа своя история" },
  pll: { image: portal, caption: "Время неизбежно" },
  pss: { image: nature, caption: "Там, где начинается тишина" },
  grob: { image: grob, caption: "Тишина. Тираж начинается." },
  dual: { image: dual, caption: "NIGHT / DAWN" },
  bingo: { image: bingo, caption: "Ваш билет в вечернюю игру" },
};

export function LotteryCatalog({ lotteries, onOpen }: { lotteries: Lottery[]; onOpen: (code: string) => void }) {
  const [filter, setFilter] = useState("all");
  const largest = Math.max(0, ...lotteries.map(lottery => lottery.jackpot));
  const visible = [...lotteries].filter(lottery => filter === "all" || lottery.kind === filter).sort((a, b) => b.jackpot - a.jackpot);

  return <section className="lottery-collection">
    <header className="collection-heading"><span>CASPER / КОЛЛЕКЦИЯ</span><h1>Лотереи<span>{lotteries.length.toString().padStart(2, "0")}</span></h1></header>
    <nav className="collection-filters" aria-label="Каталог лотерей">
      {[["all", "Все"], ["DAILY", "Каждый день"], ["WEEKLY", "Раз в неделю"]].map(([id, label]) => <button key={id} type="button" aria-pressed={filter === id} onClick={() => setFilter(id)}>{label}</button>)}
    </nav>
    <div className="collection-list" aria-label="Витрина лотерей">
      {visible.map((lottery, index) => {
        const identity = identities[lottery.code];
        return <button className={`collection-card collection-${lottery.code}`} key={lottery.code} type="button" onClick={() => onOpen(lottery.code)} aria-label={`Открыть ${lottery.name}`}>
          {identity && <img className="collection-scene" src={identity.image} alt="" width="1536" height="1024" loading={index === 0 ? "eager" : "lazy"} decoding="async" />}
          <div className="collection-card-content">
            <div className="collection-card-meta"><span>{lottery.kind === "WEEKLY" ? "Еженедельная" : "Ежедневная"}</span>{lottery.jackpot > 0 && lottery.jackpot === largest && <span className="collection-highlight">Главный джекпот</span>}</div>
            <div className="collection-identity"><h2>{lottery.name}</h2>{identity && <p>{identity.caption}</p>}</div>
            <div className="collection-prize"><small>Джекпот</small><strong title={formatCas(lottery.jackpot)}><Money value={lottery.jackpot} compact /></strong></div>
            <div className="collection-card-footer"><div className="collection-details"><time dateTime={lottery.scheduled_at ?? undefined}>{lottery.scheduled_at ? `${formatMoscow(lottery.scheduled_at)} МСК` : "Расписание внутри"}</time><span>{lottery.ticket_price === null ? "Цена скоро" : <>Билет <Money value={lottery.ticket_price} /></>}</span></div><span className="collection-open">Открыть <span aria-hidden="true">↗</span></span></div>
          </div>
        </button>;
      })}
      {visible.length === 0 && <p className="collection-empty">В этой категории пока нет лотерей.</p>}
    </div>
    {filter === "all" && <button className="collection-instant" type="button" onClick={() => onOpen("kasper-live")} aria-label="Открыть Casper LIVE"><span className="collection-live-mark" aria-hidden="true">LIVE</span><span><strong>Casper LIVE</strong><small>Мгновенный результат · билет <Money value={2_000} /></small></span><span aria-hidden="true">↗</span></button>}
  </section>;
}
