import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import GrandPicker from "./GrandPicker";
import { webApi } from "./api";
import type { Lottery } from "./types";

vi.mock("./api", () => ({ ApiError: class extends Error {}, webApi: { purchase: vi.fn() } }));

test("Grand purchase keeps both fields and reuses the key after a transport failure", async () => {
  const lottery: Lottery = { code: "weekly", name: "Casper Grand", ruleset_code: "grand_fixed_5_35_2_5", kind: "WEEKLY", numbers_to_pick: 7, max_number: 40, primary_numbers_to_pick: 5, primary_max_number: 35, secondary_numbers_to_pick: 2, secondary_max_number: 5, secondary_storage_offset: 35, ticket_price: 50000, jackpot: 5000000000, draw_number: 1, scheduled_at: "2099-10-11T17:00:00Z", sales_close_at: "2099-10-11T16:55:00Z", purchase_available: true, player_ticket_count: 0, sales_status: "OPEN", max_tickets_per_purchase: 100 };
  vi.mocked(webApi.purchase).mockRejectedValueOnce(new Error("timeout")).mockResolvedValueOnce({ ticket_ids: ["ticket"], total_cost: 50000, balance_after: 100000 });
  const onBought = vi.fn();
  render(<GrandPicker lottery={lottery} onClose={vi.fn()} onBought={onBought} />);
  for (const n of [4,13,21,28,35]) fireEvent.click(screen.getByRole("button", { name: `Основные числа ${n}` }));
  for (const n of [2,5]) fireEvent.click(screen.getByRole("button", { name: `Золотые шары ${n}` }));
  fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));
  await waitFor(() => expect(onBought).toHaveBeenCalledOnce());
  const calls = vi.mocked(webApi.purchase).mock.calls;
  expect(calls[0][1]).toEqual([[4,13,21,28,35,37,40]]);
  expect(calls[0][2]).toEqual(calls[1][2]);
});
