import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { miniAppApi } from "./api";
import { KasperLiveView } from "./KasperLiveView";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {},
  miniAppApi: {
    kasperLiveHistory: vi.fn(),
    kasperLivePurchase: vi.fn(),
  },
}));

vi.mock("./telegram", () => ({
  errorHaptic: vi.fn(),
  selectionHaptic: vi.fn(),
  successHaptic: vi.fn(),
}));

const purchase = {
  operation_id: "operation",
  tickets: [
    { id: "one", public_number: 101, symbols: [1, 2, 3], prize_amount: 5_000 },
    { id: "two", public_number: 102, symbols: [4, 5, 6], prize_amount: 0 },
    { id: "three", public_number: 103, symbols: [7, 8, 1], prize_amount: 1_000 },
  ],
  total_cost: 6_000,
  total_prize: 6_000,
  balance_after: 20_000,
  already_processed: false,
};

beforeEach(() => {
  vi.useFakeTimers();
  vi.mocked(miniAppApi.kasperLiveHistory).mockResolvedValue([]);
  vi.mocked(miniAppApi.kasperLivePurchase).mockResolvedValue(purchase);
});

afterEach(() => {
  vi.useRealTimers();
});

it("buys three tickets once, blocks repeat input and reveals them together", async () => {
  const settled = vi.fn();
  render(<KasperLiveView initData="signed" balance={30_000} onClose={vi.fn()} onSettled={settled} />);

  fireEvent.click(screen.getByRole("button", { name: /3 билета/ }));
  expect(screen.getByText("Создаём билет")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /1 билет/ })).not.toBeInTheDocument();
  expect(miniAppApi.kasperLivePurchase).toHaveBeenCalledWith("signed", 3, expect.any(String));

  await act(async () => { await vi.advanceTimersByTimeAsync(2_500); });

  const result = screen.getByText("ЭФИР ЗАВЕРШЁН").closest("section");
  expect(result).not.toBeNull();
  expect(within(result!).getAllByText(/№ 10/)).toHaveLength(3);
  expect(settled).toHaveBeenCalledWith(purchase);
  expect(screen.getByRole("button", { name: "Купить ещё" })).toBeInTheDocument();
});
