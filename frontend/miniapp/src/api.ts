import { brandViewData } from "../../shared/brandNames";
import { durablePurchase, setPurchaseOwner } from "./purchaseJournal";
import type { Receipt } from "./purchaseJournal";
import type { Publication } from "../../shared/publications";
import type { Highlights } from "./Today";
import type { ArchivePage } from "./types";
import type { BingoFeed, BingoInventory } from "./BingoView";
import type { Account, Dashboard, Favorite, InstantPurchaseResult, InstantTicket, LiveFeed, NotificationPreferences, PurchaseResult, TicketPage, UserNotification } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export function sendTiming(initData: string, metric: "startup_client" | "dashboard_client" | "purchase_client", duration: number, status = 200): void {
  if (!Number.isFinite(duration) || duration < 0 || duration > 120_000) return;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (initData) headers["X-Telegram-Init-Data"] = initData;
  void fetch(`${API_BASE}/api/v1/miniapp/telemetry`, {
    method: "POST", credentials: "include", headers, keepalive: true,
    signal: typeof AbortSignal.timeout === "function" ? AbortSignal.timeout(5_000) : undefined,
    body: JSON.stringify({ metric, duration_ms: Math.round(duration), status }),
  }).catch(() => undefined);
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export async function rawRequest<T>(path: string, initData: string, init?: RequestInit): Promise<T> {
  const started = performance.now();
  let observedStatus = 0;
  const controller = init?.signal ? null : new AbortController();
  const timeout = controller ? window.setTimeout(() => controller.abort(), 20_000) : null;
  try {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (initData) headers.set("X-Telegram-Init-Data", initData);
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: init?.method && init.method !== "GET" ? init.cache : "no-store",
    credentials: "include",
    headers,
    signal: init?.signal ?? controller?.signal,
  });
  observedStatus = response.status;
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    const translated: Record<number, string> = {
      402: "Недостаточно CAS для этой покупки.",
      409: "Продажи на выбранный тираж завершены. Обновите расписание и выберите следующий.",
      422: "Комбинация или количество билетов не прошли проверку.",
      429: "Слишком много быстрых покупок. Подождите несколько секунд и попробуйте снова.",
      503: "Лотерея временно недоступна. Попробуйте ещё раз немного позже.",
    };
    throw new ApiError(translated[response.status] ?? payload.detail ?? "Не удалось выполнить запрос.", response.status);
  }
  if (response.status === 204) return undefined as T;
  return brandViewData(await response.json()) as T;
  } catch (reason) {
    if (reason instanceof ApiError) throw reason;
    observedStatus = 0;
    throw new Error(path.endsWith("/purchases")
      ? "Связь прервалась. Проверяем результат покупки — пока не покупайте заново."
      : "Не удалось получить ответ сервера. Проверьте интернет и попробуйте снова.");
  } finally {
    if (timeout !== null) window.clearTimeout(timeout);
    const metric = path.endsWith("/purchases") ? "purchase_client" : path === "/api/v1/miniapp/dashboard" ? "dashboard_client" : null;
    if (metric) sendTiming(initData, metric, performance.now() - started, observedStatus);
  }
}

async function request<T>(path: string, initData: string, init?: RequestInit, cartIds: string[] = []): Promise<T> {
  if (init?.method === "POST" && path.endsWith("/purchases")) {
    const payload = JSON.parse(String(init.body)) as { idempotency_key: string };
    if (!payload.idempotency_key.startsWith("m1-")) payload.idempotency_key = `m1-${payload.idempotency_key}`;
    const body = JSON.stringify(payload);
    return durablePurchase(path, body, () => rawRequest<Receipt>(path, initData, { ...init, body }),
      reason => reason instanceof ApiError && [402, 409, 422].includes(reason.status), cartIds) as Promise<T>;
  }
  const value = await rawRequest<T>(path, initData, init);
  if (path === "/api/v1/miniapp/dashboard") {
    const id = (value as Dashboard).owner_user_id;
    if (id) setPurchaseOwner(id);
  }
  return value;
}

