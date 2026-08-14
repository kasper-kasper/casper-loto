interface TelegramWebApp {
  initData: string;
  colorScheme?: "light" | "dark";
  ready(): void;
  expand(): void;
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
