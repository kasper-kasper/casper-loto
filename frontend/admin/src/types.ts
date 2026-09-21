export interface AdminSession {
  username: string;
  csrf_token: string;
  expires_at: string;
  miniapp_url?: string | null;
  remembered?: boolean;
}

export interface Player {
  id: string;
  display_name: string;
  username: string | null;
  telegram_id: number | null;
  is_active: boolean;
  balance: number;
  ticket_count: number;
  active_ticket_count: number;
  spent: number;
  won: number;
  net: number;
  telegram_notifications_enabled: boolean;
  auto_play_enabled: boolean;
  auto_play_tickets_per_draw: number;
  auto_play_last_attempted_at: string | null;
  auto_play_last_succeeded_at: string | null;
  auto_play_last_error: string | null;
}

export interface Lottery {
  id: string;
  code: string;
  name: string;
  kind: "WEEKLY" | "DAILY";
  ticket_price: number | null;
  base_jackpot: number;
  current_jackpot: number;
  distribution_fund: number;
  reserve: number;
  schedule: Record<string, unknown>;
  sales_cutoff_minutes: number | null;
  max_tickets_per_purchase: number;
  max_tickets_per_user_per_draw: number;
  is_active: boolean;
  next_draw_number: number | null;
  next_draw_at: string | null;
}

export interface Transaction {
  id: string;
  operation_id: string;
  type: string;
  account_kind: string;
  amount: number;
  balance_before: number;
  balance_after: number;
  user_id: string | null;
  lottery_id: string | null;
  draw_id: string | null;
  ticket_id: string | null;
  created_at: string;
  details: Record<string, unknown>;
}

export interface Draw {
  id: string;
  lottery_id: string;
  lottery_code: string;
  lottery_name: string;
  public_number: number;
  status: string;
  scheduled_at: string;
  sales_close_at: string;
  executed_at: string | null;
  winning_numbers: number[] | null;
  ticket_count: number;
  total_sales: number;
  total_payout: number;
  jackpot_opening: number | null;
  jackpot_closing: number | null;
  distribution_opening: number | null;
  distribution_closing: number | null;
  reserve_used: number;
  kasper_fund_used: number;
  correlation_id: string;
  jackpot_amount?: number | null;
}

export interface DrawTicket {
  id: string;
  public_number: number;
  user_id: string;
  player_name?: string;
  player_username?: string | null;
  player_telegram_id?: number | null;
  is_jackpot_winner?: boolean;
  numbers: number[];
  purchase_price: number;
  matches: number | null;
  prize_amount: number;
  bingo_result?: { moves: number[]; amounts: number[] } | null;
}

export interface DrawDetail {
  draw: Draw;
  tickets: DrawTicket[];
}

export interface ScheduleEntry {
  id: string;
  lottery_id: string;
  lottery_name: string;
  public_number: number;
  scheduled_at: string;
}

export interface NumberStatistic {
  number: number;
  appearances: number;
  draw_percentage: number;
  last_appearance: string | null;
  draws_since_last: number | null;
}

export interface NumberStatisticsReport {
  lottery_id: string;
  lottery_name: string;
  period_start: string | null;
  window_size: number | null;
  draw_count: number;
  first_draw_at: string | null;
  last_draw_at: string | null;
  numbers: NumberStatistic[];
}

export interface AuditEntry {
  id: string;
  admin_user_id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  reason: string | null;
  created_at: string;
}

export interface Dashboard {
  version: string;
  uptime_seconds: number;
  database_healthy: boolean;
  bot_configured: boolean;
  scheduler_enabled: boolean;
  counts: {
    users: number;
    tickets: number;
    completed_draws: number;
    pending_draws: number;
  };
  lotteries: Lottery[];
  recent_draws: Draw[];
  recent_transactions: Transaction[];
  operations: {
    today: {
      completed_draws: number;
      purchased_tickets: number;
      sales: number;
      winning_tickets: number;
      payout: number;
      net: number;
      by_lottery?: Array<{
        lottery_id: string;
        lottery_name: string;
        purchased_tickets: number;
        sales: number;
        winning_tickets: number;
        payout: number;
        net: number;
      }>;
    };
    scheduler: {
      last_started_at: string | null;
      last_succeeded_at: string | null;
      last_failed_at: string | null;
      last_error: string | null;
      settled_count: number;
      prepared_count: number;
    };
    stuck_draw_count: number;
    notifications: Record<string, number>;
    next_draws: Array<{
      id: string;
      lottery_name: string;
      draw_number: number;
      scheduled_at: string;
      sales_close_at: string;
      status: string;
      ticket_count: number;
      participant_count: number;
      total_sales: number;
    }>;
  };
  jackpots: {
    kasper_fund_balance: number;
    total_wins: number;
    total_paid: number;
    largest_win: number;
    lotteries: Array<{ lottery_id?: string; code: string; name: string; is_active?: boolean; win_count: number; total_paid: number; last_win_at: string | null; largest_win?: number; last_win_amount?: number | null; last_draw_id?: string | null; last_draw_number?: number | null }>;
    last_win?: JackpotEvent | null;
    history: JackpotEvent[];
  };
}

export interface ReleaseNote {
  version: string;
  date: string | null;
  content: string;
  sequence: number | null;
}

export interface TicketAnalyticsRow {
  lottery_id: string | null;
  lottery_name: string;
  is_active: boolean | null;
  total_tickets: number;
  active_tickets: number;
  settled_tickets: number;
  winning_tickets: number;
  participants: number;
  winning_players: number;
  total_sales: number;
  total_payout: number;
}

export interface TicketAnalytics {
  overall: TicketAnalyticsRow;
  lotteries: TicketAnalyticsRow[];
}

export interface ActivityPoint {
  bucket_at: string;
  ticket_count: number;
  total_sales: number;
  total_payout: number;
}

export interface NotificationItem {
  id: string;
  event_key: string;
  user_id: string;
  type: string;
  status: string;
  attempts: number;
  available_at: string;
  sent_at: string | null;
  last_error: string | null;
  created_at: string;
}

export type InterestingFactStatus = "new" | "viewed" | "used" | "hidden";

export interface InterestingFact {
  id: string;
  generation_date: string;
  generated_at: string;
  lottery_id: string;
  lottery_code: string;
  lottery_name: string;
  fact_type: string;
  title: string;
  description: string;
  numeric_values: Record<string, unknown>;
  score: number;
  status: InterestingFactStatus;
}


export interface JackpotEvent {
  id: string;
  lottery_code: string;
  lottery_name: string;
  draw_id: string;
  draw_number?: number;
  jackpot_amount: number;
  winner_ticket_count: number;
  winner_user_count: number;
  base_jackpot_after: number;
  occurred_at: string;
}
