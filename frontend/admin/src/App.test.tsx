import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";

import App from "./App";
import { adminApi } from "./api";
import type { Dashboard, Lottery, NumberStatisticsReport, Player, PlayerHistoryPage, ScheduleEntry, TicketAnalytics, Transaction } from "./types";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error { status = 500; },
  adminApi: {
    login: vi.fn(), session: vi.fn(), logout: vi.fn(), dashboard: vi.fn(), kasperLive: vi.fn(),
    players: vi.fn(), playerTicketHistory: vi.fn(), lotteries: vi.fn(), schedule: vi.fn(), draws: vi.fn(), draw: vi.fn(), jackpotEvents: vi.fn(),
    transactions: vi.fn(), playerTransactions: vi.fn(), statistics: vi.fn(), ticketAnalytics: vi.fn(), activity: vi.fn(), audit: vi.fn(),
    notifications: vi.fn(), releaseNotes: vi.fn(), interestingFacts: vi.fn(), setInterestingFactStatus: vi.fn(),
    setBalance: vi.fn(), configureLottery: vi.fn(), setReserve: vi.fn(), setJackpot: vi.fn(),
    setAutoPlay: vi.fn(),
  },
}));

const session = { username: "owner", csrf_token: "csrf", expires_at: "2026-08-16T00:00:00Z", miniapp_url: "https://play.example.test/" };
const lottery: Lottery = { id: "lottery", code: "weekly", name: "Weekly 5/20", kind: "WEEKLY", ticket_price: 100, base_jackpot: 10_000, current_jackpot: 12_000, distribution_fund: 500, reserve: 100_000, schedule: { weekday: "sunday" }, sales_cutoff_minutes: 5, max_tickets_per_purchase: 1000, max_tickets_per_user_per_draw: 5000, is_active: true, next_draw_number: 8, next_draw_at: "2026-08-16T17:00:00Z" };
const dashboard: Dashboard = { version: "0.8.0", uptime_seconds: 120, database_healthy: true, bot_configured: true, scheduler_enabled: true, counts: { users: 1, tickets: 6, completed_draws: 3, pending_draws: 1 }, lotteries: [lottery], recent_draws: [], recent_transactions: [], operations: { today: { completed_draws: 2, purchased_tickets: 4, sales: 400, winning_tickets: 1, payout: 250, net: 150, by_lottery: [{ lottery_id: "lottery", lottery_name: "Weekly 5/20", purchased_tickets: 4, sales: 400, winning_tickets: 1, payout: 250, net: 150 }] }, scheduler: { last_started_at: null, last_succeeded_at: null, last_failed_at: null, last_error: null, settled_count: 0, prepared_count: 0 }, stuck_draw_count: 0, notifications: {}, next_draws: [] }, jackpots: { kasper_fund_balance: 1_000_000_000_000_000, total_wins: 0, total_paid: 0, largest_win: 0, lotteries: [{ code: "weekly", name: "Weekly 5/20", win_count: 0, total_paid: 0, last_win_at: null }], history: [] } };
const player: Player = { id: "player", display_name: "Test Player", username: "player", telegram_id: 123, is_active: true, balance: 5_000, ticket_count: 6, active_ticket_count: 2, spent: 600, won: 250, net: -350, telegram_notifications_enabled: false, auto_play_enabled: false, auto_play_tickets_per_draw: 5, auto_play_last_attempted_at: null, auto_play_last_succeeded_at: null, auto_play_last_error: null };
const playerTransaction: Transaction = { id: "ledger-row", operation_id: "operation", type: "TICKET_PURCHASE", account_kind: "USER_BALANCE", amount: -100, balance_before: 5_100, balance_after: 5_000, user_id: "player", lottery_id: "lottery", draw_id: "draw", ticket_id: "ticket", created_at: "2026-09-20T12:00:00Z", details: {} };
const playerHistory: PlayerHistoryPage = { items: [{ id: "ticket-1", ticket_kind: "DRAW", purchased_at: "2026-09-20T12:00:00Z", lottery_id: "lottery", lottery_code: "weekly", lottery_name: "Weekly 5/20", draw_number: 7, public_number: 77, numbers: [1, 2, 3, 4, 5], purchase_price: 100, prize_amount: 250, status: "SETTLED", source: "MANUAL", matches: 5, winning_numbers: [1, 2, 3, 4, 5], bingo_result: null }], total: 1, offset: 0, limit: 100, lottery_stats: [{ lottery_id: "lottery", lottery_code: "weekly", lottery_name: "Weekly 5/20", ticket_count: 6, active_ticket_count: 2, winning_ticket_count: 1, spent: 600, won: 250 }] };
const analytics: TicketAnalytics = { overall: { lottery_id: null, lottery_name: "Все лотереи", is_active: null, total_tickets: 100, active_tickets: 10, settled_tickets: 90, winning_tickets: 21, participants: 8, winning_players: 5, total_sales: 10_000, total_payout: 2_500 }, lotteries: [{ lottery_id: "lottery", lottery_name: "Weekly 5/20", is_active: true, total_tickets: 100, active_tickets: 10, settled_tickets: 90, winning_tickets: 21, participants: 8, winning_players: 5, total_sales: 10_000, total_payout: 2_500 }] };
const numberStatistics: NumberStatisticsReport = { lottery_id: "lottery", lottery_name: "Weekly 5/20", period_start: "2026-08-31T21:00:00Z", window_size: 20, draw_count: 2, first_draw_at: "2026-09-01T09:00:00Z", last_draw_at: "2026-09-01T15:00:00Z", numbers: [{ number: 7, appearances: 2, draw_percentage: 100, last_appearance: "2026-09-01T15:00:00Z", draws_since_last: 0 }] };
const scheduleEntries: ScheduleEntry[] = [{ id: "scheduled-draw", lottery_id: "lottery", lottery_name: "Weekly 5/20", public_number: 8, scheduled_at: "2026-09-02T17:00:00Z" }];
const interestingFact = { id: "fact", generation_date: "2026-09-15", generated_at: "2026-09-15T01:10:00Z", lottery_id: "lottery", lottery_code: "weekly", lottery_name: "Weekly 5/20", fact_type: "jackpot_drought", title: "12 тиражей без джекпота", description: "Джекпот продолжает копиться.", numeric_values: { draws_without_jackpot: 12, jackpot: 3_000_000 }, score: 82, status: "new" as const };

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState({}, "", "/");
  window.localStorage.clear();
  vi.mocked(adminApi.session).mockResolvedValue(session);
  vi.mocked(adminApi.login).mockResolvedValue(session);
  vi.mocked(adminApi.logout).mockResolvedValue();
  vi.mocked(adminApi.dashboard).mockResolvedValue(dashboard);
  vi.mocked(adminApi.kasperLive).mockResolvedValue({ ticket_count: 100, winning_tickets: 30, losing_tickets: 70, result: 79_000 });
  vi.mocked(adminApi.players).mockResolvedValue([player]);
  vi.mocked(adminApi.playerTicketHistory).mockResolvedValue(playerHistory);
  vi.mocked(adminApi.lotteries).mockResolvedValue([lottery]);
  vi.mocked(adminApi.draws).mockResolvedValue([]);
  vi.mocked(adminApi.jackpotEvents).mockResolvedValue([]);
  vi.mocked(adminApi.schedule).mockResolvedValue(scheduleEntries);
  vi.mocked(adminApi.transactions).mockResolvedValue([]);
  vi.mocked(adminApi.playerTransactions).mockResolvedValue([]);
  vi.mocked(adminApi.statistics).mockResolvedValue(numberStatistics);
  vi.mocked(adminApi.ticketAnalytics).mockResolvedValue(analytics);
  vi.mocked(adminApi.activity).mockResolvedValue([]);
  vi.mocked(adminApi.audit).mockResolvedValue([]);
  vi.mocked(adminApi.notifications).mockResolvedValue([]);
  vi.mocked(adminApi.releaseNotes).mockImplementation(async (kind) => [{
    version: "0.15.0", date: "2026-08-31", content: kind === "changelog" ? "Публичное изменение" : "Техническое изменение", sequence: kind === "devlog" ? 15 : null,
  }]);
  vi.mocked(adminApi.interestingFacts).mockResolvedValue([interestingFact]);
  vi.mocked(adminApi.setInterestingFactStatus).mockImplementation(async (_id, status) => ({ ...interestingFact, status }));
  vi.mocked(adminApi.setBalance).mockResolvedValue({ amount: 9_000, already_processed: false });
  vi.mocked(adminApi.configureLottery).mockResolvedValue(lottery);
  vi.mocked(adminApi.setJackpot).mockResolvedValue({ amount: lottery.current_jackpot, already_processed: false });
  vi.mocked(adminApi.setReserve).mockResolvedValue({ amount: 100_000, already_processed: false });
  vi.mocked(adminApi.setAutoPlay).mockResolvedValue(player);
});

