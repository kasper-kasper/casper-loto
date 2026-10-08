import { afterEach, expect, it, vi } from "vitest";
import { disableTelegramVerticalSwipes, lockInteractionViewport } from "./interactionLock";

afterEach(() => { delete window.Telegram; document.body.removeAttribute("style"); document.documentElement.removeAttribute("style"); vi.restoreAllMocks(); });

it("freezes the page, restores scroll and Telegram settings only after the last user exits", () => {
  const disableVerticalSwipes = vi.fn(), enableVerticalSwipes = vi.fn();
  window.Telegram = { WebApp: { initData: "signed", ready: vi.fn(), expand: vi.fn(), isVerticalSwipesEnabled: true, disableVerticalSwipes, enableVerticalSwipes } };
  document.body.style.overflow = "auto";
  vi.spyOn(window, "scrollY", "get").mockReturnValueOnce(125).mockReturnValue(0);
  const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
  const release = lockInteractionViewport(), nested = lockInteractionViewport();
  expect(document.body.style.position).toBe("fixed");
  expect(document.body.style.top).toBe("-125px");
  expect(disableVerticalSwipes).toHaveBeenCalledOnce();
  release(); release();
  expect(enableVerticalSwipes).not.toHaveBeenCalled();
  nested();
  expect(document.body.style.position).toBe("");
  expect(document.body.style.overflow).toBe("auto");
  expect(scroll).toHaveBeenCalledWith(0, 125);
  expect(enableVerticalSwipes).toHaveBeenCalledOnce();
});

it("preserves already disabled swipes and survives an unsupported Telegram client", () => {
  const enableVerticalSwipes = vi.fn();
  window.Telegram = { WebApp: { initData: "signed", ready: vi.fn(), expand: vi.fn(), isVerticalSwipesEnabled: false, disableVerticalSwipes: vi.fn(), enableVerticalSwipes } };
  lockInteractionViewport()();
  expect(enableVerticalSwipes).not.toHaveBeenCalled();
  window.Telegram.WebApp!.disableVerticalSwipes = () => { throw new Error("unsupported"); };
  const release = lockInteractionViewport();
  expect(document.body.style.position).toBe("fixed");
  release();
  expect(document.body.style.position).toBe("");
});

it("keeps native swipes disabled for the immersive page across nested scratch gestures", () => {
  const disableVerticalSwipes = vi.fn(), enableVerticalSwipes = vi.fn();
  window.Telegram = { WebApp: { initData: "signed", ready: vi.fn(), expand: vi.fn(), disableVerticalSwipes, enableVerticalSwipes } };
  const leave = disableTelegramVerticalSwipes();
  const scratch = lockInteractionViewport();
  scratch();
  expect(document.body.style.position).toBe("");
  expect(disableVerticalSwipes).toHaveBeenCalledOnce();
  expect(enableVerticalSwipes).not.toHaveBeenCalled();
  leave();
  expect(enableVerticalSwipes).toHaveBeenCalledOnce();
});
