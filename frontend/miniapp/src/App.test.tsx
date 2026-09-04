import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";

import App from "./App";
import { miniAppApi } from "./api";
import { MINIAPP_TEXTS } from "./content";
import type { Account, Dashboard, Ticket } from "./types";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error {},
  miniAppApi: {
    devSession: vi.fn(),
    devRefill: vi.fn(),
    dashboard: vi.fn(),
    account: vi.fn(),
    notifications: vi.fn(),
    notificationPreferences: vi.fn(),
    testNotification: vi.fn(),
    markNotificationsRead: vi.fn(),
    live: vi.fn(),
    liveStream: vi.fn(),
    tickets: vi.fn(),
    purchase: vi.fn(),
    favorites: vi.fn(),
    saveFavorite: vi.fn(),
    deleteFavorite: vi.fn(),
  },
}));

const dashboard: Dashboard = {
  server_time: "2026-08-15T12:00:00Z",
  balance: 5_000,
  active_ticket_count: 0,
  lotteries: [
    {
      code: "weekly",
      name: "Weekly 5/20",
      kind: "WEEKLY",
      numbers_to_pick: 5,
      max_number: 20,
      ticket_price: 100,
      jackpot: 10_000,
      draw_number: 7,
      scheduled_at: "2026-08-16T17:00:00Z",
      sales_close_at: "2026-08-16T16:55:00Z",
      sales_open: true,
      purchase_available: true,
      player_ticket_count: 2,
      sales_status: "OPEN",
      max_tickets_per_purchase: 1000,
      max_tickets_per_user_per_draw: 5000,
    },
    {
      code: "pll",
      name: "ПЛЛ-лото",
      kind: "DAILY",
      numbers_to_pick: 4,
      max_number: 15,
      ticket_price: null,
      jackpot: 0,
      draw_number: 12,
      scheduled_at: "2026-08-15T15:00:00Z",
      sales_close_at: "2026-08-15T15:00:00Z",
      sales_open: false,
      purchase_available: false,
      player_ticket_count: 0,
      sales_status: "CLOSED",
      max_tickets_per_purchase: 1000,
      max_tickets_per_user_per_draw: 5000,
    },
    {
      code: "flash",
      name: "FLASH",
      kind: "DAILY",
      numbers_to_pick: 3,
      max_number: 15,
      ticket_price: 888,
      jackpot: 888_888,
      draw_number: 1,
      scheduled_at: "2026-08-15T12:20:00Z",
      sales_close_at: "2026-08-15T12:19:00Z",
      sales_open: true,
      purchase_available: true,
      player_ticket_count: 0,
      sales_status: "OPEN",
      max_tickets_per_purchase: 100,
      max_tickets_per_user_per_draw: 500,
    },
    {
      code: "shadow",
      name: "SHADOW",
      kind: "DAILY",
      numbers_to_pick: 3,
      max_number: 15,
      ticket_price: 888,
      jackpot: 888_888,
      draw_number: 1,
      scheduled_at: "2026-08-15T12:10:00Z",
      sales_close_at: "2026-08-15T12:09:00Z",
      sales_open: true,
      purchase_available: true,
      player_ticket_count: 0,
      sales_status: "OPEN",
      max_tickets_per_purchase: 100,
      max_tickets_per_user_per_draw: 500,
    },
  ],
  recent_results: [],
  monthly_total_payout: 0,
};
const account: Account = {
  display_name: "Test Player",
  balance: 5_000,
  ticket_count: 0,
  active_ticket_count: 0,
  winning_ticket_count: 0,
  total_spent: 0,
  total_won: 0,
  best_win: 0,
  unread_notification_count: 0,
  notification_preferences: {
    telegram_enabled: false,
    draw_results_enabled: true,
    inactivity_reminders_enabled: true,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(miniAppApi.devSession).mockResolvedValue({ mode: "local-development" });
  vi.mocked(miniAppApi.devRefill).mockResolvedValue({ balance: 105_000 });
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(dashboard);
  vi.mocked(miniAppApi.account).mockResolvedValue(account);
  vi.mocked(miniAppApi.notifications).mockResolvedValue([]);
  vi.mocked(miniAppApi.notificationPreferences).mockResolvedValue(account.notification_preferences);
  vi.mocked(miniAppApi.markNotificationsRead).mockResolvedValue();
  vi.mocked(miniAppApi.live).mockResolvedValue({ server_time: new Date().toISOString(), latest_completed: null, next_scheduled: null, recent_completed: [] });
  vi.mocked(miniAppApi.liveStream).mockImplementation(async () => undefined);
  vi.mocked(miniAppApi.tickets).mockResolvedValue([]);
  vi.mocked(miniAppApi.favorites).mockResolvedValue([]);
  vi.mocked(miniAppApi.purchase).mockResolvedValue({
    operation_id: "operation",
    draw_id: "draw",
    draw_ids: ["draw"],
    draw_count: 1,
    ticket_ids: ["ticket"],
    total_cost: 100,
    balance_after: 4_900,
    already_processed: false,
  });
  vi.stubGlobal("crypto", {
    ...crypto,
    randomUUID: vi.fn(() => "00000000-0000-4000-8000-000000000001"),
    getRandomValues: crypto.getRandomValues.bind(crypto),
  });
});

