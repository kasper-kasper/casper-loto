import { newestLiveFeed } from "./live";
import { describe, expect, it } from "vitest";

import {
  LIVE_REVEAL_INTERVAL_MS,
  LIVE_REVEAL_LEAD_MS,
  FAST_PRELIVE_MS,
  FAST_RESULT_HOLD_MS,
  REPLAY_REVEAL_INTERVAL_MS,
  REPLAY_REVEAL_LEAD_MS,
  livePresentation,
  fastLivePresentation,
  replayPresentation,
} from "./live";
import type { LiveDraw, LiveFeed } from "./types";

const startsAt = Date.parse("2026-08-31T09:00:00Z");
const completed: LiveDraw = {
  lottery_code: "pss", lottery_name: "ПСС-Лото", lottery_kind: "DAILY", draw_number: 812,
  scheduled_at: new Date(startsAt).toISOString(), status: "COMPLETED", winning_numbers: [2, 5, 9, 14],
  jackpot: 24_000_000, player_ticket_count: 1, player_winning_ticket_count: 0,
  player_best_matches: 1, player_total_prize: 0, highlighted_tickets: [],
  sales_close_at: new Date(startsAt - 120_000).toISOString(), sales_status: "COMPLETED",
  live_starts_at: new Date(startsAt).toISOString(),
  reveal_at: [0, 1, 2, 3].map((index) => new Date(startsAt + LIVE_REVEAL_LEAD_MS + index * LIVE_REVEAL_INTERVAL_MS).toISOString()),
  live_ends_at: new Date(startsAt + LIVE_REVEAL_LEAD_MS + 4 * LIVE_REVEAL_INTERVAL_MS).toISOString(),
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

describe("embedded Fast broadcast", () => {
  const fastCompleted = {
    ...completed,
    lottery_code: "flash",
    lottery_name: "FLASH",
    winning_numbers: [2, 5, 9],
    reveal_at: [0, 1, 2].map((index) => new Date(startsAt + LIVE_REVEAL_LEAD_MS + index * LIVE_REVEAL_INTERVAL_MS).toISOString()),
    live_ends_at: new Date(startsAt + LIVE_REVEAL_LEAD_MS + 3 * LIVE_REVEAL_INTERVAL_MS).toISOString(),
  };

  it("appears only during the final twenty seconds", () => {
    const fastNext = { ...fastCompleted, status: "SCHEDULED" as const, winning_numbers: null };
    const fastFeed = { ...feed, latest_completed: null, next_scheduled: fastNext };
    expect(fastLivePresentation(fastFeed, startsAt - FAST_PRELIVE_MS - 1)).toBeNull();
    expect(fastLivePresentation(fastFeed, startsAt - FAST_PRELIVE_MS)?.phase).toBe("waiting");
  });

  it("reveals the result and removes it after a short hold", () => {
    const fastFeed = { ...feed, latest_completed: fastCompleted, next_scheduled: null };
    expect(fastLivePresentation(fastFeed, startsAt + LIVE_REVEAL_LEAD_MS + 100)?.phase).toBe("revealing");
    const endsAt = new Date(fastCompleted.live_ends_at).getTime();
    expect(fastLivePresentation(fastFeed, endsAt)?.phase).toBe("result");
    expect(fastLivePresentation(fastFeed, endsAt + FAST_RESULT_HOLD_MS)).toBeNull();
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


it("ignores a delayed HTTP snapshot after a newer stream event", () => {
  const current = { ...feed, server_time: "2026-09-05T12:00:02Z" };
  const old = { ...feed, server_time: "2026-09-05T12:00:01Z", latest_completed: null };
  expect(newestLiveFeed(current, old)).toBe(current);
  expect(newestLiveFeed(old, current)).toBe(current);
  expect(newestLiveFeed(null, current)).toBe(current);
});
