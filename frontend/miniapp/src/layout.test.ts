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
    expect(styles).toContain("env(safe-area-inset-top)");
    expect(styles).toContain("env(safe-area-inset-bottom)");
    expect(styles).toMatch(/padding: max\(16px, env\(safe-area-inset-top\)\)/);
    expect(styles).toMatch(/calc\(100px \+ env\(safe-area-inset-bottom\)\)/);
  });

  it("honours reduced-motion preferences", () => {
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
    expect(styles).toContain("transition-duration: .01ms !important");
  });
});
