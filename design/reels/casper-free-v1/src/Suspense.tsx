import { Atmosphere, Ball, Brand, C, heading, Reveal, Scene } from "./design";
export function Suspense() {
  return (
    <Scene>
      <Atmosphere art />
      <Brand top={120} width={310} />
      <div style={{ position: "absolute", left: 88, top: 300 }}>
        <Reveal>
          <h1 style={{ ...heading, fontSize: 106 }}>А ВДРУГ</h1>
        </Reveal>
        <Reveal delay={0.15}>
          <h1 style={{ ...heading, fontSize: 106, color: C.gold }}>
            СОВПАДЁТ?
          </h1>
        </Reveal>
      </div>
      <Ball
        number="04"
        x={110}
        y={720}
        size={230}
        delay={0.25}
        ivory
        tilt={-10}
      />
      <Ball number="12" x={403} y={690} size={230} delay={0.6} tilt={4} />
      <Ball
        number="19"
        x={695}
        y={750}
        size={230}
        delay={0.95}
        ivory
        tilt={12}
      />
      <Ball number="27" x={135} y={1045} size={230} delay={1.3} tilt={-8} />
      <Ball
        number="31"
        x={425}
        y={1015}
        size={230}
        delay={1.65}
        ivory
        tilt={3}
      />
      <Ball number="36" x={715} y={1070} size={230} delay={2} tilt={14} />
      <Reveal
        delay={2.45}
        style={{
          position: "absolute",
          left: 88,
          top: 1430,
          fontSize: 56,
          lineHeight: 1.18,
          fontWeight: 700,
        }}
      >
        Каждый раз —<br />
        <span style={{ color: C.gold }}>новая интрига.</span>
      </Reveal>
    </Scene>
  );
}
