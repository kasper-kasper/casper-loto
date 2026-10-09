import type { Account, Dashboard, Favorite, InstantTicket, LiveDraw, LiveFeed, Ticket, UserNotification } from "./types";
import { broadcastPreviewConfig } from "./broadcastPreview";

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
const nowIso = () => new Date().toISOString();
const future = (minutes: number) => new Date(Date.now() + minutes * 60_000).toISOString();
const nextDualPreviewDraw = () => {
  const draw = new Date();
  draw.setUTCHours(4, 30, 0, 0); // DAWN 07:30 Europe/Moscow
  while (draw.getTime() - 120_000 <= Date.now()) {
    if (draw.getUTCHours() === 4) draw.setUTCHours(21, 30, 0, 0);
    else { draw.setUTCDate(draw.getUTCDate() + 1); draw.setUTCHours(4, 30, 0, 0); }
  }
  return draw.toISOString();
};
const followingDualPreviewDraw = (scheduledAt: string) => {
  const draw = new Date(scheduledAt);
  if (draw.getUTCHours() === 4) draw.setUTCHours(21, 30, 0, 0);
  else { draw.setUTCDate(draw.getUTCDate() + 1); draw.setUTCHours(4, 30, 0, 0); }
  return draw.toISOString();
};
const broadcastPreview = broadcastPreviewConfig();
const previewStartsAt = Date.now() + 5_000;

const lotterySeed = [
  { code: "dual", name: "Casper Dual", kind: "DAILY" as const, ruleset_code: "casper_dual_2_12_2_12", numbers_to_pick: 4, max_number: 24, primary_numbers_to_pick: 2, primary_max_number: 12, secondary_numbers_to_pick: 2, secondary_max_number: 12, secondary_storage_offset: 12, ticket_price: 20_000, jackpot: 5_000_000, draw_number: 501, scheduled_at: nextDualPreviewDraw() },
  { code: "bingo", name: "Casper Bingo", kind: "DAILY" as const, numbers_to_pick: 12, max_number: 60, ticket_price: 50_000, jackpot: 10_000_250_000, draw_number: 1, scheduled_at: future(180) },
  { code: "shadow", name: "CODE", kind: "DAILY" as const, ruleset_code: "code_5_digits", numbers_to_pick: 5, max_number: 9, ticket_price: 888, jackpot: 888_888, draw_number: 38, scheduled_at: future(7) },
  { code: "flash", name: "FLASH", kind: "DAILY" as const, ruleset_code: "fast_5_20_jackpot_only", numbers_to_pick: 5, max_number: 20, ticket_price: 888, jackpot: 901_320, draw_number: 42, scheduled_at: future(17) },
  { code: "pulse", name: "PULSE", kind: "DAILY" as const, ruleset_code: "pulse_2_12_2_6_cipher_199", numbers_to_pick: 5, max_number: 18, primary_numbers_to_pick: 2, primary_max_number: 12, secondary_numbers_to_pick: 2, secondary_max_number: 6, secondary_storage_offset: 12, ticket_price: 1_234, jackpot: 1_234_567, draw_number: 1, scheduled_at: future(10) },
  { code: "grob", name: "Casper Halloween", kind: "DAILY" as const, ruleset_code: "halloween_3_28", numbers_to_pick: 3, max_number: 28, fixed_payouts: { "2": 28_000 }, ticket_price: 6_666, jackpot: 6_666_666, draw_number: 1, scheduled_at: future(36) },
  { code: "september", name: "3 СЕНТЯБРЯ", kind: "DAILY" as const, numbers_to_pick: 3, max_number: 33, ticket_price: 333, jackpot: 33_333_333, draw_number: 1, scheduled_at: future(83) },
  { code: "pll", name: "2:22", kind: "DAILY" as const, numbers_to_pick: 4, max_number: 15, ticket_price: 24_000, jackpot: 18_640_000, draw_number: 418, scheduled_at: future(145) },
  { code: "pss", name: "Casper Ball", kind: "DAILY" as const, numbers_to_pick: 6, max_number: 44, primary_numbers_to_pick: 5, primary_max_number: 36, secondary_numbers_to_pick: 1, secondary_max_number: 8, secondary_storage_offset: 36, ticket_price: 24_000, jackpot: 24_000_000, draw_number: 219, scheduled_at: future(230) },
  { code: "khan", name: "6 из 36", kind: "DAILY" as const, numbers_to_pick: 6, max_number: 36, ticket_price: 48_000, jackpot: 33_456_000, draw_number: 174, scheduled_at: future(310) },
  { code: "weekly", fixed_payouts: {21:50000,22:50000,30:100000,31:200000,32:300000,40:500000,41:1000000,42:3000000,50:10000000,51:20000000} as Record<string, number>, name: "Casper Grand", kind: "WEEKLY" as const, numbers_to_pick: 7, max_number: 40, primary_numbers_to_pick: 5, primary_max_number: 35, secondary_numbers_to_pick: 2, secondary_max_number: 5, secondary_storage_offset: 35, ticket_price: 50_000, jackpot: 5_000_182_500, draw_number: 4, scheduled_at: future(1_420) },
];

