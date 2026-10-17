import type { CSSProperties, ReactNode } from "react";
import {
  AbsoluteFill,
  CanvasImage,
  Easing,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/fonts";

loadFont({
  family: "Manrope",
  url: staticFile("Manrope.ttf"),
  weight: "200 800",
});
export const C = {
  navy: "#080f20",
  ivory: "#F6EDD7",
  gold: "#D4A962",
  white: "#fffaf0",
};
export const clamp = {
  extrapolateLeft: "clamp",
  extrapolateRight: "clamp",
} as const;
export const ease = Easing.bezier(0.16, 1, 0.3, 1);

export function Scene({
  children,
  light = false,
}: {
  children: ReactNode;
  light?: boolean;
}) {
  return (
    <AbsoluteFill
      style={{
        background: light ? C.ivory : C.navy,
        color: light ? C.navy : C.ivory,
        fontFamily: "Manrope, Arial, sans-serif",
        overflow: "hidden",
      }}
    >
      {children}
    </AbsoluteFill>
  );
}
export function Atmosphere({ art = false }: { art?: boolean }) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      {art && (
        <CanvasImage
          src={staticFile("orbits.webp")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity: 0.32,
            scale: interpolate(f, [0, 6 * fps], [1.06, 1.19], clamp),
          }}
        />
      )}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at 73% 50%, #88663128, transparent 57%), linear-gradient(0deg, #080f20 4%, transparent 45%, #080f20cc 100%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 1100,
          height: 1100,
          left: -10,
          top: 460,
          border: "1px solid #D4A96220",
          borderRadius: "50%",
          scale: 1 + Math.sin(f / 65) * 0.035,
        }}
      />
      {Array.from({ length: 36 }, (_, i) => (
        <i
          key={i}
          style={{
            position: "absolute",
            left: (i * 137.73) % 1080,
            top:
              (((i * 217.5 - f * (0.3 + (i % 3) * 0.17)) % 1920) + 1920) % 1920,
            width: i % 5 === 0 ? 4 : 2,
            height: i % 5 === 0 ? 4 : 2,
            background: C.gold,
            borderRadius: "50%",
            opacity: 0.16 + (0.32 * (1 + Math.sin(f / 25 + i))) / 2,
          }}
        />
      ))}
    </AbsoluteFill>
  );
}
export function Brand({
  top = 140,
  width = 340,
  center = false,
}: {
  top?: number;
  width?: number;
  center?: boolean;
}) {
  return (
    <CanvasImage
      src={staticFile("logo.png")}
      style={{
        position: "absolute",
        top,
        left: center ? (1080 - width) / 2 : 70,
        width,
      }}
    />
  );
}
export function Reveal({
  children,
  delay = 0,
  style = {},
}: {
  children: ReactNode;
  delay?: number;
  style?: CSSProperties;
}) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div
      style={{
        opacity: interpolate(f, [delay * fps, delay * fps + 7], [0, 1], clamp),
        translate: `0 ${interpolate(f, [delay * fps, delay * fps + 18], [65, 0], { ...clamp, easing: ease })}px`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
export function Ball({
  number,
  size = 230,
  x,
  y,
  delay = 0,
  ivory = false,
  tilt = 0,
}: {
  number: string;
  size?: number;
  x: number;
  y: number;
  delay?: number;
  ivory?: boolean;
  tilt?: number;
}) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({
    frame: f - delay * fps,
    fps,
    config: { damping: 17, stiffness: 135 },
  });
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: size,
        height: size,
        borderRadius: "50%",
        background: ivory
          ? "radial-gradient(circle at 32% 22%, #fffef9 0%, #f6eaca 35%, #c6ad76 65%, #6e4b27 90%)"
          : "radial-gradient(circle at 32% 22%, #fff2c8 0%, #dfb96d 26%, #ad742e 60%, #39271a 88%)",
        boxShadow: `inset -${size * 0.025}px -${size * 0.03}px ${size * 0.08}px #180e1060, inset 4px 5px 8px #fff8df80, 0 35px 65px #0006`,
        scale: p,
        translate: `0 ${Math.sin(f / 22 + x) * 10 + (1 - p) * 160}px`,
        rotate: `${tilt + Math.sin(f / 40 + x) * 5}deg`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: "59%",
          height: "59%",
          border: `2px solid ${ivory ? "#80613935" : "#fff2c838"}`,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#261b16",
          background: "#fff3d235",
          fontSize: size * 0.35,
          letterSpacing: -size * 0.025,
          fontWeight: 800,
          textShadow: "0 1px 1px #ffffff55",
        }}
      >
        {number}
      </div>
      <div
        style={{
          position: "absolute",
          width: "24%",
          height: "10%",
          left: "20%",
          top: "14%",
          background: "#fffbeaa0",
          filter: "blur(8px)",
          rotate: "-35deg",
          borderRadius: "50%",
        }}
      />
    </div>
  );
}
export function Pill({
  children,
  style = {},
  dark = false,
}: {
  children: ReactNode;
  style?: CSSProperties;
  dark?: boolean;
}) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px 34px",
        borderRadius: 99,
        background: dark ? C.navy : C.gold,
        color: dark ? C.ivory : C.navy,
        fontWeight: 800,
        fontSize: 38,
        letterSpacing: 1,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
export function Phone({
  src,
  width = 510,
  left = 270,
  top = 520,
  tilt = 0,
  children,
}: {
  src: string;
  width?: number;
  left?: number;
  top?: number;
  tilt?: number;
  children?: ReactNode;
}) {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const h = ((width - 24) / 430) * 880 + 24;
  return (
    <div
      style={{
        position: "absolute",
        left,
        top,
        width,
        height: h,
        borderRadius: 57,
        background:
          "linear-gradient(135deg, #d9d2bd, #292c34 25%, #848074 50%, #1d2027 75%, #b3a790)",
        padding: 12,
        boxSizing: "border-box",
        boxShadow: "0 70px 110px #0009, 0 0 0 2px #d7c79b50",
        rotate: `${tilt}deg`,
        scale: interpolate(f, [0, 0.65 * fps], [0.86, 1], {
          ...clamp,
          easing: ease,
        }),
        translate: `0 ${interpolate(f, [0, 0.65 * fps], [170, 0], { ...clamp, easing: ease })}px`,
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          borderRadius: 46,
          overflow: "hidden",
          position: "relative",
          background: C.navy,
        }}
      >
        <CanvasImage
          src={staticFile(src)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
        {children}
      </div>
    </div>
  );
}
export const heading: CSSProperties = {
  fontSize: 108,
  lineHeight: 1.04,
  fontWeight: 800,
  letterSpacing: -5,
  margin: 0,
};
