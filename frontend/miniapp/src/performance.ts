const AMBIENT_MOTION_SELECTOR = [
  ".lottery-visual",
  ".storefront-card",
  ".fast-card",
  ".fast-live-card",
  ".fast-divider",
  ".ny-environment",
  ".ny-coupon-lights",
].join(",");

function setAnimationsPaused(element: Element, paused: boolean): void {
  element.classList.toggle("motion-paused", paused);
  if (!("getAnimations" in element)) return;
  for (const animation of element.getAnimations({ subtree: true })) {
    if (paused) animation.pause();
    else animation.play();
  }
}

/**
 * Keep visible scenes alive while preventing off-screen cards and a hidden
 * Telegram WebView from consuming the phone's rendering budget.
 */
export function installMotionBudget(): () => void {
  const root = document.documentElement;
  const observed = new Set<Element>();
  const visible = new WeakMap<Element, boolean>();
  const intersection = typeof IntersectionObserver === "undefined"
    ? null
    : new IntersectionObserver((entries) => {
      for (const entry of entries) {
        visible.set(entry.target, entry.isIntersecting);
        setAnimationsPaused(entry.target, !entry.isIntersecting || document.hidden);
      }
    }, { rootMargin: "120px 0px" });

  const observeNewScenes = () => {
    for (const element of observed) {
      if (element.isConnected) continue;
      intersection?.unobserve(element);
      observed.delete(element);
    }
    for (const element of document.querySelectorAll(AMBIENT_MOTION_SELECTOR)) {
      if (observed.has(element)) continue;
      observed.add(element);
      intersection?.observe(element);
      if (document.hidden) setAnimationsPaused(element, true);
    }
  };
  const syncVisibility = () => {
    root.classList.toggle("app-backgrounded", document.hidden);
    for (const element of observed) {
      if (document.hidden) setAnimationsPaused(element, true);
      else setAnimationsPaused(element, intersection ? visible.get(element) === false : false);
    }
  };

  observeNewScenes();
  syncVisibility();
  const mutations = typeof MutationObserver === "undefined"
    ? null
    : new MutationObserver(observeNewScenes);
  mutations?.observe(document.body, { childList: true, subtree: true });
  document.addEventListener("visibilitychange", syncVisibility);

  return () => {
    document.removeEventListener("visibilitychange", syncVisibility);
    mutations?.disconnect();
    intersection?.disconnect();
    root.classList.remove("app-backgrounded");
  };
}
