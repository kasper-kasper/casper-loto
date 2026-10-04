import { fireEvent, render, screen } from "@testing-library/react";
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

describe("lottery catalog", () => {
  it("keeps server prices and jackpot ordering while filtering daily and weekly games", () => {
    render(<LotteryCatalog lotteries={[daily, weekly]} onOpen={vi.fn()} />);
    expect(screen.getAllByRole("button", { name: /^Открыть / }).map(button => button.getAttribute("aria-label"))).toEqual(["Открыть Casper Grand", "Открыть 6 из 36", "Открыть Casper LIVE"]);
    expect(screen.getByLabelText("48 000 CAS")).toBeInTheDocument();
    expect(screen.getByText("Цена скоро")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Каждый день" }));
    expect(screen.getByRole("button", { name: "Открыть 6 из 36" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Открыть Casper Grand" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Открыть Casper LIVE" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Раз в неделю" }));
    expect(screen.getByRole("button", { name: "Раз в неделю" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Открыть Casper Grand" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Открыть 6 из 36" })).not.toBeInTheDocument();
  });

  it("opens the chosen game once without a purchase action", () => {
    const onOpen = vi.fn();
    render(<LotteryCatalog lotteries={[daily, weekly]} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("button", { name: "Открыть 6 из 36" }));
    fireEvent.click(screen.getByRole("button", { name: "Открыть Casper Grand" }));
    fireEvent.click(screen.getByRole("button", { name: "Открыть Casper LIVE" }));
    expect(onOpen.mock.calls).toEqual([["khan"], ["weekly"], ["kasper-live"]]);
  });
});
