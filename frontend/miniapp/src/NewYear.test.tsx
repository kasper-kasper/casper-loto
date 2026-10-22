import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { NewYearHeader, NewYearRules, NewYearTicketDetail, NewYearPurchaseNotice } from "./NewYear";
import { NEW_YEAR_SYMBOLS } from "./newYearSymbols";
import { TicketComposer } from "./TicketComposer";
import { LotteryCatalog } from "./LotteryCatalog";
import { Today } from "./Today";
import { LiveView } from "./LiveView";
import type { Lottery, Ticket, LiveDraw } from "./types";

vi.mock("./telegram", () => ({ selectionHaptic: vi.fn(), liveStartHaptic: vi.fn() }));
const lottery: Lottery = {
  code: "newyear2027", name: "Новогоднее лото 2027", kind: "DAILY",
  numbers_to_pick: 3, max_number: 12, ticket_price: 10_000, jackpot: 0,
  draw_number: 1, scheduled_at: "2026-10-21T18:15:00Z", sales_close_at: "2026-10-21T18:13:00Z",
  sales_open: true, purchase_available: true, sales_status: "OPEN", player_ticket_count: 0,
  max_tickets_per_purchase: 101, max_tickets_per_user_per_draw: 101,
};
const ticket: Ticket = {
  id: "ny-1", public_number: 1, lottery_code: lottery.code, lottery_name: lottery.name,
  draw_number: 1, scheduled_at: lottery.scheduled_at!, numbers: [1, 4, 12],
  purchase_price: 10_000, source: "MANUAL", status: "PURCHASED", matches: null, prize_amount: 0, winning_numbers: null,
};
function composer(overrides: Partial<Lottery> = {}) {
  const onBuy = vi.fn().mockResolvedValue(false);
  const rendered = render(<TicketComposer lottery={{ ...lottery, ...overrides }} balance={1_000_000} now={0} purchasing={false} favorites={[]} onBuy={onBuy} onBuyMany={vi.fn()} onSaveFavorite={vi.fn()} onDeleteFavorite={vi.fn()} />);
  return { onBuy, ...rendered };
}
describe("New Year 2027", () => {
  it("supports quick triples, five draws, saving and restoring symbol favorites", () => {
    const onBuy = vi.fn().mockResolvedValue(false);
    const onBuyMany = vi.fn();
    const onSaveFavorite = vi.fn();
    const onDeleteFavorite = vi.fn();
    render(<TicketComposer lottery={lottery} balance={10_000_000} now={0} purchasing={false} favorites={[{ id: "saved-triple", numbers: [2, 7, 9] }]} onBuy={onBuy} onBuyMany={onBuyMany} onSaveFavorite={onSaveFavorite} onDeleteFavorite={onDeleteFavorite} />);
    fireEvent.click(screen.getByText("Повторы и избранное"));
    fireEvent.click(screen.getByRole("button", { name: "5 тиражей" }));
    fireEvent.click(screen.getByRole("button", { name: "Купить 25 случайных билетов" }));
    expect(onBuyMany).toHaveBeenCalledWith(expect.any(Array), 5);
    const combinations = onBuyMany.mock.calls[0][0] as number[][];
    expect(combinations).toHaveLength(25);
    expect(combinations.every(c => new Set(c).size === 3 && c.every(n => n >= 1 && n <= 12))).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Выбрать сохранённую тройку" }));
    fireEvent.click(screen.getByRole("button", { name: "Купить на 5 тиражей" }));
    expect(onBuy).toHaveBeenCalledWith([2, 7, 9], 5, "random");
    fireEvent.click(screen.getByRole("button", { name: "Удалить из избранного" }));
    expect(onDeleteFavorite).toHaveBeenCalledWith("saved-triple");
    fireEvent.click(screen.getByRole("button", { name: "Случайные символы" }));
    // Make a distinct deterministic manual triple before saving.
    for (const button of screen.getByRole("group", { name: "Игровые символы" }).querySelectorAll('[aria-pressed="true"]')) fireEvent.click(button);
    for (const name of ["Мандарины", "Часы", "Колокольчик"]) fireEvent.click(screen.getByRole("button", { name }));
    fireEvent.click(screen.getByRole("button", { name: "Сохранить комбинацию" }));
    expect(onSaveFavorite).toHaveBeenCalledWith([1, 4, 12]);
  });
  it("restricts quick purchases to remaining capacity and locks all actions while purchasing", () => {
    const props = { lottery: { ...lottery, player_ticket_count: 100 }, balance: 1_000_000, now: 0, purchasing: false, favorites: [], onBuy: vi.fn(), onBuyMany: vi.fn(), onSaveFavorite: vi.fn(), onDeleteFavorite: vi.fn() };
    const { rerender } = render(<TicketComposer {...props} />);
    expect(screen.getByRole("button", { name: "Купить 1 случайный билет" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Купить 5 случайных билетов" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Купить 25 случайных билетов" })).toBeDisabled();
    rerender(<TicketComposer {...props} purchasing />);
    expect(screen.getByRole("button", { name: "Купить 1 случайный билет" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "5 тиражей" })).toBeDisabled();
  });
  it("preserves the selected field when a purchase notice appears and clears", () => {
    const view = (notice: string | null) => <><NewYearPurchaseNotice error={null} notice={notice} /><TicketComposer lottery={lottery} balance={1_000_000} now={0} purchasing={false} favorites={[]} onBuy={vi.fn()} onBuyMany={vi.fn()} onSaveFavorite={vi.fn()} onDeleteFavorite={vi.fn()} /></>;
    const { rerender } = render(view(null));
    const field = screen.getByRole("group", { name: "Игровые символы" });
    fireEvent.click(within(field).getByRole("button", { name: "Открытка" }));
    rerender(view("Билет куплен"));
    expect(screen.getByText("Билет куплен")).toHaveClass("ny-purchase-notice");
    expect(screen.getByRole("group", { name: "Игровые символы" })).toBe(field);
    rerender(view(null));
    expect(within(field).getByRole("button", { name: "Открытка" })).toHaveAttribute("aria-pressed", "true");
  });
  it("keeps the 12 symbol order and allows exactly three unique objects", () => {
    const { container, onBuy } = composer();
    const grid = within(screen.getByRole("group", { name: "Игровые символы" }));
    expect(grid.getAllByRole("button").map(el => el.getAttribute("aria-label"))).toEqual(NEW_YEAR_SYMBOLS);
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeDisabled();
    for (const name of ["Мандарины", "Часы", "Колокольчик", "Оливье"]) fireEvent.click(grid.getByRole("button", { name }));
    expect(grid.getByRole("button", { name: "Оливье" })).toHaveAttribute("aria-pressed", "false");
    expect(container.querySelectorAll('.ny-object-grid [aria-pressed="true"]')).toHaveLength(3);
    expect(container.querySelectorAll('.ny-ticket-strip .ny-object')).toHaveLength(3);
    fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));
    expect(onBuy).toHaveBeenCalledWith([1, 4, 12], 1, "manual");
    fireEvent.click(grid.getByRole("button", { name: "Часы" }));
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeDisabled();
  });
  it("keeps rapid toggles, count and paper strip consistent", () => {
    const { container } = composer();
    const button = screen.getByRole("button", { name: "Мандарины" });
    for (let i = 0; i < 11; i++) fireEvent.click(button);
    expect(screen.getByRole("status")).toHaveTextContent("1 / 3");
    expect(container.querySelectorAll('.ny-ticket-strip .ny-object')).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Случайные символы" }));
    expect(screen.getByRole("status")).toHaveTextContent("3 / 3");
    expect(container.querySelectorAll('.ny-object-grid [aria-pressed="true"]')).toHaveLength(3);
  });
  it("never enables checkout after sales close", () => {
    composer({ purchase_available: false });
    fireEvent.click(screen.getByRole("button", { name: "Случайные символы" }));
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeDisabled();
  });
  it("uses the same named images on a stored receipt and displays server payout", () => {
    render(<NewYearTicketDetail ticket={{ ...ticket, status: "SETTLED", winning_numbers: [1, 2, 4], matches: 2, prize_amount: 30_000 }} onClose={vi.fn()} />);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getAllByRole("img")).toHaveLength(6);
    expect(within(dialog).getByText("Совпадений", { exact: false })).toHaveTextContent("совпадений 2");
    expect(within(dialog).getByText("30 000")).toBeInTheDocument();
    expect(within(dialog).queryByText(/Джекпот|Главный приз/)).not.toBeInTheDocument();
  });
  it("shows the shared million only inside the rules", () => {
    const { container } = render(<NewYearRules />);
    fireEvent.click(screen.getByText("Правила и выплаты"));
    expect(container).toHaveTextContent("1 000 000 CAS");
    expect(container).toHaveTextContent("101");
    expect(container).toHaveTextContent("30 000 CAS");
  });
  it("has a holiday catalog card without a jackpot block", () => {
    const onOpen = vi.fn();
    const { container } = render(<LotteryCatalog lotteries={[lottery]} onOpen={onOpen} now={0} selectedFilter="holiday" />);
    fireEvent.click(screen.getByRole("button", { name: `Открыть ${lottery.name}` }));
    expect(onOpen).toHaveBeenCalledWith("newyear2027");
    expect(container).toHaveTextContent("3 символа из 12");
    expect(container).not.toHaveTextContent("Джекпот");
  });
  it("keeps the main header and home feature free of prize-fund headlines", () => {
    const { container } = render(<><NewYearHeader lottery={lottery} now={0} onClose={vi.fn()} /><Today lotteries={[lottery]} now={Date.parse("2026-10-21T17:00:00Z")} highlights={null} totalTicketCount={0} totalWinningTicketCount={0} monthlyTotalPayout={0} onOpen={vi.fn()} onCatalog={vi.fn()} onTickets={vi.fn()} onArchive={vi.fn()} /></>);
    expect(container.querySelector('.home-feature-newyear2027')).not.toBeNull();
    expect(container).not.toHaveTextContent(/Джекпот|Главный приз|1 000 000/);
  });
  it("reveals symbol art in the broadcast and has no jackpot facts", () => {
    const draw: LiveDraw = {
      lottery_code: lottery.code, lottery_name: lottery.name, lottery_kind: "DAILY", draw_number: 1,
      scheduled_at: lottery.scheduled_at!, sales_close_at: lottery.sales_close_at!, status: "SCHEDULED", winning_numbers: null, jackpot: 0,
      player_ticket_count: 0, player_winning_ticket_count: 0, player_best_matches: null, player_total_prize: 0, highlighted_tickets: [],
      live_starts_at: lottery.scheduled_at!, reveal_at: [], live_ends_at: lottery.scheduled_at!, sales_status: "OPEN",
    };
    const { container } = render(<LiveView feed={{ server_time: "", latest_completed: null, next_scheduled: draw, recent_completed: [] }} now={Date.parse("2026-10-21T17:00:00Z")} loading={false} onPlay={vi.fn()} onTickets={vi.fn()} />);
    expect(container.querySelectorAll('.ny-symbol-slot')).toHaveLength(3);
    expect(container).not.toHaveTextContent(/Джекпот|Главный приз|1 000 000/);
  });
});