afterEach(() => vi.unstubAllGlobals());

async function selectWeekly(): Promise<void> {
  fireEvent.click(await screen.findByRole("button", { name: /^Weekly 5\/20/ }));
}

it("requires a signed Telegram launch", () => {
  render(<App initData="" />);

  expect(screen.getByText("Откройте K-Loto в Telegram")).toBeInTheDocument();
});

it("opens a loopback development session outside Telegram", async () => {
  render(<App initData="" localDev />);

  expect(await screen.findByRole("button", { name: "+ TEST CAS" })).toBeInTheDocument();
  expect(miniAppApi.devSession).toHaveBeenCalledOnce();
  expect(miniAppApi.dashboard).toHaveBeenCalledWith("");
});

it("renders server-authoritative balance and lottery states", async () => {
  const { container } = render(<App initData="signed" />);

  expect(await screen.findByText("5 000 CAS")).toBeInTheDocument();
  expect(screen.getByLabelText("Каспер")).toBeInTheDocument();
  expect(container.querySelector(".wordmark")?.textContent).toBe("Каспер");
  await selectWeekly();
  expect(screen.getAllByText("10 000 CAS").length).toBeGreaterThan(0);
  expect(screen.getByRole("button", { name: /Выбрать числа.*100 CAS/ })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: /^ПЛЛ/ }));
  expect(screen.getByRole("button", { name: /Проверить продажи.*—/ })).toBeDisabled();
});

it("renders the GROB identity and its three-of-sixteen picker", async () => {
  const grobDashboard: Dashboard = {
    ...dashboard,
    lotteries: [{
      code: "grob",
      name: "ГРОБ",
      kind: "DAILY",
      numbers_to_pick: 3,
      max_number: 16,
      ticket_price: 6_666,
      jackpot: 6_666_666,
      draw_number: 1,
      scheduled_at: "2026-09-02T03:06:00Z",
      sales_close_at: "2026-09-02T03:04:00Z",
      sales_open: true,
      purchase_available: true,
      player_ticket_count: 0,
      sales_status: "OPEN",
      max_tickets_per_purchase: 1_000,
      max_tickets_per_user_per_draw: 5_000,
    }],
  };
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(grobDashboard);
  const { container } = render(<App initData="signed" />);

  expect(await screen.findByText("RIP 0001")).toBeInTheDocument();
  expect(screen.getByText(MINIAPP_TEXTS.grob.moodline)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Выбрать числа/ }));

  await waitFor(() => expect(container.querySelector(".number-grid")).not.toBeNull());
  const grid = container.querySelector(".number-grid");
  expect(grid).not.toBeNull();
  expect(within(grid as HTMLElement).getAllByRole("button")).toHaveLength(16);
  expect(screen.getByText("Поле захоронений")).toBeInTheDocument();
});

it("refreshes a stale sales state before opening the number picker", async () => {
  const stale: Dashboard = {
    ...dashboard,
    lotteries: dashboard.lotteries.map((lottery) => lottery.code === "weekly" ? { ...lottery, purchase_available: false, sales_open: false } : lottery),
  };
  vi.mocked(miniAppApi.dashboard).mockResolvedValueOnce(stale).mockResolvedValue(dashboard);
  render(<App initData="signed" />);

  await selectWeekly();
  fireEvent.click(await screen.findByRole("button", { name: /Проверить продажи.*100 CAS/ }));

  expect(await screen.findByRole("button", { name: "Случайные числа" })).toBeInTheDocument();
  expect(miniAppApi.dashboard).toHaveBeenCalledTimes(2);
});

it("opens the permanent live tab and requests the server clock", async () => {
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: "Эфир" }));

  expect(await screen.findByText("Расписание готовится")).toBeInTheDocument();
  expect(miniAppApi.live).toHaveBeenCalledWith("signed");
});

