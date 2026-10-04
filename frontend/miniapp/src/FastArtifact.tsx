import { useEffect, useRef } from "react";
import flash from "./assets/lotteries/fast-flash-device-v1.webp";
import pulse from "./assets/lotteries/fast-pulse-device-v1.webp";
import code from "./assets/lotteries/fast-code-device-v1.webp";

/** Decorative only. Draw timing and ticket state never depend on this animation. */
export function FastArtifact({ kind, className = "" }: { kind: string; className?: string }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = root.current;
    if (!node) return;
    let visible = true;
    const update = () => { node.dataset.moving = String(visible && !document.hidden); };
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(entries => {
      visible = entries[0]?.isIntersecting ?? false;
      update();
    });
    observer?.observe(node);
    document.addEventListener("visibilitychange", update);
    update();
    return () => { observer?.disconnect(); document.removeEventListener("visibilitychange", update); };
  }, []);
  return <div ref={root} className={`fast-artifact artifact-${kind} ${className}`} aria-hidden="true"><i className="artifact-aura" /><i className="artifact-orbit" /><img src={kind === "pulse" ? pulse : kind === "flash" ? flash : code} alt="" width="480" height="480" decoding="async" /><i className="artifact-reflection" /></div>;
}