it("restores an authenticated session and renders Russian system truth", async () => {
  render(<App />);

  expect(await screen.findByText("Всего сорвано джекпотов")).toBeInTheDocument();
  expect(screen.getByText("ТИРАЖИ СЕГОДНЯ")).toBeInTheDocument();
  expect(screen.getByText("Весь проект одним взглядом")).toBeInTheDocument();
  expect(screen.getByText("12 000 CAS")).toBeInTheDocument();
  expect(screen.queryByText("v0.8.0 · работает 2 мин.")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /^12Журналы$/ }));
  fireEvent.click(screen.getByRole("tab", { name: "Состояние" }));
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

  await waitFor(() => expect(adminApi.login).toHaveBeenCalledWith("owner", "password", true));
  expect(await screen.findByText("Всего сорвано джекпотов")).toBeInTheDocument();
});

it("adjusts a player balance only with a mandatory reason", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Игроки/ }));

  const save = await screen.findByRole("button", { name: "ПРОВЕРИТЬ ИЗМЕНЕНИЕ" });
  expect(save).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Новый баланс"), { target: { value: "9000" } });
  fireEvent.change(screen.getByLabelText("Обязательная причина"), { target: { value: "Тестовое начисление" } });
  fireEvent.click(save);
  fireEvent.click(await screen.findByRole("button", { name: "Подтвердить" }));

  await waitFor(() => expect(adminApi.setBalance).toHaveBeenCalledWith("player", 9000, "Тестовое начисление"));
});

