import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LotteryCatalog } from "./LotteryCatalog";
import type { Lottery } from "./types";

const daily: Lottery = {
  code: "khan", name: "6 из 36", kind: "DAILY", numbers_to_pick: 6, max_number: 36,
  jackpot: 33_456_000, ticket_price: 48_000, draw_number: 174,
  scheduled_at: "2026-09-28T17:00:00Z", sales_close_at: "2026-09-28T16:58:00Z",
  sales_open: true, purchase_available: true, player_ticket_count: 0, sales_status: "OPEN",
  max_tickets_per_purchase: 1000, max_tickets_per_user_per_draw: 5000,
};
const weekly: Lottery = { ...daily, code: "weekly", name: "Casper Grand", kind: "WEEKLY", jackpot: 5_000_000_000, ticket_price: null };

const holiday: Lottery = { ...daily, code: "grob", name: "ГРОБ" };
const fast: Lottery = { ...daily, code: "pulse", name: "Casper PULSE" };
const now = Date.parse("2026-09-28T16:30:00Z");

describe("lottery catalog", () => {
  it("shows one stable grid including LIVE and keeps server prices and jackpots", () => {
    const { rerender } = render(<LotteryCatalog lotteries={[weekly, fast, holiday, daily]} now={now} onOpen={vi.fn()} />);
    const order = () => screen.getAllByRole("button", { name: /^Открыть / }).map(button => button.getAttribute("aria-label"));
    expect(order()).toEqual(["Открыть Casper LIVE", "Открыть 6 из 36", "Открыть Casper Grand", "Открыть ГРОБ", "Открыть Casper PULSE"]);
    expect(screen.getAllByLabelText("48 000 CAS")).toHaveLength(3);
    expect(screen.getByText("Цена скоро")).toBeInTheDocument();
    expect(screen.getByLabelText("5 000 000 000 CAS")).toBeInTheDocument();
    expect(screen.getAllByText("Через 30 мин")).toHaveLength(4);
    rerender(<LotteryCatalog lotteries={[{ ...fast, jackpot: 10_000_000_000 }, holiday, daily, weekly]} now={now} onOpen={vi.fn()} />);
    expect(order()).toEqual(["Открыть Casper LIVE", "Открыть 6 из 36", "Открыть Casper Grand", "Открыть ГРОБ", "Открыть Casper PULSE"]);
  });

  it("filters overlapping festive and draw games without a separate weekly section", () => {
    render(<LotteryCatalog lotteries={[daily, weekly, holiday, fast]} now={now} onOpen={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Все" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Праздничные" }));
    expect(screen.getByRole("button", { name: "Праздничные" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByRole("button", { name: /^Открыть / })).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Открыть ГРОБ" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Моментальные" }));
    expect(screen.getAllByRole("button", { name: /^Открыть / })).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Открыть Casper LIVE" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Тиражные" }));
    expect(screen.getAllByRole("button", { name: /^Открыть / })).toHaveLength(4);
    expect(screen.getByRole("button", { name: "Открыть ГРОБ" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Открыть Casper Grand" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Открыть Casper LIVE" })).not.toBeInTheDocument();
  });

  it("opens each card once through the existing route", () => {
    const onOpen = vi.fn();
    render(<LotteryCatalog lotteries={[daily, weekly, holiday, fast]} now={now} onOpen={onOpen} />);
    for (const name of ["6 из 36", "Casper Grand", "Casper LIVE", "ГРОБ", "Casper PULSE"]) fireEvent.click(screen.getByRole("button", { name: `Открыть ${name}` }));
    expect(onOpen.mock.calls).toEqual([["khan"], ["weekly"], ["kasper-live"], ["grob"], ["pulse"]]);
  });

  it("shows Moscow dates and truthful unavailable or overdue draw states", () => {
    const { rerender } = render(<LotteryCatalog lotteries={[{ ...daily, scheduled_at: "2026-09-28T18:00:00Z" }]} now={now} onOpen={vi.fn()} />);
    expect(screen.getByText("Сегодня, 21:00")).toBeInTheDocument();
    rerender(<LotteryCatalog lotteries={[{ ...daily, scheduled_at: "2026-09-29T17:00:00Z" }]} now={now} onOpen={vi.fn()} />);
    expect(screen.getByText(/29 сент.*20:00/)).toBeInTheDocument();
    rerender(<LotteryCatalog lotteries={[{ ...daily, scheduled_at: null }]} now={now} onOpen={vi.fn()} />);
    expect(screen.getByText("Расписание внутри")).toBeInTheDocument();
    rerender(<LotteryCatalog lotteries={[daily]} now={now + 3600000} onOpen={vi.fn()} />);
    expect(screen.getByText("Обновляем тираж")).toBeInTheDocument();
  });

  it("supports empty festive categories and does not duplicate a server LIVE entry", () => {
    render(<LotteryCatalog lotteries={[daily, { ...daily, code: "kasper-live" }]} now={now} onOpen={vi.fn()} />);
    expect(screen.getAllByRole("button", { name: "Открыть Casper LIVE" })).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Праздничные" }));
    expect(screen.getByText("В этой категории пока нет лотерей.")).toBeInTheDocument();
  });
});


it("restores saved scroll after the lazy catalogue mounts and cancels pending restoration", () => {
  const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => undefined);
  let restore: FrameRequestCallback = () => undefined;
  const frame = vi.spyOn(window, "requestAnimationFrame").mockImplementation(callback => { restore = callback; return 7; });
  const cancel = vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
  const { unmount } = render(<LotteryCatalog lotteries={[daily]} now={now} restoreScroll={640} onOpen={vi.fn()} />);
  expect(scroll).not.toHaveBeenCalled();
  act(() => restore(0));
  expect(scroll).toHaveBeenCalledWith({ top: 640, behavior: "instant" });
  unmount();
  expect(cancel).toHaveBeenCalledWith(7);
  scroll.mockRestore();frame.mockRestore();cancel.mockRestore();
});
