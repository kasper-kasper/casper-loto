import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LotteryCatalog } from "./LotteryCatalog";
import { LiveView } from "./LiveView";
import { MiniTicketDetail } from "./MiniTicket";
import { MiniHeader } from "./MiniIdentity";
import { TicketComposer } from "./TicketComposer";
import type { LiveDraw, Lottery, Ticket } from "./types";
import miniClover from "./assets/lotteries/mini-clover.svg";

vi.mock("./telegram", () => ({ selectionHaptic: vi.fn(), liveStartHaptic: vi.fn() }));

const lottery: Lottery = {
  code: "mini", name: "Casper Mini", kind: "DAILY", ruleset_code: "casper_mini_6_30",
  numbers_to_pick: 6, max_number: 30, ticket_price: 10_000, jackpot: 20_000_000,
  draw_number: 1, scheduled_at: "2026-10-21T07:30:00Z", sales_close_at: "2026-10-21T07:28:00Z",
  sales_open: true, purchase_available: true, sales_status: "OPEN", player_ticket_count: 0,
  max_tickets_per_purchase: 100, max_tickets_per_user_per_draw: 500,
  fixed_payouts: {2: 10_000, 3: 30_000, 4: 140_000, 5: 1_000_000},
};
const ticket: Ticket = {
  id: "mini-ticket", public_number: 9924, lottery_code: "mini", lottery_name: "Casper Mini",
  draw_number: 144, scheduled_at: "2026-10-21T07:30:00Z", numbers: [3, 8, 12, 19, 24, 30],
  purchase_price: 10_000, source: "MANUAL", status: "PURCHASED", matches: null, prize_amount: 0, winning_numbers: null,
};
function composer(overrides: Partial<Lottery> = {}) {
  const onBuy = vi.fn().mockResolvedValue(false), onBuyMany = vi.fn().mockResolvedValue(false);
  render(<TicketComposer lottery={{...lottery, ...overrides}} balance={100_000_000} now={Date.parse("2026-10-21T07:00:00Z")} purchasing={false} favorites={[]} onBuy={onBuy} onBuyMany={onBuyMany} onSaveFavorite={vi.fn()} onDeleteFavorite={vi.fn()} />);
  return { onBuy, onBuyMany };
}