it("shows a player's internal ID, per-lottery stats, and searchable ticket history", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Игроки/ }));

  expect(await screen.findByText("История билетов")).toBeInTheDocument();
  expect(screen.getByText("player", { selector: "code" })).toBeInTheDocument();
  expect(screen.getByText("Результаты по лотереям")).toBeInTheDocument();
  expect(await screen.findByText("Билет №77 · тираж №7")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Выигрыши" }));
  await waitFor(() => expect(adminApi.playerTicketHistory).toHaveBeenLastCalledWith("player", "wins", "", 0));
});

it("loads player ticket history in pages beyond the first hundred records", async () => {
  vi.mocked(adminApi.playerTicketHistory)
    .mockResolvedValueOnce({ ...playerHistory, total: 101 })
    .mockResolvedValueOnce({ ...playerHistory, items: [{ ...playerHistory.items[0], id: "ticket-101", public_number: 101 }], offset: 1, total: 101 });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Игроки/ }));

  fireEvent.click(await screen.findByRole("button", { name: /Показать ещё/ }));
  await waitFor(() => expect(adminApi.playerTicketHistory).toHaveBeenLastCalledWith("player", "all", "", 1));
  expect(await screen.findByText("Билет №101 · тираж №7")).toBeInTheDocument();
});

it("opens a player dossier directly from the event log", async () => {
  vi.mocked(adminApi.transactions).mockResolvedValue([playerTransaction]);
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Журналы/ }));
  fireEvent.click(await screen.findByRole("tab", { name: "Лента событий" }));

  fireEvent.click(await screen.findByRole("button", { name: /Игрок · player/ }));
  expect(await screen.findByLabelText("Поиск игрока")).toHaveValue("player");
  expect(await screen.findByText("История билетов")).toBeInTheDocument();
});

