import { useId } from "react";

export type DimensionalIconName = "home" | "catalog" | "fast" | "profile" | "ticket" | "history" | "bell" | "settings";

/** Small vector solids: fixed geometry and lighting, no WebGL startup or texture downloads. */
export function DimensionalIcon({ name }: { name: DimensionalIconName }) {
  const id = useId().replace(/:/g, "");
  const front = `url(#${id}-front)`;
  const metal = `url(#${id}-metal)`;
  const warm = name === "fast";
  return <svg className={`dimensional-icon dimensional-${name}`} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id={`${id}-front`} x1="0" y1="0" x2=".85" y2="1" gradientUnits="objectBoundingBox"><stop stopColor={warm ? "#ffd4c9" : "#f5e9c9"} /><stop offset=".45" stopColor={warm ? "#ec877f" : "#d9bd80"} /><stop offset="1" stopColor={warm ? "#a33b58" : "#9b7742"} /></linearGradient>
      <linearGradient id={`${id}-metal`} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#cfdef1" /><stop offset=".45" stopColor="#8da8d1" /><stop offset="1" stopColor="#344d77" /></linearGradient>
    </defs>
    <ellipse cx="25" cy="42" rx="15" ry="3" fill="#12223b" opacity=".16" />
    {name === "home" && <><path d="M9 23 25 10 40 22v16l-16 6-15-7Z" fill="#5a472f" /><path d="M8 21 23 8l15 13v16l-15 5-15-6Z" fill={front} stroke="#f9ebcf" strokeWidth=".7" /><path d="m5 21 18-16 18 14-3 5L23 12 9 25Z" fill={metal} stroke="#d5e1f2" strokeWidth=".8" /><path d="M19 40V27l8-1v14" fill="#243b5d" /><path d="M12 29v-4l4-1v5" fill="#fff6df" opacity=".8" /></>}
    {(name === "catalog" || name === "ticket") && <><g transform="translate(2 3) rotate(-13 24 24)"><rect x="10" y="9" width="28" height="33" rx="5" fill="#233b60" /><rect x="7" y="6" width="28" height="33" rx="5" fill={metal} stroke="#dae5f2" strokeWidth=".7" /></g><g transform="rotate(9 24 24)"><path d="M12 12h23a3 3 0 0 1 3 3v6a4 4 0 0 0 0 8v9a3 3 0 0 1-3 3H12a3 3 0 0 1-3-3V15a3 3 0 0 1 3-3" fill="#785d39" /><path d="M11 9h23a3 3 0 0 1 3 3v6a4 4 0 0 0 0 8v9a3 3 0 0 1-3 3H11a3 3 0 0 1-3-3V12a3 3 0 0 1 3-3" fill={front} stroke="#fff0ce" strokeWidth=".8" /><path d="M15 16h14M15 21h8M13 29h18" stroke="#795e38" strokeWidth="1.7" strokeLinecap="round" opacity=".65" /><path d="M13 32h18" stroke="#fff5d8" strokeWidth="1" opacity=".7" /></g></>}
    {name === "fast" && <><path d="m29 5-18 22h12l-3 18 20-26H27Z" fill="#743047" /><path d="m25 3-17 22h12l-3 17 20-26H24Z" fill={front} stroke="#ffe1d4" strokeWidth="1" /><path d="m25 3-5 15h10" stroke="#fff2e9" strokeWidth="1.5" fill="none" opacity=".75" /></>}
    {name === "profile" && <><circle cx="26" cy="25" r="18" fill="#314866" /><circle cx="23" cy="22" r="18" fill={metal} stroke="#e0e9f6" strokeWidth=".7" /><circle cx="23" cy="17" r="6" fill={front} stroke="#ffeccb" strokeWidth=".6" /><path d="M12 33c0-7 5-10 11-10s11 3 11 10c-5 4-17 4-22 0" fill={front} stroke="#f6e4c0" strokeWidth=".6" /></>}
    {name === "history" && <><circle cx="26" cy="25" r="18" fill="#3f5066" /><circle cx="23" cy="22" r="18" fill={metal} stroke="#dae5f3" strokeWidth=".8" /><circle cx="23" cy="22" r="13" fill="#20354e" /><path d="M23 12v11l8 4" stroke="#edd8a4" strokeWidth="3" fill="none" strokeLinecap="round" /><circle cx="23" cy="23" r="2.2" fill="#fff1cf" /></>}
    {name === "bell" && <><path d="M14 34h25l-4-8V17c0-14-20-14-20 0v9l-4 8h3" fill="#8c663e" /><path d="M11 31h25l-4-8V15c0-13-19-13-19 0v8l-4 8Z" fill={front} stroke="#fff0c8" strokeWidth=".8" /><path d="M18 35c1 7 10 7 11 0" fill={metal} /><path d="M17 15c0-5 3-7 6-7" stroke="#fff6db" strokeWidth="2" fill="none" opacity=".7" /></>}
    {name === "settings" && <><path d="m24 4 6 4 7 1 2 8 5 6-5 6-2 8-7 1-6 5-6-5-7-1-2-8-5-6 5-6 2-8 7-1Z" fill="#344b6b" transform="translate(1 2)" /><path d="m23 3 6 4 7 1 2 8 5 6-5 6-2 8-7 1-6 5-6-5-7-1-2-8-5-6 5-6 2-8 7-1Z" fill={metal} stroke="#dce8f7" strokeWidth=".8" /><circle cx="23" cy="22" r="8" fill="#243d5e" stroke="#e0ca9b" strokeWidth="3" /></>}
  </svg>;
}
