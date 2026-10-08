import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { webApi } from "../api";
import HalloweenExperienceHost from "./HalloweenExperienceHost";
import type { Dashboard, Lottery } from "../types";

vi.mock("../api", () => ({ ApiError: class extends Error {}, webApi: { dashboard: vi.fn(), purchase: vi.fn() } }));
const lottery: Lottery = { code: "grob", name: "Casper Halloween", ruleset_code: "halloween_3_28", kind: "DAILY", numbers_to_pick: 3, max_number: 28, primary_numbers_to_pick: 3, primary_max_number: 28, secondary_numbers_to_pick: 0, secondary_max_number: 0, secondary_storage_offset: 0, ticket_price: 6666, jackpot: 6666666, draw_number: 1, scheduled_at: new Date(Date.now() + 3600000).toISOString(), sales_close_at: null, purchase_available: true, player_ticket_count: 0, sales_status: "OPEN", max_tickets_per_purchase: 1000, max_tickets_per_user_per_draw: 5000, fixed_payouts: { "2": 28000 } };
const dashboard: Dashboard = { app_version: "test", server_time: new Date().toISOString(), balance: 1000000, active_ticket_count: 0, lotteries: [lottery], recent_results: [], monthly_total_payout: 0 };

test("web Halloween accepts 28 and preserves idempotent purchase through the existing hook", async () => {
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  vi.mocked(webApi.dashboard).mockResolvedValue(dashboard);
  vi.mocked(webApi.purchase).mockResolvedValue({ ticket_ids: ["new-ticket"], total_cost: 6666, balance_after: 993334 });
  render(<HalloweenExperienceHost lottery={lottery} balance={1000000} userId="halloween-test" onClose={vi.fn()} onBalance={vi.fn()} />);
  const grid = screen.getByLabelText("Числа");
  expect(within(grid).getAllByRole("button")).toHaveLength(28);
  for (const value of [1, 14, 28]) fireEvent.click(within(grid).getByRole("button", { name: String(value) }));
  fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));
  await waitFor(() => expect(webApi.purchase).toHaveBeenCalledWith("grob", [[1, 14, 28]], expect.any(String), 1, expect.any(AbortSignal)));
  expect(screen.getByRole("button", { name: "Купить 25 случайных билетов" })).toBeInTheDocument();
  vi.unstubAllGlobals();
});