it("groups administration into thirteen owner-oriented sections", async () => {
  render(<App />);
  await screen.findByText("Всего сорвано джекпотов");

  const nav = within(screen.getByRole("navigation"));
  for (const label of ["Сегодня", "Fast", "Kasper LIVE", "Лотереи", "Расписание", "Тиражи", "Джекпоты", "Архив", "Игроки", "Аналитика", "Interesting Facts", "Тест эфира", "Журналы"]) {
    expect(nav.getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
  }
  fireEvent.click(nav.getByRole("button", { name: /Журналы/ }));
  expect(await screen.findByRole("tab", { name: "Журнал CAS" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Уведомления" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Аудит действий" })).toBeInTheDocument();
});

it("shows only the four agreed Kasper LIVE aggregates", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Kasper LIVE/ }));

  expect(await screen.findByText("КОЛИЧЕСТВО БИЛЕТОВ")).toBeInTheDocument();
  expect(screen.getByText("ВЫИГРЫШИ")).toBeInTheDocument();
  expect(screen.getByText("ПРОИГРЫШИ")).toBeInTheDocument();
  expect(screen.getByText("РЕЗУЛЬТАТ")).toBeInTheDocument();
  expect(screen.getByText("+79 000 CAS")).toBeInTheDocument();
  expect(adminApi.kasperLive).toHaveBeenCalledTimes(1);
});

it("shows the daily owner result and its lottery breakdown", async () => {
  render(<App />);
  expect(await screen.findByText("ПЛЮС ЛОТО ЗА ДЕНЬ")).toBeInTheDocument();
  expect(screen.getByText("Из чего сложился итог дня")).toBeInTheDocument();
  expect(screen.getAllByText("+150 CAS").length).toBeGreaterThan(0);
});

it("shows precomputed interesting facts and updates their workflow status", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Interesting Facts/ }));

  expect(await screen.findByText("12 тиражей без джекпота")).toBeInTheDocument();
  expect(screen.getByLabelText("Статус факта")).toHaveValue("new");
  expect(adminApi.interestingFacts).toHaveBeenCalledWith("");
  fireEvent.click(screen.getByRole("button", { name: "Использовано" }));

  await waitFor(() => expect(adminApi.setInterestingFactStatus).toHaveBeenCalledWith("fact", "used"));
  expect(screen.queryByText("12 тиражей без джекпота")).not.toBeInTheDocument();
});

it("opens an isolated non-Fast broadcast rehearsal in the Mini App", async () => {
  const open = vi.spyOn(window, "open").mockImplementation(() => null);
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Тест эфира/ }));

  expect(await screen.findByText("Проверьте эфир глазами игрока")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Сценарий тестового эфира"), { target: { value: "loss" } });
  fireEvent.click(screen.getByRole("button", { name: /Запустить тестовый эфир/ }));

  expect(open).toHaveBeenCalledOnce();
  const launched = new URL(String(open.mock.calls[0][0]));
  expect(launched.origin).toBe("https://play.example.test");
  expect(launched.searchParams.get("broadcast-preview")).toBe("weekly");
  expect(launched.searchParams.get("scenario")).toBe("loss");
  open.mockRestore();
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
  fireEvent.click(await screen.findByRole("button", { name: /^12Журналы$/ }));
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
  fireEvent.change(screen.getByLabelText("Комментарий для истории изменений"), { target: { value: "Настройки владельца" } });
  fireEvent.click(screen.getByRole("button", { name: "СОХРАНИТЬ НАСТРОЙКИ" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Да, сохранить" }));

  await waitFor(() => expect(adminApi.configureLottery).toHaveBeenCalledWith("lottery", 22222, 2811996, 5, 1000, 5000, "Настройки владельца"));
  expect(adminApi.setReserve).not.toHaveBeenCalled();
  expect(await screen.findByText("Цена билета, базовый джекпот и лимиты сохранены.")).toBeInTheDocument();
});

it("adjusts the current jackpot through the ledger action", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Лотереи/ }));

  fireEvent.change(await screen.findByLabelText("Текущий джекпот, CAS"), { target: { value: "999999" } });
  fireEvent.change(screen.getByLabelText("Комментарий для истории изменений"), { target: { value: "Решение владельца" } });
  fireEvent.click(screen.getByRole("button", { name: "ИЗМЕНИТЬ ДЖЕКПОТ" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Да, изменить" }));

  await waitFor(() => expect(adminApi.setJackpot).toHaveBeenCalledWith("lottery", 999999, "Решение владельца"));
  expect(await screen.findByText("Текущий джекпот изменён через журнал CAS.")).toBeInTheDocument();
});

it("keeps lottery controls available after changing the current jackpot", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Лотереи/ }));

  fireEvent.change(await screen.findByLabelText("Текущий джекпот, CAS"), { target: { value: "999999" } });
  fireEvent.click(screen.getByRole("button", { name: "ИЗМЕНИТЬ ДЖЕКПОТ" }));
  fireEvent.click(await screen.findByRole("button", { name: "Да, изменить" }));
  await waitFor(() => expect(adminApi.setJackpot).toHaveBeenCalled());

  fireEvent.change(screen.getByLabelText("Цена билета, CAS"), { target: { value: "22222" } });
  fireEvent.click(screen.getByRole("button", { name: "СОХРАНИТЬ НАСТРОЙКИ" }));
  fireEvent.click(await screen.findByRole("button", { name: "Да, сохранить" }));

  await waitFor(() => expect(adminApi.configureLottery).toHaveBeenCalledWith("lottery", 22222, 10000, 5, 1000, 5000, "Изменение настроек владельцем"));
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
  await waitFor(() => expect(adminApi.dashboard).toHaveBeenCalledTimes(4));
  expect(screen.getByRole("button", { name: /Скрыть историю джекпотов/ })).toHaveAttribute("aria-expanded", "true");
});

