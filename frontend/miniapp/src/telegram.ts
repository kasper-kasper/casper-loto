interface TelegramWebApp {
  initData: string;
  colorScheme?: "light" | "dark";
  ready(): void;
  expand(): void;
  requestWriteAccess?(callback?: (allowed: boolean) => void): void;
  HapticFeedback?: {
    impactOccurred(style: "light" | "medium" | "heavy" | "rigid" | "soft"): void;
    notificationOccurred(type: "error" | "success" | "warning"): void;
    selectionChanged(): void;
  };
}

export function selectionHaptic(): void {
  window.Telegram?.WebApp?.HapticFeedback?.selectionChanged();
}

export function successHaptic(): void {
  window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred("success");
}

export function errorHaptic(): void {
  window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred("error");
}

export function liveStartHaptic(): void {
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred("light");
}

export function requestTelegramWriteAccess(): Promise<boolean> {
  const method = window.Telegram?.WebApp?.requestWriteAccess;
  if (!method) return Promise.resolve(false);
  return new Promise((resolve) => method.call(window.Telegram?.WebApp, resolve));
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export function initializeTelegram(): string {
  const webApp = window.Telegram?.WebApp;
  if (!webApp) return "";
  webApp.ready();
  webApp.expand();
  document.documentElement.dataset.telegramTheme = webApp.colorScheme ?? "dark";
  return webApp.initData;
}

export function isLocalDevMode(): boolean {
  return import.meta.env.VITE_LOCAL_DEV_AUTH === "true";
}
