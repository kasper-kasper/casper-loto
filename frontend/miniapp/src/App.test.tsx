import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";

import App from "./App";
import { miniAppApi } from "./api";
import type { Dashboard } from "./types";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {},
  miniAppApi: {
    dashboard: vi.fn(),
    tickets: vi.fn(),
    purchase: vi.fn(),
  },
}));

const dashboard: Dashboard = {
  balance: 5_000,
  active_ticket_count: 0,
  lotteries: [
    {
      code: "weekly",
      name: "Weekly 5/20",
      kind: "WEEKLY",
      numbers_to_pick: 5,
      max_number: 20,
      ticket_price: 100,
      jackpot: 10_000,
      draw_number: 7,
      scheduled_at: "2026-08-16T17:00:00Z",
      sales_close_at: "2026-08-16T16:55:00Z",
      sales_open: true,
      purchase_available: true,
    },
    {
      code: "daily",
      name: "Daily 4/15",
      kind: "DAILY",
      numbers_to_pick: 4,
      max_number: 15,
      ticket_price: null,
      jackpot: 0,
      draw_number: 12,
      scheduled_at: "2026-08-15T15:00:00Z",
      sales_close_at: "2026-08-15T15:00:00Z",
      sales_open: false,
      purchase_available: false,
    },
  ],
  recent_results: [],
};

beforeEach(() => {
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(dashboard);
  vi.mocked(miniAppApi.tickets).mockResolvedValue([]);
  vi.mocked(miniAppApi.purchase).mockResolvedValue({
    operation_id: "operation",
    draw_id: "draw",
    ticket_ids: ["ticket"],
    total_cost: 100,
    balance_after: 4_900,
    already_processed: false,
  });
  vi.stubGlobal("crypto", {
    ...crypto,
    randomUUID: vi.fn(() => "00000000-0000-4000-8000-000000000001"),
    getRandomValues: crypto.getRandomValues.bind(crypto),
  });
});

afterEach(() => vi.unstubAllGlobals());

it("requires a signed Telegram launch", () => {
  render(<App initData="" />);

  expect(screen.getByText("Откройте K-Loto в Telegram")).toBeInTheDocument();
});

it("renders server-authoritative balance and lottery states", async () => {
  render(<App initData="signed" />);

  expect(await screen.findByText("5 000 CAS")).toBeInTheDocument();
  expect(screen.getByText("10 000 CAS")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Купить за 100 CAS" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Скоро" })).toBeDisabled();
});

it("selects five numbers, adds a ticket and buys the cart atomically", async () => {
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: "Купить за 100 CAS" }));

  const grid = document.querySelector(".number-grid");
  expect(grid).not.toBeNull();
  for (const number of [1, 2, 3, 4, 5]) {
    fireEvent.click(within(grid as HTMLElement).getByRole("button", { name: String(number) }));
  }
  fireEvent.click(screen.getByRole("button", { name: "Добавить ещё" }));

  expect(screen.getByText("1 бил.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Купить всё" }));

  await waitFor(() =>
    expect(miniAppApi.purchase).toHaveBeenCalledWith(
      "signed",
      [[1, 2, 3, 4, 5]],
      "00000000-0000-4000-8000-000000000001",
    ),
  );
});