it("restores an old development URL inside System", async () => {
  window.history.replaceState({}, "", "/development");
  render(<App />);
  expect(await screen.findByText("Публичное изменение")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Журналы" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Разработка" })).toHaveAttribute("aria-selected", "true");
});

it("reports a failed owner balance change without pretending it succeeded", async () => {
  vi.mocked(adminApi.setBalance).mockRejectedValueOnce(new Error("Не удалось сохранить баланс"));
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Игроки/ }));
  fireEvent.change(await screen.findByLabelText("Обязательная причина"), { target: { value: "Уточнение" } });
  fireEvent.click(screen.getByRole("button", { name: "ПРОВЕРИТЬ ИЗМЕНЕНИЕ" }));
  fireEvent.click(await screen.findByRole("button", { name: "Подтвердить" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось сохранить баланс");
});

it.each([null, 200])("uses the recorded jackpot event in draw details, amount=%s", async (amount) => {
  const event = { id: "event", lottery_code: "weekly", lottery_name: "Weekly 5/20", draw_id: "draw", draw_number: 7, jackpot_amount: 200, winner_ticket_count: 1, winner_user_count: 1, base_jackpot_after: 500, occurred_at: "2026-09-04T12:00:00Z" };
  vi.mocked(adminApi.dashboard).mockResolvedValue({ ...dashboard, jackpots: { ...dashboard.jackpots, last_win: event } });
  vi.mocked(adminApi.draw).mockResolvedValue({ draw: {
    id: "draw", lottery_id: "lottery", lottery_code: "weekly", lottery_name: "Weekly 5/20", public_number: 7, status: "COMPLETED", scheduled_at: event.occurred_at, sales_close_at: event.occurred_at, executed_at: event.occurred_at, winning_numbers: [1,2,3,4,5], ticket_count: 1, total_sales: 100, total_payout: 200, jackpot_opening: 200, jackpot_closing: amount ? 500 : 100, distribution_opening: 0, distribution_closing: 0, reserve_used: 0, kasper_fund_used: 0, correlation_id: "internal-correlation", jackpot_amount: amount,
  }, tickets: amount ? [{ id: "winner-ticket", public_number: 77, user_id: "player", player_name: "Jackpot Player", player_username: "jackpot", player_telegram_id: 777, is_jackpot_winner: true, numbers: [1,2,3,4,5], purchase_price: 100, matches: 5, prize_amount: 200 }] : [] });
  vi.mocked(adminApi.draws).mockResolvedValue([{
    id: "draw", lottery_id: "lottery", lottery_code: "weekly", lottery_name: "Weekly 5/20", public_number: 7, status: "COMPLETED", scheduled_at: event.occurred_at, sales_close_at: event.occurred_at, executed_at: event.occurred_at, winning_numbers: [1,2,3,4,5], ticket_count: 1, total_sales: 100, total_payout: 200, jackpot_opening: 200, jackpot_closing: amount ? 500 : 100, distribution_opening: 0, distribution_closing: 0, reserve_used: 0, kasper_fund_used: 0, correlation_id: "internal-correlation", jackpot_amount: amount,
  }]);
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Тиражи/ }));
  fireEvent.click((await screen.findAllByText("Weekly 5/20")).at(-1)!);
  const dialog = await screen.findByRole("dialog");
  if (amount) {
    expect(within(dialog).getByText("ДЖЕКПОТ ЭТОГО ТИРАЖА СОРВАН")).toBeInTheDocument();
    expect(within(dialog).getByText("Кто сорвал джекпот")).toBeInTheDocument();
    expect(within(dialog).getAllByText("Jackpot Player").length).toBeGreaterThan(0);
  }
  else expect(within(dialog).queryByText("ДЖЕКПОТ ЭТОГО ТИРАЖА СОРВАН")).not.toBeInTheDocument();
  expect(within(dialog).queryByText("internal-correlation")).not.toBeInTheDocument();
  fireEvent.keyDown(window, { key: "Escape" });
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
});

