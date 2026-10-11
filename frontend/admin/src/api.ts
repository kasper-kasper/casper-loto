import { brandViewData } from "../../shared/brandNames";
import type { MonitoringSnapshot } from "./OperationalMonitor";
import type { Publication, PublicationInput, PublicationTemplate } from "../../shared/publications";
import type {
  AdminSession,
  AuditEntry,
  Dashboard,
  Draw,
  DrawDetail,
  InterestingFact,
  InterestingFactStatus,
  JackpotEvent,
  KasperLiveSummary,
  Lottery,
  NumberStatisticsReport,
  NotificationItem,
  Player,
  PlayerHistoryPage,
  Transaction, TicketAnalytics,
  ReleaseNote,
  ScheduleEntry,
  ActivityPoint,
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

const errorMessages: Record<string, string> = {
  "Proposal expired after 24 hours; refresh suggestions.": "Предложение устарело. Обновите предложку.",
  "Jackpot series ended; refresh suggestions.": "Серия джекпота уже прервалась. Обновите предложку.",
  "Эта лотерея не участвует в распределительных тиражах.": "Эта лотерея не участвует в распределительных тиражах.",
  "Назначение возможно только до окончания продаж.": "Продажи уже закрыты — распределение назначить нельзя.",
  "Для назначения настройте бота и канал публикаций.": "Настройте бота и канал публикаций перед назначением.",
  "Обновите календарь тиражей.": "Расписание обновилось. Выберите дату и тираж заново.",
  "В это время по расписанию нет тиража.": "В это время по расписанию нет тиража.",
  "Publication changed; reload it.": "Публикация изменена в другой вкладке. Откройте её заново.",
  "Only drafts can be edited; duplicate a published story first.": "Опубликованную историю можно изменить через создание копии.",
  "Publication identifier already used.": "Этот черновик уже сохранён. Откройте запись из списка или создайте новую.",
  "Administrator authentication is required.": "Требуется вход администратора.",
  "Administrator session is invalid or expired.": "Сессия администратора недействительна или истекла.",
  "Administrator CSRF token is missing or invalid.": "Защитный токен отсутствует или недействителен.",
  "Administrator authentication is not configured.": "Доступ администратора не настроен.",
  "Invalid administrator credentials.": "Неверный логин или пароль администратора.",
  "Transaction date filters must include a timezone.": "В фильтре даты необходимо указать часовой пояс.",
  "A reason of 1 to 512 characters is required.": "Укажите причину длиной от 1 до 512 символов.",
  "Player does not exist.": "Игрок не найден.",
  "Player balance does not exist.": "Баланс игрока не найден.",
  "Lottery reserve does not exist.": "Резерв лотереи не найден.",
  "Lottery CAS values are outside their valid range.": "Значения CAS для лотереи выходят за допустимый диапазон.",
  "Lottery or jackpot account does not exist.": "Лотерея или счёт джекпота не найден.",
  "Weekly ticket price must be divisible by 4 CAS.": "Цена еженедельного билета должна делиться на 4 CAS.",
  "Daily ticket price must be even.": "Цена ежедневного билета должна быть чётным числом CAS.",
  "CAS balance cannot be negative.": "Баланс CAS не может быть отрицательным.",
  "Idempotency key must contain 1 to 100 characters.": "Ключ операции должен содержать от 1 до 100 символов.",
  "Lottery does not exist.": "Лотерея не найдена.",
  "Draw does not exist.": "Тираж не найден.",
};

function localizedError(detail: string | undefined, status: number): string {
  if (detail && errorMessages[detail]) return errorMessages[detail];
  if (status === 401) return "Необходимо снова войти в систему.";
  if (status === 403) return "Недостаточно прав для этой операции.";
  if (status === 404) return "Запрошенная запись не найдена.";
  if (status === 422) return "Проверьте заполненные поля.";
  return `Ошибка сервера администратора (${status}).`;
}

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
    let detail: string | undefined;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail;
    } catch {
      // Preserve the status-based fallback for non-JSON failures.
    }
    throw new ApiError(localizedError(detail, response.status), response.status);
  }
  if (response.status === 204) return undefined as T;
  return brandViewData(await response.json()) as T;
}

function rememberSession(session: AdminSession): AdminSession {
  csrfToken = session.csrf_token;
  return session;
}

export type LotteryScope = "standard" | "fast" | "all";

async function drawPage(query = ""): Promise<Draw[]> {
  const params = new URLSearchParams(query);
  if (!params.has("limit")) params.set("limit", "100");
  return request<Draw[]>(`/draws?${params.toString()}`);
}

export interface DistributionDraw {
  id: string; lottery_id: string; lottery_name: string; number: number; scheduled_at: string; sales_close_at: string;
  jackpot: number; ticket_count: number; is_distribution: boolean; status: string; announcement_state: string | null; post: string;
}

