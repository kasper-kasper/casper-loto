import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";

import App from "./App";
import { adminApi } from "./api";
import type { Dashboard, Lottery, NumberStatisticsReport, Player, ScheduleEntry, TicketAnalytics } from "./types";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error { status = 500; },
  adminApi: {
    login: vi.fn(), session: vi.fn(), logout: vi.fn(), dashboard: vi.fn(),
    players: vi.fn(), lotteries: vi.fn(), schedule: vi.fn(), draws: vi.fn(), draw: vi.fn(),
    transactions: vi.fn(), statistics: vi.fn(), ticketAnalytics: vi.fn(), activity: vi.fn(), audit: vi.fn(),
    notifications: vi.fn(), releaseNotes: vi.fn(),
    setBalance: vi.fn(), configureLottery: vi.fn(), setReserve: vi.fn(), setJackpot: vi.fn(),
    setAutoPlay: vi.fn(),
  },
}));

const session = { username: "owner", csrf_token: "csrf", expires_at: "2026-08-16T00:00:00Z" };
const lottery: Lottery = { id: "lottery", code: "weekly", name: "Weekly 5/20", kind: "WEEKLY", ticket_price: 100, base_jackpot: 10_000, current_jackpot: 12_000, distribution_fund: 500, reserve: 100_000, schedule: { weekday: "sunday" }, sales_cutoff_minutes: 5, max_tickets_per_purchase: 1000, max_tickets_per_user_per_draw: 5000, is_active: true, next_draw_number: 8, next_draw_at: "2026-08-16T17:00:00Z" };
const dashboard: Dashboard = { version: "0.8.0", uptime_seconds: 120, database_healthy: true, bot_configured: true, scheduler_enabled: true, counts: { users: 1, tickets: 6, completed_draws: 3, pending_draws: 1 }, lotteries: [lottery], recent_draws: [], recent_transactions: [], operations: { scheduler: { last_started_at: null, last_succeeded_at: null, last_failed_at: null, last_error: null, settled_count: 0, prepared_count: 0 }, stuck_draw_count: 0, notifications: {}, next_draws: [] }, jackpots: { kasper_fund_balance: 1_000_000_000_000_000, total_wins: 0, total_paid: 0, largest_win: 0, lotteries: [{ code: "weekly", name: "Weekly 5/20", win_count: 0, total_paid: 0, last_win_at: null }], history: [] } };
const player: Player = { id: "player", display_name: "Test Player", username: "player", telegram_id: 123, is_active: true, balance: 5_000, ticket_count: 6, spent: 600, won: 250, net: -350, telegram_notifications_enabled: false, auto_play_enabled: false, auto_play_tickets_per_draw: 5, auto_play_last_succeeded_at: null, auto_play_last_error: null };
const analytics: TicketAnalytics = { overall: { lottery_id: null, lottery_name: "Все лотереи", is_active: null, total_tickets: 100, active_tickets: 10, settled_tickets: 90, winning_tickets: 21, participants: 8, winning_players: 5, total_sales: 10_000, total_payout: 2_500 }, lotteries: [{ lottery_id: "lottery", lottery_name: "Weekly 5/20", is_active: true, total_tickets: 100, active_tickets: 10, settled_tickets: 90, winning_tickets: 21, participants: 8, winning_players: 5, total_sales: 10_000, total_payout: 2_500 }] };
const numberStatistics: NumberStatisticsReport = { lottery_id: "lottery", lottery_name: "Weekly 5/20", period_start: "2026-08-31T21:00:00Z", window_size: 20, draw_count: 2, first_draw_at: "2026-09-01T09:00:00Z", last_draw_at: "2026-09-01T15:00:00Z", numbers: [{ number: 7, appearances: 2, draw_percentage: 100, last_appearance: "2026-09-01T15:00:00Z", draws_since_last: 0 }] };
const scheduleEntries: ScheduleEntry[] = [{ id: "scheduled-draw", lottery_id: "lottery", lottery_name: "Weekly 5/20", public_number: 8, scheduled_at: "2026-09-02T17:00:00Z" }];

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState({}, "", "/");
  window.localStorage.clear();
  vi.mocked(adminApi.session).mockResolvedValue(session);
  vi.mocked(adminApi.login).mockResolvedValue(session);
  vi.mocked(adminApi.logout).mockResolvedValue();
  vi.mocked(adminApi.dashboard).mockResolvedValue(dashboard);
  vi.mocked(adminApi.players).mockResolvedValue([player]);
  vi.mocked(adminApi.lotteries).mockResolvedValue([lottery]);
  vi.mocked(adminApi.draws).mockResolvedValue([]);
  vi.mocked(adminApi.schedule).mockResolvedValue(scheduleEntries);
  vi.mocked(adminApi.transactions).mockResolvedValue([]);
  vi.mocked(adminApi.statistics).mockResolvedValue(numberStatistics);
  vi.mocked(adminApi.ticketAnalytics).mockResolvedValue(analytics);
  vi.mocked(adminApi.activity).mockResolvedValue([]);
  vi.mocked(adminApi.audit).mockResolvedValue([]);
  vi.mocked(adminApi.notifications).mockResolvedValue([]);
  vi.mocked(adminApi.releaseNotes).mockImplementation(async (kind) => [{
    version: "0.15.0", date: "2026-08-31", content: kind === "changelog" ? "Публичное изменение" : "Техническое изменение", sequence: kind === "devlog" ? 15 : null,
  }]);
  vi.mocked(adminApi.setBalance).mockResolvedValue({ amount: 9_000, already_processed: false });
  vi.mocked(adminApi.configureLottery).mockResolvedValue(lottery);
  vi.mocked(adminApi.setJackpot).mockResolvedValue({ amount: lottery.current_jackpot, already_processed: false });
  vi.mocked(adminApi.setReserve).mockResolvedValue({ amount: 100_000, already_processed: false });
  vi.mocked(adminApi.setAutoPlay).mockResolvedValue(player);
});

