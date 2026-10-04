import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { miniAppApi } from "./api";
import { DrawArchive } from "./DrawArchive";
import type { ArchiveDraw, ArchivePage } from "./types";

vi.mock("./api", () => ({ miniAppApi: { drawArchive: vi.fn() } }));
const draw: ArchiveDraw = { id: "one", lottery_code: "khan", lottery_name: "6 из 36", draw_number: 123, scheduled_at: "2026-10-04T15:00:00Z", total_payout: 12000, ticket_count: 5, winning_numbers: [1, 2, 3, 4, 5, 6], primary_numbers_to_pick: 6, secondary_storage_offset: 0, jackpot_amount: null };
const page: ArchivePage = { items: [draw], lotteries: [{ code: "khan", name: "6 из 36" }, { code: "bingo", name: "Casper Bingo" }], next_cursor: null };
beforeEach(() => vi.resetAllMocks());

it("loads older pages, preserves cards and displays jackpot and compact Bingo", async () => {
  vi.mocked(miniAppApi.drawArchive).mockResolvedValueOnce({ ...page, next_cursor: "one" }).mockResolvedValueOnce({ ...page, items: [{ ...draw, id: "two", lottery_code: "bingo", lottery_name: "Casper Bingo", draw_number: 1, jackpot_amount: 10000, winning_numbers: null, ticket_count: null }] });
  render(<DrawArchive initData="auth" onBack={vi.fn()} />);
  await screen.findByText("№ 123");
  fireEvent.click(screen.getByText(/Результаты тиража/));
  expect(screen.getByRole("list", { name: "Выигрышная комбинация" })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Показать более ранние" }));
  await screen.findByText("Джекпот сорван!");
  expect(miniAppApi.drawArchive).toHaveBeenLastCalledWith("auth", "", false, "one", expect.any(AbortSignal));
  expect(screen.getByText("№ 123")).toBeVisible();
  expect(screen.getAllByText(/Результаты тиража/)).toHaveLength(1);
  expect(screen.getByText("Вы дошли до начала истории")).toBeVisible();
});

it("resets pagination on filters and ignores stale requests", async () => {
  let resolveOld!: (value: ArchivePage) => void;
  vi.mocked(miniAppApi.drawArchive).mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; })).mockResolvedValue({ ...page, items: [] });
  render(<DrawArchive initData="auth" onBack={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: /Только джекпоты/ }));
  await screen.findByText("Сорванных джекпотов пока нет.");
  resolveOld(page);
  await waitFor(() => expect(screen.queryByText("№ 123")).not.toBeInTheDocument());
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "khan" } });
  await waitFor(() => expect(miniAppApi.drawArchive).toHaveBeenLastCalledWith("auth", "khan", true, null, expect.any(AbortSignal)));
});

it("retries failures and decodes separate fields from historical metadata", async () => {
  vi.mocked(miniAppApi.drawArchive).mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ ...page, items: [{ ...draw, primary_numbers_to_pick: 2, secondary_storage_offset: 35, winning_numbers: [2, 9, 38] }] });
  const onBack = vi.fn();
  render(<DrawArchive initData="" onBack={onBack} />);
  fireEvent.click(await screen.findByRole("button", { name: "Повторить" }));
  await screen.findByText("№ 123");
  fireEvent.click(screen.getByText(/Результаты тиража/));
  expect(screen.getByRole("list", { name: "Поле 2" })).toHaveTextContent("3");
  fireEvent.click(screen.getByRole("button", { name: /На главную/ }));
  expect(onBack).toHaveBeenCalledOnce();
});
