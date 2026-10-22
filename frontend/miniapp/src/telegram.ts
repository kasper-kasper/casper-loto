interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: { user?: { id?: number; language_code?: string } };
  colorScheme?: "light" | "dark";
  isFullscreen?: boolean;
  isVerticalSwipesEnabled?: boolean;
  disableVerticalSwipes?(): void;
  enableVerticalSwipes?(): void;
  isVersionAtLeast?(version: string): boolean;
  requestFullscreen?(): void;
  setHeaderColor?(color: string): void;
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
  // Older clients keep their expanded sheet; auth data is independent of presentation.
  if (webApp.initData && webApp.isVersionAtLeast?.("8.0")) {
    try {
      webApp.setHeaderColor?.("#050d27");
      if (!webApp.isFullscreen) webApp.requestFullscreen?.();
    } catch {
      // Unsupported desktop/platform combinations still open the ordinary Mini App.
    }
  }
  document.documentElement.dataset.telegramTheme = webApp.colorScheme ?? "dark";
  return webApp.initData;
}

export function isLocalDevMode(): boolean {
  return import.meta.env.VITE_LOCAL_DEV_AUTH === "true";
}