let balance = 100_000_000_000;
let purchasedTickets: Ticket[] = [];
let favoriteRows: Favorite[] = [];
let instantTickets: InstantTicket[] = [
  { id: "instant-preview-1", public_number: 10_042, symbols: [5, 5, 5], prize_amount: 20_000 },
  { id: "instant-preview-2", public_number: 10_041, symbols: [1, 2, 3], prize_amount: 0 },
];

const dashboard = (): Dashboard => ({
  server_time: nowIso(),
  balance,
  active_ticket_count: purchasedTickets.length,
  lotteries: lotterySeed.map((lottery) => { const scheduledAt = lottery.code === broadcastPreview?.lotteryCode ? new Date(previewStartsAt).toISOString() : lottery.scheduled_at; return ({ ...lottery, scheduled_at: scheduledAt, sales_close_at: new Date(new Date(scheduledAt).getTime() - (["flash", "shadow", "pulse"].includes(lottery.code) ? 8_000 : 120_000)).toISOString(), sales_open: true, purchase_available: true, player_ticket_count: lottery.code === broadcastPreview?.lotteryCode ? 1 : purchasedTickets.filter((ticket) => ticket.lottery_code === lottery.code).length, sales_status: "OPEN" as const, max_tickets_per_purchase: ["flash", "shadow", "pulse"].includes(lottery.code) ? 100 : 1_000, max_tickets_per_user_per_draw: ["flash", "shadow", "pulse"].includes(lottery.code) ? 500 : 5_000 }); }),
  recent_results: [],
  monthly_total_payout: 12_333_333,
  total_ticket_count: 18_432,
  total_winning_ticket_count: 1_208,
});

const account = (): Account => ({ display_name: "Дизайн-превью", balance, ticket_count: purchasedTickets.length + 42, active_ticket_count: purchasedTickets.length, winning_ticket_count: 7, total_spent: 14_760_000, total_won: 19_333_333, best_win: 12_000_000, unread_notification_count: 1, notification_preferences: { telegram_enabled: true, draw_results_enabled: true, inactivity_reminders_enabled: true } });

const previewNumbers: Record<string, number[]> = { dual: [3, 10, 17, 23], pll: [2, 6, 11, 14], pss: [1, 5, 9, 15], khan: [4, 12, 19, 23, 31, 36], weekly: [3, 9, 18, 27, 34, 37, 40], september: [3, 9, 28], grob: [2, 8, 16] };
const previewLosingTickets: Record<string, number[]> = { pll: [1, 3, 5, 7], pss: [2, 4, 6, 8], khan: [1, 2, 3, 5, 6, 7], weekly: [1, 2, 4, 8, 12, 36, 38], september: [1, 2, 4], grob: [1, 3, 5] };

const liveDraw = (): LiveDraw => {
  const lottery = lotterySeed.find((item) => item.code === (broadcastPreview?.lotteryCode ?? "grob")) ?? lotterySeed.find((item) => item.code === "grob")!;
  const winningNumbers = previewNumbers[lottery.code] ?? [2, 8, 16];
  const winning = broadcastPreview?.scenario !== "loss";
  const ticketNumbers = winning ? [...winningNumbers] : previewLosingTickets[lottery.code] ?? [1, 3, 5];
  const revealLead = lottery.code === "khan" ? 4_000 : 1_000;
  const revealInterval = lottery.code === "khan" ? 3_200 : 2_000;
  const starts = broadcastPreview ? new Date(previewStartsAt).toISOString() : lottery.scheduled_at;
  const revealAt = winningNumbers.map((_, index) => new Date(new Date(starts).getTime() + revealLead + index * revealInterval).toISOString());
  const prize = winning ? (lottery.code === "weekly" ? 5_000_000_000 : 250_000) : 0;
  return { primary_max_number: lottery.max_number, lottery_code: lottery.code, lottery_name: lottery.name, lottery_kind: lottery.kind, draw_number: lottery.draw_number, scheduled_at: starts, status: broadcastPreview ? "COMPLETED" : "SCHEDULED", winning_numbers: broadcastPreview ? winningNumbers : null, jackpot: lottery.jackpot, player_ticket_count: broadcastPreview ? 1 : purchasedTickets.filter((ticket) => ticket.lottery_code === lottery.code).length, player_winning_ticket_count: winning ? 1 : 0, player_best_matches: winning ? winningNumbers.length : 0, player_total_prize: prize, highlighted_tickets: broadcastPreview ? [{ public_number: 2811, numbers: ticketNumbers, matches: winning ? winningNumbers.length : 0, prize_amount: prize }] : [], sales_close_at: new Date(new Date(starts).getTime() - 120_000).toISOString(), sales_status: broadcastPreview ? "COMPLETED" : "OPEN", live_starts_at: starts, reveal_at: revealAt, live_ends_at: new Date(new Date(starts).getTime() + revealLead + winningNumbers.length * revealInterval).toISOString() };
};

