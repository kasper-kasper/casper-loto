import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { Ball, C, clamp, heading, Pill, Reveal, Scene } from "./design";
export function Free() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Scene light>
      <div
        style={{
          position: "absolute",
          width: 1000,
          height: 1000,
          left: 40,
          top: 330,
          borderRadius: "50%",
          border: "2px solid #b9965b35",
          scale: interpolate(f, [0, 3 * fps], [0.8, 1.25], clamp),
        }}
      />
      <Reveal style={{ position: "absolute", top: 305, left: 88 }}>
        <h1 style={{ ...heading, fontSize: 110 }}>ЛОТО ЗА</h1>
      </Reveal>
      <Reveal
        delay={0.08}
        style={{
          position: "absolute",
          top: 495,
          left: 65,
          display: "flex",
          alignItems: "baseline",
        }}
      >
        <span
          style={{
            fontSize: 560,
            fontWeight: 800,
            lineHeight: 1,
            letterSpacing: -45,
          }}
        >
          0
        </span>
        <span style={{ fontSize: 285, fontWeight: 600, marginLeft: 38 }}>
          ₽
        </span>
      </Reveal>
      <Reveal
        delay={0.38}
        style={{ position: "absolute", left: 88, top: 1120 }}
      >
        <Pill
          dark
          style={{ fontSize: 58, padding: "24px 40px", rotate: "-3deg" }}
        >
          БЕСПЛАТНО
        </Pill>
      </Reveal>
      <Reveal
        delay={0.65}
        style={{
          position: "absolute",
          left: 88,
          top: 1290,
          fontSize: 66,
          fontWeight: 800,
          lineHeight: 1.15,
          letterSpacing: -2,
        }}
      >
        БЕЗ ВЛОЖЕНИЙ.
        <br />
        РАДИ ИНТЕРЕСА.
      </Reveal>
      <Ball number="✦" size={178} x={792} y={1280} delay={0.55} tilt={20} />
      <Reveal
        delay={0.85}
        style={{
          position: "absolute",
          left: 88,
          top: 1540,
          fontSize: 32,
          fontWeight: 600,
          color: "#5b5346",
        }}
      >
        Игра на виртуальные CAS
      </Reveal>
      <div
        style={{
          position: "absolute",
          right: 0,
          width: interpolate(f, [2.84 * fps, 3 * fps], [0, 1080], clamp),
          height: "100%",
          background: C.navy,
        }}
      />
    </Scene>
  );
}
