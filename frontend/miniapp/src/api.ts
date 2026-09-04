import type { Account, Dashboard, Favorite, LiveFeed, NotificationPreferences, PurchaseResult, TicketPage, UserNotification } from "./types";

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
  if (response.status === 204) return undefined as T;
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
  account: (initData: string) =>
    request<Account>("/api/v1/miniapp/account", initData),
  notifications: (initData: string) =>
    request<UserNotification[]>("/api/v1/miniapp/notifications", initData),
  notificationPreferences: (initData: string, preferences: NotificationPreferences) =>
    request<NotificationPreferences>("/api/v1/miniapp/notification-preferences", initData, { method: "PUT", body: JSON.stringify(preferences) }),
  markNotificationsRead: (initData: string, notificationId?: string) =>
    request<void>("/api/v1/miniapp/notifications/read", initData, { method: "POST", body: JSON.stringify({ notification_id: notificationId ?? null }) }),
  testNotification: (initData: string) =>
    request<{ queued: boolean }>("/api/v1/miniapp/notifications/test", initData, { method: "POST" }),
  live: (initData: string, scope: "standard" | "fast" = "standard") =>
    request<LiveFeed>(`/api/v1/miniapp/live?scope=${scope}`, initData),
  liveStream: async (initData: string, onSnapshot: (feed: LiveFeed) => void, signal: AbortSignal, scope: "standard" | "fast" = "standard") => {
    const headers = new Headers({ Accept: "text/event-stream" });
    if (initData) headers.set("X-Telegram-Init-Data", initData);
    const response = await fetch(`${API_BASE}/api/v1/miniapp/live/stream?scope=${scope}`, { credentials: "include", headers, signal });
    if (!response.ok || !response.body) throw new ApiError("Не удалось подключиться к эфиру.", response.status);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (!signal.aborted) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const event of events) {
        const data = event.split("\n").find((line) => line.startsWith("data: "));
        if (data) onSnapshot(JSON.parse(data.slice(6)) as LiveFeed);
      }
    }
  },
  tickets: async (initData: string, state: "active" | "history", lotteryCode = "", winsOnly = false, offset = 0) => {
    const params = new URLSearchParams({ state });
    if (lotteryCode) params.set("lottery_code", lotteryCode);
    if (winsOnly) params.set("wins_only", "true");
    params.set("limit", "100");
    params.set("offset", String(offset));
    return request<TicketPage>(
      `/api/v1/miniapp/tickets?${params.toString()}`,
      initData,
    );
  },
  purchase: (
    initData: string,
    lotteryCode: string,
    combinations: number[][],
    idempotencyKey: string,
    drawCount: 1 | 5 = 1,
  ) =>
    request<PurchaseResult>(
      `/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/purchases`,
      initData,
      {
      method: "POST",
      body: JSON.stringify({ combinations, idempotency_key: idempotencyKey, draw_count: drawCount }),
      },
    ),
  favorites: (initData: string, lotteryCode: string) =>
    request<Favorite[]>(`/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/favorites`, initData),
  saveFavorite: (initData: string, lotteryCode: string, numbers: number[]) =>
    request<Favorite>(`/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/favorites`, initData, { method: "POST", body: JSON.stringify({ numbers }) }),
  deleteFavorite: (initData: string, lotteryCode: string, favoriteId: string) =>
    request<void>(`/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/favorites/${encodeURIComponent(favoriteId)}`, initData, { method: "DELETE" }),
};
