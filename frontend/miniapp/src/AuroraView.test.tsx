import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { miniAppApi } from "./api";
import { AuroraView } from "./AuroraView";
vi.mock("./api", () => ({ ApiError: class extends Error {}, miniAppApi: { auroraHistory: vi.fn(), auroraPurchase: vi.fn() } }));
vi.mock("./telegram", () => ({ errorHaptic: vi.fn(), selectionHaptic: vi.fn(), successHaptic: vi.fn() }));
const result = { operation_id: "op", tickets: [
  { id: "one", public_number: 101, symbols: [4,4,4], prize_amount: 6000 },
  { id: "two", public_number: 102, symbols: [1,2,3], prize_amount: 0 },
  { id: "three", public_number: 103, symbols: [2,2,2], prize_amount: 2000 },
], total_cost: 9000, total_prize: 8000, balance_after: 29000, already_processed: false };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(miniAppApi.auroraHistory).mockResolvedValue([]); vi.mocked(miniAppApi.auroraPurchase).mockResolvedValue(result); });
afterEach(() => { vi.useRealTimers(); });
it("buys three once, holds one crystal with paused progress then opens the rest together", async () => {
  const settled = vi.fn(); render(<AuroraView initData="signed" balance={30000} onClose={vi.fn()} onSettled={settled} />);
  fireEvent.click(screen.getByRole("button", { name: /3 билета.*Открыть вместе/ }));
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /Купить 3 билета/ })); });
  expect(miniAppApi.auroraPurchase).toHaveBeenCalledWith("signed",3,expect.any(String));
  expect(settled).toHaveBeenCalledWith(result);
  const crystal = screen.getByRole("button", { name: "Удерживать кристалл билета № 101" });
  expect(within(screen.getByRole("article", { name: "Билет № 101" })).queryByRole("status")).not.toBeInTheDocument();
  vi.useFakeTimers({ toFake: ["setInterval","clearInterval","performance"] });
  fireEvent.keyDown(crystal,{key:" "}); expect(document.body.style.position).toBe("fixed");
  await act(async () => { vi.advanceTimersByTime(800); });
  fireEvent.keyUp(crystal,{key:" "}); expect(document.body.style.position).toBe("");
  expect(crystal).toHaveTextContent("50%");
  await act(async () => { vi.advanceTimersByTime(2000); }); expect(crystal).toBeInTheDocument();
  fireEvent.keyDown(crystal,{key:" "});
  await act(async () => { vi.advanceTimersByTime(840); });
  expect(crystal).not.toBeInTheDocument(); expect(document.body.style.position).toBe("");
  expect(screen.getAllByRole("button", {name:/Удерживать кристалл/})).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", {name:/Открыть все/}));
  expect(screen.queryByRole("button", {name:/Удерживать кристалл/})).not.toBeInTheDocument();
  expect(screen.getByText("Общий выигрыш").parentElement).toHaveTextContent("8 000");
  expect(miniAppApi.auroraPurchase).toHaveBeenCalledTimes(1);
});
it("retries an unknown purchase with the same key and quantity", async () => {
  vi.mocked(miniAppApi.auroraPurchase).mockRejectedValueOnce(new Error("timeout"));
  render(<AuroraView initData="signed" balance={30000} onClose={vi.fn()} onSettled={vi.fn()} />);
  await act(async () => { fireEvent.click(screen.getByRole("button", {name:/Купить билет/})); });
  const key=vi.mocked(miniAppApi.auroraPurchase).mock.calls[0][2];
  expect(screen.getByRole("button", {name:/3 билета.*Открыть вместе/})).toBeDisabled();
  await act(async () => { fireEvent.click(screen.getByRole("button", {name:/Повторить запрос/})); });
  expect(miniAppApi.auroraPurchase).toHaveBeenLastCalledWith("signed",1,key);
});
it("requires the full 9000 balance for three tickets", () => {
  render(<AuroraView initData="signed" balance={8999} onClose={vi.fn()} onSettled={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", {name:/3 билета.*Открыть вместе/}));
  expect(screen.getByRole("button", {name:/Купить 3 билета/})).toBeDisabled();
});