export const adminApi = {
  monitoring: () => request<MonitoringSnapshot>("/api/v1/admin/monitoring"),
  distributionDraws: (lotteryId: string, day: string) => request<DistributionDraw[]>(`/distribution-draws?lottery_id=${encodeURIComponent(lotteryId)}&day=${encodeURIComponent(day)}`),
  assignDistribution: (draw: DistributionDraw) => request<DistributionDraw>(`/distribution-draws/${draw.id}`, { method: "POST", body: JSON.stringify({ lottery_id: draw.lottery_id, scheduled_at: draw.scheduled_at }) }),
  publicationTemplates: () => request<PublicationTemplate[]>("/publications/templates"),
  publicationChannel: (check = false) => request<{ channel: string | null; delivery_enabled: boolean; checked: boolean; can_post: boolean; bot_username?: string; error?: string }>(`/publications/channel?check=${check}`),
  preparePublicationSuggestions: () => request<{ prepared: boolean }>("/publications/suggestions/prepare", { method: "POST" }),
  publications: (before?: string, view: "all" | "suggestions" = "all") => request<Publication[]>(`/publications?view=${view}${before ? `&before=${encodeURIComponent(before)}` : ""}`),
  savePublication: (id: string, payload: PublicationInput) => request<Publication>(`/publications/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  editPublication: (id: string, revision: number, payload: PublicationInput) => request<Publication>(`/publications/${id}`, { method: "PATCH", body: JSON.stringify({ ...payload, revision }) }),
  publicationAction: (id: string, revision: number, action: "publish" | "archive" | "delete") => request<Publication>(`/publications/${id}/${action}`, { method: "POST", body: JSON.stringify({ revision }) }),
  login: (username: string, password: string, rememberBrowser = true) =>
    request<AdminSession>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password, remember_browser: rememberBrowser }),
    }).then(rememberSession),
  session: () => request<AdminSession>("/auth/session").then(rememberSession),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  dashboard: (scope: LotteryScope = "all") => request<Dashboard>(`/dashboard?scope=${scope}`),
  vault: () => request<KasperLiveSummary>("/vault"),
  aurora: () => request<KasperLiveSummary>("/aurora"),
  kasperLive: () => request<KasperLiveSummary>("/kasper-live"),
  players: (query = "") => request<Player[]>(`/players?limit=500${query ? `&q=${encodeURIComponent(query)}` : ""}`),
  playerTicketHistory: (userId: string, filter = "all", lotteryCode = "", offset = 0) => {
    const params = new URLSearchParams({ filter, limit: "100", offset: String(offset) });
    if (lotteryCode) params.set("lottery_code", lotteryCode);
    return request<PlayerHistoryPage>(`/players/${encodeURIComponent(userId)}/ticket-history?${params.toString()}`);
  },
  lotteries: () => request<Lottery[]>("/lotteries"),
  draws: drawPage,
  jackpotEvents: (scope: LotteryScope = "all", lotteryId = "", offset = 0) => {
    const params = new URLSearchParams({ scope, limit: "100", offset: String(offset) });
    if (lotteryId) params.set("lottery_id", lotteryId);
    return request<JackpotEvent[]>(`/jackpots?${params.toString()}`);
  },
  schedule: (scope: LotteryScope = "all") => request<ScheduleEntry[]>(`/schedule?scope=${scope}`),
  draw: (id: string) => request<DrawDetail>(`/draws/${id}`),
  transactions: (query = "") =>
    request<Transaction[]>(`/transactions${query ? `?${query}` : ""}`),
  playerTransactions: (userId: string, offset = 0, type = "") => {
    const params = new URLSearchParams({ user_id: userId, limit: "100", offset: String(offset) });
    if (type) params.set("type", type);
    return request<Transaction[]>(`/transactions?${params.toString()}`);
  },
  statistics: (lotteryId: string, limit = 20, dateFrom = "2026-08-31T21:00:00.000Z") => {
    const params = new URLSearchParams({ limit: String(limit), date_from: dateFrom });
    return request<NumberStatisticsReport>(`/lotteries/${lotteryId}/number-statistics?${params.toString()}`);
  },
  ticketAnalytics: (scope: LotteryScope = "all") => request<TicketAnalytics>(`/ticket-analytics?scope=${scope}`),
  activity: (periodDays = 1, scope: LotteryScope = "all") => request<ActivityPoint[]>(`/activity?period_days=${periodDays}&scope=${scope}`),
  audit: () => request<AuditEntry[]>("/audit"),
  notifications: () => request<NotificationItem[]>("/notifications"),
  releaseNotes: (kind: "changelog" | "devlog") =>
    request<ReleaseNote[]>(`/release-notes/${kind}`),
  interestingFacts: (query = "fact_status=new&limit=50") =>
    request<InterestingFact[]>(`/interesting-facts${query ? `?${query}` : ""}`),
  setInterestingFactStatus: (id: string, status: InterestingFactStatus) =>
    request<InterestingFact>(`/interesting-facts/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
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
  setAutoPlay: (userId: string, enabled: boolean, ticketsPerDraw: number, reason: string) =>
    request<Player>(`/players/${userId}/auto-play`, {
      method: "PUT",
      body: JSON.stringify({ enabled, tickets_per_draw: ticketsPerDraw, reason }),
    }),
  configureLottery: (
    lotteryId: string,
    ticketPrice: number,
    baseJackpot: number,
    salesCutoffMinutes: number,
    maxTicketsPerPurchase: number,
    maxTicketsPerUserPerDraw: number,
    reason: string,
  ) =>
    request<Lottery>(`/lotteries/${lotteryId}/configuration`, {
      method: "PUT",
      body: JSON.stringify({
        ticket_price: ticketPrice,
        base_jackpot: baseJackpot,
        sales_cutoff_minutes: salesCutoffMinutes,
        max_tickets_per_purchase: maxTicketsPerPurchase,
        max_tickets_per_user_per_draw: maxTicketsPerUserPerDraw,
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
  setJackpot: (lotteryId: string, targetAmount: number, reason: string) =>
    request<{ amount: number; already_processed: boolean }>(
      `/lotteries/${lotteryId}/jackpot-adjustments`,
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
