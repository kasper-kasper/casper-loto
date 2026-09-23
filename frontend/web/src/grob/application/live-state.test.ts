import { expect, test } from "vitest";
import type { LiveDraw } from "../../types";
import { deriveGrobLiveView, grobLivePhase } from "./live-state";

const draw:LiveDraw={lottery_code:"grob",lottery_name:"ГРОБ",draw_number:6,scheduled_at:"2026-09-23T20:00:00Z",status:"COMPLETED",winning_numbers:[3,10,16],jackpot:1,player_ticket_count:1,player_total_prize:6666,highlighted_tickets:[],live_starts_at:"2026-09-23T20:00:00Z",reveal_at:["2026-09-23T20:00:01Z","2026-09-23T20:00:03Z","2026-09-23T20:00:05Z"],live_ends_at:"2026-09-23T20:00:07Z"};
test("never reveals a number before its server timestamp",()=>{expect(deriveGrobLiveView(draw,Date.parse("2026-09-23T20:00:02Z")).revealedNumbers).toEqual([3]);});
test("late join restores all reveals and server result",()=>{const value=deriveGrobLiveView(draw,Date.parse("2026-09-23T20:00:08Z"));expect(value.revealedNumbers).toEqual([3,10,16]);expect(value.resultKind).toBe("win");});
test("maps the server timeline to waiting, reveal and settled phases",()=>{
  expect(grobLivePhase(deriveGrobLiveView(draw,Date.parse("2026-09-23T19:59:59Z")))).toBe("drawWaiting");
  expect(grobLivePhase(deriveGrobLiveView(draw,Date.parse("2026-09-23T20:00:04Z")))).toBe("liveReveal");
  expect(grobLivePhase(deriveGrobLiveView(draw,Date.parse("2026-09-23T20:00:08Z")))).toBe("result");
});
