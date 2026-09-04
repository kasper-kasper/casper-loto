import type { LiveDraw, LiveFeed } from "./types";

export const LIVE_REVEAL_LEAD_MS = 1_000;
export const LIVE_REVEAL_INTERVAL_MS = 2_000;
export const LIVE_RESULT_HOLD_MS = 90_000;
export const FAST_PRELIVE_MS = 20_000;
export const FAST_RESULT_HOLD_MS = 12_000;
export const REPLAY_REVEAL_LEAD_MS = 700;
export const REPLAY_REVEAL_INTERVAL_MS = 1_250;

export type LivePhase = "idle" | "waiting" | "starting" | "revealing" | "result";

export interface LivePresentation {
  phase: LivePhase;
  draw: LiveDraw | null;
  revealedNumbers: number[];
  currentNumber: number | null;
  nextDraw: LiveDraw | null;
}

export function replayPresentation(draw: LiveDraw, elapsed: number): LivePresentation {
  const numbers = draw.winning_numbers ?? [];
  const revealElapsed = elapsed - REPLAY_REVEAL_LEAD_MS;
  if (revealElapsed < 0) {
    return { phase: "starting", draw, revealedNumbers: [], currentNumber: null, nextDraw: null };
  }
  const currentIndex = Math.floor(revealElapsed / REPLAY_REVEAL_INTERVAL_MS);
  if (currentIndex < numbers.length) {
    return {
      phase: "revealing",
      draw,
      revealedNumbers: numbers.slice(0, currentIndex),
      currentNumber: numbers[currentIndex],
      nextDraw: null,
    };
  }
  return { phase: "result", draw, revealedNumbers: numbers, currentNumber: null, nextDraw: null };
}

export function livePresentation(feed: LiveFeed | null, now: number): LivePresentation {
  if (!feed) return { phase: "idle", draw: null, revealedNumbers: [], currentNumber: null, nextDraw: null };
  const completed = feed.latest_completed;
  if (completed?.winning_numbers?.length) {
    const startsAt = new Date(completed.live_starts_at ?? completed.scheduled_at).getTime();
    const revealTimes = completed.reveal_at?.map((value) => new Date(value).getTime()) ?? completed.winning_numbers.map((_, index) => startsAt + LIVE_REVEAL_LEAD_MS + index * LIVE_REVEAL_INTERVAL_MS);
    const revealEndsAt = new Date(completed.live_ends_at ?? new Date((revealTimes.at(-1) ?? startsAt) + LIVE_REVEAL_INTERVAL_MS).toISOString()).getTime();
    if (now >= startsAt && now < revealEndsAt + LIVE_RESULT_HOLD_MS) {
      const currentIndex = revealTimes.findIndex((revealAt) => now < revealAt);
      if (now < revealTimes[0]) {
        return { phase: "starting", draw: completed, revealedNumbers: [], currentNumber: null, nextDraw: feed.next_scheduled };
      }
      if (now < revealEndsAt) {
        const revealedCount = currentIndex === -1 ? completed.winning_numbers.length : currentIndex;
        const activeIndex = Math.min(completed.winning_numbers.length - 1, Math.max(0, revealedCount - 1));
        return {
          phase: "revealing",
          draw: completed,
          revealedNumbers: completed.winning_numbers.slice(0, activeIndex),
          currentNumber: completed.winning_numbers[activeIndex],
          nextDraw: feed.next_scheduled,
        };
      }
      return {
        phase: "result",
        draw: completed,
        revealedNumbers: completed.winning_numbers,
        currentNumber: null,
        nextDraw: feed.next_scheduled,
      };
    }
  }
  if (feed.next_scheduled) {
    const startsIn = new Date(feed.next_scheduled.scheduled_at).getTime() - now;
    return {
      phase: startsIn <= 0 ? "starting" : "waiting",
      draw: feed.next_scheduled,
      revealedNumbers: [],
      currentNumber: null,
      nextDraw: null,
    };
  }
  return { phase: "idle", draw: null, revealedNumbers: [], currentNumber: null, nextDraw: null };
}

export function fastLivePresentation(feed: LiveFeed | null, now: number): LivePresentation | null {
  if (!feed) return null;
  const completed = feed.latest_completed;
  if (completed?.winning_numbers?.length) {
    const liveEndsAt = new Date(completed.live_ends_at).getTime();
    if (now >= new Date(completed.live_starts_at).getTime() && now < liveEndsAt + FAST_RESULT_HOLD_MS) {
      return livePresentation(feed, now);
    }
  }
  const next = feed.next_scheduled;
  if (!next) return null;
  const startsIn = new Date(next.scheduled_at).getTime() - now;
  if (startsIn > FAST_PRELIVE_MS || startsIn < -120_000) return null;
  return livePresentation({ ...feed, latest_completed: null }, now);
}
