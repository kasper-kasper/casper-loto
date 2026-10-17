import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import {
  Atmosphere,
  Brand,
  C,
  clamp,
  heading,
  Pill,
  Reveal,
  Scene,
} from "./design";
export function Finale() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Scene>
      <Atmosphere art />
      <div
        style={{ position: "absolute", inset: 0, background: "#080f2070" }}
      />
      <Brand top={180} width={620} center />
      <div style={{ position: "absolute", left: 88, top: 490 }}>
        <Reveal>
          <h1 style={{ ...heading, fontSize: 128 }}>ПРОВЕРЬ</h1>
        </Reveal>
        <Reveal delay={0.12}>
          <h1 style={{ ...heading, fontSize: 128 }}>СВОЮ</h1>
        </Reveal>
        <Reveal delay={0.24}>
          <h1 style={{ ...heading, fontSize: 158, color: C.gold }}>УДАЧУ</h1>
        </Reveal>
      </div>
      <Reveal
        delay={0.55}
        style={{ position: "absolute", left: 88, top: 1000, rotate: "-3deg" }}
      >
        <Pill style={{ fontSize: 56, padding: "23px 38px" }}>
          ЭТО БЕСПЛАТНО
        </Pill>
      </Reveal>
      <Reveal
        delay={0.85}
        style={{
          position: "absolute",
          left: 88,
          top: 1215,
          width: 800,
          height: 125,
          borderRadius: 30,
          background: C.ivory,
          color: C.navy,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 22,
          boxShadow: "0 10px 60px #d4a96220",
        }}
      >
        <svg width="54" height="54" viewBox="0 0 24 24" fill="none">
          <path
            d="m21 3-7.1 18-4.1-7-6.8-3L21 3Z"
            stroke={C.navy}
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path
            d="m9.8 14 5.7-6"
            stroke={C.navy}
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
        <span style={{ fontSize: 39, fontWeight: 800 }}>ОТКРОЙ В TELEGRAM</span>
        <span style={{ fontSize: 48, translate: `${Math.sin(f / 8) * 5}px 0` }}>
          ↗
        </span>
      </Reveal>
      <Reveal
        delay={1.1}
        style={{
          position: "absolute",
          left: 88,
          top: 1410,
          fontSize: 41,
          fontWeight: 800,
          color: C.ivory,
        }}
      >
        БЕЗ РЕАЛЬНЫХ ДЕНЕГ
      </Reveal>
      <Reveal
        delay={1.25}
        style={{
          position: "absolute",
          left: 88,
          top: 1495,
          fontSize: 30,
          color: "#d2c9b8",
          lineHeight: 1.5,
        }}
      >
        CAS — игровые единицы.
        <br />
        Без покупки и вывода за деньги.
      </Reveal>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          height: 5,
          background: C.gold,
          width: interpolate(f, [0, 6 * fps], [0, 1080], clamp),
        }}
      />
    </Scene>
  );
}