describe("Casper Mini", () => {
  it("has its own coupon and four-leaf emblem instead of the classic drum", () => {
    const { container } = render(<MiniHeader lottery={lottery} now={0} onClose={vi.fn()} />);
    expect(container.querySelector(".mini-jackpot-band img")).toHaveAttribute("src", miniClover);
    expect(container.querySelector(".classic-machine")).toBeNull();
  });
  it("appears in the draw catalogue with its classic label and opens by its own code", () => {
    const onOpen = vi.fn();
    render(<LotteryCatalog lotteries={[lottery]} onOpen={onOpen} now={0} selectedFilter="draw" />);
    expect(screen.getByText("Классика")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Открыть Casper Mini" }));
    expect(onOpen).toHaveBeenCalledWith("mini");
  });
  it("selects exactly six numbers, removes balls, and submits a manual ticket", () => {
    const { onBuy } = composer();
    const grid = screen.getByLabelText("Числа");
    expect(within(grid).getAllByRole("button")).toHaveLength(30);
    for (const number of [3, 8, 12, 19, 24, 30, 29]) fireEvent.click(within(grid).getByRole("button", { name: String(number) }));
    expect(within(grid).getByRole("button", { name: "29" })).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(screen.getByRole("button", { name: "Убрать число 12" }));
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeDisabled();
    fireEvent.click(within(grid).getByRole("button", { name: "12" }));
    fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));
    expect(onBuy).toHaveBeenCalledWith([3, 8, 12, 19, 24, 30], 1, "manual");
    expect(screen.getByLabelText("Классический билет 6 из 30")).toBeInTheDocument();
    expect(document.querySelector(".mini-coupon")).not.toBeNull();
    expect(document.querySelector(".classic-coupon")).toBeNull();
  });
  it("autofills and quick-buys only distinct numbers from 1 to 30", () => {
    const { onBuy, onBuyMany } = composer();
    fireEvent.click(screen.getByRole("button", { name: "Случайные числа" }));
    fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));
    expect(onBuy).toHaveBeenCalledWith(expect.any(Array), 1, "random");
    fireEvent.click(screen.getByRole("button", { name: "Купить 25 случайных билетов" }));
    const combinations = onBuyMany.mock.calls[0][0] as number[][];
    expect(combinations).toHaveLength(25);
    for (const numbers of [onBuy.mock.calls[0][0] as number[], ...combinations]) {
      expect(new Set(numbers).size).toBe(6);
      expect(numbers.every(n => n >= 1 && n <= 30)).toBe(true);
    }
  });
  it("respects the remaining player capacity and total limit when repeating five draws", () => {
    composer({ player_ticket_count: 496 });
    expect(screen.getByRole("button", { name: "Купить 5 случайных билетов" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Купить 1 случайный билет" })).toBeEnabled();
  });
  it("keeps five-draw quick purchases within 100 total tickets", () => {
    composer();
    fireEvent.click(screen.getByRole("button", { name: "5 тиражей" }));
    expect(screen.getByRole("button", { name: "Купить 25 случайных билетов" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Купить 5 случайных билетов" })).toBeEnabled();
  });
  it("renders the server prize table and official Moscow schedule", () => {
    composer();
    const rules = screen.getByText("Правила и выигрыши").closest("details")!;
    expect(rules).toHaveTextContent("10:30 и 19:15 МСК");
    expect(rules).toHaveTextContent("Europe/Moscow");
    expect(rules).toHaveTextContent("500");
    const rows = rules.querySelectorAll("dl > div");
    expect(rows[2]).toHaveTextContent("10 000");
    expect(rows[3]).toHaveTextContent("30 000");
    expect(rows[4]).toHaveTextContent("140 000");
    expect(rows[5]).toHaveTextContent("1 000 000");
  });
  it("shows a purchased ticket with the six-ball combination and thirty-number field", () => {
    const onClose = vi.fn();
    render(<MiniTicketDetail ticket={ticket} onClose={onClose} />);
    expect(screen.getByRole("dialog")).toHaveTextContent("Билет #9924");
    expect(screen.getByText("Ожидает тиража")).toBeInTheDocument();
    expect(document.querySelectorAll(".mini-receipt-grid i")).toHaveLength(30);
    expect(document.querySelectorAll(".mini-receipt-grid .selected")).toHaveLength(6);
    expect(document.querySelectorAll(".mini-receipt-combination i")).toHaveLength(6);
    fireEvent.click(screen.getByRole("button", { name: "Закрыть билет" }));
    expect(onClose).toHaveBeenCalledOnce();
  });
  it("uses the stored payout and marks only matching numbers on a settled ticket", () => {
    render(<MiniTicketDetail ticket={{...ticket, status: "SETTLED", matches: 2, winning_numbers: [1, 2, 3, 8, 20, 21], prize_amount: 10_000}} onClose={vi.fn()} />);
    expect(screen.getByText("Выигрыш зачислен")).toBeInTheDocument();
    expect(document.querySelectorAll(".mini-receipt-grid .matched")).toHaveLength(2);
    expect(document.querySelector(".mini-receipt-result")).toHaveTextContent("10 000");
  });
  it("uses the classic six-ball broadcast in its own theme", () => {
    const start = Date.parse(lottery.scheduled_at!);
    const draw: LiveDraw = {
      lottery_code: "mini", lottery_name: "Casper Mini", lottery_kind: "DAILY", draw_number: 1,
      scheduled_at: lottery.scheduled_at!, status: "COMPLETED", winning_numbers: [3, 8, 12, 19, 24, 30], jackpot: 20_004_000,
      player_ticket_count: 1, player_winning_ticket_count: 1, player_best_matches: 6, player_total_prize: 20_004_000,
      highlighted_tickets: [{ public_number: 1, numbers: [3, 8, 12, 19, 24, 30], matches: 2, prize_amount: 0 }],
      sales_close_at: lottery.sales_close_at!, sales_status: "COMPLETED", live_starts_at: lottery.scheduled_at!,
      reveal_at: [4000, 7200, 10400, 13600, 16800, 20000].map(ms => new Date(start + ms).toISOString()),
      live_ends_at: new Date(start + 23200).toISOString(),
    };
    render(<LiveView feed={{ server_time: new Date(start + 7300).toISOString(), latest_completed: draw, recent_completed: [draw], next_scheduled: null }} now={start + 7300} loading={false} onPlay={vi.fn()} onTickets={vi.fn()} />);
    expect(screen.getByText("КЛАССИКА · 6 ИЗ 30")).toBeInTheDocument();
    expect(screen.getByText("ШАР 2 ИЗ 6")).toBeInTheDocument();
    expect(document.querySelector(".lottery-mini .khan-draw-console")).not.toBeNull();
    expect(document.querySelectorAll(".khan-ball-rack i.filled")).toHaveLength(2);
  });
});