it("does not present Bingo ball frequency as ordinary number statistics", async () => {
  vi.mocked(adminApi.lotteries).mockResolvedValue([{ ...lottery, id: "bingo-lottery", code: "bingo", name: "Kasper Bingo", kind: "DAILY" }, lottery]);
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Аналитика/ }));
  fireEvent.click(await screen.findByRole("tab", { name: "Числа" }));
  const selector = await screen.findByLabelText("Лотерея");
  expect(within(selector).queryByRole("option", { name: "Kasper Bingo" })).not.toBeInTheDocument();
  expect(screen.getByText(/Bingo здесь не показывается/)).toBeInTheDocument();
});

it("lets the owner choose the auto-play ticket count and shows its state", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Игроки/ }));
  expect(await screen.findByText("АВТОУЧАСТИЕ · ОТКЛЮЧЕНО")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Билетов автоучастия на тираж"), { target: { value: "3" } });
  fireEvent.change(screen.getByLabelText("Причина автоучастия"), { target: { value: "Пожелание игрока" } });
  fireEvent.click(screen.getByRole("button", { name: "ВКЛЮЧИТЬ АВТОУЧАСТИЕ" }));
  fireEvent.click(await screen.findByRole("button", { name: "Подтвердить" }));
  await waitFor(() => expect(adminApi.setAutoPlay).toHaveBeenCalledWith("player", true, 3, "Пожелание игрока"));
});

it("summarizes Bingo by stages and keeps the full ball protocol collapsed", async () => {
  const bingoLottery: Lottery = { ...lottery, id: "bingo-lottery", code: "bingo", name: "Kasper Bingo", kind: "DAILY" };
  const bingoDraw = {
    id: "bingo-draw", lottery_id: bingoLottery.id, lottery_code: "bingo", lottery_name: "Kasper Bingo", public_number: 18, status: "COMPLETED", scheduled_at: "2026-09-14T19:00:00Z", sales_close_at: "2026-09-14T18:58:00Z", executed_at: "2026-09-14T19:03:00Z", winning_numbers: Array.from({ length: 58 }, (_, index) => index + 1), ticket_count: 2, total_sales: 100_000, total_payout: 600_000, jackpot_opening: 10_000_000, jackpot_closing: 10_100_000, distribution_opening: 0, distribution_closing: 0, reserve_used: 0, kasper_fund_used: 600_000, correlation_id: "bingo-correlation", jackpot_amount: null,
  };
  vi.mocked(adminApi.lotteries).mockResolvedValue([lottery, bingoLottery]);
  vi.mocked(adminApi.draws).mockResolvedValue([bingoDraw]);
  vi.mocked(adminApi.draw).mockResolvedValue({ draw: bingoDraw, tickets: [
    { id: "winner", public_number: 101, user_id: "user-a", numbers: [1,2,3,4,5,6,7,8,9,10,11,12], purchase_price: 50_000, matches: 12, prize_amount: 600_000, bingo_result: { moves: [16, 31, 40], amounts: [100_000, 500_000, 0] } },
    { id: "loser", public_number: 102, user_id: "user-b", numbers: [1,2,3,4,5,6,7,8,9,10,59,60], purchase_price: 50_000, matches: 10, prize_amount: 0, bingo_result: { moves: [20, 61, 61], amounts: [0, 0, 0] } },
  ] });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Тиражи/ }));
  fireEvent.click((await screen.findAllByText("Kasper Bingo")).at(-1)!);
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByText("58 ходов")).toBeInTheDocument();
  expect(within(dialog).getByText("Не выпали: 59 · 60")).toBeInTheDocument();
  expect(within(dialog).getByText("РАННЯЯ СТРОКА")).toBeInTheDocument();
  expect(within(dialog).getByText("Выигрышные · 1")).toBeInTheDocument();
  expect(within(dialog).getByText("№0101")).toBeInTheDocument();
  expect(within(dialog).queryByText("№0102")).not.toBeInTheDocument();
  expect(within(dialog).getByText("Полный протокол шаров").closest("details")).not.toHaveAttribute("open");
});

