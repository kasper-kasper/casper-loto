import type { LiveDraw } from "../../types";
import type { GrobLiveView, GrobPhase } from "../bridge/contracts";

export function deriveGrobLiveView(draw: LiveDraw | null, now: number): GrobLiveView {
  if (!draw) return { draw: null, revealedNumbers: [], revealCount: 0, resultKind: "waiting" };
  const starts = Date.parse(draw.live_starts_at);
  const ends = Date.parse(draw.live_ends_at);
  const revealCount = Math.min(draw.winning_numbers?.length ?? 0, draw.reveal_at.filter(value => Date.parse(value) <= now).length);
  const resultKind = now < starts ? "waiting" : now <= ends ? "live" : draw.player_ticket_count === 0 ? "spectator" : draw.player_total_prize > 0 ? "win" : "loss";
  return { draw, revealCount, revealedNumbers: (draw.winning_numbers ?? []).slice(0, revealCount), resultKind };
}

export function grobLivePhase(live: GrobLiveView): GrobPhase {
  if (live.resultKind === "waiting") return "drawWaiting";
  if (live.resultKind === "live") return live.revealCount > 0 ? "liveReveal" : "liveStarting";
  return "result";
}