const liveFeed = (): LiveFeed => { const draw = liveDraw(); return broadcastPreview ? { server_time: nowIso(), latest_completed: draw, next_scheduled: Date.now() < previewStartsAt ? draw : null, recent_completed: [] } : { server_time: nowIso(), latest_completed: null, next_scheduled: draw, recent_completed: [] }; };

function bingoLive() {
  const elapsed = Date.now() - previewStartsAt;
  const count = elapsed < 0 ? 0 : Math.min(30, Math.floor(elapsed / 1_000) + 1);
  const sequence = Array.from({ length: 30 }, (_, index) => index + 1);
  const numbers = sequence.slice(0, count);
  const winning = broadcastPreview?.scenario !== "loss";
  const ticketNumbers = winning ? [1, 5, 9, 18, 2, 10, 20, 26, 3, 11, 21, 28] : [31, 34, 37, 40, 42, 45, 48, 51, 53, 56, 58, 60];
  const complete = count >= sequence.length;
  return { server_time: nowIso(), rules: { total_moves: 30, jackpot_move: 28, tour_moves: [18, 26], tour_prizes: [100_000, 500_000], pool_size: 2000 }, draw: { draw_number: 1, scheduled_at: new Date(previewStartsAt).toISOString(), complete, numbers, total_moves: 30, jackpot_move: 28, tour_prizes: [100_000, 500_000], stages: winning ? [{ move: count >= 18 ? 18 : null, winners: count >= 18 ? 1 : 0 }, { move: count >= 26 ? 26 : null, winners: count >= 26 ? 1 : 0 }, { move: count >= 28 ? 28 : null, winners: count >= 28 ? 1 : 0 }] : [{ move: null, winners: 0 }, { move: null, winners: 0 }, { move: null, winners: 0 }], tickets: [{ id: "preview-bingo-ticket", public_number: 2811, numbers: ticketNumbers, price: 50_000, result: complete ? { moves: winning ? [18, 26, 28] : [61, 61, 61], amounts: winning ? [100_000, 500_000, 10_000_250_000] : [0, 0, 0] } : null }] } };
}

const notifications: UserNotification[] = [{ id: "preview-notice", type: "DRAW_INVITATION", title: "Сегодня особый тираж", body: "«3 СЕНТЯБРЯ» уже ждёт вашу комбинацию.", payload: {}, read_at: null, created_at: nowIso() }];

