import { act, render } from "@testing-library/react";
import { useMemo, useState } from "react";
import { expect, it, vi } from "vitest";
import { webApi } from "../../api";
import type { Dashboard, Lottery } from "../../types";
import { KhanBridge } from "../bridge/KhanBridge";
import { useKhanExperience } from "./useKhanExperience";

vi.mock("../../api", () => ({ ApiError: class extends Error {}, webApi: { dashboard: vi.fn() } }));

it("polls once on opening and every 30 seconds despite parent callback changes", async () => {
  vi.useFakeTimers();
  vi.stubGlobal("matchMedia", () => ({ matches: false }));
  const lottery: Lottery = { code: "khan", name: "6 из 36", ruleset_code: "daily_classic_6_36", kind: "DAILY", numbers_to_pick: 6, max_number: 36, primary_numbers_to_pick: 6, primary_max_number: 36, secondary_numbers_to_pick: 0, secondary_max_number: 0, secondary_storage_offset: 0, ticket_price: 100, jackpot: 1000, draw_number: 1, scheduled_at: "2026-10-14T15:00:00Z", sales_close_at: "2026-10-14T14:58:00Z", purchase_available: true, player_ticket_count: 0, sales_status: "OPEN", max_tickets_per_purchase: 1000 };
  const response: Dashboard = { app_version: "test", server_time: "2026-10-14T12:00:00Z", balance: 900, active_ticket_count: 0, lotteries: [lottery], recent_results: [], monthly_total_payout: 0 };
  // Cap a regressed loop so its failure is a request count, not a hanging test.
  vi.mocked(webApi.dashboard).mockImplementation(async () => {
    if (vi.mocked(webApi.dashboard).mock.calls.length > 3) return new Promise(() => undefined);
    return response;
  });
  function Parent() {
    const [dashboard, setDashboard] = useState(response);
    const bridge = useMemo(() => new KhanBridge(), []);
    const snapshot = useKhanExperience({ bridge, initialLottery: lottery, initialBalance: dashboard.balance, userId: "test", onExit: () => undefined, onBalance: balance => setDashboard(current => ({ ...current, balance })) });
    return <span>{snapshot.balance}</span>;
  }
  const view = render(<Parent />);
  try {
    await act(async () => { await Promise.resolve(); });
    expect(webApi.dashboard).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(29_999); });
    expect(webApi.dashboard).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(webApi.dashboard).toHaveBeenCalledTimes(2);
  } finally {
    view.unmount(); vi.useRealTimers(); vi.unstubAllGlobals();
  }
});
