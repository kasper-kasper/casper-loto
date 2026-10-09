import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
    highlights: vi.fn(),
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
    {
      code: "pulse",
      name: "PULSE",
      kind: "DAILY",
      numbers_to_pick: 3,
      max_number: 15,
      primary_numbers_to_pick: 2,
      primary_max_number: 10,
      secondary_numbers_to_pick: 1,
      secondary_max_number: 5,
      secondary_storage_offset: 10,
      ticket_price: 1_234,
      jackpot: 1_234_567,
      draw_number: 1,
      scheduled_at: "2026-08-15T12:06:00Z",
      sales_close_at: "2026-08-15T12:05:00Z",
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
  total_ticket_count: 18_432,
  total_winning_ticket_count: 1_208,
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
  vi.stubGlobal("scrollTo", vi.fn());
  vi.mocked(miniAppApi.highlights).mockResolvedValue({ last_jackpot: null });
  vi.mocked(miniAppApi.devSession).mockResolvedValue({ mode: "local-development" });
  vi.mocked(miniAppApi.devRefill).mockResolvedValue({ balance: 105_000 });
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(dashboard);
  vi.mocked(miniAppApi.account).mockResolvedValue(account);
  vi.mocked(miniAppApi.notifications).mockResolvedValue([]);
  vi.mocked(miniAppApi.notificationPreferences).mockResolvedValue(account.notification_preferences);
  vi.mocked(miniAppApi.markNotificationsRead).mockResolvedValue();
  vi.mocked(miniAppApi.live).mockResolvedValue({ server_time: new Date().toISOString(), latest_completed: null, next_scheduled: null, recent_completed: [] });
  vi.mocked(miniAppApi.liveStream).mockImplementation(async () => undefined);
  vi.mocked(miniAppApi.tickets).mockResolvedValue({ tickets: [], total: 0, has_more: false });
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

async function openWeeklyFromStorefront(): Promise<void> {
  fireEvent.click(await screen.findByRole("button", { name: "Лотереи" }));
  fireEvent.click(await screen.findByRole("button", { name: "Открыть Weekly 5/20" }));
}

it("requires a signed Telegram launch", () => {
  render(<App initData="" />);

  expect(screen.getByText("Откройте Casper Loto в Telegram")).toBeInTheDocument();
});

it("opens a loopback development session outside Telegram", async () => {
  render(<App initData="" localDev />);

  expect(await screen.findByRole("button", { name: "+ TEST CAS" })).toBeInTheDocument();
  expect(miniAppApi.devSession).toHaveBeenCalledOnce();
  expect(miniAppApi.dashboard).toHaveBeenCalledWith("");
});

it("renders server-authoritative balance and lottery states", async () => {
  const { container } = render(<App initData="signed" />);

  expect(await screen.findByLabelText("5 000 CAS")).toHaveTextContent("5 000C");
  expect(screen.getByLabelText("Casper Loto")).toBeInTheDocument();
  expect(container.querySelector(".brand-logo-horizontal")).toHaveAttribute("src", "/brand/logo-horizontal-432-v1.png");
  expect(within(container.querySelector(".mobile-dock") as HTMLElement).getAllByRole("button").map(b => b.textContent)).toEqual(["Сегодня", "Лотереи", "Casper Fast", "Моё"]);
  fireEvent.click(screen.getByRole("button", { name: "Лотереи" }));
  expect(await screen.findByRole("button", { name: "Открыть Weekly 5/20" }, { timeout: 5000 })).toBeEnabled();
});

it("shows the dashboard while the account request is still pending", async () => {
  vi.mocked(miniAppApi.account).mockImplementation(() => new Promise(() => undefined));
  const { container } = render(<App initData="signed" />);
  expect(container.querySelector(".skeleton-shell .brand-logo-horizontal")).toHaveAttribute("src", "/brand/logo-horizontal-432-v1.png");
  expect(await screen.findByRole("heading", { name: "Сегодня" })).toBeInTheDocument();
  expect(screen.getByLabelText("Casper Loto")).toBeInTheDocument();
  expect(miniAppApi.account).toHaveBeenCalledOnce();
});

it("shows the personal home dashboard while keeping Fast separate", async () => {
  const template = dashboard.lotteries[0];
  const showcaseDashboard: Dashboard = {
    ...dashboard,
    lotteries: [
      template,
      { ...template, code: "bingo", name: "Casper Bingo", jackpot: 10_000_000_000, numbers_to_pick: 12, max_number: 60 },
      dashboard.lotteries[1],
      { ...template, code: "pss", name: "ПСС-Лото", scheduled_at: "2026-08-15T16:00:00Z" },
      { ...template, code: "khan", name: "ХАН-Лото", scheduled_at: "2026-08-15T17:00:00Z" },
      { ...template, code: "grob", name: "Casper Halloween", scheduled_at: "2026-08-15T18:00:00Z" },
      { ...template, code: "september", name: "3 сентября", scheduled_at: "2026-08-15T19:00:00Z" },
      ...dashboard.lotteries.slice(2),
    ],
  };
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(showcaseDashboard);
  render(<App initData="signed" />);

  await screen.findByRole("button", { name: "Лотереи" });
  expect(screen.getByRole("heading", { name: "Дальше по расписанию" })).toBeInTheDocument();
  expect(screen.getByText("Ближайший с вашим билетом")).toBeInTheDocument();
  expect(screen.getByText("12 билетов ждут тиража")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Статистика Casper"));
  expect(screen.getAllByText("18 432")).toHaveLength(1);
  expect(screen.getAllByText("1 208")).toHaveLength(1);
  expect(screen.queryByLabelText("Витрина лотерей")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Лотереи" }));
  const storefront = await screen.findByLabelText("Витрина лотерей");
  expect(within(storefront).getAllByRole("heading").map((heading) => heading.textContent)).toEqual([
    "Casper LIVE", "Casper Aurora", "ХАН-Лото", "Casper Bingo", "Weekly 5/20", "ПЛЛ-лото", "ПСС-Лото", "3 сентября", "Casper Halloween", "FLASH", "PULSE", "SHADOW",
  ]);
  expect(screen.queryByText("Каспер выплатил игрокам за месяц")).not.toBeInTheDocument();
  expect(screen.queryByText("Случайная комбинация")).not.toBeInTheDocument();
});

it("shows unread notifications as a red dot without exposing the count", async () => {
  vi.mocked(miniAppApi.account).mockResolvedValue({ ...account, unread_notification_count: 7 });
  const { container } = render(<App initData="signed" />);

  expect(await screen.findByRole("button", { name: "Моё: есть непрочитанные уведомления" })).toBeInTheDocument();
  expect(container.querySelector(".mobile-dock .dock-notification")?.textContent).toBe("");
});

it("renders Casper Halloween and its three-of-twenty-eight picker", async () => {
  const grobDashboard: Dashboard = {
    ...dashboard,
    lotteries: [{
      code: "grob",
      name: "Casper Halloween",
      kind: "DAILY",
      numbers_to_pick: 3,
      max_number: 28,
      fixed_payouts: { "2": 28_000 },
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

  expect(await screen.findByRole("heading", { name: "Casper Halloween" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Открыть лотерею" }));

  await waitFor(() => expect(container.querySelector(".ticket-number-grid")).not.toBeNull());
  const grid = container.querySelector(".ticket-number-grid");
  expect(grid).not.toBeNull();
  expect(within(grid as HTMLElement).getAllByRole("button")).toHaveLength(28);
  expect(screen.getByRole("heading", { name: "Выберите 3 числа из 28" })).toBeInTheDocument();
});

it("renders the classic 6 of 36 identity and complete number field", async () => {
  const classicDashboard: Dashboard = {
    ...dashboard,
    lotteries: [{
      ...dashboard.lotteries[0],
      code: "khan",
      name: "6 из 36",
      kind: "DAILY",
      numbers_to_pick: 6,
      max_number: 36,
      ticket_price: 48_000,
      jackpot: 33_456_000,
    }],
  };
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(classicDashboard);
  const { container } = render(<App initData="signed" />);

  expect(await screen.findByRole("heading", { name: "6 из 36" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Моя лотерея" }));
  await waitFor(() => expect(container.querySelector(".ticket-number-grid")).not.toBeNull());
  expect(within(container.querySelector(".ticket-number-grid") as HTMLElement).getAllByRole("button")).toHaveLength(36);
  expect(screen.queryByText("Выберите 6 чисел")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Ваш билет" })).toBeInTheDocument();
});

it("refreshes a stale sales state before opening the number picker", async () => {
  const stale: Dashboard = {
    ...dashboard,
    lotteries: dashboard.lotteries.map((lottery) => lottery.code === "weekly" ? { ...lottery, purchase_available: false, sales_open: false } : lottery),
  };
  vi.mocked(miniAppApi.dashboard).mockResolvedValueOnce(stale).mockResolvedValue(dashboard);
  render(<App initData="signed" />);

  await openWeeklyFromStorefront();

  expect(await screen.findByRole("button", { name: "Случайные числа" })).toBeInTheDocument();
  expect(miniAppApi.dashboard).toHaveBeenCalledTimes(2);
});

it("opens the selected lottery live room", async () => {
  render(<App initData="signed" />);
  await openWeeklyFromStorefront();
  fireEvent.click(await screen.findByRole("button", { name: "Эфир и результаты" }));

  expect(await screen.findByText("Расписание готовится")).toBeInTheDocument();
  expect(miniAppApi.live).toHaveBeenCalledWith("signed", "standard", "weekly");
});

it("allows a previously saved cart to be completed atomically", async () => {
  sessionStorage.setItem("k-loto:cart:v2", JSON.stringify({ expiresAt: Number.MAX_SAFE_INTEGER, tickets: [{ id: "saved-ticket", lotteryCode: "weekly", lotteryName: "Weekly 5/20", price: 100, numbers: [1, 2, 3, 4, 5], drawCount: 1 }] }));
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: "Корзина: 1 комбинация" }));

  expect(screen.getByText("1 комбинация")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Добавить комбинацию" }));
  expect(screen.getByLabelText("Витрина лотерей")).toBeInTheDocument();
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
  expect(await screen.findByText("1 билет куплен · списано 100 CAS")).toBeInTheDocument();
  expect(screen.queryByRole("dialog", { name: /покупк/i })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Билеты уже в игре" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Купить ещё" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Мои билеты" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "На главную" }));
  expect(await screen.findByRole("heading", { name: "Сегодня" })).toBeInTheDocument();
  expect(document.querySelector(".ticket-number-grid")).toBeNull();
}, 10_000);

it("keeps a confirmed purchase successful when the following refresh fails", async () => {
  render(<App initData="signed" />);
  await openWeeklyFromStorefront();
  await waitFor(() => expect(document.querySelector(".ticket-number-grid")).not.toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "Случайные числа" }));
  expect(screen.getByRole("button", { name: "Купить билет" })).toBeEnabled();
  vi.mocked(miniAppApi.dashboard).mockRejectedValue(new Error("refresh unavailable"));
  vi.mocked(miniAppApi.account).mockRejectedValue(new Error("refresh unavailable"));
  fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));

  expect(await screen.findByLabelText("4 900 CAS")).toBeInTheDocument();
  expect(screen.queryByText("Покупка не выполнена.")).not.toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("button", { name: "Купить билет" })).toBeDisabled());
});

it("keeps Casper Grand main and special number fields independent", async () => {
  const grandDashboard: Dashboard = {
    ...dashboard,
    lotteries: [{
      ...dashboard.lotteries[0],
      name: "Casper Grand",
      numbers_to_pick: 7,
      max_number: 40,
      primary_numbers_to_pick: 5,
      primary_max_number: 35,
      secondary_numbers_to_pick: 2,
      secondary_max_number: 5,
      secondary_storage_offset: 35,
    }],
  };
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(grandDashboard);
  render(<App initData="signed" />);

  fireEvent.click(await screen.findByRole("button", { name: "Моя лотерея" }));
  const main = (await screen.findByText("Основные числа")).closest("section") as HTMLElement;
  const special = screen.getByText("Золотые шары").closest("section") as HTMLElement;
  for (const number of [1, 2, 3, 4, 5]) fireEvent.click(within(main).getByRole("button", { name: `Основные числа ${number}` }));
  for (const number of [1, 2]) fireEvent.click(within(special).getByRole("button", { name: `Золотые шары ${number}` }));
  fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));

  await waitFor(() => expect(miniAppApi.purchase).toHaveBeenCalledWith(
    "signed", "weekly", [[1, 2, 3, 4, 5, 36, 37]],
    "00000000-0000-4000-8000-000000000001", 1,
  ));
  expect(screen.getByRole("heading", { name: "Casper Grand" })).toBeInTheDocument();
  await waitFor(() => {
    const refreshedMain = screen.getByText("Основные числа").closest("section") as HTMLElement;
    expect(within(refreshedMain).queryAllByRole("button", { pressed: true })).toHaveLength(0);
  });
  await waitFor(() => expect(screen.getByRole("button", { name: "Купить билет" })).toBeDisabled());
});

it("buys a random batch from a long lottery without opening the cart", async () => {
  render(<App initData="signed" />);
  await openWeeklyFromStorefront();
  fireEvent.click(await screen.findByRole("button", { name: "Купить 25 случайных билетов" }));

  await waitFor(() => expect(miniAppApi.purchase).toHaveBeenCalledOnce());
  expect(vi.mocked(miniAppApi.purchase).mock.calls[0][2]).toHaveLength(25);
  expect(screen.getByRole("heading", { name: "Weekly 5/20" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Билеты уже в игре" })).not.toBeInTheDocument();
});

it("offers an explicit prepaid five-draw purchase without enabling it by default", async () => {
  render(<App initData="signed" />);
  await openWeeklyFromStorefront();
  fireEvent.click(await screen.findByText("Повторы и избранное"));
  fireEvent.click(screen.getByRole("button", { name: "5 тиражей" }));
  const grid = document.querySelector(".ticket-number-grid") as HTMLElement;
  for (const number of [1, 2, 3, 4, 5]) fireEvent.click(within(grid).getByRole("button", { name: String(number) }));
  fireEvent.click(screen.getByRole("button", { name: "Купить на 5 тиражей" }));

  await waitFor(() => expect(miniAppApi.purchase).toHaveBeenCalledWith(
    "signed", "weekly", [[1, 2, 3, 4, 5]],
    "00000000-0000-4000-8000-000000000001", 5,
  ));
});

it("opens the separate Fast section without replacing the nearest main draw", async () => {
  render(<App initData="signed" />);
  expect(await screen.findByText(/Ближайший тираж/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Casper Fast" }));

  expect(await screen.findByRole("heading", { name: "Casper Fast" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "FLASH" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "SHADOW" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "PULSE" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Собрать сигнал/ })).toBeInTheDocument();
  expect(screen.queryByText("Отдельный мир Каспера")).not.toBeInTheDocument();
});

it("shows one simple notification control and no auto-play panel", async () => {
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));

  fireEvent.click(await screen.findByText("Настройки уведомлений"));
  expect(await screen.findByRole("button", { name: "Включить уведомления" })).toBeInTheDocument();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(screen.queryByText("Автоучастие")).not.toBeInTheDocument();
  expect(screen.queryByText(MINIAPP_TEXTS.account.subtitle)).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Моё" })).toBeInTheDocument();
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
  vi.mocked(miniAppApi.tickets).mockResolvedValue({ tickets: history, total: history.length, has_more: false });
  render(<App initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));
  fireEvent.click(await screen.findByRole("button", { name: /Активные билеты/ }));
  fireEvent.click(await screen.findByRole("button", { name: "История" }));

  expect(await screen.findByText("Без выигрыша")).toBeInTheDocument();
  const losingTicket = screen.getByText("Билет #0465").closest(".ticket-card");
  const winningTicket = screen.getByText("Билет #0466").closest(".ticket-card");
  expect(within(losingTicket as HTMLElement).getByText("0 CAS").closest(".ticket-result")).toHaveClass("loss");
  expect(within(winningTicket as HTMLElement).getByText("+300 CAS").closest(".ticket-result")).toHaveClass("win");
  fireEvent.click(winningTicket as HTMLElement);
  const fullTicket = await screen.findByRole("dialog", { name: "Билет 466" });
  expect(within(fullTicket).getByText("Выигрыш: 300 CAS")).toBeInTheDocument();
  expect(fullTicket.querySelectorAll(".paper-number-field i.matched")).toHaveLength(3);
  fireEvent.click(within(fullTicket).getByRole("button", { name: "Закрыть билет" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});


it("ignores backend version mismatch when the served frontend is current", async () => {
  vi.mocked(miniAppApi.dashboard).mockResolvedValue({ ...dashboard, app_version: "0.0.1" });
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ version: __APP_VERSION__ })));
  try {
    render(<App initData="test" />);
    await screen.findByRole("button", { name: "Моё" });
    expect(screen.queryByText("Доступно обновление")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/version.json?"), { cache: "no-store" });
  } finally { fetchMock.mockRestore(); }
});

it.each([
  ["pll", "2:22", 4, 15],
  ["pss", "ПСС-Лото", 4, 15],
  ["september", "3 сентября", 3, 33],
] as const)("keeps number selection usable for %s", async (code, name, pick, max) => {
  const ordinaryDashboard: Dashboard = {
    ...dashboard,
    lotteries: [{
      ...dashboard.lotteries[0],
      code,
      name,
      kind: "DAILY",
      numbers_to_pick: pick,
      max_number: max,
      ticket_price: 24_000,
    }],
  };
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(ordinaryDashboard);
  const { container } = render(<App initData="signed" />);

  fireEvent.click(await screen.findByRole("button", { name: /Открыть лотерею|Моя лотерея/ }));
  await waitFor(() => expect(container.querySelector(".ticket-number-grid")).not.toBeNull());
  const grid = container.querySelector(".ticket-number-grid") as HTMLElement;
  const numbers = within(grid).getAllByRole("button");
  expect(numbers).toHaveLength(max);
  for (let index = 0; index < pick; index += 1) fireEvent.click(numbers[index]);
  for (let index = 0; index < pick; index += 1) expect(numbers[index]).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Купить билет" })).toBeEnabled();
});

it("offers an update only for a different served frontend", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ version: "99.0.0" })));
  try {
    render(<App initData="test" />);
    expect(await screen.findByText("Доступно обновление")).toBeInTheDocument();
  } finally { fetchMock.mockRestore(); }
});

it("opens completed tickets directly from the account overview", async () => {
  render(<App initData="test" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));
  fireEvent.click(await screen.findByRole("button", { name: /История участия/ }));
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenCalledWith("test", "history", "", false));
});


