import english from "./locales/en.json";

export type Language = "ru" | "en";
const messages: Readonly<Record<string, string>> = english;
const listeners = new Set<() => void>();
let selected: Language | null = null;
let owner = "browser";
let automatic: Language = "ru";

function languageCode(value: string | null | undefined): Language | null {
  const code = value?.trim().toLowerCase().split(/[-_]/)[0];
  return code === "ru" || code === "en" ? code : null;
}

/** Unsupported languages use English; a present Telegram language is authoritative. */
export function resolveLanguage(choice: string | null, telegram: string | null | undefined, browser: readonly string[]): Language {
  const explicit = languageCode(choice);
  if (explicit) return explicit;
  if (telegram?.trim()) return languageCode(telegram) ?? "en";
  return languageCode(browser.find(value => value.trim())) ?? "en";
}

function telegramUser(): { id?: number; language_code?: string } | undefined {
  const app = window.Telegram?.WebApp;
  // Presentation only. Signed initData continues to be verified by the server.
  try {
    const value: unknown = app?.initDataUnsafe?.user ?? JSON.parse(new URLSearchParams(app?.initData ?? "").get("user") ?? "null");
    if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
    const user = value as Record<string, unknown>;
    return {
      id: typeof user.id === "number" && Number.isSafeInteger(user.id) && user.id > 0 ? user.id : undefined,
      language_code: typeof user.language_code === "string" ? user.language_code : undefined,
    };
  } catch { return undefined; }
}

function storageKey(): string { return `casper-loto:language:${owner}`; }

export function initializeLanguage(): void {
  const user = telegramUser();
  owner = user?.id === undefined ? "browser" : String(user.id);
  automatic = resolveLanguage(null, user?.language_code, navigator.languages?.length ? navigator.languages : [navigator.language]);
  try { selected = languageCode(localStorage.getItem(storageKey())); }
  catch { selected = null; }
  updateDocument();
}

export function getLanguage(): Language {
  return selected ?? automatic;
}

export function getLocale(): "ru-RU" | "en-GB" { return getLanguage() === "ru" ? "ru-RU" : "en-GB"; }

function updateDocument(): void { document.documentElement.lang = getLanguage(); }

export function setLanguage(value: Language): void {
  selected = value;
  try { localStorage.setItem(storageKey(), value); } catch { /* Switching still works for this session. */ }
  updateDocument();
  listeners.forEach(listener => listener());
}

export function subscribeLanguage(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Only presentation strings are translated. Objects, numbers and IDs stay intact. */
export function tr<T>(message: T, ...values: unknown[]): T {
  if (typeof message !== "string") return message;
  const translated = getLanguage() === "en" ? messages[message] ?? message : message;
  return translated.replace(/\{(\d+)\}/g, (placeholder, index: string) => Number(index) < values.length ? String(values[Number(index)]) : placeholder) as T;
}

window.addEventListener("storage", event => {
  if (event.key !== null && event.key !== storageKey()) return;
  try { selected = languageCode(localStorage.getItem(storageKey())); } catch { selected = null; }
  updateDocument();
  listeners.forEach(listener => listener());
});
