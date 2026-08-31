import type { Dashboard, PurchaseResult, Ticket } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, initData: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (initData) headers.set("X-Telegram-Init-Data", initData);
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(payload.detail ?? "Не удалось выполнить запрос.", response.status);
  }
  return (await response.json()) as T;
}

export const miniAppApi = {
  devSession: () =>
    request<{ mode: "local-development" }>(
      "/api/v1/miniapp/dev/session",
      "",
      { method: "POST" },
    ),
  devRefill: () =>
    request<{ balance: number }>("/api/v1/miniapp/dev/refill", "", {
      method: "POST",
    }),
  dashboard: (initData: string) =>
    request<Dashboard>("/api/v1/miniapp/dashboard", initData),
  tickets: async (initData: string, state: "active" | "history") => {
    const response = await request<{ tickets: Ticket[] }>(
      `/api/v1/miniapp/tickets?state=${state}`,
      initData,
    );
    return response.tickets;
  },
  purchase: (
    initData: string,
    lotteryCode: string,
    combinations: number[][],
    idempotencyKey: string,
  ) =>
    request<PurchaseResult>(
      `/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/purchases`,
      initData,
      {
      method: "POST",
      body: JSON.stringify({ combinations, idempotency_key: idempotencyKey }),
      },
    ),
};