it("keeps the Fast countdown steady when a stream snapshot has a different clock", async () => {
  vi.useFakeTimers({ toFake: ["Date", "performance", "setInterval", "clearInterval", "setTimeout", "clearTimeout"] });
  vi.setSystemTime(Date.parse(dashboard.server_time));
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ version: __APP_VERSION__ })));
  let push: ((feed: import("./types").LiveFeed) => void) | undefined;
  vi.mocked(miniAppApi.liveStream).mockImplementation(async (_init, callback) => { push = callback; });
  let unmount: (() => void) | undefined;
  try {
    let container: HTMLElement;
    await act(async () => { const app = render(<App initData="test" />); container = app.container; unmount = app.unmount; });
    fireEvent.click(screen.getByRole("button", { name: "Casper Fast" }));
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    const timer = () => container!.querySelector(".fast-shadow .fast-card-main strong")?.textContent;
    const before = timer();
    expect(before).toBe("00:09:59");
    await act(async () => {
      push?.({ server_time: "2026-08-15T12:00:09Z", latest_completed: null, next_scheduled: null, recent_completed: [] });
    });
    expect(timer()).toBe(before);
    await act(async () => { await vi.advanceTimersByTimeAsync(1_000); });
    expect(timer()).toBe("00:09:58");
  } finally { unmount?.(); vi.useRealTimers(); fetchMock.mockRestore(); }
});


