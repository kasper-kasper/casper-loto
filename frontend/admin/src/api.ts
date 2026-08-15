import type {
  AdminSession,
  AuditEntry,
  Dashboard,
  Draw,
  DrawDetail,
  Lottery,
  NumberStatistic,
  Player,
  Transaction,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

let csrfToken = "";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (csrfToken && init.method && init.method !== "GET") {
    headers.set("X-Admin-CSRF", csrfToken);
  }
  const response = await fetch(`/api/v1/admin${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    let message = `Admin API error ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the status-based fallback for non-JSON failures.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function rememberSession(session: AdminSession): AdminSession {
  csrfToken = session.csrf_token;
  return session;
}

export const adminApi = {
  login: (username: string, password: string) =>
    request<AdminSession>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }).then(rememberSession),
  session: () => request<AdminSession>("/auth/session").then(rememberSession),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  dashboard: () => request<Dashboard>("/dashboard"),
  players: () => request<Player[]>("/players"),
  lotteries: () => request<Lottery[]>("/lotteries"),
  draws: (query = "") => request<Draw[]>(`/draws${query ? `?${query}` : ""}`),
  draw: (id: string) => request<DrawDetail>(`/draws/${id}`),
  transactions: (query = "") =>
    request<Transaction[]>(`/transactions${query ? `?${query}` : ""}`),
  statistics: (lotteryId: string) =>
    request<NumberStatistic[]>(`/lotteries/${lotteryId}/number-statistics`),
  audit: () => request<AuditEntry[]>("/audit"),
  setBalance: (userId: string, targetAmount: number, reason: string) =>
    request<{ amount: number; already_processed: boolean }>(
      `/players/${userId}/balance-adjustments`,
      {
        method: "POST",
        body: JSON.stringify({
          target_amount: targetAmount,
          reason,
          idempotency_key: crypto.randomUUID(),
        }),
      },
    ),
  configureLottery: (
    lotteryId: string,
    ticketPrice: number,
    baseJackpot: number,
    reason: string,
  ) =>
    request<Lottery>(`/lotteries/${lotteryId}/configuration`, {
      method: "PUT",
      body: JSON.stringify({
        ticket_price: ticketPrice,
        base_jackpot: baseJackpot,
        reason,
      }),
    }),
  setReserve: (lotteryId: string, targetAmount: number, reason: string) =>
    request<{ amount: number; already_processed: boolean }>(
      `/lotteries/${lotteryId}/reserve-adjustments`,
      {
        method: "POST",
        body: JSON.stringify({
          target_amount: targetAmount,
          reason,
          idempotency_key: crypto.randomUUID(),
        }),
      },
    ),
};
