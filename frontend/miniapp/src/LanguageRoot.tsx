import { useSyncExternalStore, type ReactNode } from "react";
import { getLanguage, subscribeLanguage, type Language } from "./i18n";

/** Re-render existing screens without remounting state or restarting API requests. */
export function LanguageRoot({ children }: { children: (language: Language) => ReactNode }) {
  const language = useSyncExternalStore(subscribeLanguage, getLanguage);
  return children(language);
}