it("does not apply the wins-only filter to active tickets", async () => {
  render(<App initData="test" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));
  fireEvent.click(await screen.findByRole("button", { name: /История участия/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Только выигрыши" }));
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenLastCalledWith("test", "history", "", true));
  fireEvent.click(screen.getByRole("button", { name: "Активные" }));
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenLastCalledWith("test", "active", "", false));
});

it("does not replace history with a late active-ticket response", async () => {
  let complete: ((page: { tickets: Ticket[]; total: number; has_more: boolean }) => void) | undefined;
  vi.mocked(miniAppApi.tickets).mockImplementation(async (_init, status) => status === "active"
    ? new Promise((resolve) => { complete = resolve; })
    : { tickets: [], total: 0, has_more: false });
  render(<App initData="test" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));
  fireEvent.click(await screen.findByRole("button", { name: /Активные билеты/ }));
  fireEvent.click(screen.getByRole("button", { name: "История" }));
  expect(await screen.findByText("История пока пуста")).toBeInTheDocument();
  await act(async () => { complete?.({ tickets: [], total: 7, has_more: false }); });
  expect(screen.getByText("0 билетов")).toBeInTheDocument();
});

it("keeps Fast tickets accessible through a separate server filter", async () => {
  render(<App initData="test" />);
  fireEvent.click(await screen.findByRole("button", { name: "Casper Fast" }));
  fireEvent.click(screen.getByRole("button", { name: /Билеты Casper Fast/ }));
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenLastCalledWith("test", "active", "scope:fast", false));
  fireEvent.change(screen.getByLabelText("Фильтр по лотерее"), { target: { value: "scope:standard" } });
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenLastCalledWith("test", "active", "scope:standard", false));
});

