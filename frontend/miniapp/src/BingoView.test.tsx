import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { BingoTicketDetail, BingoView } from "./BingoView";
import { miniAppApi } from "./api";
import type { Lottery, Ticket } from "./types";

vi.mock("./api", () => ({ ApiError: class extends Error {}, miniAppApi: { bingoInventory: vi.fn(), bingoLive: vi.fn(), bingoPurchase: vi.fn(), tickets: vi.fn() } }));

const lottery: Lottery = { code: "bingo", name: "Casper Bingo", kind: "DAILY", numbers_to_pick: 12, max_number: 60, ticket_price: 50000, jackpot: 10000000000, draw_number: 1, scheduled_at: "2026-09-06T19:00:00Z", sales_close_at: "2026-09-06T18:58:00Z", sales_open: true, purchase_available: true, player_ticket_count: 49, sales_status: "OPEN", max_tickets_per_purchase: 50, max_tickets_per_user_per_draw: 50 };
const numbers = [1, 8, 21, 59, 2, 15, 29, 60, 3, 17, 42, 51];
const inventory = { draw_id: "draw", draw_number: 1, scheduled_at: lottery.scheduled_at!, price: 50000, has_more: false, kasper_set_available: true, tickets: [1, 2].map(i => ({ id: `pool-${i}`, pool_position: i, numbers })) };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(miniAppApi.bingoInventory).mockResolvedValue(inventory);
  vi.mocked(miniAppApi.bingoLive).mockResolvedValue({ server_time: "2026-09-06T18:00:00Z", draw: null, rules: { total_moves: 58, jackpot_move: 28, tour_moves: [18, 34], tour_prizes: [100000, 500000], pool_size: 2000 } });
  vi.mocked(miniAppApi.tickets).mockResolvedValue({ tickets: [], total: 0, has_more: false });
});

test("selecting the 50th ticket blocks another selection and purchases its pool ID", async () => {
  vi.mocked(miniAppApi.bingoPurchase).mockResolvedValue({ operation_id: "op", draw_id: "draw", draw_ids: ["draw"], draw_count: 1, ticket_ids: ["ticket"], total_cost: 50000, balance_after: 50000, already_processed: false });
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn().mockResolvedValue(undefined)} />);
  const choices = await screen.findAllByRole("button", { name: "Выбрать вариант билета" });
  fireEvent.click(choices[0]);
  expect(choices[1]).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Купить билеты" }));
  await waitFor(() => expect(miniAppApi.bingoPurchase).toHaveBeenCalledWith("auth", "draw", { ticketIds: ["pool-1"] }, expect.any(String)));
  expect(await screen.findByText("Куплено: 1 · 50 000 CAS")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Casper Bingo" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Мои билеты →" })).toBeInTheDocument();
});

test("uncertain purchase retry reuses the same operation key", async () => {
  vi.mocked(miniAppApi.bingoPurchase).mockRejectedValue(new Error("Connection lost"));
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  fireEvent.click((await screen.findAllByRole("button", { name: "Выбрать вариант билета" }))[0]);
  fireEvent.click(screen.getByRole("button", { name: "Купить билеты" }));
  fireEvent.click(await screen.findByRole("button", { name: "Проверить покупку" }));
  await waitFor(() => expect(miniAppApi.bingoPurchase).toHaveBeenCalledTimes(2));
  expect(vi.mocked(miniAppApi.bingoPurchase).mock.calls[0]).toEqual(vi.mocked(miniAppApi.bingoPurchase).mock.calls[1]);
});

test("the detailed ticket preserves three rows and marks only revealed numbers", () => {
  const ticket: Ticket = { id: "ticket", public_number: 1, lottery_code: "bingo", lottery_name: "Casper Bingo", draw_number: 1, scheduled_at: lottery.scheduled_at!, numbers, purchase_price: 50000, source: "MANUAL", status: "SETTLED", matches: 10, prize_amount: 100000, winning_numbers: numbers.filter(n => n < 59), bingo_result: { moves: [30, 61, 61], amounts: [100000, 0, 0] } };
  const { container } = render(<BingoTicketDetail ticket={ticket} onClose={vi.fn()} />);
  expect(container.querySelectorAll(".bingo-grid > div")).toHaveLength(3);
  expect(container.querySelectorAll(".bingo-grid .hit")).toHaveLength(10);
  expect(screen.getByLabelText("59")).toBeInTheDocument();
  expect(screen.getByText("KB-000001")).toBeInTheDocument();
  expect(screen.getByText("Совпало 10 из 12")).toBeInTheDocument();
});

test("tapping a paper ticket selects it while inspect opens its detail", async () => {
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  const paper = (await screen.findAllByRole("button", { name: "Выбрать вариант билета" }))[0];
  fireEvent.click(paper);
  expect(paper).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(screen.getAllByRole("button", { name: /Рассмотреть/ })[0]);
  expect(screen.getByRole("dialog")).toBeInTheDocument();
});

test("quick buy all uses the remaining player allowance", async () => {
  vi.mocked(miniAppApi.bingoPurchase).mockResolvedValue({ operation_id: "op", draw_id: "draw", draw_ids: ["draw"], draw_count: 1, ticket_ids: ["ticket"], total_cost: 50000, balance_after: 50000, already_processed: false });
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn().mockResolvedValue(undefined)} />);
  fireEvent.click(screen.getByText("Подбор по числам и наборы"));
  fireEvent.click(await screen.findByRole("button", { name: "Купить все доступные · 1" }));
  await waitFor(() => expect(miniAppApi.bingoPurchase).toHaveBeenCalledWith("auth", "draw", { quantity: 1, requiredNumbers: [] }, expect.any(String)));
});

