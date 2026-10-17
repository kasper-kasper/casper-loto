import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import {
  Atmosphere,
  Brand,
  C,
  clamp,
  heading,
  Phone,
  Reveal,
  Scene,
} from "./design";
export function Choose() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = Math.max(0, Math.min(6, Math.floor((f / fps - 0.7) / 0.37) + 1));
  const positions = [
    [61, 326],
    [354, 326],
    [61, 414],
    [295, 414],
    [61, 502],
    [354, 502],
  ];
  const point = positions[Math.max(0, n - 1)];
  const tap = (f / fps - 0.7) % 0.37;
  return (
    <Scene>
      <Atmosphere />
      <Brand top={120} width={310} />
      <div style={{ position: "absolute", left: 88, top: 265 }}>
        <Reveal>
          <h1 style={{ ...heading, fontSize: 96 }}>ВЫБЕРИ</h1>
        </Reveal>
        <Reveal delay={0.12}>
          <h1 style={{ ...heading, fontSize: 96, color: C.gold }}>
            СВОИ ЧИСЛА
          </h1>
        </Reveal>
      </div>
      <Phone
        src={n ? `picker-${n}.png` : "picker.png"}
        top={535}
        left={260}
        width={510}
        tilt={-3 + Math.sin(f / 45) * 1.4}
      >
        {n > 0 && f / fps < 2.95 && (
          <div
            style={{
              position: "absolute",
              left: (point[0] / 430) * 100 + "%",
              top: (point[1] / 880) * 100 + "%",
              width: 50,
              height: 50,
              marginLeft: -25,
              marginTop: -25,
              border: "3px solid #ffe0a1",
              background: "#ffd78633",
              borderRadius: "50%",
              scale: 1 + tap * 3,
              opacity: interpolate(tap, [0, 0.37], [0.95, 0], clamp),
            }}
          />
        )}
      </Phone>
      <Reveal
        delay={0.5}
        style={{
          position: "absolute",
          left: 82,
          top: 1260,
          rotate: "-8deg",
          padding: "20px 30px",
          background: C.gold,
          color: C.navy,
          borderRadius: 20,
          fontSize: 42,
          fontWeight: 800,
          boxShadow: "0 15px 40px #0006",
        }}
      >
        ТВОЯ КОМБИНАЦИЯ ↗
      </Reveal>
      <div
        style={{
          position: "absolute",
          left: 88,
          top: 1630,
          fontSize: 27,
          color: "#c2baa8",
        }}
      >
        Демо интерфейса · CAS — игровые единицы
      </div>
    </Scene>
  );
}
