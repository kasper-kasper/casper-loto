// Shared by immersive viewers and scratch gestures; nested users restore once.
let users = 0;
let restore: (() => void) | undefined;

export function lockInteractionViewport(): () => void {
  if (users++ === 0) {
    const body = document.body, html = document.documentElement;
    const x = window.scrollX, y = window.scrollY;
    const saved = { position: body.style.position, top: body.style.top, left: body.style.left, width: body.style.width, overflow: body.style.overflow };
    const overflow = html.style.overflow, overscroll = html.style.overscrollBehavior;
    const releaseSwipes = disableTelegramVerticalSwipes();
    Object.assign(body.style, { position: "fixed", top: `${-y}px`, left: `${-x}px`, width: "100%", overflow: "hidden" });
    html.style.overflow = "hidden"; html.style.overscrollBehavior = "none";
    restore = () => {
      Object.assign(body.style, saved);
      html.style.overflow = overflow; html.style.overscrollBehavior = overscroll;
      if (window.scrollX !== x || window.scrollY !== y) window.scrollTo(x, y);
      releaseSwipes();
    };
  }
  let released = false;
  return () => {
    if (released) return;
    released = true;
    if (--users === 0) { restore?.(); restore = undefined; }
  };
}

let swipeUsers = 0;
let restoreSwipes: (() => void) | undefined;

// Disable before a native touch begins, while an immersive screen is open.
export function disableTelegramVerticalSwipes(): () => void {
  if (swipeUsers++ === 0) {
    const webApp = window.Telegram?.WebApp;
    const enabled = webApp?.isVerticalSwipesEnabled !== false;
    let disabled = false;
    try {
      if (webApp?.disableVerticalSwipes && webApp.enableVerticalSwipes && (!webApp.isVersionAtLeast || webApp.isVersionAtLeast("7.7"))) {
        webApp.disableVerticalSwipes(); disabled = true;
      }
    } catch { /* Older clients still receive browser scroll protection. */ }
    restoreSwipes = () => {
      if (disabled && enabled) {
        try { webApp?.enableVerticalSwipes?.(); } catch { /* Platform may have closed. */ }
      }
    };
  }
  let released = false;
  return () => {
    if (released) return;
    released = true;
    if (--swipeUsers === 0) { restoreSwipes?.(); restoreSwipes = undefined; }
  };
}
