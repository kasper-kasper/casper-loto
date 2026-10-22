import { act, fireEvent, render, screen, within, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Achievements, AchievementSummary } from "./Achievements";
import { AchievementNotices } from "./AchievementNotices";
import { AchievementRewards } from "./AchievementRewards";
import { miniAppApi } from "./api";
import type { Achievement, AchievementPage } from "./achievementTypes";

vi.mock("./api", () => ({ miniAppApi: { achievements: vi.fn(), achievementNotices: vi.fn(), achievementSeen: vi.fn().mockResolvedValue(undefined) } }));
const won: Achievement = { code: "first_ticket", title: "Ты с нами!", description: "Купить первый платный билет", rarity: "common", icon: "ticket-check", status: "earned", secret: false, reward_pending: true, earned_at: "2026-10-19T00:00:00Z" };
const locked: Achievement = { code: "ten_tickets", title: "Затянуло", description: "Купить 10 билетов", rarity: "common", status: "locked", secret: false, progress: [{ metric: "paid_tickets", current: 7, target: 10, operator: "gte" }], progress_mode: "all", reward_pending: true };
const page: AchievementPage = { enabled: true, total: 22, earned: 1, total_by_category: { common: 22, rare: 0 }, earned_by_category: { common: 1 }, items: [won, locked], next_offset: null };
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); });