test("three favorite numbers filter the available pool", async () => {
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  fireEvent.click(screen.getByText("Подбор по числам и наборы"));
  for (const [index, value] of [2, 9, 16].entries()) fireEvent.change(screen.getByLabelText(`Любимое число ${index + 1}`), { target: { value: String(value) } });
  fireEvent.click(screen.getByRole("button", { name: "Найти билеты" }));
  await waitFor(() => expect(miniAppApi.bingoInventory).toHaveBeenCalledWith("auth", 0, [2, 9, 16]));
  expect(screen.getByText("Нашли варианты: 2")).toBeInTheDocument();
});

test("favorite search supports one or two numbers", async () => {
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  fireEvent.click(screen.getByText("Подбор по числам и наборы"));
  await screen.findAllByRole("button", { name: "Выбрать вариант билета" });
  const search = screen.getByRole("button", { name: "Найти билеты" });
  expect(search).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Любимое число 1"), { target: { value: "2" } });
  expect(search).toBeEnabled();
  fireEvent.click(search);
  await waitFor(() => expect(miniAppApi.bingoInventory).toHaveBeenCalledWith("auth", 0, [2]));
  fireEvent.change(screen.getByLabelText("Любимое число 2"), { target: { value: "9" } });
  fireEvent.click(search);
  await waitFor(() => expect(miniAppApi.bingoInventory).toHaveBeenCalledWith("auth", 0, [2, 9]));
});

test("favorite search errors stay inside the search card", async () => {
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  fireEvent.click(screen.getByText("Подбор по числам и наборы"));
  await screen.findAllByRole("button", { name: "Выбрать вариант билета" });
  vi.mocked(miniAppApi.bingoInventory).mockRejectedValueOnce(new Error("Поиск временно недоступен"));
  for (const [index, value] of [2, 9, 16].entries()) fireEvent.change(screen.getByLabelText(`Любимое число ${index + 1}`), { target: { value: String(value) } });
  fireEvent.click(screen.getByRole("button", { name: "Найти билеты" }));
  expect(await screen.findByText("Поиск не сработал. Попробуйте ещё раз.")).toHaveClass("bingo-search-feedback");
  expect(document.querySelector(".bingo-message.is-error")).not.toBeInTheDocument();
});

test("shows favorite-number mistakes inside the search card", async () => {
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  fireEvent.click(screen.getByText("Подбор по числам и наборы"));
  await screen.findAllByRole("button", { name: "Выбрать вариант билета" });
  for (const [index, value] of [2, 2, 3].entries()) fireEvent.change(screen.getByLabelText(`Любимое число ${index + 1}`), { target: { value: String(value) } });
  fireEvent.click(screen.getByRole("button", { name: "Найти билеты" }));
  expect(screen.getByRole("alert")).toHaveTextContent("Введите до трёх разных чисел от 1 до 60.");
  expect(miniAppApi.bingoInventory).toHaveBeenCalledTimes(1);
});

test("Casper set requests ten tickets with its four numbers", async () => {
  const roomyLottery = { ...lottery, player_ticket_count: 0 };
  vi.mocked(miniAppApi.bingoPurchase).mockResolvedValue({ operation_id: "op", draw_id: "draw", draw_ids: ["draw"], draw_count: 1, ticket_ids: Array.from({ length: 10 }, (_, index) => `ticket-${index}`), total_cost: 500000, balance_after: 500000, already_processed: false });
  render(<BingoView lottery={roomyLottery} initData="auth" now={0} balance={1000000} onClose={vi.fn()} onPurchased={vi.fn().mockResolvedValue(undefined)} />);
  fireEvent.click(screen.getByText("Подбор по числам и наборы"));
  fireEvent.click(await screen.findByRole("button", { name: /НАБОР КАСПЕРА/ }));
  await waitFor(() => expect(miniAppApi.bingoPurchase).toHaveBeenCalledWith("auth", "draw", { quantity: 10, requiredNumbers: [28, 16, 2, 9] }, expect.any(String)));
});

test("the ticket deck keeps multiple selections and the original row order without purchasing", async () => {
  render(<BingoView lottery={{ ...lottery, player_ticket_count: 0 }} initData="auth" now={0} balance={1000000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  const choices = await screen.findAllByRole("button", { name: "Выбрать вариант билета" });
  const firstRows = choices[0].querySelectorAll(".edition-grid > div");
  expect(Array.from(firstRows).map(row => Array.from(row.querySelectorAll("b")).map(n => Number(n.textContent)))).toEqual([numbers.slice(0, 4), numbers.slice(4, 8), numbers.slice(8, 12)]);
  fireEvent.click(choices[0]);
  fireEvent.click(choices[1]);
  expect(choices[0]).toHaveAttribute("aria-pressed", "true");
  expect(choices[1]).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("Выбрано билетов: 2")).toBeInTheDocument();
  fireEvent.click(choices[0]);
  expect(choices[0]).toHaveAttribute("aria-pressed", "false");
  expect(choices[1]).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("Выбрано билетов: 1")).toBeInTheDocument();
  expect(miniAppApi.bingoPurchase).not.toHaveBeenCalled();
});

test("ticket inspection closes with Escape and restores focus to the originating card", async () => {
  render(<BingoView lottery={lottery} initData="auth" now={0} balance={100000} onClose={vi.fn()} onPurchased={vi.fn()} />);
  const inspect = (await screen.findAllByRole("button", { name: /Рассмотреть/ }))[0];
  inspect.focus();
  fireEvent.click(inspect);
  expect(screen.getByRole("dialog").querySelector(".bingo-edition")).toBeInTheDocument();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(inspect).toHaveFocus();
  expect(miniAppApi.bingoPurchase).not.toHaveBeenCalled();
});
