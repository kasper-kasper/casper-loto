import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const styles = readFileSync(resolve(process.cwd(), "src/styles.css"), "utf8");

describe("mobile layout contract", () => {
  it("supports narrow phones without horizontal overflow", () => {
    expect(styles).toContain("min-width: 320px");
    expect(styles).toContain("overflow-x: hidden");
    expect(styles).toContain("@media (max-width: 359px)");
    expect(styles).toContain("grid-template-columns: repeat(5, 1fr)");
    expect(styles).toContain("grid-template-columns: repeat(4, 1fr)");
    expect(styles).toContain(".live-stage { position: relative; display: grid; min-width: 0;");
  });

  it("keeps content and navigation inside iPhone safe areas", () => {
    expect(styles).toContain("env(safe-area-inset-top,0px)");
    expect(styles).toContain("env(safe-area-inset-bottom,0px)");
    expect(styles).toContain("padding: max(16px, var(--app-safe-top))");
    expect(styles).toContain("calc(100px + var(--app-safe-bottom))");
  });

  it("honours reduced-motion preferences", () => {
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
    expect(styles).toContain("transition-duration: .01ms !important");
    expect(styles).toContain("@keyframes live-signal");
    expect(styles).toContain("@keyframes live-slot-settle");
    expect(styles).toContain(".live-stage.final-minute");
  });
});
