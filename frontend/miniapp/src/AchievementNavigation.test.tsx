import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import App from "./App";
import { miniAppApi } from "./api";
import { setLanguage } from "./i18n";
import type { Account, Dashboard } from "./types";
import type { Achievement, AchievementPage } from "./achievementTypes";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {},
  miniAppApi: {
    achievements: vi.fn(), achievementNotices: vi.fn(),
    achievementSeen: vi.fn().mockResolvedValue(undefined),
    activity: vi.fn().mockResolvedValue(undefined),
    collection: vi.fn().mockResolvedValue({ active_badge: null, active_theme: null, items: [] }),
    dashboard: vi.fn(), highlights: vi.fn(), account: vi.fn(), notifications: vi.fn(),
    notificationPreferences: vi.fn(), markNotificationsRead: vi.fn().mockResolvedValue(undefined),
    tickets: vi.fn().mockResolvedValue({ tickets: [], total: 0, has_more: false }),
  },
}));

const target: Achievement = {
  code: "rare_hunter", title: "Охотник за удачей", description: "Получить 150 побед",
  rarity: "rare", status: "earned", secret: false,
};
const page: AchievementPage = {
  enabled: true, total: 42, earned: 1, total_by_category: { common: 22, rare: 20 },
  earned_by_category: { rare: 1 }, items: [], next_offset: null,
};
const account: Account = {
  display_name: "Player", balance: 5000, ticket_count: 0, active_ticket_count: 0,
  winning_ticket_count: 0, total_spent: 0, total_won: 0, best_win: 0,
  unread_notification_count: 1,
  notification_preferences: {
    telegram_enabled: true, draw_results_enabled: true,
    inactivity_reminders_enabled: false, in_app_enabled: true,
  },
};
const dashboard: Dashboard = {
  server_time: "2026-10-23T12:00:00Z", balance: 5000, active_ticket_count: 0,
  lotteries: [], recent_results: [], monthly_total_payout: 0,
  total_ticket_count: 0, total_winning_ticket_count: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
  setLanguage("ru");
  vi.stubGlobal("scrollTo", vi.fn());
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true, value: function (this: HTMLDialogElement) { this.setAttribute("open", ""); },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", { configurable: true, value: function (this: HTMLDialogElement) { this.removeAttribute("open"); } });
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(dashboard);
  vi.mocked(miniAppApi.highlights).mockResolvedValue({ last_jackpot: null });
  vi.mocked(miniAppApi.account).mockResolvedValue(account);
  vi.mocked(miniAppApi.achievementNotices).mockResolvedValue([]);
  vi.mocked(miniAppApi.notifications).mockResolvedValue([{
    id: "notice", type: "ACHIEVEMENT", title: "Достижение получено",
    body: target.title!, payload: { achievement: target.code },
    read_at: null, created_at: "2026-10-23T12:00:00Z",
  }]);
  vi.mocked(miniAppApi.achievements).mockImplementation(async (_init, options) => (
    options?.focus ? { ...page, focused_item: target, focused_category: "rare" } : page
  ));
  vi.mocked(miniAppApi.notificationPreferences).mockImplementation(async (_init, preferences) => preferences);
});
afterEach(() => { vi.unstubAllGlobals(); });

it("opens the notified achievement from the bell in its real category", async () => {
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: /^Моё/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Уведомления: есть непрочитанные" }, { timeout: 5000 }));
  fireEvent.click(await screen.findByRole("button", { name: "Открыть достижение" }));
  expect(await screen.findByRole("dialog", { name: target.title })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Редкие/ })).toHaveAttribute("aria-pressed", "true");
  expect(miniAppApi.achievements).toHaveBeenLastCalledWith("signed", {
    category: "rare", status: "all", focus: target.code,
  }, expect.any(AbortSignal));
});

it("saves and restores the independent in-app switch without changing Telegram", async () => {
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: /^Моё/ }));
  const toggle = await screen.findByRole("switch", { name: "Всплывающие уведомления о достижениях" });
  fireEvent.click(toggle);
  await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "false"));
  expect(miniAppApi.notificationPreferences).toHaveBeenCalledExactlyOnceWith("signed", {
    ...account.notification_preferences, in_app_enabled: false,
  });
  expect(screen.getByRole("button", { name: "Уведомления: есть непрочитанные" })).toBeInTheDocument();
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  // A second click restores the setting without changing Telegram preferences.
  fireEvent.click(toggle);
  await waitFor(() => expect(toggle).toHaveAttribute("aria-checked", "true"));
  expect(miniAppApi.notificationPreferences).toHaveBeenLastCalledWith("signed", account.notification_preferences);
});