it("keeps Casper Dual as one 2+2 ticket with no favorites or five-draw repeat", async () => {
  const scheduled = new Date(Date.now() + 60 * 60_000).toISOString();
  const dualDashboard: Dashboard = {
    ...dashboard,
    server_time: new Date().toISOString(),
    balance: 1_000_000,
    lotteries: [{
      ...dashboard.lotteries[0],
      code: "dual", name: "Casper Dual", kind: "DAILY",
      ruleset_code: "casper_dual_2_12_2_12", numbers_to_pick: 4, max_number: 24,
      primary_numbers_to_pick: 2, primary_max_number: 12,
      secondary_numbers_to_pick: 2, secondary_max_number: 12,
      secondary_storage_offset: 12, ticket_price: 20_000,
      jackpot: 5_000_000, draw_number: 501, scheduled_at: scheduled,
      sales_close_at: new Date(Date.parse(scheduled) - 120_000).toISOString(),
      player_ticket_count: 0,
    }],
  };
  vi.mocked(miniAppApi.dashboard).mockResolvedValue(dualDashboard);
  render(<App initData="test" />);
  fireEvent.click(await screen.findByRole("button", { name: "Лотереи" }));
  fireEvent.click(screen.getByRole("button", { name: "Открыть Casper Dual" }));
  expect(screen.getByText("Раунд #0501")).toBeInTheDocument();
  expect(screen.getByLabelText("5 000 000 CAS")).toBeInTheDocument();
  expect(screen.queryByText("Один билет. Два раунда.")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "NIGHT 3" }));
  fireEvent.click(screen.getByRole("button", { name: "NIGHT 10" }));
  fireEvent.click(screen.getByRole("button", { name: "NIGHT 11" }));
  fireEvent.click(screen.getByRole("button", { name: "DAWN 5" }));
  fireEvent.click(screen.getByRole("button", { name: "DAWN 11" }));
  fireEvent.click(screen.getByRole("button", { name: "DAWN 12" }));
  expect(screen.getByRole("button", { name: "NIGHT 11" })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("button", { name: "DAWN 12" })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("button", { name: "NIGHT 3" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "DAWN 5" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getAllByText("2 / 2")).toHaveLength(2);
  expect(screen.getByRole("button", { name: "Купить билет" })).toBeEnabled();
  expect(screen.queryByText("Избранные комбинации")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "5 тиражей" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Купить 25 случайных билетов" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Купить билет" }));
  await waitFor(() => expect(miniAppApi.purchase).toHaveBeenCalledWith(
    "test", "dual", [[3, 10, 17, 23]], expect.any(String), 1,
  ));
});


