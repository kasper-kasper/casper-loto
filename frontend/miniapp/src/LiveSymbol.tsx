import { tr } from "./i18n";
import { useId } from "react";
import { logoSymbol } from "./brand";
import { liveSymbolDefinitions } from "./liveSymbols";
import "./live-symbols.css";

export function LiveSymbol({ value }: { value: number }) {
  const gradientId = useId();
  const definition = liveSymbolDefinitions.find(symbol => symbol.id === value);
  const material = definition?.material ?? "gold";
  const colors: Record<string, string[]> = {
    bronze: ["#ffe6b5", "#ce9655", "#825025"],
    silver: ["#ffffff", "#c7d7e3", "#647e96"],
    gold: ["#fff6d0", "#efc666", "#a56a22"],
    ruby: ["#ffc9d3", "#ed5773", "#861a3f"],
    diamond: ["#ffffff", "#afe5ff", "#568eaf"],
    signature: ["#fff4bb", "#edc365", "#a25f18"],
  };
  const palette = colors[material];
  const shapes = [
    <><path d="M13 10h12v20a7 7 0 0 0 14 0V10h12v21a19 19 0 0 1-38 0Z" /><path className="live-symbol-cut" d="M19 17v4m0 9v4m26-17v4m0 9v4" /></>,
    <><path d="M32 32C8 32 6 15 19 12c8-2 13 5 13 12 0-7 5-14 13-12 13 3 11 20-13 20 24-2 27 17 13 20-7 1-13-6-13-12 0 6-6 13-13 12C5 49 8 30 32 32Z" /><path d="m29 40-4 18h14l-4-18Z" /><path className="live-symbol-cut" d="m20 21 12 11 12-11M20 44l12-12 12 12" /></>,
    <><circle cx="32" cy="32" r="24" /><circle className="live-symbol-cut" cx="32" cy="32" r="18" /><path className="live-symbol-cut" d="M39 23a12 12 0 1 0 0 18" /><circle cx="32" cy="32" r="4" /></>,
    <><path d="m32 7 7 16 18 2-14 12 4 18-15-9-15 9 4-18L7 25l18-2Z" /><path className="live-symbol-cut" d="M32 7v25L7 25m25 7 25-7M32 32l15 23M32 32 17 55" /></>,
    <><path d="m32 7 21 12 5 23-26 16L6 42l5-23Z" /><path className="live-symbol-cut" d="m11 19 21 8 21-8M6 42l26-15 26 15M32 7v20l-8 18 8 13 8-13-8-18M6 42l18 3h16l18-3" /><path className="live-symbol-glint" d="m14 21 8 3-10 11Z" /></>,
    <><path d="m19 11-13 16 26 31 26-31-13-16Z" /><path className="live-symbol-cut" d="M6 27h52M19 11l-1 16 14 31 14-31-1-16M32 11 18 27h28Z" /><path className="live-symbol-glint" d="m20 14-9 10h13l8-10Z" /></>,
    <><circle cx="32" cy="32" r="27" /><circle className="live-symbol-cut" cx="32" cy="32" r="23" /><circle fill="#672034" stroke="#ffe4a6" cx="32" cy="32" r="20" /><image href={logoSymbol} x="13" y="13" width="38" height="38" /><path className="live-symbol-glint" d="m11 12 2-5 2 5 5 2-5 2-2 5-2-5-5-2Z" /></>,
    <path d="M14 11h39v9L34 55H20l20-33H14Z" />,
  ];
  return <svg className={`live-symbol live-symbol-${material}`} viewBox="0 0 64 64" role="img" aria-label={tr(definition?.name ?? tr("Символ"))}>
    <defs><linearGradient id={gradientId} x2=".8" y2="1"><stop stopColor={palette[0]} /><stop offset=".45" stopColor={palette[1]} /><stop offset="1" stopColor={palette[2]} /></linearGradient></defs>
    <g fill={`url(#${gradientId})`} stroke={palette[0]} strokeWidth="1.2" strokeLinejoin="round">{shapes[value - 1] ?? shapes[0]}</g>
  </svg>;
}
