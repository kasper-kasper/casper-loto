import type { LiveDraw, LiveFeed, Lottery } from "./types";

export const FAST_ORDER = ["flash", "shadow", "pulse"];
export const fastName = (code: string) => code === "shadow" ? "CODE" : code.toUpperCase();
export const timeLeft = (date: string | null, now: number) => {
  if (!date) return "—";
  const seconds = Math.max(0, Math.ceil((Date.parse(date) - now) / 1000));
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
};

// Match Mini App: server reveal timestamps, eight-second prelive, six-second result hold.
export function fastPresentation(feed: LiveFeed | null, now: number) {
  const completed = feed?.latest_completed;
  if (completed?.winning_numbers?.length && now >= Date.parse(completed.scheduled_at)
    && now < Date.parse(completed.live_ends_at) + 6000) {
    const end = Date.parse(completed.live_ends_at);
    const count = now < Date.parse(completed.live_starts_at) ? 0
      : completed.reveal_at.filter(t => Date.parse(t) <= now).length;
    return {
      draw: completed, phase: now >= end ? "result" : count ? "revealing" : "starting",
      numbers: now >= end ? completed.winning_numbers : completed.winning_numbers.slice(0, count),
    };
  }
  const next = feed?.next_scheduled;
  if (next && now - Date.parse(next.scheduled_at) < 120000) return {
    draw: next, phase: now >= Date.parse(next.scheduled_at) ? "starting"
      : Date.parse(next.scheduled_at) - now <= 8000 ? "prelive" : "waiting", numbers: [],
  };
  return { draw: null, phase: "idle", numbers: [] };
}

// Use the draw's format, not the current sales format, for historical results.
export function displayedNumber(draw: LiveDraw, value: number, index: number) {
  if (draw.lottery_code === "pulse" && draw.secondary_storage_offset !== undefined && index >= (draw.primary_numbers_to_pick || 2)) {
    return `P${value - draw.secondary_storage_offset}`;
  }
  return draw.lottery_code === "shadow" ? String(value) : String(value).padStart(2, "0");
}

function randomBelow(max: number) {
  const bound = Math.floor(0x100000000 / max) * max;
  const random = new Uint32Array(1);
  do { crypto.getRandomValues(random) } while (random[0] >= bound);
  return random[0] % max;
}
function sample(max: number, count: number) {
  if (count < 0 || max < count || max < 0) throw new Error("Формат игры временно недоступен");
  const pool = Array.from({ length: max }, (_, i) => i + 1);
  for (let i = 0; i < count; i++) {
    const j = i + randomBelow(max - i);
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  return pool.slice(0, count).sort((a, b) => a - b);
}
export function randomFastTicket(lottery: Lottery): number[] {
  if (lottery.ruleset_code === "code_4_digits") return Array.from({ length: lottery.primary_numbers_to_pick }, () => randomBelow(10));
  return [...sample(lottery.primary_max_number, lottery.primary_numbers_to_pick),
    ...sample(lottery.secondary_max_number, lottery.secondary_numbers_to_pick).map(n => n + lottery.secondary_storage_offset)];
}