it("account hub sends the empty state to the catalog", async () => {
  vi.mocked(miniAppApi.dashboard).mockResolvedValue({ ...dashboard, lotteries: dashboard.lotteries.map(lottery => ({ ...lottery, player_ticket_count: 0 })) });
  render(<App initData="test" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));
  fireEvent.click(await screen.findByRole("button", { name: /Выбрать игру/ }));
  expect(await screen.findByLabelText("Витрина лотерей")).toBeInTheDocument();
  expect(window.scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: "instant" });
  expect(miniAppApi.purchase).not.toHaveBeenCalled();
});

it("account hub clears a stale Fast filter when opening all active tickets", async () => {
  render(<App initData="test" />);
  fireEvent.click(await screen.findByRole("button", { name: "Casper Fast" }));
  fireEvent.click(screen.getByRole("button", { name: /Билеты Casper Fast/ }));
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenLastCalledWith("test", "active", "scope:fast", false));
  fireEvent.click(screen.getByRole("button", { name: "Обзор" }));
  fireEvent.click(await screen.findByRole("button", { name: /Активные билеты/ }));
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenLastCalledWith("test", "active", "", false));
});

it("returns to the personal overview when reselecting My in the dock", async () => {
  render(<App initData="test" />);
  const dock = await screen.findByRole("navigation", { name: "Основная навигация" });
  fireEvent.click(within(dock).getByRole("button", { name: "Моё" }));
  expect(within(dock).getByRole("button", { name: "Моё" })).toHaveAttribute("aria-current", "page");
  fireEvent.click(await screen.findByRole("button", { name: /История участия/ }));
  expect(await screen.findByRole("heading", { name: "Мои билеты" })).toBeInTheDocument();
  fireEvent.click(within(dock).getByRole("button", { name: "Моё" }));
  expect(await screen.findByRole("heading", { name: "Моё" })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Мои билеты" })).not.toBeInTheDocument();
  expect(window.scrollTo).toHaveBeenLastCalledWith({ top: 0, behavior: "instant" });
  expect(miniAppApi.purchase).not.toHaveBeenCalled();
});

it("opens active regular tickets from home after previously viewing winning history", async () => {
  render(<App initData="test" />);
  fireEvent.click(await screen.findByRole("button", { name: "Моё" }));
  fireEvent.click(await screen.findByRole("button", { name: /История участия/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Только выигрыши" }));
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenLastCalledWith("test", "history", "", true));
  fireEvent.click(screen.getByRole("button", { name: "Сегодня" }));
  fireEvent.click(await screen.findByRole("button", { name: /Мои билеты/ }));
  await waitFor(() => expect(miniAppApi.tickets).toHaveBeenLastCalledWith("test", "active", "scope:standard", false));
  expect(miniAppApi.purchase).not.toHaveBeenCalled();
});


it("keeps festive selection on return and opens Fast directly from the unified catalog", async () => {
  vi.mocked(miniAppApi.dashboard).mockResolvedValue({ ...dashboard, lotteries: [...dashboard.lotteries, { ...dashboard.lotteries[0], code: "grob", name: "ГРОБ" }] });
  render(<App initData="signed" />);
  await screen.findByRole("heading", { name: "Сегодня" });
  fireEvent.click(screen.getByRole("button", { name: "Лотереи" }));
  fireEvent.click(await screen.findByRole("button", { name: "Праздничные" }));
  fireEvent.click(screen.getByRole("button", { name: "Открыть ГРОБ" }));
  fireEvent.click(await screen.findByRole("button", { name: "Вернуться к лотереям" }));
  expect(await screen.findByRole("button", { name: "Праздничные" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getAllByRole("button", { name: /^Открыть / })).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Тиражные" }));
  fireEvent.click(screen.getByRole("button", { name: "Открыть FLASH" }));
  const close = await screen.findByRole("button", { name: /Вернуться|Закрыть|Назад/ });
  fireEvent.click(close);
  expect(await screen.findByRole("button", { name: "Тиражные" })).toHaveAttribute("aria-pressed", "true");
});