describe("achievements UI", () => {
  it("opens epic with 82 entries and ten Grand tickets, keeping future cases hidden", async () => {
    const epic: Achievement = { ...locked, code: "epic_hundred_thousand_tickets", title: "Тут всё моё", rarity: "epic", reward_pending: false, rewards: [{ type: "cas", amount: 20000000 }, ...Array.from({ length: 10 }, () => ({ type: "ticket", amount: 1, lottery: "weekly" })), { type: "case", amount: 4, planned: true }] };
    vi.mocked(miniAppApi.achievements).mockImplementation(async (_init, options) => ({ ...page, total: 82, total_by_category: { common: 22, uncommon: 23, rare: 20, epic: 17 }, items: options?.category === "epic" ? [epic] : [won] }));
    const { container } = render(<Achievements initData="fixture" onBack={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /Эпические/ }));
    expect(await screen.findByText("Тут всё моё")).toBeInTheDocument();
    expect(screen.getByText(/82 открыто/)).toBeInTheDocument();
    expect(screen.getByText("10 билетов «Casper Grand»")).toBeInTheDocument();
    expect(screen.queryByText("4 кейса · позже")).not.toBeInTheDocument();
    expect(container.querySelector(".achievement-badge.rarity-epic .achievement-badge-mark")).toHaveTextContent("100000");
  });
  it("opens the rare category with 65 total entries and a readable thousand badge", async () => {
    const rare: Achievement = { ...locked, code: "rare_thousand_tickets", title: "Косарь", rarity: "rare", flavor: "Тысяча билетов! Да ты серьёзно взялся за дело.", reward_pending: false, progress: [{ metric: "paid_tickets", current: 7, target: 1000, operator: "gte" }], rewards: [{ type: "cas", amount: 900000 }, ...Array.from({ length: 5 }, () => ({ type: "ticket", amount: 1, lottery: "weekly" }))] };
    vi.mocked(miniAppApi.achievements).mockImplementation(async (_init, options) => ({ ...page, total: 65, total_by_category: { common: 22, uncommon: 23, rare: 20 }, items: options?.category === "rare" ? [rare] : [won] }));
    const { container } = render(<Achievements initData="fixture" onBack={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /Редкие/ }));
    expect(await screen.findByText("Косарь")).toBeInTheDocument();
    expect(screen.getByText(/65 открыто/)).toBeInTheDocument();
    expect(screen.getByText("7 / 1 000")).toBeInTheDocument();
    expect(screen.getByText("5 билетов «Casper Grand»")).toBeInTheDocument();
    expect(container.querySelector(".achievement-badge.rarity-rare .achievement-badge-mark")).toHaveTextContent("1000");
  });
  it("opens uncommon with the shared total, flavor copy and grouped ticket pack", async () => {
    const uncommon: Achievement = { ...locked, reward_pending: false, code: "uncommon_grand_two", title: "Маленький Гранд", flavor: "Начало положено.", rarity: "uncommon", rewards: Array.from({ length: 3 }, () => ({ type: "ticket", amount: 1, lottery: "weekly" })) };
    vi.mocked(miniAppApi.achievements).mockImplementation(async (_init, options) => ({ ...page, total: 45, total_by_category: { common: 22, uncommon: 23 }, items: options?.category === "uncommon" ? [uncommon] : [won] }));
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", { value: function (this: HTMLDialogElement) { this.setAttribute("open", ""); }, configurable: true });
    Object.defineProperty(HTMLDialogElement.prototype, "close", { value: function (this: HTMLDialogElement) { this.removeAttribute("open"); }, configurable: true });
    render(<Achievements initData="fixture" onBack={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /Необычные/ }));
    expect(await screen.findByText("3 билета «Casper Grand»")).toBeInTheDocument();
    expect(screen.getByText(/45 открыто/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Маленький Гранд/ }));
    expect(within(screen.getByRole("dialog")).getByText("Начало положено.")).toBeInTheDocument();
  });

  it("groups individual idempotent parts into Bingo cards and five-ticket rewards", () => {
    render(<AchievementRewards item={{ ...locked, reward_pending: false, rewards: [
      ...Array.from({ length: 3 }, () => ({ type: "ticket", amount: 1, lottery: "bingo" })),
      ...Array.from({ length: 5 }, () => ({ type: "ticket", amount: 1, lottery: "khan" })),
      { type: "case", amount: 1, planned: true },
    ] }} />);
    expect(screen.getByText("3 карточки «Casper Bingo»")).toBeInTheDocument();
    expect(screen.getByText("5 билетов «6 из 36»")).toBeInTheDocument();
    expect(screen.queryByText("1 кейс · позже")).not.toBeInTheDocument();
  });
  it("refreshes the first page when progress reorders entries during pagination", async () => {
    vi.mocked(miniAppApi.achievements)
      .mockResolvedValueOnce({ ...page, items: [won], updated_at: "before", next_offset: 12 })
      .mockResolvedValueOnce({ ...page, items: [locked], updated_at: "after" })
      .mockResolvedValueOnce({ ...page, items: [locked], updated_at: "after" });
    render(<Achievements initData="fixture" onBack={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Показать ещё" }));
    expect(await screen.findByText("Затянуло")).toBeInTheDocument();
    expect(screen.queryByText("Ты с нами!")).not.toBeInTheDocument();
    expect(miniAppApi.achievements).toHaveBeenLastCalledWith("fixture", { category: "common", status: "all" });
  });
  it("shows real progress and requests category filters, hiding empty rarities", async () => {
    vi.mocked(miniAppApi.achievements).mockImplementation(async (_init, options) => ({ ...page, items: options?.status === "earned" ? [won] : options?.status === "locked" ? [locked] : page.items }));
    const back = vi.fn();
    render(<Achievements initData="fixture" onBack={back} />);
    expect(await screen.findByText("Затянуло")).toBeInTheDocument();
    expect(screen.getByText("7 / 10")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Редкие/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Обычные/ }));
    await waitFor(() => expect(miniAppApi.achievements).toHaveBeenLastCalledWith("fixture", { category: "common", status: "all" }, expect.any(AbortSignal)));
    fireEvent.click(screen.getByRole("button", { name: "Получены" }));
    await waitFor(() => expect(screen.queryByText("Затянуло")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "← В профиль" }));
    expect(back).toHaveBeenCalledOnce();
  });
  it("opens accessible details and closes them without losing the list", async () => {
    vi.mocked(miniAppApi.achievements).mockResolvedValue(page);
    const show = vi.fn(function (this: HTMLDialogElement) { this.setAttribute("open", ""); });
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", { value: show, configurable: true });
    Object.defineProperty(HTMLDialogElement.prototype, "close", { value: function (this: HTMLDialogElement) { this.removeAttribute("open"); }, configurable: true });
    render(<Achievements initData="fixture" onBack={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: /Ты с нами/ }));
    expect(screen.getByRole("dialog", { name: "Ты с нами!" })).toBeInTheDocument();
    expect(screen.getByText(/Получено 19 октября/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Закрыть подробности" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(show).toHaveBeenCalledOnce();
    vi.restoreAllMocks();
  });
  it("shows an honest empty summary and never invents earned tiles", async () => {
    vi.mocked(miniAppApi.achievements).mockResolvedValue({ ...page, earned: 0, items: [] });
    const open = vi.fn();
    render(<AchievementSummary initData="fixture" onOpen={open} />);
    expect(await screen.findByText(/Ваши первые достижения ещё впереди/)).toBeInTheDocument();
    expect(screen.queryByText("Ты с нами!")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Все достижения/ }));
    expect(open).toHaveBeenCalledOnce();
  });
  it("shows one toast at a time, acknowledges after display and performs no continuous polling", async () => {
    vi.useFakeTimers();
    vi.mocked(miniAppApi.achievementNotices).mockResolvedValue([{ ...won, notification_id: "n1" }, { ...locked, status: "earned", notification_id: "n2" }]);
    const { unmount } = render(<AchievementNotices initData="fixture" />);
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(screen.getByRole("status")).toHaveTextContent("Ты с нами!");
    expect(screen.queryByText("Затянуло")).not.toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(4500); });
    expect(miniAppApi.achievementSeen).toHaveBeenCalledWith("fixture", ["n1"]);
    expect(screen.getByRole("status")).toHaveTextContent("Затянуло");
    await act(async () => { await vi.advanceTimersByTimeAsync(30000); });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    const calls = vi.mocked(miniAppApi.achievementNotices).mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(60000); });
    expect(miniAppApi.achievementNotices).toHaveBeenCalledTimes(calls);
    unmount();
  });
});


it("shows mixed approved rewards while keeping future cases hidden", async () => {
  vi.spyOn(HTMLDialogElement.prototype, "showModal").mockImplementation(function (this: HTMLDialogElement) { this.setAttribute("open", ""); });
  const mixed: Achievement = { ...locked, rewards: [ { type: "cas", amount: 100000 },
    { type: "ticket", amount: 1, lottery: "pll" }, { type: "case", amount: 1, planned: true } ], reward_pending: false };
  vi.mocked(miniAppApi.achievements).mockResolvedValue({ ...page, items: [mixed] });
  render(<Achievements initData="fixture" onBack={() => undefined} />);
  expect(await screen.findByText("1 билет «2:22»")).toBeInTheDocument();
  expect(screen.queryByText("1 кейс · позже")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /Затянуло/ }));
  expect(within(screen.getByRole("dialog")).queryByText(/кейс/i)).not.toBeInTheDocument();
  expect(within(screen.getByRole("dialog")).queryByText(/после запуска системы кейсов/)).not.toBeInTheDocument();
  vi.restoreAllMocks();
});
