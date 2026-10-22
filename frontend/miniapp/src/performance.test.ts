import { afterEach, describe, expect, it, vi } from "vitest";

import { installMotionBudget } from "./performance";

describe("motion budget", () => {
  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("resumes visible New Year lights after returning to the tab, without an intersection change", () => {
    let notify: IntersectionObserverCallback = () => undefined;
    class Observer {
      constructor(callback: IntersectionObserverCallback) { notify = callback; }
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    vi.stubGlobal("IntersectionObserver", Observer);
    let hidden = false;
    vi.spyOn(document, "hidden", "get").mockImplementation(() => hidden);
    document.body.innerHTML = '<div class="ny-environment"></div><div class="fast-card"></div>';
    const visible = document.querySelector(".ny-environment")!;
    const offscreen = document.querySelector(".fast-card")!;
    const cleanup = installMotionBudget();
    notify([{ target: visible, isIntersecting: true }, { target: offscreen, isIntersecting: false }] as IntersectionObserverEntry[], {} as IntersectionObserver);
    hidden = true;
    document.dispatchEvent(new Event("visibilitychange"));
    expect(visible).toHaveClass("motion-paused");
    hidden = false;
    document.dispatchEvent(new Event("visibilitychange"));
    expect(visible).not.toHaveClass("motion-paused");
    expect(offscreen).toHaveClass("motion-paused");
    cleanup();
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
