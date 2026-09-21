import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FastPicker, FastView } from "./FastView";
import type { LiveDraw, LiveFeed, Lottery } from "./types";

const drawTime = Date.parse("2026-09-04T08:30:00Z");

function lottery(code: "flash" | "shadow" | "pulse", scheduledAt: string): Lottery {
  return {
    code,
    name: code.toUpperCase(),
    kind: "DAILY",
    numbers_to_pick: 3,
    max_number: code === "flash" ? 20 : 15,
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
  it("shows the current jackpot and buys random tickets from the card", () => {
    const onQuickBuy = vi.fn();
    const entry = lottery("flash", "2026-09-04T08:40:00Z");
    render(<FastView feed={null} lotteries={[entry]} now={drawTime} balance={20_000} onOpen={() => undefined} onQuickBuy={onQuickBuy} />);

    expect(screen.getByLabelText("1 000 000 CAS")).toHaveTextContent("1 000 000");
    fireEvent.click(screen.getByRole("button", { name: "Купить 5 случайных билетов FLASH" }));
    expect(onQuickBuy).toHaveBeenCalledWith("flash", expect.arrayContaining([
      expect.arrayContaining([expect.any(Number), expect.any(Number), expect.any(Number)]),
    ]));
    expect(onQuickBuy.mock.calls[0][1]).toHaveLength(5);
  });

  it("does not demote the round in the gap between settlement and broadcast", () => {
    const feed: LiveFeed = { server_time: new Date(drawTime).toISOString(), latest_completed: completedShadow, next_scheduled: null, recent_completed: [completedShadow] };
    const lotteries = [lottery("flash", "2026-09-04T08:40:00Z"), lottery("shadow", "2026-09-04T08:50:00Z")];
    const { container, rerender } = render(<FastView feed={feed} lotteries={lotteries} now={drawTime} onOpen={() => undefined} />);
    expect(container.querySelector(".fast-view > div:first-of-type > article")).toHaveClass("fast-live-card", "fast-shadow");
    expect(screen.getByText("Каспер выбирает числа")).toBeInTheDocument();
    expect(container.querySelectorAll(".fast-live-slots .lit")).toHaveLength(0);
    rerender(<FastView feed={feed} lotteries={lotteries} now={drawTime + 6_500} onOpen={() => undefined} />);
    expect(container.querySelector(".fast-view > div:first-of-type > article")).toHaveClass("fast-shadow");
    expect(container.querySelectorAll(".fast-live-slots .lit")).toHaveLength(1);
  });

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

describe("PULSE picker", () => {
  it("renders both additional numbers in the live 2+2 result", () => {
    const pulseDraw: LiveDraw = {
      ...completedShadow,
      lottery_code: "pulse",
      lottery_name: "PULSE",
      winning_numbers: [1, 7, 12, 15],
      reveal_at: [6_000, 7_000, 8_000, 9_000].map((offset) => new Date(drawTime + offset).toISOString()),
      live_ends_at: new Date(drawTime + 10_000).toISOString(),
    };
    const feed: LiveFeed = { server_time: new Date(drawTime + 11_000).toISOString(), latest_completed: pulseDraw, next_scheduled: null, recent_completed: [pulseDraw] };
    const { container } = render(<FastView feed={feed} lotteries={[lottery("pulse", "2026-09-04T08:36:00Z")]} now={drawTime + 11_000} onOpen={() => undefined} />);

    expect(container.querySelectorAll(".pulse-slots > i")).toHaveLength(4);
    expect(container.querySelectorAll(".pulse-slots > i.special")).toHaveLength(2);
  });

  it("submits two main numbers and two tagged Pulse numbers", () => {
    const onBuy = vi.fn().mockResolvedValue(true);
    render(
      <FastPicker
        lottery={{
          ...lottery("pulse", "2026-09-04T08:36:00Z"),
          numbers_to_pick: 4,
          primary_numbers_to_pick: 2,
          primary_max_number: 12,
          secondary_numbers_to_pick: 2,
          secondary_max_number: 6,
          secondary_storage_offset: 12,
        }}
        purchasing={false}
        success={false}
        onBuy={onBuy}
        onClose={() => undefined}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Позиция 1" }));
    fireEvent.click(screen.getByRole("button", { name: "Позиция 12" }));
    fireEvent.click(screen.getByRole("button", { name: "Pulse-число 6" }));
    fireEvent.click(screen.getByRole("button", { name: "Pulse-число 2" }));
    fireEvent.click(screen.getByRole("button", { name: /Запустить пульс/i }));
    expect(onBuy).toHaveBeenCalledWith([1, 12, 14, 18]);
  });
});

describe("CODE picker", () => {
  it("uses the familiar phone keypad order", () => {
    const { container } = render(
      <FastPicker
        lottery={{ ...lottery("shadow", "2026-09-04T08:33:00Z"), name: "CODE", ruleset_code: "code_4_digits", numbers_to_pick: 4, max_number: 9 }}
        purchasing={false}
        success={false}
        onBuy={async () => true}
        onClose={() => undefined}
      />,
    );
    expect(Array.from(container.querySelectorAll(".code-keypad button:not(.code-backspace)"), (button) => button.textContent)).toEqual(["01", "02", "03", "04", "05", "06", "07", "08", "09", "00"]);
  });

  it("submits four ordered digits including zero and repeats", () => {
    const onBuy = vi.fn().mockResolvedValue(true);
    render(
      <FastPicker
        lottery={{
          ...lottery("shadow", "2026-09-04T08:33:00Z"),
          name: "CODE",
          ruleset_code: "code_4_digits",
          numbers_to_pick: 4,
          max_number: 9,
        }}
        purchasing={false}
        success={false}
        onBuy={onBuy}
        onClose={() => undefined}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Цифра 0" }));
    fireEvent.click(screen.getByRole("button", { name: "Цифра 7" }));
    fireEvent.click(screen.getByRole("button", { name: "Цифра 0" }));
    fireEvent.click(screen.getByRole("button", { name: "Цифра 3" }));
    fireEvent.click(screen.getByRole("button", { name: /Подтвердить код/i }));
    expect(onBuy).toHaveBeenCalledWith([0, 7, 0, 3]);
  });
});
