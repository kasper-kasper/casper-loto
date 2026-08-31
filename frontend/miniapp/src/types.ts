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
  status: TicketStatus;
  matches: number | null;
  prize_amount: number;
  winning_numbers: number[] | null;
}

export interface Dashboard {
  balance: number;
  active_ticket_count: number;
  lotteries: Lottery[];
  recent_results: Ticket[];
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
  status: "SCHEDULED" | "COMPLETED";
  winning_numbers: number[] | null;
  jackpot: number;
  player_ticket_count: number;
  player_winning_ticket_count: number;
  player_best_matches: number | null;
  player_total_prize: number;
  highlighted_tickets: LiveTicket[];
}

export interface LiveFeed {
  server_time: string;
  latest_completed: LiveDraw | null;
  next_scheduled: LiveDraw | null;
}

export interface PurchaseResult {
  operation_id: string;
  draw_id: string;
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
}
