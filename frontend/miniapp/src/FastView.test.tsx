import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FastView } from "./FastView";
import type { LiveDraw, LiveFeed, Lottery } from "./types";

const drawTime = Date.parse("2026-09-04T08:30:00Z");

function lottery(code: "flash" | "shadow", scheduledAt: string): Lottery {
  return {
    code,
    name: code.toUpperCase(),
    kind: "DAILY",
    numbers_to_pick: 3,
    max_number: 15,
    ticket_price: 888,
    jackpot: 1_000_000,
    draw_number: 185,
    scheduled_at: scheduledAt,
    sales_close_at: scheduledAt,
    sales_open: true,
    purchase_available: true,
    player_ticket_count: 0,
    sales_status: "OPEN",
    max_tickets_per_purchase: 1000,
    max_tickets_per_user_per_draw: 5000,
  };
}

const completedShadow: LiveDraw = {
  lottery_code: "shadow",
  lottery_name: "SHADOW",
  lottery_kind: "DAILY",
  draw_number: 184,
  scheduled_at: new Date(drawTime).toISOString(),
  status: "COMPLETED",
  winning_numbers: [6, 7, 14],
  jackpot: 1_000_000,
  player_ticket_count: 6,
  player_winning_ticket_count: 0,
  player_best_matches: 1,
  player_total_prize: 0,
  highlighted_tickets: [],
  sales_close_at: new Date(drawTime - 60_000).toISOString(),
  sales_status: "COMPLETED",
  live_starts_at: new Date(drawTime + 5_000).toISOString(),
  reveal_at: [6_000, 8_000, 10_000].map((offset) => new Date(drawTime + offset).toISOString()),
  live_ends_at: new Date(drawTime + 12_000).toISOString(),
};

describe("Fast draw placement", () => {
  it("keeps the active broadcast first when the dashboard advances to later draws", () => {
    const feed: LiveFeed = {
      server_time: new Date(drawTime + 8_500).toISOString(),
      latest_completed: completedShadow,
      next_scheduled: null,
      recent_completed: [completedShadow],
    };
    const { container } = render(
      <FastView
        feed={feed}
        lotteries={[
          lottery("flash", "2026-09-04T08:40:00Z"),
          lottery("shadow", "2026-09-04T08:50:00Z"),
        ]}
        now={drawTime + 8_500}
        onOpen={() => undefined}
      />,
    );

    expect(container.querySelector(".fast-view > div:first-of-type > article")).toHaveClass("fast-live-card", "fast-shadow");
  });
});