it("restores an authenticated session and renders Russian system truth", async () => {
  render(<App />);

  expect(await screen.findByText("Всего сорвано джекпотов")).toBeInTheDocument();
  expect(screen.getByText("12 000 CAS")).toBeInTheDocument();
  expect(screen.queryByText("v0.8.0 · работает 2 мин.")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Система/ }));
  expect(await screen.findByText("БАЗА ДАННЫХ РАБОТАЕТ")).toBeInTheDocument();
  expect(screen.getByText("v0.8.0 · работает 2 мин.")).toBeInTheDocument();
});

it("distinguishes one draw jackpot from the all-time lottery total", async () => {
  vi.mocked(adminApi.dashboard).mockResolvedValueOnce({
    ...dashboard,
    jackpots: {
      ...dashboard.jackpots,
      total_wins: 34,
      total_paid: 34_000_000,
      lotteries: [{ code: "shadow", name: "SHADOW", win_count: 34, total_paid: 34_000_000, last_win_at: "2026-09-04T16:15:00Z" }],
      history: [{ id: "event", lottery_code: "shadow", lottery_name: "SHADOW", draw_id: "draw", jackpot_amount: 1_019_980, winner_ticket_count: 1, winner_user_count: 1, base_jackpot_after: 1_000_000, occurred_at: "2026-09-04T16:15:00Z" }],
    },
  });
  render(<App />);

  expect(await screen.findByText("Выплачено за всё время")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Показать последние выигрыши/ }));
  expect(screen.getByText("Джекпот этого тиража")).toBeInTheDocument();
  expect(screen.getAllByText("1 019 980 CAS")).toHaveLength(2);
});

it("shows login and authenticates when no session exists", async () => {
  vi.mocked(adminApi.session).mockRejectedValueOnce(new Error("unauthorized"));
  render(<App />);

  fireEvent.change(await screen.findByLabelText("ЛОГИН АДМИНИСТРАТОРА"), { target: { value: "owner" } });
  fireEvent.change(screen.getByLabelText("ПАРОЛЬ"), { target: { value: "password" } });
  fireEvent.click(screen.getByRole("button", { name: "ВОЙТИ" }));

  await waitFor(() => expect(adminApi.login).toHaveBeenCalledWith("owner", "password"));
  expect(await screen.findByText("Всего сорвано джекпотов")).toBeInTheDocument();
});

it("adjusts a player balance only with a mandatory reason", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Игроки/ }));

  const save = await screen.findByRole("button", { name: "ИЗМЕНИТЬ ЧЕРЕЗ ЖУРНАЛ" });
  expect(save).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Новый баланс"), { target: { value: "9000" } });
  fireEvent.change(screen.getByLabelText("Обязательная причина"), { target: { value: "Тестовое начисление" } });
  fireEvent.click(save);

  await waitFor(() => expect(adminApi.setBalance).toHaveBeenCalledWith("player", 9000, "Тестовое начисление"));
});