it("opens the dedicated Fast control room and requests a bounded Fast draw page", async () => {
  render(<App />);
  await screen.findByText("Всего сорвано джекпотов");
  expect(adminApi.dashboard).toHaveBeenCalledWith("standard");
  expect(adminApi.dashboard).toHaveBeenCalledWith("all");
  fireEvent.click(screen.getByRole("button", { name: /^02Fast$/ }));
  await waitFor(() => expect(adminApi.dashboard).toHaveBeenCalledWith("fast"));
  expect(adminApi.ticketAnalytics).toHaveBeenCalledWith("fast");
  fireEvent.click(screen.getByRole("button", { name: /Тиражи/ }));
  fireEvent.click(within(screen.getByRole("tablist", { name: "Тип игр" })).getByRole("tab", { name: "Fast" }));
  await waitFor(() => expect(adminApi.draws).toHaveBeenCalledWith("scope=fast&period=today&limit=100&offset=0"));
  fireEvent.click(screen.getByRole("tab", { name: "Завершённые" }));
  await waitFor(() => expect(adminApi.draws).toHaveBeenLastCalledWith("scope=fast&period=completed&limit=100&offset=0"));
});

it("opens the last Fast jackpot directly from the Fast control room", async () => {
  vi.mocked(adminApi.dashboard).mockResolvedValue({
    ...dashboard,
    jackpots: {
      ...dashboard.jackpots,
      total_wins: 1,
      last_win: {
        id: "fast-jackpot", lottery_code: "flash", lottery_name: "FLASH", draw_id: "fast-draw",
        draw_number: 411, jackpot_amount: 25_000, winner_ticket_count: 2, winner_user_count: 1,
        base_jackpot_after: 1_000, occurred_at: "2026-09-19T12:00:00Z",
      },
    },
  });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /^02Fast$/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Тираж №0411/ }));
  expect(adminApi.draw).toHaveBeenCalledWith("fast-draw");
});

it("opens a Fast jackpot from its own catalog and routes to the draw details", async () => {
  vi.mocked(adminApi.jackpotEvents).mockResolvedValue([{
    id: "jackpot-event", lottery_code: "flash", lottery_name: "FLASH", draw_id: "flash-draw", draw_number: 411,
    jackpot_amount: 25_000, winner_ticket_count: 2, winner_user_count: 1, base_jackpot_after: 1_000,
    occurred_at: "2026-09-19T12:00:00Z",
  }]);
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Джекпоты/ }));
  fireEvent.click(within(screen.getByRole("tablist", { name: "Тип игр" })).getByRole("tab", { name: "Fast" }));
  await waitFor(() => expect(adminApi.jackpotEvents).toHaveBeenCalledWith("fast", "", 0));
  fireEvent.click(await screen.findByRole("button", { name: /Открыть детали/ }));
  expect(adminApi.draw).toHaveBeenCalledWith("flash-draw");
});

it("opens the separate archive on historical completed formats", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Архив/ }));
  await waitFor(() => expect(adminApi.draws).toHaveBeenCalledWith("scope=all&period=archived&limit=100&offset=0"));
  expect(await screen.findByText("Архив завершённых лотерей")).toBeInTheDocument();
});
