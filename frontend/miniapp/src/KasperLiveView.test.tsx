import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { miniAppApi } from "./api";
import { KasperLiveView } from "./KasperLiveView";

vi.mock("./api", () => ({ ApiError: class ApiError extends Error {}, miniAppApi: { kasperLiveHistory: vi.fn(), kasperLivePurchase: vi.fn() } }));
vi.mock("./telegram", () => ({ errorHaptic: vi.fn(), selectionHaptic: vi.fn(), successHaptic: vi.fn() }));
const purchase = { operation_id: "operation", tickets: [
  { id: "one", public_number: 101, symbols: [4, 4, 4], prize_amount: 5_000 },
  { id: "two", public_number: 102, symbols: [4, 5, 6], prize_amount: 0 },
  { id: "three", public_number: 103, symbols: [2, 2, 2], prize_amount: 1_000 },
], total_cost: 6_000, total_prize: 6_000, balance_after: 20_000, already_processed: false };
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(miniAppApi.kasperLiveHistory).mockResolvedValue([]);
  vi.mocked(miniAppApi.kasperLivePurchase).mockResolvedValue(purchase);
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});
it("settles one purchase immediately, opens a single ticket then the remainder without purchasing again", async () => {
  const settled = vi.fn();
  let resolve!: (value: typeof purchase) => void;
  vi.mocked(miniAppApi.kasperLivePurchase).mockReturnValue(new Promise(done => { resolve = done; }));
  render(<KasperLiveView initData="signed" balance={30_000} onClose={vi.fn()} onSettled={settled} />);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /3 билета.*Открывайте/ })); });
  fireEvent.click(screen.getByRole("button", { name: /Купить 3 билета/ }));
  expect(screen.getByRole("button", { name: /Печатаем/ })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: /Печатаем/ }));
  expect(miniAppApi.kasperLivePurchase).toHaveBeenCalledTimes(1);
  expect(miniAppApi.kasperLivePurchase).toHaveBeenCalledWith("signed", 3, expect.any(String));
  await act(async () => { resolve(purchase); });
  expect(settled).toHaveBeenCalledWith(purchase);
  expect(screen.getAllByRole("button", { name: /^Открыть билет №/ })).toHaveLength(3);
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(within(screen.getByRole("article", { name: "Билет № 101" })).queryByRole("img", { name: "Золотая звезда" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Открыть билет № 101" }));
  expect(screen.getAllByRole("button", { name: /^Открыть билет №/ })).toHaveLength(2);
  expect(within(screen.getByRole("article", { name: "Билет № 101" })).getAllByRole("img", { name: "Золотая звезда" })).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", { name: /Открыть все/ }));
  expect(screen.getByRole("status")).toHaveTextContent("Общий выигрыш");
  expect(screen.queryByRole("button", { name: /^Открыть билет №/ })).not.toBeInTheDocument();
  expect(miniAppApi.kasperLivePurchase).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: /Купить ещё/ }));
  expect(screen.getByRole("button", { name: /Купить 3 билета/ })).toBeInTheDocument();
});
it("supports a single losing ticket and guards insufficient balance", async () => {
  vi.mocked(miniAppApi.kasperLivePurchase).mockResolvedValue({ ...purchase, tickets: [purchase.tickets[1]], total_cost: 2_000, total_prize: 0 });
  const { rerender } = render(<KasperLiveView initData="signed" balance={1_000} onClose={vi.fn()} onSettled={vi.fn()} />);
  expect(screen.getByRole("button", { name: /Купить билет/ })).toBeDisabled();
  rerender(<KasperLiveView initData="signed" balance={3_000} onClose={vi.fn()} onSettled={vi.fn()} />);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /Купить билет/ })); });
  fireEvent.click(screen.getByRole("button", { name: "Открыть билет" }));
  expect(screen.getByRole("status")).toHaveTextContent("В этот раз без выигрыша");
  expect(screen.getByRole("article", { name: "Билет № 102" })).not.toHaveClass("winner");
});
it("shows errors without inventing tickets or a settlement", async () => {
  const settled = vi.fn();
  vi.mocked(miniAppApi.kasperLivePurchase).mockRejectedValue(new Error("offline"));
  render(<KasperLiveView initData="signed" balance={30_000} onClose={vi.fn()} onSettled={settled} />);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /Купить билет/ })); });
  expect(screen.getByRole("alert")).toHaveTextContent("Проверьте историю");
  expect(settled).not.toHaveBeenCalled();
  expect(screen.queryByRole("article")).not.toBeInTheDocument();
});

it("renders the maximum server prize with the branded medallion without deriving payouts from artwork", async () => {
  vi.mocked(miniAppApi.kasperLivePurchase).mockResolvedValue({ ...purchase, tickets: [{ ...purchase.tickets[0], symbols: [7, 7, 7], prize_amount: 1_000_000 }], total_prize: 1_000_000 });
  render(<KasperLiveView initData="signed" balance={30_000} onClose={vi.fn()} onSettled={vi.fn()} />);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /Купить билет/ })); });
  const ticket = screen.getByRole("article", { name: "Билет № 101" });
  expect(within(ticket).queryByRole("img", { name: "Золотой жетон Casper" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Открыть билет" }));
  expect(within(ticket).getAllByRole("img", { name: "Золотой жетон Casper" })).toHaveLength(3);
  expect(screen.getByRole("status").querySelector('.money-value')).toHaveAttribute("aria-label", "1 000 000 CAS");
});

it("locks only while scratching, keeps partial strokes and reveals without another purchase", async () => {
  window.PointerEvent = MouseEvent as typeof PointerEvent;
  render(<KasperLiveView initData="signed" balance={30_000} onClose={vi.fn()} onSettled={vi.fn()} />);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /Купить билет/ })); });
  const cover = screen.getByRole("button", { name: "Открыть билет № 101" });
  vi.spyOn(cover, "getBoundingClientRect").mockReturnValue({ left: 0, top: 0, width: 200, height: 85 } as DOMRect);
  fireEvent.pointerDown(cover, { clientX: 0, clientY: 20 });
  expect(document.body.style.position).toBe("fixed");
  fireEvent.pointerMove(cover, { clientX: 190, clientY: 20, buttons: 1 });
  fireEvent.pointerUp(cover, { clientX: 190, clientY: 20 });
  fireEvent.click(cover, { detail: 1 });
  expect(cover).toBeInTheDocument();
  expect(document.body.style.position).toBe("");
  fireEvent.pointerDown(cover, { clientX: 190, clientY: 20 });
  fireEvent.pointerMove(cover, { clientX: 0, clientY: 20, buttons: 1 });
  expect(cover).not.toBeInTheDocument();
  expect(document.body.style.position).toBe("");
  expect(miniAppApi.kasperLivePurchase).toHaveBeenCalledOnce();
});

it("releases a cancelled scratch and viewport lock when unmounted", async () => {
  window.PointerEvent = MouseEvent as typeof PointerEvent;
  const { unmount } = render(<KasperLiveView initData="signed" balance={30_000} onClose={vi.fn()} onSettled={vi.fn()} />);
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: /Купить билет/ })); });
  const cover = screen.getByRole("button", { name: "Открыть билет № 101" });
  fireEvent.pointerDown(cover, { clientX: 10, clientY: 20 });
  fireEvent.pointerCancel(cover);
  expect(document.body.style.position).toBe("");
  expect(cover).toBeInTheDocument();
  fireEvent.pointerDown(cover, { clientX: 10, clientY: 20 });
  unmount();
  expect(document.body.style.position).toBe("");
});
