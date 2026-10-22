import { tr } from "./i18n";
import type { CSSProperties } from "react";
import scene from "./assets/lotteries/grand-hall-v1.webp";
import "./grand-hall.css";

export function GrandDrawScene({ active, revealed }: { active: boolean; revealed: number[] }) {
  return <div className={`grand-live-theatre ${active ? "is-active" : ""}`} aria-label={tr("Большой зал Casper Grand")}><img src={scene} alt="" /><div className="grand-machines" aria-hidden="true">{[0,1].map(field => <div className={`grand-machine ${field ? "golden" : ""}`} key={field}><div className="grand-globe"><div className="grand-orbit">{Array.from({ length: field ? 5 : 9 }, (_, i) => <i key={i} style={{ "--angle": `${i * 40}deg`, "--depth": `${(i % 3 - 1) * 16}px` } as CSSProperties} />)}</div><b /><b /><b /></div><div className="grand-machine-base" /></div>)}</div><div className="grand-live-rack">{Array.from({ length: 7 },(_,i) => <span className={i>4 ? "golden" : ""} key={i}>{tr(revealed[i] !== undefined ? (revealed[i]>35 ? revealed[i]-35 : revealed[i]) : "·")}</span>)}</div><small>{active ? (revealed.length>5 ? tr("ЗОЛОТЫЕ ШАРЫ") : tr("ОСНОВНОЕ ПОЛЕ")) : tr("ВОСКРЕСНЫЙ БОЛЬШОЙ ТИРАЖ")}</small></div>;
}