export function installDesignPreview(): void {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(raw, window.location.origin);
    const path = url.pathname;
    if (!path.startsWith("/api/v1/miniapp/")) return nativeFetch(input, init);
    if (path.includes("/bingo/inventory")) return json({ draw_id: "preview-bingo", draw_number: 1, scheduled_at: future(180), price: 50000, has_more: true, kasper_set_available: true, tickets: Array.from({ length: 6 }, (_, i) => ({ id: `bingo-${i}`, pool_position: i + 1, numbers: [2, 14, 27, 41, 8, 22, 36, 52, 11, 25, 43, 59].map(n => (n + i - 1) % 60 + 1) })) });
    if (path.includes("/bingo/live")) return json(broadcastPreview ? bingoLive() : { server_time: nowIso(), rules: { total_moves: 58, jackpot_move: 28, tour_moves: [18, 34], tour_prizes: [100000, 500000], pool_size: 2000 }, draw: null });
    if (path.endsWith("/bingo/purchases") && init?.method === "POST") {
      const body = JSON.parse(String(init.body)) as { ticket_ids: string[]; quantity?: number };
      const quantity = body.ticket_ids.length || body.quantity || 0;
      const totalCost = 50_000 * quantity;
      balance -= totalCost;
      return json({ operation_id: crypto.randomUUID(), draw_id: "preview-bingo", draw_ids: ["preview-bingo"], draw_count: 1, ticket_ids: Array.from({ length: quantity }, () => crypto.randomUUID()), total_cost: totalCost, balance_after: balance, already_processed: false });
    }
    if (path.endsWith("/dev/session")) return json({ mode: "design-preview" });
    if (path.endsWith("/dev/refill")) { balance = 100_000_000_000; return json({ balance }); }
    if (path.endsWith("/highlights")) return json({ last_jackpot: null, next_event: null });
    if (path.endsWith("/dashboard")) return json(dashboard());
    if (path.endsWith("/kasper-live/tickets")) return json(instantTickets);
    if (path.endsWith("/kasper-live/purchases") && init?.method === "POST") {
      const quantity = (JSON.parse(String(init.body)) as { quantity: 1 | 3 }).quantity;
      const created = Array.from({ length: quantity }, (_, index): InstantTicket => ({ id: crypto.randomUUID(), public_number: 10_043 + index, symbols: index === 0 ? [4, 4, 4] : [1, 2, 3], prize_amount: index === 0 ? 5_000 : 0 }));
      const totalCost = quantity * 2_000;
      const totalPrize = created.reduce((sum, ticket) => sum + ticket.prize_amount, 0);
      balance = balance - totalCost + totalPrize;
      instantTickets = [...created, ...instantTickets];
      return json({ operation_id: crypto.randomUUID(), tickets: created, total_cost: totalCost, total_prize: totalPrize, balance_after: balance, already_processed: false }, 201);
    }
    if (path.endsWith("/account")) return json(account());
    if (path.endsWith("/live/stream")) {
      const payload = new TextEncoder().encode(`data: ${JSON.stringify(liveFeed())}\n\n`);
      return new Response(new ReadableStream({ start(controller) { controller.enqueue(payload); controller.close(); } }), { headers: { "Content-Type": "text/event-stream" } });
    }
    if (path.endsWith("/live")) return json(liveFeed());
    if (path.endsWith("/tickets")) return json({ tickets: purchasedTickets });
    if (path.endsWith("/notifications/read")) return new Response(null, { status: 204 });
    if (path.endsWith("/notifications/test")) return json({ queued: true });
    if (path.endsWith("/notifications")) return json(notifications);
    if (path.endsWith("/notification-preferences")) return json(init?.body ? JSON.parse(String(init.body)) : account().notification_preferences);
    const favoriteMatch = path.match(/\/lotteries\/([^/]+)\/favorites(?:\/([^/]+))?$/);
    if (favoriteMatch) {
      if (init?.method === "POST") { const favorite = { id: crypto.randomUUID(), numbers: (JSON.parse(String(init.body)) as { numbers: number[] }).numbers }; favoriteRows = [...favoriteRows, favorite]; return json(favorite); }
      if (init?.method === "DELETE") { favoriteRows = favoriteRows.filter((row) => row.id !== favoriteMatch[2]); return new Response(null, { status: 204 }); }
      return json(favoriteRows);
    }
    const purchaseMatch = path.match(/\/lotteries\/([^/]+)\/purchases$/);
    if (purchaseMatch && init?.method === "POST") {
      const lottery = lotterySeed.find((item) => item.code === purchaseMatch[1]);
      if (!lottery) return json({ detail: "Лотерея не найдена" }, 404);
      const body = JSON.parse(String(init.body)) as { combinations: number[][]; draw_count: number };
      const totalCost = lottery.ticket_price * body.combinations.length * body.draw_count;
      balance -= totalCost;
      const created = body.combinations.map((numbers, index): Ticket => ({ id: crypto.randomUUID(), public_number: purchasedTickets.length + index + 1, lottery_code: lottery.code, lottery_name: lottery.name, draw_number: lottery.draw_number, scheduled_at: lottery.scheduled_at, numbers: lottery.code === "pulse" ? [...numbers, 1_001 + Math.floor(Math.random() * 199)] : numbers, purchase_price: lottery.ticket_price, source: "MANUAL", status: "PURCHASED", matches: null, prize_amount: 0, winning_numbers: null, ...(lottery.code === "dual" ? { second_draw_number: lottery.draw_number + 1, second_scheduled_at: followingDualPreviewDraw(lottery.scheduled_at), first_phase: new Date(lottery.scheduled_at).getUTCHours() === 4 ? "DAWN" as const : "NIGHT" as const, first_winning_numbers: null, second_winning_numbers: null, dual_night_matches: null, dual_dawn_matches: null } : {}) }));
      purchasedTickets = [...created, ...purchasedTickets];
      return json({ operation_id: crypto.randomUUID(), draw_id: "preview-draw", draw_ids: lottery.code === "dual" ? ["preview-draw", "preview-second-draw"] : ["preview-draw"], draw_count: body.draw_count, ticket_ids: created.map((ticket) => ticket.id), total_cost: totalCost, balance_after: balance, already_processed: false });
    }
    return json({ detail: "Design preview route is not implemented" }, 404);
  };
}
