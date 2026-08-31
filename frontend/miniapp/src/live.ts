import type { LiveDraw, LiveFeed } from "./types";

export const LIVE_REVEAL_LEAD_MS = 1_000;
export const LIVE_REVEAL_INTERVAL_MS = 2_000;
export const LIVE_RESULT_HOLD_MS = 90_000;
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
    const startsAt = new Date(completed.scheduled_at).getTime();
    const revealEndsAt = startsAt + LIVE_REVEAL_LEAD_MS + completed.winning_numbers.length * LIVE_REVEAL_INTERVAL_MS;
    if (now >= startsAt && now < revealEndsAt + LIVE_RESULT_HOLD_MS) {
      const revealElapsed = now - startsAt - LIVE_REVEAL_LEAD_MS;
      if (revealElapsed < 0) {
        return { phase: "starting", draw: completed, revealedNumbers: [], currentNumber: null, nextDraw: feed.next_scheduled };
      }
      if (now < revealEndsAt) {
        const currentIndex = Math.min(completed.winning_numbers.length - 1, Math.floor(revealElapsed / LIVE_REVEAL_INTERVAL_MS));
        return {
          phase: "revealing",
          draw: completed,
          revealedNumbers: completed.winning_numbers.slice(0, currentIndex),
          currentNumber: completed.winning_numbers[currentIndex],
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
