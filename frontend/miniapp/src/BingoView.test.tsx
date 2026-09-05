import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { BingoTicketDetail, BingoView } from "./BingoView";
import { miniAppApi } from "./api";
import type { Lottery, Ticket } from "./types";

vi.mock("./api", () => ({ ApiError: class extends Error {}, miniAppApi: { bingoInventory: vi.fn(), bingoLive: vi.fn(), bingoPurchase: vi.fn(), tickets: vi.fn() } }));

const lottery: Lottery = { code: "bingo", name: "Kasper Bingo", kind: "DAILY", numbers_to_pick: 12, max_number: 60, ticket_price: 50000, jackpot: 10000000000, draw_number: 1, scheduled_at: "2026-09-06T19:00:00Z", sales_close_at: "2026-09-06T18:58:00Z", sales_open: true, purchase_available: true, player_ticket_count: 49, sales_status: "OPEN", max_tickets_per_purchase: 50, max_tickets_per_user_per_draw: 50 };
const numbers = [1, 8, 21, 59, 2, 15, 29, 60, 3, 17, 42, 51];
const inventory = { draw_id: "draw", draw_number: 1, scheduled_at: lottery.scheduled_at!, price: 50000, has_more: false, tickets: [1, 2].map(i => ({ id: `pool-${i}`, public_number: i, numbers })) };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(miniAppApi.bingoInventory).mockResolvedValue(inventory);
  vi.mocked(miniAppApi.bingoLive).mockResolvedValue({ server_time: "2026-09-06T18:00:00Z", draw: null, rules: { total_moves: 58, jackpot_move: 28, tour_prizes: [100000, 500000], pool_size: 2000 } });
  vi.mocked(miniAppApi.tickets).mockResolvedValue({ tickets: [], total: 0, has_more: false });
});

test("selecting the 50th ticket blocks another selection and purchases its pool ID", async () => {
  vi.mocked(miniAppApi.bingoPurchase).mockResolvedValue({ operation_id: "op", draw_id: "draw", draw_ids: ["draw"], draw_count: 1, ticket_ids: ["ticket"], total_cost: 50000, balance_after: 50000, already_processed: false });
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn().mockResolvedValue(undefined)} />);
  const choices = await screen.findAllByRole("button", { name: "+ Выбрать билет" });
  fireEvent.click(choices[0]);
  expect(choices[1]).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Купить билеты ↗" }));
  await waitFor(() => expect(miniAppApi.bingoPurchase).toHaveBeenCalledWith("auth", "draw", ["pool-1"], expect.any(String)));
  expect(await screen.findByText(/Ваши билеты готовы/)).toBeInTheDocument();
});

test("uncertain purchase retry reuses the same operation key", async () => {
  vi.mocked(miniAppApi.bingoPurchase).mockRejectedValue(new Error("Connection lost"));
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  fireEvent.click((await screen.findAllByRole("button", { name: "+ Выбрать билет" }))[0]);
  fireEvent.click(screen.getByRole("button", { name: "Купить билеты ↗" }));
  fireEvent.click(await screen.findByRole("button", { name: "Проверить покупку" }));
  await waitFor(() => expect(miniAppApi.bingoPurchase).toHaveBeenCalledTimes(2));
  expect(vi.mocked(miniAppApi.bingoPurchase).mock.calls[0]).toEqual(vi.mocked(miniAppApi.bingoPurchase).mock.calls[1]);
});

test("the detailed ticket preserves three rows and marks only revealed numbers", () => {
  const ticket: Ticket = { id: "ticket", public_number: 1, lottery_code: "bingo", lottery_name: "Kasper Bingo", draw_number: 1, scheduled_at: lottery.scheduled_at!, numbers, purchase_price: 50000, source: "MANUAL", status: "SETTLED", matches: 10, prize_amount: 100000, winning_numbers: numbers.filter(n => n < 59), bingo_result: { moves: [30, 61, 61], amounts: [100000, 0, 0] } };
  const { container } = render(<BingoTicketDetail ticket={ticket} onClose={vi.fn()} />);
  expect(container.querySelectorAll(".bingo-grid > div")).toHaveLength(3);
  expect(container.querySelectorAll(".bingo-grid .hit")).toHaveLength(10);
  expect(screen.getByLabelText("59")).toBeInTheDocument();
  expect(screen.getByText("KB-000001-000001")).toBeInTheDocument();
  expect(screen.getByText("Совпало 10 из 12")).toBeInTheDocument();
});

test("tapping a paper ticket selects it while inspect opens its detail", async () => {
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  const paper = await screen.findByRole("button", { name: "Выбрать билет 1" });
  fireEvent.click(paper);
  expect(paper).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(screen.getAllByRole("button", { name: /Рассмотреть/ })[0]);
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});
