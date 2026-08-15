import type { Dashboard, DrawResult, Ticket, WebSession } from "./types";

let csrfToken = "";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (csrfToken && init?.method && init.method !== "GET") {
    headers.set("X-Web-CSRF", csrfToken);
  }
  const response = await fetch(`/api/v1/web${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(body.detail ?? "Запрос не выполнен.", response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function rememberSession(session: WebSession): WebSession {
  csrfToken = session.csrf_token;
  return session;
}

export const webApi = {
  login: (username: string, password: string) =>
    request<WebSession>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }).then(rememberSession),
  session: () => request<WebSession>("/auth/session").then(rememberSession),
  logout: () => request<void>("/auth/logout", { method: "POST" }).finally(() => { csrfToken = ""; }),
  dashboard: () => request<Dashboard>("/dashboard"),
  tickets: (state: "active" | "history") =>
    request<{ tickets: Ticket[] }>(`/tickets?state=${state}`).then((value) => value.tickets),
  results: () => request<{ draws: DrawResult[] }>("/results").then((value) => value.draws),
  purchase: (
    kind: "weekly" | "daily",
    combinations: number[][],
    idempotencyKey: string,
  ) =>
    request<{ ticket_ids: string[]; total_cost: number; balance_after: number }>(
      `/${kind}/purchases`,
      {
        method: "POST",
        body: JSON.stringify({ combinations, idempotency_key: idempotencyKey }),
      },
    ),
};
