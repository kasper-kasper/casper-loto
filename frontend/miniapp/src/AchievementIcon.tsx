import { tr } from "./i18n";
import { createElement, type ReactNode } from "react";
import { achievementGlyphs } from "./achievementGlyphs";

const paths: Record<string, ReactNode> = {
  "ticket-check": <><path d="M3 7h18v4a2 2 0 0 0 0 4v3H3v-3a2 2 0 0 0 0-4Z" /><path d="m8 12 3 3 5-5" /></>,
  tickets: <><path d="M3 9h15v3a2 2 0 0 0 0 4v3H3v-3a2 2 0 0 0 0-4ZM6 5h15v11" /></>,
  coins: <><circle cx="8" cy="8" r="5" /><path d="M8 6v4m8-4a5 5 0 0 1-2 10m5-5a5 5 0 0 1-5 10" /></>,
  wallet: <><path d="M20 8V5H6a3 3 0 0 0 0 6h15v9H6a3 3 0 0 1-3-3V8m18 5h-5v4h5" /></>,
  "trending-up": <><path d="m3 17 6-6 4 4 8-10m-6 0h6v6" /></>,
  flame: <path d="M12 3c-5 6 2 7-2 11-2-1-3-2-3-4-6 8-1 12 5 12 8-1 10-9 0-19Z" />,
  trophy: <><path d="M7 3h10v6a5 5 0 0 1-10 0Zm0 2H3v3a4 4 0 0 0 5 4m9-7h4v3a4 4 0 0 1-5 4m-4 2v6m-4 0h8" /></>,
  compass: <><circle cx="12" cy="12" r="9" /><path d="m16 8-2 6-6 2 2-6Z" /></>,
  zap: <path d="m13 2-9 12h7l-1 8 10-13h-8Z" />,
  "clock-3": <><circle cx="12" cy="12" r="9" /><path d="M12 7v5h5" /></>,
  star: <path d="m12 3 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1Z" />,
  history: <><path d="M3 11a9 9 0 1 1 2 7M3 4v7h7m2-4v6l4 2" /></>,
  "circle-dot": <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="2" /></>,
  crown: <><path d="m3 6 4 4 5-7 5 7 4-4-2 13H5ZM6 22h12" /></>,
  split: <><path d="M12 21v-6L5 8V3m7 12 7-7V3M2 6l3-3 3 3m8 0 3-3 3 3" /></>,
  "grid-3x3": <><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 3v18m6-18v18M3 9h18M3 15h18" /></>,
  "calendar-check": <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 3v4m10-4v4M3 10h18m-13 5 3 3 5-5" /></>,
  "list-ordered": <><path d="M9 5h12M9 12h12M9 19h12M3 3h1v5m-1 3h2l-2 4h2m-2 3h2v4H3" /></>,
  "shopping-bag": <><rect x="4" y="7" width="16" height="14" rx="2" /><path d="M8 7V5a4 4 0 0 1 8 0v2" /></>,
  gift: <><rect x="3" y="8" width="18" height="4" rx="1" /><path d="M5 12v9h14v-9M12 8v13m0-13H8a3 3 0 1 1 3-3Zm0 0h4a3 3 0 1 0-3-3Z" /></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2" /></>,
};

export function AchievementIcon({ name = "trophy" }: { name?: string }) {
  const glyph = achievementGlyphs[name];
  return <svg aria-hidden="true" data-glyph={glyph || paths[name] ? name : "trophy"} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{tr(glyph ? glyph.map(([tag, attributes], index) => createElement(tag, { ...attributes, key: index })) : paths[name] ?? paths.trophy)}</svg>;
}
