import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { Today } from "./Today";
import type { Lottery } from "./types";
import miniClover from "./assets/lotteries/mini-clover.svg";

const lottery: Lottery = {
  code: "khan", name: "6 из 36", kind: "DAILY", numbers_to_pick: 6, max_number: 36,
  jackpot: 33_456_000, ticket_price: 48_000, draw_number: 174,
  scheduled_at: "2026-09-28T17:00:00Z", sales_close_at: "2026-09-28T16:58:00Z",
  sales_open: true, purchase_available: true, player_ticket_count: 0, sales_status: "OPEN",
  max_tickets_per_purchase: 1000, max_tickets_per_user_per_draw: 5000,
};
const props = { lotteries: [lottery], now: Date.parse("2026-09-28T16:00:00Z"), highlights: null, totalTicketCount: 42, totalWinningTicketCount: 7, monthlyTotalPayout: 15000, onOpen: vi.fn(), onCatalog: vi.fn(), onTickets: vi.fn(), onArchive: vi.fn() };

it("uses Mini's clover artwork when Mini is the next home draw", () => {
  const { container } = render(<Today {...props} lotteries={[{ ...lottery, code: "mini", name: "Casper Mini" }]} />);
  expect(container.querySelector(".home-feature-mini .home-feature-art img")).toHaveAttribute("src", miniClover);
});

it("keeps personal home tickets and catalog accessible with and without active tickets", () => {
  const onTickets = vi.fn(), onCatalog = vi.fn();
  const { rerender } = render(<Today {...props} onTickets={onTickets} onCatalog={onCatalog} />);
  fireEvent.click(screen.getByRole("button", { name: /Все лотереи/ }));
  fireEvent.click(screen.getByRole("button", { name: /Мои билеты/ }));
  expect(onTickets).toHaveBeenCalledOnce();
  expect(onCatalog).toHaveBeenCalledOnce();
  rerender(<Today {...props} lotteries={[{ ...lottery, player_ticket_count: 5 }]} onTickets={onTickets} onCatalog={onCatalog} />);
  fireEvent.click(screen.getByRole("button", { name: /Мои билеты/ }));
  expect(onTickets).toHaveBeenCalledTimes(2);
  expect(screen.getByText("5 билетов ждут тиража")).toBeInTheDocument();
});

it.each(["live", "result"])("opens the server-highlighted %s event in the live/results screen", phase => {
  const onOpen = vi.fn();
  render(<Today {...props} onOpen={onOpen} highlights={{ last_jackpot: null, next_event: { lottery_code: "khan", scheduled_at: lottery.scheduled_at!, draw_number: 175, player_ticket_count: 2, jackpot: 44000, phase } }} />);
  const event = screen.getByRole("region", { name: "Ближайший тираж" });
  expect(within(event).getByLabelText("44 000 CAS")).toBeInTheDocument();
  fireEvent.click(within(event).getByRole("button"));
  expect(onOpen).toHaveBeenCalledWith("khan", true);
});

it("keeps empty schedules usable and includes Moscow dates for future events", () => {
  const { rerender } = render(<Today {...props} lotteries={[]} />);
  expect(screen.getByRole("heading", { name: "Новые тиражи скоро" })).toBeInTheDocument();
  rerender(<Today {...props} lotteries={[{ ...lottery, code: "weekly", name: "Casper Grand", scheduled_at: "2026-09-30T17:00:00Z" }, lottery]} />);
  const event = screen.getByRole("region", { name: "Ближайший тираж" });
  expect(within(event).getByRole("heading", { name: "6 из 36" })).toBeInTheDocument();
  expect(screen.getByText("30 сент., 20:00")).toBeInTheDocument();
  expect(within(event).getByText("01:00:00")).toBeInTheDocument();
});

it("opens the draw archive from the home sections", () => {
  const onArchive = vi.fn();
  render(<Today {...props} onArchive={onArchive} />);
  fireEvent.click(screen.getByRole("button", { name: /Архив тиражей/ }));
  expect(onArchive).toHaveBeenCalledOnce();
});
