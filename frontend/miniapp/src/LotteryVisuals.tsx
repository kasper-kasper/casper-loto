import { useCallback, useEffect, useState } from "react";
import { motion } from "motion/react";

import khanScene from "./assets/lotteries/khan-scene.webp";
import septemberScene from "./assets/lotteries/september-embankment.jpg";
import pllScene from "./assets/lotteries/pll-portal.jpg";
import pssScene from "./assets/lotteries/pss-nature-scene.webp";
import kasperGrandScene from "./assets/lotteries/kasper-grand-scene.webp";
import grobScene from "./assets/lotteries/grob-scene.webp";
import dualScene from "./assets/lotteries/casper-dual-scene.webp";

type VisualContext = "catalog" | "hero" | "picker" | "live";

interface LotteryVisualProps {
  code: string;
  context?: VisualContext;
  animated?: boolean;
}

const draw = {
  hidden: { opacity: 0, pathLength: 0 },
  visible: { opacity: 1, pathLength: 1 },
};

function useSceneMotion(enabled: boolean) {
  const [element, setElement] = useState<Element | null>(null);
  const [active, setActive] = useState(enabled && !document.hidden);
  const captureElement = useCallback((node: Element | null) => setElement(node), []);

  useEffect(() => {
    if (!enabled || !element) return;
    const node = element;
    let inView = true;
    const syncVisibility = () => {
      setActive(inView && !document.hidden);
    };
    if (typeof IntersectionObserver === "undefined") {
      const initial = window.setTimeout(syncVisibility, 0);
      document.addEventListener("visibilitychange", syncVisibility);
      return () => {
        window.clearTimeout(initial);
        document.removeEventListener("visibilitychange", syncVisibility);
      };
    }
    const observer = new IntersectionObserver(([entry]) => {
      inView = entry.isIntersecting;
      syncVisibility();
    }, { rootMargin: "120px 0px" });
    observer.observe(node);
    document.addEventListener("visibilitychange", syncVisibility);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", syncVisibility);
    };
  }, [element, enabled]);

  return [captureElement, enabled && active] as const;
}

