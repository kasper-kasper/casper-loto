import type { Account, Dashboard, Favorite, LiveDraw, LiveFeed, Ticket, UserNotification } from "./types";

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
const nowIso = () => new Date().toISOString();
const future = (minutes: number) => new Date(Date.now() + minutes * 60_000).toISOString();

const lotterySeed = [
  { code: "shadow", name: "SHADOW", kind: "DAILY" as const, numbers_to_pick: 3, max_number: 15, ticket_price: 888, jackpot: 888_888, draw_number: 38, scheduled_at: future(7) },
  { code: "flash", name: "FLASH", kind: "DAILY" as const, numbers_to_pick: 3, max_number: 15, ticket_price: 888, jackpot: 901_320, draw_number: 42, scheduled_at: future(17) },
  { code: "pulse", name: "PULSE", kind: "DAILY" as const, numbers_to_pick: 3, max_number: 15, primary_numbers_to_pick: 2, primary_max_number: 10, secondary_numbers_to_pick: 1, secondary_max_number: 5, secondary_storage_offset: 10, ticket_price: 1_234, jackpot: 1_234_567, draw_number: 1, scheduled_at: future(10) },
  { code: "grob", name: "ГРОБ", kind: "DAILY" as const, numbers_to_pick: 3, max_number: 16, ticket_price: 6_666, jackpot: 6_666_666, draw_number: 1, scheduled_at: future(36) },
  { code: "september", name: "3 СЕНТЯБРЯ", kind: "DAILY" as const, numbers_to_pick: 3, max_number: 33, ticket_price: 333, jackpot: 33_333_333, draw_number: 1, scheduled_at: future(83) },
  { code: "pll", name: "ПЛЛ-Лото", kind: "DAILY" as const, numbers_to_pick: 4, max_number: 15, ticket_price: 24_000, jackpot: 18_640_000, draw_number: 418, scheduled_at: future(145) },
  { code: "pss", name: "ПСС-Лото", kind: "DAILY" as const, numbers_to_pick: 4, max_number: 15, ticket_price: 24_000, jackpot: 24_000_000, draw_number: 219, scheduled_at: future(230) },
  { code: "khan", name: "ХАН-Лото", kind: "DAILY" as const, numbers_to_pick: 4, max_number: 15, ticket_price: 24_000, jackpot: 24_000_000, draw_number: 174, scheduled_at: future(310) },
  { code: "weekly", name: "Kasper Grand", kind: "WEEKLY" as const, numbers_to_pick: 7, max_number: 40, primary_numbers_to_pick: 5, primary_max_number: 35, secondary_numbers_to_pick: 2, secondary_max_number: 5, secondary_storage_offset: 35, ticket_price: 50_000, jackpot: 5_000_182_500, draw_number: 4, scheduled_at: future(1_420) },
];

let balance = 100_000_000_000;
let purchasedTickets: Ticket[] = [];
let favoriteRows: Favorite[] = [];

const dashboard = (): Dashboard => ({
  server_time: nowIso(),
  balance,
  active_ticket_count: purchasedTickets.length,
  lotteries: lotterySeed.map((lottery) => ({ ...lottery, sales_close_at: new Date(new Date(lottery.scheduled_at).getTime() - (["flash", "shadow", "pulse"].includes(lottery.code) ? 8_000 : 120_000)).toISOString(), sales_open: true, purchase_available: true, player_ticket_count: purchasedTickets.filter((ticket) => ticket.lottery_code === lottery.code).length, sales_status: "OPEN" as const, max_tickets_per_purchase: ["flash", "shadow", "pulse"].includes(lottery.code) ? 100 : 1_000, max_tickets_per_user_per_draw: ["flash", "shadow", "pulse"].includes(lottery.code) ? 500 : 5_000 })),
  recent_results: [],
  monthly_total_payout: 12_333_333,
});

const account = (): Account => ({ display_name: "Дизайн-превью", balance, ticket_count: purchasedTickets.length + 42, active_ticket_count: purchasedTickets.length, winning_ticket_count: 7, total_spent: 14_760_000, total_won: 19_333_333, best_win: 12_000_000, unread_notification_count: 1, notification_preferences: { telegram_enabled: true, draw_results_enabled: true, inactivity_reminders_enabled: true } });

const liveDraw = (): LiveDraw => {
  const lottery = lotterySeed.find((item) => item.code === "grob")!;
  const starts = lottery.scheduled_at;
  return { lottery_code: lottery.code, lottery_name: lottery.name, lottery_kind: lottery.kind, draw_number: lottery.draw_number, scheduled_at: starts, status: "SCHEDULED", winning_numbers: null, jackpot: lottery.jackpot, player_ticket_count: purchasedTickets.filter((ticket) => ticket.lottery_code === lottery.code).length, player_winning_ticket_count: 0, player_best_matches: null, player_total_prize: 0, highlighted_tickets: [], sales_close_at: new Date(new Date(starts).getTime() - 120_000).toISOString(), sales_status: "OPEN", live_starts_at: starts, reveal_at: [0, 1, 2].map((index) => new Date(new Date(starts).getTime() + 3_000 + index * 4_000).toISOString()), live_ends_at: new Date(new Date(starts).getTime() + 18_000).toISOString() };
};

const liveFeed = (): LiveFeed => ({ server_time: nowIso(), latest_completed: null, next_scheduled: liveDraw(), recent_completed: [] });

const notifications: UserNotification[] = [{ id: "preview-notice", type: "DRAW_INVITATION", title: "Сегодня особый тираж", body: "«3 СЕНТЯБРЯ» уже ждёт вашу комбинацию.", payload: {}, read_at: null, created_at: nowIso() }];

export function installDesignPreview(): void {
  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(raw, window.location.origin);
    const path = url.pathname;
    if (!path.startsWith("/api/v1/miniapp/")) return nativeFetch(input, init);
    if (path.endsWith("/dev/session")) return json({ mode: "design-preview" });
    if (path.endsWith("/dev/refill")) { balance = 100_000_000_000; return json({ balance }); }
    if (path.endsWith("/dashboard")) return json(dashboard());
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
      const created = body.combinations.map((numbers, index): Ticket => ({ id: crypto.randomUUID(), public_number: purchasedTickets.length + index + 1, lottery_code: lottery.code, lottery_name: lottery.name, draw_number: lottery.draw_number, scheduled_at: lottery.scheduled_at, numbers, purchase_price: lottery.ticket_price, source: "MANUAL", status: "PURCHASED", matches: null, prize_amount: 0, winning_numbers: null }));
      purchasedTickets = [...created, ...purchasedTickets];
      return json({ operation_id: crypto.randomUUID(), draw_id: "preview-draw", draw_ids: ["preview-draw"], draw_count: body.draw_count, ticket_ids: created.map((ticket) => ticket.id), total_cost: totalCost, balance_after: balance, already_processed: false });
    }
    return json({ detail: "Design preview route is not implemented" }, 404);
  };
}
