export type LotteryKind = "WEEKLY" | "DAILY";
export type TicketStatus = "PURCHASED" | "SETTLED";

export interface Lottery {
  code: string;
  name: string;
  kind: LotteryKind;
  numbers_to_pick: number;
  max_number: number;
  ticket_price: number | null;
  jackpot: number;
  draw_number: number | null;
  scheduled_at: string | null;
  sales_close_at: string | null;
  sales_open: boolean;
  purchase_available: boolean;
  player_ticket_count: number;
  sales_status: "OPEN" | "CLOSING_SOON" | "CLOSED" | "DRAWING" | "COMPLETED";
  max_tickets_per_purchase: number;
  max_tickets_per_user_per_draw: number;
}

export interface Ticket {
  id: string;
  public_number: number;
  lottery_code: string;
  lottery_name: string;
  draw_number: number;
  scheduled_at: string;
  numbers: number[];
  purchase_price: number;
  source: "MANUAL" | "AUTO_PLAY";
  status: TicketStatus;
  matches: number | null;
  prize_amount: number;
  winning_numbers: number[] | null;
}

export interface Dashboard {
  app_version?: string;
  server_time: string;
  balance: number;
  active_ticket_count: number;
  lotteries: Lottery[];
  recent_results: Ticket[];
  monthly_total_payout: number;
}

export interface LiveTicket {
  public_number: number;
  numbers: number[];
  matches: number | null;
  prize_amount: number;
}

export interface LiveDraw {
  lottery_code: string;
  lottery_name: string;
  lottery_kind: LotteryKind;
  draw_number: number;
  scheduled_at: string;
  status: "SCHEDULED" | "CLOSED" | "DRAWING" | "SETTLING" | "COMPLETED";
  winning_numbers: number[] | null;
  jackpot: number;
  player_ticket_count: number;
  player_winning_ticket_count: number;
  player_best_matches: number | null;
  player_total_prize: number;
  highlighted_tickets: LiveTicket[];
  sales_close_at: string;
  sales_status: "OPEN" | "CLOSING_SOON" | "CLOSED" | "DRAWING" | "COMPLETED";
  live_starts_at: string;
  reveal_at: string[];
  live_ends_at: string;
}

export interface LiveFeed {
  server_time: string;
  latest_completed: LiveDraw | null;
  next_scheduled: LiveDraw | null;
  recent_completed: LiveDraw[];
}

export interface PurchaseResult {
  operation_id: string;
  draw_id: string;
  draw_ids: string[];
  draw_count: number;
  ticket_ids: string[];
  total_cost: number;
  balance_after: number;
  already_processed: boolean;
}

export interface CartTicket {
  id: string;
  lotteryCode: string;
  lotteryName: string;
  price: number;
  numbers: number[];
  drawCount: 1 | 5;
}

export interface Favorite {
  id: string;
  numbers: number[];
}

export interface NotificationPreferences {
  telegram_enabled: boolean;
  draw_results_enabled: boolean;
  inactivity_reminders_enabled: boolean;
}

export interface Account {
  display_name: string;
  balance: number;
  ticket_count: number;
  active_ticket_count: number;
  winning_ticket_count: number;
  total_spent: number;
  total_won: number;
  best_win: number;
  unread_notification_count: number;
  notification_preferences: NotificationPreferences;
}

export interface UserNotification {
  id: string;
  type: "WIN" | "DRAW_RESULT" | "DRAW_INVITATION" | "JACKPOT_NEWS";
  title: string;
  body: string;
  payload: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}
