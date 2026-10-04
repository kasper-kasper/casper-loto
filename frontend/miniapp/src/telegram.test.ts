import { afterEach, expect, it, vi } from "vitest";
import { initializeTelegram } from "./telegram";

afterEach(() => { delete window.Telegram; delete document.documentElement.dataset.telegramTheme; });

it("requests fullscreen on supported authenticated clients while preserving init data", () => {
  const ready = vi.fn(), expand = vi.fn(), requestFullscreen = vi.fn(), setHeaderColor = vi.fn();
  window.Telegram = { WebApp: { initData: "signed-init-data", ready, expand, requestFullscreen, setHeaderColor, isVersionAtLeast: () => true } };
  expect(initializeTelegram()).toBe("signed-init-data");
  expect(ready).toHaveBeenCalledOnce();
  expect(expand).toHaveBeenCalledOnce();
  expect(requestFullscreen).toHaveBeenCalledOnce();
  expect(setHeaderColor).toHaveBeenCalledWith("#050d27");
});

it("keeps older clients expanded without requesting unsupported fullscreen", () => {
  const requestFullscreen = vi.fn(), expand = vi.fn();
  window.Telegram = { WebApp: { initData: "old-client", ready: vi.fn(), expand, requestFullscreen, isVersionAtLeast: () => false } };
  expect(initializeTelegram()).toBe("old-client");
  expect(expand).toHaveBeenCalledOnce();
  expect(requestFullscreen).not.toHaveBeenCalled();
});

it("does not break startup when a platform refuses fullscreen", () => {
  window.Telegram = { WebApp: { initData: "supported-version", ready: vi.fn(), expand: vi.fn(), isVersionAtLeast: () => true, requestFullscreen: () => { throw new Error("unsupported platform"); } } };
  expect(initializeTelegram()).toBe("supported-version");
});

it("does not re-enter an existing fullscreen or request it outside Telegram", () => {
  const requestFullscreen = vi.fn();
  window.Telegram = { WebApp: { initData: "already-fullscreen", ready: vi.fn(), expand: vi.fn(), isFullscreen: true, isVersionAtLeast: () => true, requestFullscreen } };
  expect(initializeTelegram()).toBe("already-fullscreen");
  expect(requestFullscreen).not.toHaveBeenCalled();
  window.Telegram.WebApp!.initData = "";
  window.Telegram.WebApp!.isFullscreen = false;
  expect(initializeTelegram()).toBe("");
  expect(requestFullscreen).not.toHaveBeenCalled();
});
