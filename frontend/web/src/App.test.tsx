import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import App from "./App";
import { webApi } from "./api";

vi.mock("./api", async () => {
  class ApiError extends Error {}
  return { ApiError, webApi: { session: vi.fn(), login: vi.fn(), telegramLogin: vi.fn(), logout: vi.fn(), dashboard: vi.fn(), tickets: vi.fn(), results: vi.fn(), purchase: vi.fn() } };
});

const session = { display_name: "Игрок", csrf_token: "csrf", expires_at: "2026-08-16T00:00:00Z" };
const dashboard = { balance: 1000, active_ticket_count: 1, recent_results: [], lotteries: [{ code: "weekly", name: "Weekly", kind: "WEEKLY" as const, numbers_to_pick: 5, max_number: 20, ticket_price: 100, jackpot: 5000, draw_number: 7, scheduled_at: "2026-08-16T17:00:00Z", sales_close_at: "2026-08-16T16:55:00Z", sales_open: true, purchase_available: true }] };

beforeEach(() => { window.history.replaceState(null, "", "/"); vi.clearAllMocks(); vi.mocked(webApi.session).mockResolvedValue(session); vi.mocked(webApi.telegramLogin).mockResolvedValue(session); vi.mocked(webApi.dashboard).mockResolvedValue(dashboard); vi.mocked(webApi.tickets).mockResolvedValue([]); vi.mocked(webApi.results).mockResolvedValue([]); });

test("exchanges a Telegram one-time link without asking for a password", async () => {
  window.location.hash = "telegram-login=abcdefghijklmnopqrstuvwxyz123456";
  render(<App />);
  expect(await screen.findByText("1 000 CAS")).toBeInTheDocument();
  expect(webApi.telegramLogin).toHaveBeenCalledWith("abcdefghijklmnopqrstuvwxyz123456");
  expect(window.location.hash).toBe("");
});

test("shows balance and Weekly after restoring a session", async () => {
  render(<App />);
  expect(await screen.findByText("1 000 CAS")).toBeInTheDocument();
  expect(screen.getByText("Weekly: 5 из 20")).toBeInTheDocument();
});

test("buys selected numbers with requested quantity", async () => {
  vi.mocked(webApi.purchase).mockResolvedValue({ ticket_ids: ["1", "2"], total_cost: 200, balance_after: 800 });
  render(<App />); await screen.findByText("Weekly: 5 из 20");
  for (const value of [1, 2, 3, 4, 5]) fireEvent.click(screen.getByRole("button", { name: String(value) }));
  fireEvent.change(screen.getByLabelText("Количество"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "Купить за 200 CAS" }));
  await waitFor(() => expect(webApi.purchase).toHaveBeenCalledWith("weekly", [[1, 2, 3, 4, 5], [1, 2, 3, 4, 5]], expect.any(String)));
});

test("loads history and draw results", async () => {
  render(<App />); await screen.findByText("Weekly: 5 из 20");
  fireEvent.click(screen.getByRole("button", { name: "История" }));
  await waitFor(() => expect(webApi.tickets).toHaveBeenCalledWith("history"));
  fireEvent.click(screen.getByRole("button", { name: "Результаты" }));
  await waitFor(() => expect(webApi.results).toHaveBeenCalled());
});

test("buys a Daily 4 of 15 ticket", async () => {
  vi.mocked(webApi.dashboard).mockResolvedValue({
    ...dashboard,
    lotteries: [
      ...dashboard.lotteries,
      { ...dashboard.lotteries[0], code: "daily", name: "Daily", kind: "DAILY", numbers_to_pick: 4, max_number: 15 },
    ],
  });
  vi.mocked(webApi.purchase).mockResolvedValue({ ticket_ids: ["daily-1"], total_cost: 100, balance_after: 900 });
  render(<App />);
  await screen.findByText("Weekly: 5 из 20");
  fireEvent.click(screen.getByRole("button", { name: "Daily" }));
  await screen.findByText("Daily: 4 из 15");
  for (const value of [1, 2, 3, 4]) fireEvent.click(screen.getByRole("button", { name: String(value) }));
  fireEvent.click(screen.getByRole("button", { name: "Купить за 100 CAS" }));
  await waitFor(() => expect(webApi.purchase).toHaveBeenCalledWith("daily", [[1, 2, 3, 4]], expect.any(String)));
});
