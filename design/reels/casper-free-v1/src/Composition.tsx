import { Audio } from "@remotion/media";
import { AbsoluteFill, Series, staticFile, useVideoConfig } from "remotion";
import { Hook } from "./Hook";
import { Free } from "./Free";
import { Choose } from "./Choose";
import { Discover } from "./Discover";
import { Suspense } from "./Suspense";
import { Finale } from "./Finale";
export const CasperReel = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      <Audio
        src={staticFile("casper-original.wav")}
        volume={0.85}
        premountFor={fps}
      />
      <Series>
        <Series.Sequence
          name="01 — А что, если?"
          durationInFrames={3 * fps}
          premountFor={fps}
        >
          <Hook />
        </Series.Sequence>
        <Series.Sequence
          name="02 — Бесплатно"
          durationInFrames={3 * fps}
          premountFor={fps}
        >
          <Free />
        </Series.Sequence>
        <Series.Sequence
          name="03 — Выбор чисел"
          durationInFrames={4 * fps}
          premountFor={fps}
        >
          <Choose />
        </Series.Sequence>
        <Series.Sequence
          name="04 — Твоя игра"
          durationInFrames={4 * fps}
          premountFor={fps}
        >
          <Discover />
        </Series.Sequence>
        <Series.Sequence
          name="05 — Интрига"
          durationInFrames={4 * fps}
          premountFor={fps}
        >
          <Suspense />
        </Series.Sequence>
        <Series.Sequence
          name="06 — Проверь удачу"
          durationInFrames={6 * fps}
          premountFor={fps}
        >
          <Finale />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
