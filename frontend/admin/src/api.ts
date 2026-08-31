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
  ReleaseNote,
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
  return (await response.json()) as T;
}

function rememberSession(session: AdminSession): AdminSession {
  csrfToken = session.csrf_token;
  return session;
}

async function allDraws(query = ""): Promise<Draw[]> {
  const pageSize = 500;
  const params = new URLSearchParams(query);
  const rows: Draw[] = [];
  for (let offset = 0; ; offset += pageSize) {
    params.set("limit", String(pageSize));
    params.set("offset", String(offset));
    const page = await request<Draw[]>(`/draws?${params.toString()}`);
    rows.push(...page);
    if (page.length < pageSize) return rows;
  }
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
  draws: allDraws,
  draw: (id: string) => request<DrawDetail>(`/draws/${id}`),
  transactions: (query = "") =>
    request<Transaction[]>(`/transactions${query ? `?${query}` : ""}`),
  statistics: (lotteryId: string) =>
    request<NumberStatistic[]>(`/lotteries/${lotteryId}/number-statistics`),
  audit: () => request<AuditEntry[]>("/audit"),
  releaseNotes: (kind: "changelog" | "devlog") =>
    request<ReleaseNote[]>(`/release-notes/${kind}`),
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