it("selects five numbers, adds a ticket and buys the cart atomically", async () => {
  render(<App initData="signed" />);
  await selectWeekly();
  fireEvent.click(await screen.findByRole("button", { name: /Выбрать числа.*100 CAS/ }));

  await waitFor(() => expect(document.querySelector(".number-grid")).not.toBeNull());
  const grid = document.querySelector(".number-grid");
  expect(grid).not.toBeNull();
  for (const number of [1, 2, 3, 4, 5]) {
    fireEvent.click(within(grid as HTMLElement).getByRole("button", { name: String(number) }));
  }
  fireEvent.click(screen.getByRole("button", { name: "В корзину" }));

  expect(screen.getByText("1 комбинация")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Добавить комбинацию" }));
  expect(screen.getByLabelText("Расписание лотерей")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Корзина: 1 комбинация" }));
  fireEvent.click(screen.getByRole("button", { name: "Купить 1 комб." }));

  await waitFor(() =>
    expect(miniAppApi.purchase).toHaveBeenCalledWith(
      "signed",
      "weekly",
      [[1, 2, 3, 4, 5]],
      "00000000-0000-4000-8000-000000000001",
      1,
    ),
  );
  expect(await screen.findByText("Билет уже участвует")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "На главную" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Мои билеты" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "На главную" }));
  expect(screen.getByLabelText("Расписание лотерей")).toBeInTheDocument();
  expect(document.querySelector(".number-grid")).toBeNull();
});

it("builds a large cart and sends one hundred tickets in one operation", async () => {
  render(<App initData="signed" />);
  await selectWeekly();
  fireEvent.click(await screen.findByRole("button", { name: /Выбрать числа.*100 CAS/ }));
  fireEvent.click(await screen.findByRole("button", { name: "+50" }));
  expect(await screen.findByText("50 комбинаций")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Добавить комбинацию" }));
  fireEvent.click(screen.getByRole("button", { name: /Выбрать числа.*100 CAS/ }));
  fireEvent.click(await screen.findByRole("button", { name: "+50" }));
  expect(await screen.findByText("100 комбинаций")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Купить 100 комб." }));

  await waitFor(() => expect(miniAppApi.purchase).toHaveBeenCalledOnce());
  expect(vi.mocked(miniAppApi.purchase).mock.calls[0][2]).toHaveLength(100);
});

it("offers an explicit prepaid five-draw purchase without enabling it by default", async () => {
  render(<App initData="signed" />);
  await selectWeekly();
  fireEvent.click(await screen.findByRole("button", { name: /Выбрать числа.*100 CAS/ }));
  fireEvent.click(await screen.findByRole("button", { name: "5 тиражей" }));
  const grid = document.querySelector(".number-grid") as HTMLElement;
  for (const number of [1, 2, 3, 4, 5]) fireEvent.click(within(grid).getByRole("button", { name: String(number) }));
  fireEvent.click(screen.getByRole("button", { name: "Купить на 5 тиражей" }));

  await waitFor(() => expect(miniAppApi.purchase).toHaveBeenCalledWith(
    "signed", "weekly", [[1, 2, 3, 4, 5]],
    "00000000-0000-4000-8000-000000000001", 5,
  ));
});

it("opens the separate Fast section without replacing the nearest main draw", async () => {
  render(<App initData="signed" />);
  expect(await screen.findByText("Ближайший тираж")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Fast" }));

  expect(await screen.findByRole("heading", { name: "Fast" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "FLASH" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "SHADOW" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Собрать сигнал/ })).toBeInTheDocument();
});

it("shows one simple notification control and no auto-play panel", async () => {
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));

  expect(await screen.findByRole("button", { name: "Включить уведомления" })).toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(screen.queryByText("Автоучастие")).not.toBeInTheDocument();
  expect(screen.getByText(MINIAPP_TEXTS.account.subtitle)).toBeInTheDocument();
});

it("renders losing history as neutral and winning history as rewarded", async () => {
  const history: Ticket[] = [
    {
      id: "loss", public_number: 465, lottery_code: "pll", lottery_name: "ПЛЛ-лото",
      draw_number: 12, scheduled_at: "2026-08-15T15:00:00Z", numbers: [1, 2, 3, 4],
      purchase_price: 100, source: "MANUAL", status: "SETTLED", matches: 0, prize_amount: 0,
      winning_numbers: [5, 6, 7, 8],
    },
    {
      id: "win", public_number: 466, lottery_code: "pll", lottery_name: "ПЛЛ-лото",
      draw_number: 12, scheduled_at: "2026-08-15T15:00:00Z", numbers: [5, 6, 7, 9],
      purchase_price: 100, source: "MANUAL", status: "SETTLED", matches: 3, prize_amount: 300,
      winning_numbers: [5, 6, 7, 8],
    },
  ];
  vi.mocked(miniAppApi.tickets).mockResolvedValue(history);
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));
  fireEvent.click(await screen.findByRole("button", { name: "Билеты" }));
  fireEvent.click(await screen.findByRole("button", { name: "История" }));

  expect(await screen.findByText("Без выигрыша")).toBeInTheDocument();
  const losingTicket = screen.getByText("Билет #0465").closest(".ticket-card");
  const winningTicket = screen.getByText("Билет #0466").closest(".ticket-card");
  expect(within(losingTicket as HTMLElement).getByText("0 CAS").closest(".ticket-result")).toHaveClass("loss");
  expect(within(winningTicket as HTMLElement).getByText("+300 CAS").closest(".ticket-result")).toHaveClass("win");
});
