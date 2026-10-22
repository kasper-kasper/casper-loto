import { useSyncExternalStore } from "react";
import { getLanguage, setLanguage, subscribeLanguage } from "./i18n";

export function LanguageSelector() {
  const language = useSyncExternalStore(subscribeLanguage, getLanguage);
  return <fieldset className="hub-language"><legend>{language === "ru" ? "Язык приложения" : "App language"}</legend><div>
    <button type="button" lang="ru" aria-pressed={language === "ru"} onClick={() => setLanguage("ru")}>Русский</button>
    <button type="button" lang="en" aria-pressed={language === "en"} onClick={() => setLanguage("en")}>English</button>
  </div></fieldset>;
}
