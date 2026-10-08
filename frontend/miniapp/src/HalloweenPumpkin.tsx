/** Decorative skin only: the parent button owns its number and interaction. */
export function HalloweenPumpkin({ id }: { id: string }) {
  return <svg className="halloween-pumpkin" viewBox="0 0 100 104" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id={`${id}-skin`} x1="0" y1="0" x2="1" y2="1">
        <stop stopColor="#ffe797" /><stop offset=".26" stopColor="#ffb23b" /><stop offset=".7" stopColor="#ed6b08" /><stop offset="1" stopColor="#a43b08" />
      </linearGradient>
      <radialGradient id={`${id}-light`} cx=".46" cy=".42" r=".65">
        <stop stopColor="#fff5b3" /><stop offset=".4" stopColor="#ffdc69" /><stop offset=".78" stopColor="#ff9d25" /><stop offset="1" stopColor="#d45c0a" />
      </radialGradient>
      <linearGradient id={`${id}-stem`} x2=".8" y2="1">
        <stop stopColor="#ffe2a0" /><stop offset=".4" stopColor="#ad803e" /><stop offset="1" stopColor="#4f341a" />
      </linearGradient>
    </defs>
    <ellipse cx="50" cy="94" rx="34" ry="5" fill="#3f160e" opacity=".55" />
    <path d="M44 23c3-8 2-13 7-17l8 3c-6 5-6 9-7 16Z" fill={`url(#${id}-stem)`} stroke="#6e421c" strokeWidth="1.5" />
    <path d="M51 17c12-8 21-4 19 2-1 4-7 2-5-1" fill="none" stroke="#d6a24d" strokeWidth="2" strokeLinecap="round" />
    <path d="M50 24C25 9 6 26 6 54c0 24 14 44 34 40 7 6 14 6 21 0 20 4 33-16 33-40 0-28-20-45-44-30Z" fill={`url(#${id}-skin)`} stroke="#ffd57a" strokeWidth="2.2" />
    <path d="M37 24C17 17 12 37 13 57c1 22 11 34 23 35-12-19-11-49 1-68Z" fill="#dd5708" opacity=".55" />
    <path d="M63 24c20-7 25 13 24 33-1 22-11 34-23 35 12-19 11-49-1-68Z" fill="#c54b06" opacity=".5" />
    <ellipse cx="50" cy="58" rx="30" ry="39" fill={`url(#${id}-light)`} stroke="#ffbc4c" strokeWidth="1.5" />
    <path d="M41 22c-14 19-15 51-4 72M59 22c14 19 15 51 4 72" fill="none" stroke="#c76c15" strokeWidth="3" opacity=".62" />
    <path d="M44 23c-10 20-11 48-4 67M56 23c10 20 11 48 4 67" fill="none" stroke="#fff3ad" strokeWidth="2" opacity=".8" />
    <path d="M50 22c-4 20-4 48 0 73" fill="none" stroke="#ffed9a" strokeWidth="1.5" opacity=".6" />
    <path d="M26 30c-6 7-9 15-9 24M73 31c5 7 8 14 9 23" fill="none" stroke="#fff3b3" strokeWidth="2.5" opacity=".65" strokeLinecap="round" />
    <path d="M27 87c13 10 34 10 46 0" fill="none" stroke="#fff0a0" strokeWidth="2" opacity=".8" />
  </svg>;
}
