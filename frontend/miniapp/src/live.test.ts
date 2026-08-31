import { describe, expect, it } from "vitest";

import {
  LIVE_REVEAL_INTERVAL_MS,
  LIVE_REVEAL_LEAD_MS,
  REPLAY_REVEAL_INTERVAL_MS,
  REPLAY_REVEAL_LEAD_MS,
  livePresentation,
  replayPresentation,
} from "./live";
import type { LiveDraw, LiveFeed } from "./types";

const startsAt = Date.parse("2026-08-31T09:00:00Z");
const completed: LiveDraw = {
  lottery_code: "pss", lottery_name: "ПСС-Лото", lottery_kind: "DAILY", draw_number: 812,
  scheduled_at: new Date(startsAt).toISOString(), status: "COMPLETED", winning_numbers: [2, 5, 9, 14],
  jackpot: 24_000_000, player_ticket_count: 1, player_winning_ticket_count: 0,
  player_best_matches: 1, player_total_prize: 0, highlighted_tickets: [],
};
const next = { ...completed, draw_number: 813, status: "SCHEDULED" as const, scheduled_at: "2026-08-31T15:00:00Z", winning_numbers: null };
const feed: LiveFeed = { server_time: new Date(startsAt).toISOString(), latest_completed: completed, next_scheduled: next, recent_completed: [completed] };

describe("server-synchronised live phases", () => {
  it("waits for the next scheduled draw", () => {
    const state = livePresentation({ ...feed, latest_completed: null, next_scheduled: { ...next, player_ticket_count: 4 } }, startsAt);
    expect(state.phase).toBe("waiting");
    expect(state.draw?.draw_number).toBe(813);
    expect(state.draw?.player_ticket_count).toBe(4);
  });

  it("shows the short start state", () => {
    expect(livePresentation(feed, startsAt + 500).phase).toBe("starting");
  });

  it("reveals saved numbers sequentially and resumes at the correct number", () => {
    const state = livePresentation(feed, startsAt + LIVE_REVEAL_LEAD_MS + LIVE_REVEAL_INTERVAL_MS * 2 + 100);
    expect(state.phase).toBe("revealing");
    expect(state.revealedNumbers).toEqual([2, 5]);
    expect(state.currentNumber).toBe(9);
  });

  it("opens the final result immediately after all numbers", () => {
    const end = startsAt + LIVE_REVEAL_LEAD_MS + LIVE_REVEAL_INTERVAL_MS * 4;
    const state = livePresentation(feed, end);
    expect(state.phase).toBe("result");
    expect(state.revealedNumbers).toEqual([2, 5, 9, 14]);
    expect(state.nextDraw?.draw_number).toBe(813);
  });
});

describe("digital replay", () => {
  it("replays the immutable saved sequence independently of draw time", () => {
    const state = replayPresentation(completed, REPLAY_REVEAL_LEAD_MS + REPLAY_REVEAL_INTERVAL_MS * 2 + 10);
    expect(state.phase).toBe("revealing");
    expect(state.revealedNumbers).toEqual([2, 5]);
    expect(state.currentNumber).toBe(9);
  });

  it("finishes on the original saved result", () => {
    const state = replayPresentation(completed, REPLAY_REVEAL_LEAD_MS + REPLAY_REVEAL_INTERVAL_MS * 4);
    expect(state.phase).toBe("result");
    expect(state.revealedNumbers).toEqual(completed.winning_numbers);
  });
});
