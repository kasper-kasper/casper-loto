import { act, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";
import messages from "./locales/en.json";
import { getLanguage, getLocale, initializeLanguage, resolveLanguage, setLanguage, tr } from "./i18n";
import { LanguageSelector } from "./LanguageSelector";
import { LanguageRoot } from "./LanguageRoot";
import { formatCas, formatCompactAmount, formatDrawLabel, formatMoscow } from "./format";
import { notificationText } from "./notificationText";
import { readdirSync, readFileSync } from "node:fs";
import ts from "typescript";
import { join, resolve } from "node:path";

afterEach(() => {
  delete window.Telegram;
  vi.restoreAllMocks();
  setLanguage("ru");
});

it.each([
  ["en", "ru", ["ru-RU"], "en"],
  ["ru", "en", ["en-GB"], "ru"],
  [null, "en-US", ["ru-RU"], "en"],
  [null, "RU", ["en"], "ru"],
  [null, undefined, ["ru_RU", "en"], "ru"],
  [null, "", ["en-US", "ru"], "en"],
  ["corrupt", undefined, ["ru"], "ru"],
  [null, "de", ["ru"], "en"],
  [null, undefined, ["fr", "ru"], "en"],
  [null, undefined, [], "en"],
] as const)("resolves choice %s, Telegram %s, browser %s as %s", (choice, telegram, browser, expected) => {
  expect(resolveLanguage(choice, telegram, browser)).toBe(expected);
});

it("persists explicit choices separately for Telegram accounts", () => {
  const app = { initData: "", initDataUnsafe: { user: { id: 123, language_code: "en" } }, ready() {}, expand() {} };
  window.Telegram = { WebApp: app };
  initializeLanguage();
  expect(getLanguage()).toBe("en");
  setLanguage("ru");
  app.initDataUnsafe.user.language_code = "en";
  initializeLanguage();
  expect(getLanguage()).toBe("ru");
  app.initDataUnsafe.user.id = 456;
  initializeLanguage();
  expect(getLanguage()).toBe("en");
  expect(document.documentElement.lang).toBe("en");
});

it("reads Telegram language from initData when unsafe user data is missing", () => {
  window.Telegram = { WebApp: { initData: new URLSearchParams({ user: JSON.stringify({ id: 789, language_code: "en" }) }).toString(), ready() {}, expand() {} } };
  initializeLanguage();
  expect(getLanguage()).toBe("en");
});

it("falls back to the browser for malformed Telegram data and blocked storage", () => {
  vi.spyOn(navigator, "languages", "get").mockReturnValue(["en-GB"]);
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  window.Telegram = { WebApp: { initData: "user=%7Binvalid", ready() {}, expand() {} } };
  initializeLanguage();
  expect(getLanguage()).toBe("en");
  setLanguage("ru");
  expect(getLanguage()).toBe("ru");
});

it("updates every screen without resetting component state", () => {
  setLanguage("ru");
  function Screen() {
    const [value, setValue] = useState(0);
    return <><h1>{tr("Мои билеты")}</h1><button onClick={() => setValue(value + 1)}>{value}</button><LanguageSelector /></>;
  }
  render(<LanguageRoot>{() => <Screen />}</LanguageRoot>);
  fireEvent.click(screen.getByRole("button", { name: "0" }));
  fireEvent.click(screen.getByRole("button", { name: "English" }));
  expect(screen.getByRole("heading", { name: "My tickets" })).toBeVisible();
  expect(screen.getByRole("button", { name: "1" })).toBeVisible();
  expect(screen.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(screen.getByRole("button", { name: "Русский" }));
  expect(screen.getByRole("heading", { name: "Мои билеты" })).toBeVisible();
});

it("syncs an explicit choice from another window", () => {
  delete window.Telegram;
  initializeLanguage();
  localStorage.setItem("casper-loto:language:browser", "en");
  act(() => window.dispatchEvent(new StorageEvent("storage", { key: "casper-loto:language:browser" })));
  expect(getLanguage()).toBe("en");
});

it("formats exact CAS, quantities and Moscow times in English", () => {
  setLanguage("en");
  expect(getLocale()).toBe("en-GB");
  expect(formatCas(3333)).toBe("3,333 CAS");
  expect(formatCompactAmount(1_200_000)).toBe("1.2 m");
  expect(formatDrawLabel("dual", 501)).toBe("Round #0501");
  expect(formatMoscow("2026-10-22T18:15:00Z")).toMatch(/22 Oct.*21:15/);
});

it("translates system history without changing IDs, names or interpolation values", () => {
  setLanguage("en");
  const original = { id: "abc", name: "Выигрыш", amount: 3333 };
  expect(tr(original)).toBe(original);
  expect(tr("{0} из {1}", "<b>Иван</b>", 25)).toBe("<b>Иван</b> of 25");
  expect(notificationText("6 из 36, тираж №0051. Выигрыш уже зачислен.")).toBe("6 of 36, draw No. 0051. Winnings credited.");
  expect(notificationText("Билет №51. Оба раунда завершены; выигрыш зачислен.")).toBe("Ticket No. 51. Both rounds finished; winnings credited.");
  expect(tr("Каспер, подвинься")).toBe("Move over, Casper");
});

it("provides English copy and preserves every interpolation placeholder", () => {
  for (const [ru, en] of Object.entries(messages)) {
    expect(en, ru).not.toMatch(/[А-Яа-яЁё]/);
    expect(en.match(/\{\d+\}/g)?.sort() ?? [], ru).toEqual(ru.match(/\{\d+\}/g)?.sort() ?? []);
    expect(en.trim(), ru).not.toBe("");
  }
});

it("covers every Russian system message in the Mini App source", () => {
  const dictionary: Record<string, string> = messages;
  const directory = resolve(process.cwd(), "src");
  for (const file of readdirSync(directory).filter(file => /\.(ts|tsx)$/.test(file) && !/\.test\.|\.d\.ts$|designPreview|broadcastPreview|LanguageSelector/.test(file))) {
    const source = ts.createSourceFile(file, readFileSync(join(directory, file), "utf8"), ts.ScriptTarget.Latest, true);
    function visit(node: ts.Node) {
      if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
        if (/[А-Яа-яЁё]/.test(node.text)) expect(dictionary[node.text], `${file}: ${node.text}`).toBeTruthy();
      }
      ts.forEachChild(node, visit);
    }
    visit(source);
  }
});
