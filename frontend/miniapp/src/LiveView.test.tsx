import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LIVE_REVEAL_INTERVAL_MS, LIVE_REVEAL_LEAD_MS } from "./live";
import { LiveView } from "./LiveView";
import type { LiveDraw, LiveFeed } from "./types";

const startsAt = Date.parse("2026-08-31T09:00:00Z");
const baseDraw: LiveDraw = {
  lottery_code: "pss", lottery_name: "ПСС-Лото", lottery_kind: "DAILY", draw_number: 812,
  scheduled_at: new Date(startsAt).toISOString(), status: "COMPLETED", winning_numbers: [2, 5, 9, 14], jackpot: 24_000_000,
  player_ticket_count: 0, player_winning_ticket_count: 0, player_best_matches: null, player_total_prize: 0, highlighted_tickets: [],
  sales_close_at: new Date(startsAt - 120_000).toISOString(), sales_status: "COMPLETED",
  live_starts_at: new Date(startsAt).toISOString(),
  reveal_at: [0, 1, 2, 3].map((index) => new Date(startsAt + LIVE_REVEAL_LEAD_MS + index * LIVE_REVEAL_INTERVAL_MS).toISOString()),
  live_ends_at: new Date(startsAt + LIVE_REVEAL_LEAD_MS + 4 * LIVE_REVEAL_INTERVAL_MS).toISOString(),
};
const resultTime = startsAt + LIVE_REVEAL_LEAD_MS + LIVE_REVEAL_INTERVAL_MS * 4;

function renderResult(draw: LiveDraw) {
  const feed: LiveFeed = { server_time: new Date(resultTime).toISOString(), latest_completed: draw, next_scheduled: null, recent_completed: [draw] };
  return render(<LiveView feed={feed} now={resultTime} loading={false} onPlay={vi.fn()} onTickets={vi.fn()} />);
}

describe("personalised live result", () => {
  it("calmly handles a draw without a user ticket", () => {
    renderResult(baseDraw);
    expect(screen.getByText("Вы не участвовали в этом тираже")).toBeInTheDocument();
  });

  it("shows a loss without golden zero winnings", () => {
    renderResult({ ...baseDraw, player_ticket_count: 1, player_best_matches: 1, highlighted_tickets: [{ public_number: 50465, numbers: [1, 3, 8, 12], matches: 1, prize_amount: 0 }] });
    expect(screen.getByText("В этот раз без выигрыша")).toBeInTheDocument();
    expect(screen.getByText("Без выигрыша")).toBeInTheDocument();
    expect(screen.queryByText("+0 CAS")).not.toBeInTheDocument();
  });

  it("highlights a real win and matched ticket numbers", () => {
    renderResult({ ...baseDraw, player_ticket_count: 1, player_winning_ticket_count: 1, player_best_matches: 3, player_total_prize: 120_000, highlighted_tickets: [{ public_number: 50466, numbers: [2, 5, 9, 11], matches: 3, prize_amount: 120_000 }] });
    expect(screen.getAllByText("+120 000 CAS")).toHaveLength(2);
    expect(document.querySelectorAll(".live-ticket .number.won")).toHaveLength(3);
  });

  it("opens a clearly labelled digital replay from the archive", () => {
    vi.stubGlobal("scrollTo", vi.fn());
    renderResult(baseDraw);
    fireEvent.click(screen.getByRole("button", { name: /ПСС-Лото.*Смотреть/ }));
    expect(screen.getByText("ПОВТОР ТИРАЖА")).toBeInTheDocument();
    expect(screen.getByText("Это цифровой повтор сохранённого результата.")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
