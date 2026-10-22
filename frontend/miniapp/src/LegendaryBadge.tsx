import { tr } from "./i18n";
import { logoSymbol } from "./brand";
import { HalloweenBrand } from "./HalloweenBrand";
import "./collection.css";
import { collectionGames } from "./collectionGames";

export function LegendaryBadge({ game, locked = false, compact = false }: { game: string; locked?: boolean; compact?: boolean }) {
  const master = game === "casper-master";
  return <span aria-hidden="true" className={`legendary-emblem${master ? " emblem-master" : ""}${locked ? " emblem-locked" : ""}${compact ? " emblem-compact" : ""}`}>
    <svg className="emblem-orbit" viewBox="0 0 100 100"><circle cx="50" cy="50" r="46" />{master && Array.from({length:10},(_,i)=>{ const a=(i*36-90)*Math.PI/180; return <circle className="emblem-star" key={i} cx={50+43*Math.cos(a)} cy={50+43*Math.sin(a)} r="2" />; })}</svg>
    <img src={logoSymbol} alt="" decoding="async" />
    {!compact && <span className="emblem-wordmark">{tr(master ? "CASPER" : game === "grob" ? <HalloweenBrand /> : collectionGames[game] ?? "Casper Loto")}</span>}
  </span>;
}
