export interface Lottery {
  code: string;
  name: string;
  kind: "WEEKLY" | "DAILY";
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
  status: "PURCHASED" | "SETTLED";
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

export interface DrawResult {
  lottery_code: string;
  lottery_name: string;
  draw_number: number;
  scheduled_at: string;
  executed_at: string | null;
  winning_numbers: number[];
  ticket_count: number;
  total_payout: number;
}

export interface WebSession {
  display_name: string;
  csrf_token: string;
  expires_at: string;
}