it("groups administration into seven owner-oriented sections", async () => {
  render(<App />);
  await screen.findByText("Всего сорвано джекпотов");

  for (const label of ["Обзор", "Лотереи", "Расписание", "Тиражи", "Игроки", "Аналитика", "Система"]) {
    expect(screen.getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
  }
  fireEvent.click(screen.getByRole("button", { name: /Система/ }));
  expect(await screen.findByRole("tab", { name: "Журнал CAS" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Уведомления" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Аудит действий" })).toBeInTheDocument();
});

it("loads the daily schedule only after opening its section", async () => {
  render(<App />);
  await screen.findByText("Всего сорвано джекпотов");
  expect(adminApi.schedule).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: /Расписание/ }));

  expect(await screen.findByText("№0008")).toBeInTheDocument();
  expect(screen.getByText("20:00")).toBeInTheDocument();
  expect(screen.getByLabelText("Лотерея расписания")).toBeInTheDocument();
  expect(adminApi.schedule).toHaveBeenCalledOnce();
});

it("shows complete changelog and devlog in separate protected tabs", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Система/ }));
  fireEvent.click(await screen.findByRole("tab", { name: "Разработка" }));

  expect(await screen.findByText("Публичное изменение")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "DEVLOG" }));
  expect(screen.getByText("Техническое изменение")).toBeInTheDocument();
  expect(screen.getByText("DEV-0015 · релиз v0.15.0")).toBeInTheDocument();
  expect(adminApi.releaseNotes).toHaveBeenCalledWith("changelog");
  expect(adminApi.releaseNotes).toHaveBeenCalledWith("devlog");
});

it("keeps the selected section in the URL and restores it after refresh", async () => {
  const first = render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Игроки/ }));
  await screen.findByText("Test Player");
  expect(window.location.pathname).toBe("/players");

  first.unmount();
  render(<App />);
  expect(await screen.findByText("Test Player")).toBeInTheDocument();
});

it("shows lightweight ticket win analytics overall and by lottery", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Аналитика/ }));
  fireEvent.click(await screen.findByRole("tab", { name: "Билеты" }));

  expect(await screen.findByText("23,33% от рассчитанных")).toBeInTheDocument();
  expect(screen.getByText("Weekly 5/20")).toBeInTheDocument();
  expect(adminApi.ticketAnalytics).toHaveBeenCalledTimes(2);
});

it("filters number statistics by lottery and draw window without changing history", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Аналитика/ }));
  fireEvent.click(await screen.findByRole("tab", { name: "Числа" }));

  expect(await screen.findByText("Статистика начата заново с 1 сентября 2026 года. История тиражей и их номера не изменялись.")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Количество тиражей"), { target: { value: "50" } });
  await waitFor(() => expect(adminApi.statistics).toHaveBeenCalledWith("lottery", 50));
});

it("saves lottery price, base jackpot and limits with one action", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Лотереи/ }));

  fireEvent.change(await screen.findByLabelText("Цена билета, CAS"), { target: { value: "22222" } });
  fireEvent.change(screen.getByLabelText("Базовый джекпот после выигрыша, CAS"), { target: { value: "2811996" } });
  fireEvent.change(screen.getByLabelText("Обязательная причина для аудита"), { target: { value: "Настройки владельца" } });
  fireEvent.click(screen.getByRole("button", { name: "СОХРАНИТЬ НАСТРОЙКИ" }));

  await waitFor(() => expect(adminApi.configureLottery).toHaveBeenCalledWith("lottery", 22222, 2811996, 5, 1000, 5000, "Настройки владельца"));
  expect(adminApi.setReserve).not.toHaveBeenCalled();
  expect(await screen.findByText("Цена билета, базовый джекпот и лимиты сохранены.")).toBeInTheDocument();
});

