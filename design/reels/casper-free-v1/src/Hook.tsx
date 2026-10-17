import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import {
  Atmosphere,
  Ball,
  Brand,
  C,
  clamp,
  heading,
  Pill,
  Reveal,
  Scene,
} from "./design";
export function Hook() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <Scene>
      <Atmosphere />
      <Brand />
      <div style={{ position: "absolute", left: 88, right: 120, top: 345 }}>
        <Reveal>
          <div
            style={{
              fontSize: 43,
              fontWeight: 600,
              letterSpacing: 4,
              color: C.gold,
            }}
          >
            А ЧТО, ЕСЛИ
          </div>
        </Reveal>
        <Reveal delay={0.12}>
          <h1 style={{ ...heading, fontSize: 158, marginTop: 28 }}>ТЕБЕ</h1>
        </Reveal>
        <Reveal delay={0.3}>
          <h1
            style={{ ...heading, fontSize: 132, color: C.gold, marginTop: 5 }}
          >
            ПОВЕЗЁТ?
          </h1>
        </Reveal>
      </div>
      <div
        style={{
          position: "absolute",
          top: 790,
          left: 95,
          width: 820,
          height: 530,
          border: "2px solid #D4A96245",
          borderRadius: "50%",
          rotate: "-26deg",
          scale: interpolate(f, [0, 3 * fps], [0.85, 1.1], clamp),
        }}
      />
      <Ball number="07" size={430} x={312} y={870} delay={0.1} tilt={-13} />
      <Ball
        number="23"
        size={175}
        x={78}
        y={1125}
        delay={0.22}
        ivory
        tilt={13}
      />
      <Ball
        number="36"
        size={205}
        x={786}
        y={780}
        delay={0.35}
        ivory
        tilt={-9}
      />
      <Reveal
        delay={0.75}
        style={{ position: "absolute", left: 88, top: 1460 }}
      >
        <Pill>ПРОВЕРИМ? ↗</Pill>
      </Reveal>
      <div
        style={{
          position: "absolute",
          bottom: 0,
          height: interpolate(f, [2.82 * fps, 3 * fps], [0, 1920], clamp),
          width: "100%",
          background: C.ivory,
        }}
      />
    </Scene>
  );
}
