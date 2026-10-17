import { useCurrentFrame } from "remotion";
import {
  Atmosphere,
  Ball,
  Brand,
  C,
  heading,
  Phone,
  Pill,
  Reveal,
  Scene,
} from "./design";
export function Discover() {
  const f = useCurrentFrame();
  return (
    <Scene>
      <Atmosphere />
      <Brand top={120} width={310} />
      <div style={{ position: "absolute", left: 88, top: 265 }}>
        <Reveal>
          <h1 style={{ ...heading, fontSize: 100 }}>НАЙДИ</h1>
        </Reveal>
        <Reveal delay={0.12}>
          <h1 style={{ ...heading, fontSize: 100, color: C.gold }}>
            СВОЮ ИГРУ
          </h1>
        </Reveal>
      </div>
      <Ball number="✦" size={185} x={100} y={675} delay={0.5} />
      <Phone
        src="catalog.png"
        top={540}
        left={285}
        width={490}
        tilt={5 + Math.sin(f / 50) * 1.2}
      />
      <Reveal
        delay={0.5}
        style={{ position: "absolute", left: 82, top: 935, rotate: "-6deg" }}
      >
        <Pill style={{ fontSize: 33 }}>МОМЕНТАЛЬНЫЕ</Pill>
      </Reveal>
      <Reveal
        delay={1.2}
        style={{ position: "absolute", right: 115, top: 1190, rotate: "6deg" }}
      >
        <Pill style={{ fontSize: 33, background: "#f6edd7" }}>ТИРАЖИ</Pill>
      </Reveal>
      <Reveal
        delay={1.9}
        style={{ position: "absolute", left: 88, top: 1450, rotate: "-4deg" }}
      >
        <Pill style={{ fontSize: 33, background: "#e0bb78" }}>
          БЫСТРЫЕ РАУНДЫ
        </Pill>
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