export const miniAppApi = {
  startupTiming: (initData: string, duration: number) => sendTiming(initData, "startup_client", duration),
  publications: (initData: string, before?: string, signal?: AbortSignal) => request<Publication[]>(`/api/v1/miniapp/publications${before ? `?before=${encodeURIComponent(before)}` : ""}`, initData, { signal }),
  drawArchive: (initData: string, lotteryCode: string, jackpotsOnly: boolean, before: string | null = null, signal?: AbortSignal) => {
    const query = new URLSearchParams({ lottery_code: lotteryCode, jackpots_only: String(jackpotsOnly) });
    if (before) query.set("before", before);
    return request<ArchivePage>(`/api/v1/miniapp/draw-archive?${query}`, initData, { signal });
  },
  highlights: (initData: string, scope: "standard" | "fast" = "standard") => request<Highlights>(`/api/v1/miniapp/highlights?scope=${scope}`, initData),
  bingoInventory: (initData: string, offset = 0, numbers: number[] = []) => {
    const query = new URLSearchParams({ offset: String(offset) });
    numbers.forEach(number => query.append("number", String(number)));
    return request<BingoInventory>(`/api/v1/miniapp/bingo/inventory?${query}`, initData);
  },
  bingoLive: (initData: string) => request<BingoFeed>("/api/v1/miniapp/bingo/live", initData),
  bingoPurchase: (initData: string, drawId: string, selection: { ticketIds?: string[]; quantity?: number; requiredNumbers?: number[] }, key: string) => request<PurchaseResult>("/api/v1/miniapp/bingo/purchases", initData, { method: "POST", body: JSON.stringify({ draw_id: drawId, ticket_ids: selection.ticketIds ?? [], quantity: selection.quantity, required_numbers: selection.requiredNumbers ?? [], idempotency_key: key }) }),
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
  kasperLiveHistory: (initData: string) =>
    request<InstantTicket[]>("/api/v1/miniapp/kasper-live/tickets", initData),
  kasperLivePurchase: (initData: string, quantity: 1 | 3, idempotencyKey: string) =>
    request<InstantPurchaseResult>("/api/v1/miniapp/kasper-live/purchases", initData, {
      method: "POST",
      body: JSON.stringify({ quantity, idempotency_key: idempotencyKey }),
    }),
  auroraHistory: (initData: string) =>
    request<InstantTicket[]>("/api/v1/miniapp/aurora/tickets", initData),
  auroraPurchase: (initData: string, quantity: 1 | 3, idempotencyKey: string) =>
    request<InstantPurchaseResult>("/api/v1/miniapp/aurora/purchases", initData, {
      method: "POST",
      body: JSON.stringify({ quantity, idempotency_key: idempotencyKey }),
    }),
  vaultHistory: (initData: string) =>
    request<InstantTicket[]>("/api/v1/miniapp/vault/tickets", initData),
  vaultPurchase: (initData: string, quantity: 1 | 3, idempotencyKey: string) =>
    request<InstantPurchaseResult>("/api/v1/miniapp/vault/purchases", initData, {
      method: "POST",
      body: JSON.stringify({ quantity, idempotency_key: idempotencyKey }),
    }),
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
  live: (initData: string, scope: "standard" | "fast" = "standard", lotteryCode = "") =>
    request<LiveFeed>(`/api/v1/miniapp/live?scope=${scope}${lotteryCode ? `&lottery_code=${encodeURIComponent(lotteryCode)}` : ""}`, initData),
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
        if (data) onSnapshot(brandViewData(JSON.parse(data.slice(6))) as LiveFeed);
      }
    }
  },
  tickets: async (initData: string, state: "active" | "history", lotteryCode = "", winsOnly = false, position: number | string = 0) => {
    const params = new URLSearchParams({ state });
    if (lotteryCode.startsWith("scope:")) params.set("scope", lotteryCode.slice(6));
    else if (lotteryCode) params.set("lottery_code", lotteryCode);
    if (winsOnly) params.set("wins_only", "true");
    params.set("limit", "20");
    if (typeof position === "string") params.set("cursor", position);
    else params.set("offset", String(position));
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
    expectedScheduledAt?: string | null,
    cartIds: string[] = [],
  ) =>
    request<PurchaseResult>(
      `/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/purchases`,
      initData,
      {
      method: "POST",
      body: JSON.stringify({ combinations, idempotency_key: idempotencyKey, draw_count: drawCount, expected_scheduled_at: expectedScheduledAt }),
      },
      cartIds,
    ),
  favorites: (initData: string, lotteryCode: string) =>
    request<Favorite[]>(`/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/favorites`, initData),
  saveFavorite: (initData: string, lotteryCode: string, numbers: number[]) =>
    request<Favorite>(`/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/favorites`, initData, { method: "POST", body: JSON.stringify({ numbers }) }),
  deleteFavorite: (initData: string, lotteryCode: string, favoriteId: string) =>
    request<void>(`/api/v1/miniapp/lotteries/${encodeURIComponent(lotteryCode)}/favorites/${encodeURIComponent(favoriteId)}`, initData, { method: "DELETE" }),
};