/** Decorative scenes are deliberately kept in SVG: crisp on every phone and cheap to load. */
export function LotteryVisual({ code, context = "hero", animated = true }: LotteryVisualProps) {
  const [captureScene, sceneActive] = useSceneMotion(animated && context !== "hero" && context !== "catalog");
  const transition = { duration: sceneActive ? 1.1 : 0, ease: "easeOut" as const };
  const prefix = `${code}-${context}`;
  const rasterScenes: Record<string, string> = { dual: dualScene, september: septemberScene, pll: pllScene, pss: pssScene, khan: khanScene, weekly: kasperGrandScene, grob: grobScene };
  const loading = context === "catalog" ? "lazy" : "eager";
  const layered = context === "picker" || context === "live";

  if (code === "dual") return <div ref={captureScene} aria-hidden="true" className={`lottery-visual visual-dual visual-${context} raster-visual`}><img alt="" className="scene-backdrop" decoding="async" fetchPriority={context === "catalog" ? "auto" : "high"} loading={loading} src={dualScene} /><i className="scene-depth" /><i className="dual-scene-glow" /></div>;

  if (rasterScenes[code]) return <div ref={captureScene} aria-hidden="true" className={`lottery-visual visual-${code} visual-${context} raster-visual ${sceneActive ? "" : "motion-paused"}`}>
    <motion.img alt="" animate={sceneActive && layered ? { scale: [1.02, 1.065], x: [-3, 3], y: [0, -2] } : undefined} className="scene-backdrop" decoding="async" fetchPriority={context === "catalog" ? "auto" : "high"} loading={loading} src={rasterScenes[code]} transition={{ duration: 14, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" }} />
    {layered && <motion.img alt="" animate={sceneActive ? { scale: [1.08, 1.14], x: [3, -5], y: [1, -3] } : undefined} className="scene-foreground" decoding="async" loading="lazy" src={rasterScenes[code]} transition={{ duration: 10, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" }} />}
    <motion.span animate={sceneActive ? { opacity: [.22, .48, .22], x: [0, 24, 0] } : undefined} className="scene-light" transition={{ duration: 7.5, ease: "easeInOut", repeat: Infinity }} />
    <i className="scene-depth" />
    <motion.i animate={sceneActive ? { opacity: [.12, .32, .12], x: [-28, 24] } : undefined} className="scene-mist" transition={{ duration: 9, ease: "easeInOut", repeat: Infinity, repeatType: "mirror" }} />
    <i className="scene-weather" />
    <i className="scene-grain" />
    <b className="scene-particles"><i /><i /><i /><i /><i /></b>
  </div>;

  if (code === "september") return <svg ref={captureScene} className={`lottery-visual visual-${code} visual-${context}`} viewBox="0 0 420 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id={`${prefix}-sky`} x1="0" y1="0" x2="1" y2="1"><stop stopColor="#384152" /><stop offset=".48" stopColor="#542d36" /><stop offset="1" stopColor="#160f1b" /></linearGradient>
      <radialGradient id={`${prefix}-fire`}><stop stopColor="#ffd28a" stopOpacity=".95" /><stop offset=".23" stopColor="#d76d35" stopOpacity=".72" /><stop offset="1" stopColor="#8e2630" stopOpacity="0" /></radialGradient>
      <filter id={`${prefix}-soft`}><feGaussianBlur stdDeviation="11" /></filter>
    </defs>
    <path d="M0 0h420v360H0z" fill={`url(#${prefix}-sky)`} />
    <path d="M0 259c73-31 121-15 180-28 79-18 143-69 240-35v164H0z" fill="#111522" opacity=".92" />
    <ellipse cx="307" cy="258" rx="92" ry="74" fill={`url(#${prefix}-fire)`} filter={`url(#${prefix}-soft)`} />
    <path d="m273 285 30-51 14 51M310 287l29-48 12 48" fill="none" stroke="#e58b4d" strokeWidth="3" opacity=".48" />
    <motion.path variants={draw} initial="hidden" animate="visible" transition={transition} d="M434 40c-71 18-86 50-128 78-33 22-69 21-112 54" fill="none" stroke="#17131b" strokeWidth="7" strokeLinecap="round" />
    <motion.path variants={draw} initial="hidden" animate="visible" transition={{ ...transition, delay: .12 }} d="M349 94c-3 48-26 80-57 117M292 120c-27 10-48 27-62 48" fill="none" stroke="#1b151d" strokeWidth="4" strokeLinecap="round" />
    {[[343,95],[327,115],[306,137],[285,155],[258,165],[238,177]].map(([x,y], index) => <g key={x} transform={`translate(${x} ${y})`}><circle r="13" fill="#8d2435" /><circle cx="-5" cy="-4" r="3" fill="#db755d" opacity=".6" /><motion.circle r="18" fill="none" stroke="#cc7257" strokeOpacity=".12" initial={{ scale: .65 }} animate={{ scale: 1 }} transition={{ delay: .3 + index * .07 }} /></g>)}
    {[44,92,151,213,273,338,393].map((x, index) => <motion.path key={x} d={`M${x} -10  ${x - 28} 176`} stroke="#c6d0d9" strokeOpacity=".12" strokeWidth="1" initial={{ y: -30 }} animate={sceneActive ? { y: 22 } : undefined} transition={{ duration: 1.6, delay: index * .08, repeat: Infinity, repeatType: "loop" }} />)}
  </svg>;

  if (code === "pll") return <svg ref={captureScene} className={`lottery-visual visual-${code} visual-${context}`} viewBox="0 0 420 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><linearGradient id={`${prefix}-bg`} x2="1" y2="1"><stop stopColor="#121b4f" /><stop offset=".55" stopColor="#25164d" /><stop offset="1" stopColor="#090d22" /></linearGradient><radialGradient id={`${prefix}-moon`}><stop stopColor="#d8d5ff" stopOpacity=".58" /><stop offset="1" stopColor="#725fe0" stopOpacity="0" /></radialGradient></defs>
    <path d="M0 0h420v360H0z" fill={`url(#${prefix}-bg)`} />
    <circle cx="325" cy="79" r="89" fill={`url(#${prefix}-moon)`} />
    <circle cx="325" cy="79" r="44" fill="none" stroke="#b9b1ff" strokeOpacity=".2" />
    <path d="M221 360V157h62v203M293 360V118h72v242M372 360V196h48" fill="#080d21" opacity=".92" />
    <path d="M233 181h38M305 143h48M305 163h48M305 183h48M305 203h48" stroke="#7067c1" strokeOpacity=".2" />
    <motion.path d="M42 292 112 238l68 18 61-79 75-38" fill="none" stroke="#9f8cff" strokeOpacity=".54" strokeWidth="1.5" variants={draw} initial="hidden" animate="visible" transition={transition} />
    {[ [42,292], [112,238], [180,256], [241,177], [316,139] ].map(([x,y], index) => <motion.circle key={x} cx={x} cy={y} r="3.5" fill="#e7e3ff" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: .18 + index * .1 }} />)}
  </svg>;

  if (code === "pss") return <svg ref={captureScene} className={`lottery-visual visual-${code} visual-${context}`} viewBox="0 0 420 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><linearGradient id={`${prefix}-bg`} y2="1"><stop stopColor="#1a56a0" /><stop offset=".52" stopColor="#0a326d" /><stop offset="1" stopColor="#06132f" /></linearGradient><radialGradient id={`${prefix}-sun`}><stop stopColor="#f7fbff" /><stop offset=".18" stopColor="#a8dbff" stopOpacity=".7" /><stop offset="1" stopColor="#78bfff" stopOpacity="0" /></radialGradient></defs>
    <path d="M0 0h420v360H0z" fill={`url(#${prefix}-bg)`} />
    <circle cx="327" cy="73" r="122" fill={`url(#${prefix}-sun)`} />
    <path d="M70 360 218 74h67L171 360ZM236 360 348 139h55l-76 221Z" fill="#d5ecff" opacity=".08" />
    <path d="M0 263h420M0 300h420M91 0v360M167 0v360M243 0v360M319 0v360" stroke="#b9ddff" strokeOpacity=".11" />
    <motion.path d="M0 247c83-19 113 25 180 3 63-20 96-67 240-63" fill="none" stroke="#c6e9ff" strokeOpacity=".34" strokeWidth="2" variants={draw} initial="hidden" animate="visible" transition={transition} />
  </svg>;

  if (code === "khan") return <svg ref={captureScene} className={`lottery-visual visual-${code} visual-${context}`} viewBox="0 0 420 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><linearGradient id={`${prefix}-bg`} x2="1" y2="1"><stop stopColor="#5b1727" /><stop offset=".48" stopColor="#2c1425" /><stop offset="1" stopColor="#090d1b" /></linearGradient><linearGradient id={`${prefix}-sun`} y2="1"><stop stopColor="#f17c61" /><stop offset="1" stopColor="#8a2035" stopOpacity=".1" /></linearGradient></defs>
    <path d="M0 0h420v360H0z" fill={`url(#${prefix}-bg)`} />
    <circle cx="318" cy="95" r="83" fill={`url(#${prefix}-sun)`} opacity=".7" />
    <path d="m209 360 34-232h70l19 232ZM307 360l40-163h73v163Z" fill="#080b14" opacity=".93" />
    <path d="M228 360 251 145h46l12 215M330 360l29-145h44" fill="none" stroke="#b65762" strokeOpacity=".2" strokeWidth="2" />
    <motion.path d="M41 289h130l28-28h122" fill="none" stroke="#ec8b79" strokeOpacity=".43" strokeWidth="2" variants={draw} initial="hidden" animate="visible" transition={transition} />
    <path d="M33 75h118M33 90h84" stroke="#f0a092" strokeOpacity=".18" />
  </svg>;

  return <svg ref={captureScene} className={`lottery-visual visual-weekly visual-${context}`} viewBox="0 0 420 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><linearGradient id={`${prefix}-bg`} x2="1" y2="1"><stop stopColor="#192b4d" /><stop offset=".55" stopColor="#0b182f" /><stop offset="1" stopColor="#18131b" /></linearGradient><radialGradient id={`${prefix}-gold`}><stop stopColor="#f2cf82" stopOpacity=".4" /><stop offset="1" stopColor="#d8a23e" stopOpacity="0" /></radialGradient></defs>
    <path d="M0 0h420v360H0z" fill={`url(#${prefix}-bg)`} />
    <ellipse cx="327" cy="112" rx="130" ry="120" fill={`url(#${prefix}-gold)`} />
    <path d="M245 0v360M270 0v360M295 0v360M320 0v360M345 0v360M370 0v360" stroke="#f1d494" strokeOpacity=".09" />
    <motion.path d="M79 312C72 169 152 75 304 57c52-6 88 8 116 27" fill="none" stroke="#efd18a" strokeOpacity=".5" strokeWidth="1.5" variants={draw} initial="hidden" animate="visible" transition={transition} />
    <motion.path d="M127 339c-12-126 59-210 187-233" fill="none" stroke="#efd18a" strokeOpacity=".18" strokeWidth="9" variants={draw} initial="hidden" animate="visible" transition={{ ...transition, delay: .12 }} />
    <path d="M55 81h116M55 98h68" stroke="#f3dca8" strokeOpacity=".2" />
  </svg>;
}
