import { afterEach, describe, expect, it, vi } from "vitest";

import { installMotionBudget } from "./performance";

describe("motion budget", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.unstubAllGlobals();
  });

  it("pauses an off-screen scene and resumes it when visible", () => {
    let notify: IntersectionObserverCallback = () => undefined;
    class Observer {
      constructor(callback: IntersectionObserverCallback) {
        notify = callback;
      }
      observe() {}
      disconnect() {}
    }
    vi.stubGlobal("IntersectionObserver", Observer);
    document.body.innerHTML = '<article class="fast-card"></article>';
    const scene = document.querySelector(".fast-card")!;

    const cleanup = installMotionBudget();
    notify([{ target: scene, isIntersecting: false } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(scene).toHaveClass("motion-paused");

    notify([{ target: scene, isIntersecting: true } as IntersectionObserverEntry], {} as IntersectionObserver);
    expect(scene).not.toHaveClass("motion-paused");
    cleanup();
  });
});