it("adjusts the current jackpot through the ledger action", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Лотереи/ }));

  fireEvent.change(await screen.findByLabelText("Текущий джекпот, CAS"), { target: { value: "999999" } });
  fireEvent.change(screen.getByLabelText("Обязательная причина для аудита"), { target: { value: "Решение владельца" } });
  fireEvent.click(screen.getByRole("button", { name: "ИЗМЕНИТЬ ЧЕРЕЗ ЖУРНАЛ" }));

  await waitFor(() => expect(adminApi.setJackpot).toHaveBeenCalledWith("lottery", 999999, "Решение владельца"));
  expect(await screen.findByText("Текущий джекпот изменён через журнал CAS.")).toBeInTheDocument();
});


it("shows a lottery's last amount even when its event is outside the history window", async () => {
  vi.mocked(adminApi.dashboard).mockResolvedValue({ ...dashboard, jackpots: { ...dashboard.jackpots,
    total_wins: 90, total_paid: 99_000_000, largest_win: 88_000_000,
    lotteries: [{ lottery_id: "lottery", code: "weekly", name: "Weekly 5/20", win_count: 90, total_paid: 99_000_000, last_win_at: "2026-09-04T12:00:00Z", last_win_amount: 12_345, largest_win: 88_000_000, last_draw_number: 8, last_draw_id: "old-draw" }], history: [],
  } });
  render(<App />);
  expect(await screen.findByText("12 345 CAS")).toBeInTheDocument();
  expect(screen.getByText("Открыть тираж №0008 →")).toBeInTheDocument();
  expect(screen.getAllByText("99 000 000 CAS")).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", { name: /Аналитика/ }));
  expect(await screen.findByText("88 млн CAS")).toBeInTheDocument();
});

it("keeps expanded jackpot history when the owner refreshes data", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Показать последние выигрыши/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Обновить данные" }));
  await waitFor(() => expect(adminApi.dashboard).toHaveBeenCalledTimes(2));
  expect(screen.getByRole("button", { name: /Скрыть историю джекпотов/ })).toHaveAttribute("aria-expanded", "true");
});

it("restores an old development URL inside System", async () => {
  window.history.replaceState({}, "", "/development");
  render(<App />);
  expect(await screen.findByText("Публичное изменение")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Система" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Разработка" })).toHaveAttribute("aria-selected", "true");
});

it("reports a failed owner balance change without pretending it succeeded", async () => {
  vi.mocked(adminApi.setBalance).mockRejectedValueOnce(new Error("Не удалось сохранить баланс"));
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Игроки/ }));
  fireEvent.change(await screen.findByLabelText("Обязательная причина"), { target: { value: "Уточнение" } });
  fireEvent.click(screen.getByRole("button", { name: "ИЗМЕНИТЬ ЧЕРЕЗ ЖУРНАЛ" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось сохранить баланс");
});

it.each([null, 200])("uses the recorded jackpot event in draw details, amount=%s", async (amount) => {
  const event = { id: "event", lottery_code: "weekly", lottery_name: "Weekly 5/20", draw_id: "draw", draw_number: 7, jackpot_amount: 200, winner_ticket_count: 1, winner_user_count: 1, base_jackpot_after: 500, occurred_at: "2026-09-04T12:00:00Z" };
  vi.mocked(adminApi.dashboard).mockResolvedValue({ ...dashboard, jackpots: { ...dashboard.jackpots, last_win: event } });
  vi.mocked(adminApi.draw).mockResolvedValue({ draw: {
    id: "draw", lottery_id: "lottery", lottery_code: "weekly", lottery_name: "Weekly 5/20", public_number: 7, status: "COMPLETED", scheduled_at: event.occurred_at, sales_close_at: event.occurred_at, executed_at: event.occurred_at, winning_numbers: [1,2,3,4,5], ticket_count: 1, total_sales: 100, total_payout: 200, jackpot_opening: 200, jackpot_closing: amount ? 500 : 100, distribution_opening: 0, distribution_closing: 0, reserve_used: 0, kasper_fund_used: 0, correlation_id: "internal-correlation", jackpot_amount: amount,
  }, tickets: [] });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Тираж №0007 →" }));
  const dialog = await screen.findByRole("dialog");
  if (amount) expect(within(dialog).getByText("ДЖЕКПОТ ЭТОГО ТИРАЖА СОРВАН")).toBeInTheDocument();
  else expect(within(dialog).queryByText("ДЖЕКПОТ ЭТОГО ТИРАЖА СОРВАН")).not.toBeInTheDocument();
  expect(within(dialog).queryByText("internal-correlation")).not.toBeInTheDocument();
  fireEvent.keyDown(window, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
