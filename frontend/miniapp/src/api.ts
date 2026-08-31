import type { Dashboard, LiveFeed, PurchaseResult, Ticket } from "./types";

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
    cache: init?.method && init.method !== "GET" ? init.cache : "no-store",
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    const translated: Record<number, string> = {
      402: "Недостаточно CAS для этой покупки.",
      409: "Продажи на выбранный тираж завершены. Обновите расписание и выберите следующий.",
      422: "Комбинация или количество билетов не прошли проверку.",
      503: "Лотерея временно недоступна. Попробуйте ещё раз немного позже.",
    };
    throw new ApiError(translated[response.status] ?? payload.detail ?? "Не удалось выполнить запрос.", response.status);
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
  live: (initData: string) =>
    request<LiveFeed>("/api/v1/miniapp/live", initData),
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
