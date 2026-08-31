import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import App from "./App";
import { adminApi } from "./api";
import type { Dashboard, Lottery, Player } from "./types";

vi.mock("./api", () => ({
  ApiError: class ApiError extends Error { status = 500; },
  adminApi: {
    login: vi.fn(), session: vi.fn(), logout: vi.fn(), dashboard: vi.fn(),
    players: vi.fn(), lotteries: vi.fn(), draws: vi.fn(), draw: vi.fn(),
    transactions: vi.fn(), statistics: vi.fn(), audit: vi.fn(),
    releaseNotes: vi.fn(),
    setBalance: vi.fn(), configureLottery: vi.fn(), setReserve: vi.fn(),
  },
}));

const session = { username: "owner", csrf_token: "csrf", expires_at: "2026-08-16T00:00:00Z" };
const lottery: Lottery = { id: "lottery", code: "weekly", name: "Weekly 5/20", kind: "WEEKLY", ticket_price: 100, base_jackpot: 10_000, current_jackpot: 12_000, distribution_fund: 500, reserve: 100_000, schedule: { weekday: "sunday" }, sales_cutoff_minutes: 5, is_active: true, next_draw_number: 8, next_draw_at: "2026-08-16T17:00:00Z" };
const dashboard: Dashboard = { version: "0.8.0", uptime_seconds: 120, database_healthy: true, bot_configured: true, scheduler_enabled: true, counts: { users: 1, tickets: 6, completed_draws: 3, pending_draws: 1 }, lotteries: [lottery], recent_draws: [], recent_transactions: [] };
const player: Player = { id: "player", display_name: "Test Player", username: "player", telegram_id: 123, is_active: true, balance: 5_000, ticket_count: 6, spent: 600, won: 250, net: -350 };

beforeEach(() => {
  vi.mocked(adminApi.session).mockResolvedValue(session);
  vi.mocked(adminApi.login).mockResolvedValue(session);
  vi.mocked(adminApi.logout).mockResolvedValue();
  vi.mocked(adminApi.dashboard).mockResolvedValue(dashboard);
  vi.mocked(adminApi.players).mockResolvedValue([player]);
  vi.mocked(adminApi.lotteries).mockResolvedValue([lottery]);
  vi.mocked(adminApi.draws).mockResolvedValue([]);
  vi.mocked(adminApi.transactions).mockResolvedValue([]);
  vi.mocked(adminApi.statistics).mockResolvedValue([]);
  vi.mocked(adminApi.audit).mockResolvedValue([]);
  vi.mocked(adminApi.releaseNotes).mockImplementation(async (kind) => [{
    version: "0.15.0", date: "2026-08-31", content: kind === "changelog" ? "Публичное изменение" : "Техническое изменение",
  }]);
  vi.mocked(adminApi.setBalance).mockResolvedValue({ amount: 9_000, already_processed: false });
  vi.mocked(adminApi.configureLottery).mockResolvedValue(lottery);
  vi.mocked(adminApi.setReserve).mockResolvedValue({ amount: 100_000, already_processed: false });
});

it("restores an authenticated session and renders Russian system truth", async () => {
  render(<App />);

  expect(await screen.findByText("БАЗА ДАННЫХ РАБОТАЕТ")).toBeInTheDocument();
  expect(screen.getByText("12 000 CAS")).toBeInTheDocument();
  expect(screen.getByText("v0.8.0 · работает 2 мин.")).toBeInTheDocument();
});

it("shows login and authenticates when no session exists", async () => {
  vi.mocked(adminApi.session).mockRejectedValueOnce(new Error("unauthorized"));
  render(<App />);

  fireEvent.change(await screen.findByLabelText("ЛОГИН АДМИНИСТРАТОРА"), { target: { value: "owner" } });
  fireEvent.change(screen.getByLabelText("ПАРОЛЬ"), { target: { value: "password" } });
  fireEvent.click(screen.getByRole("button", { name: "ВОЙТИ" }));

  await waitFor(() => expect(adminApi.login).toHaveBeenCalledWith("owner", "password"));
  expect(await screen.findByText("БАЗА ДАННЫХ РАБОТАЕТ")).toBeInTheDocument();
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

it("exposes immutable archive, ledger, statistics and audit navigation", async () => {
  render(<App />);
  await screen.findByText("БАЗА ДАННЫХ РАБОТАЕТ");

  for (const label of ["Архив тиражей", "Журнал CAS", "Статистика чисел", "Аудит действий", "Разработка"]) {
    expect(screen.getByRole("button", { name: new RegExp(label) })).toBeInTheDocument();
  }
});

it("shows complete changelog and devlog in separate protected tabs", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Разработка/ }));

  expect(await screen.findByText("Публичное изменение")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "DEVLOG" }));
  expect(screen.getByText("Техническое изменение")).toBeInTheDocument();
  expect(adminApi.releaseNotes).toHaveBeenCalledWith("changelog");
  expect(adminApi.releaseNotes).toHaveBeenCalledWith("devlog");
});

it("saves lottery price, jackpot and reserve with one action", async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: /Лотереи/ }));

  fireEvent.change(await screen.findByLabelText("Цена билета, CAS"), { target: { value: "22222" } });
  fireEvent.change(screen.getByLabelText("Базовый джекпот, CAS"), { target: { value: "2811996" } });
  fireEvent.change(screen.getByLabelText("Резерв, CAS"), { target: { value: "9999999999" } });
  fireEvent.change(screen.getByLabelText("Обязательная причина для аудита"), { target: { value: "Настройки владельца" } });
  fireEvent.click(screen.getByRole("button", { name: "СОХРАНИТЬ ВСЕ НАСТРОЙКИ" }));

  await waitFor(() => expect(adminApi.configureLottery).toHaveBeenCalledWith("lottery", 22222, 2811996, "Настройки владельца"));
  expect(adminApi.setReserve).toHaveBeenCalledWith("lottery", 9999999999, "Настройки владельца");
  expect(await screen.findByText("Цена билета, джекпот и резерв сохранены.")).toBeInTheDocument();
});
