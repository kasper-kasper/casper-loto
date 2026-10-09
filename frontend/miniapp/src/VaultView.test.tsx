import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { miniAppApi } from "./api";
import { VaultView } from "./VaultView";
vi.mock("./api", () => ({ ApiError: class extends Error {}, miniAppApi: { vaultHistory: vi.fn(), vaultPurchase: vi.fn() } }));
vi.mock("./telegram", () => ({ errorHaptic: vi.fn(), selectionHaptic: vi.fn(), successHaptic: vi.fn() }));
const result = { operation_id: "op", tickets: [
  { id: "one", public_number: 101, symbols: [4,4,4], prize_amount: 10000 },
  { id: "two", public_number: 102, symbols: [1,2,3], prize_amount: 0 },
  { id: "three", public_number: 103, symbols: [2,2,2], prize_amount: 3000 },
], total_cost: 15000, total_prize: 13000, balance_after: 28000, already_processed: false };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(miniAppApi.vaultHistory).mockResolvedValue([]); vi.mocked(miniAppApi.vaultPurchase).mockResolvedValue(result); });
it("buys three once, retains partially unlocked wheel and reveals remaining without buying", async () => {
  const settled=vi.fn(); render(<VaultView initData="signed" balance={30000} onClose={vi.fn()} onSettled={settled} />);
  fireEvent.click(screen.getByRole("button", {name:/3 билета.*Открыть вместе/}));
  await act(async()=>{fireEvent.click(screen.getByRole("button",{name:/Купить 3 билета/}));});
  expect(miniAppApi.vaultPurchase).toHaveBeenCalledWith("signed",3,expect.any(String));
  expect(settled).toHaveBeenCalledWith(result);
  const wheel=screen.getByRole("button",{name:"Повернуть колесо сейфа № 101"});
  for(let i=0;i<3;i++) fireEvent.keyDown(wheel,{key:"ArrowRight"});
  fireEvent.blur(wheel);
  expect(wheel).toHaveTextContent("2 из 5 замков открыто");
  for(let i=0;i<3;i++) fireEvent.keyDown(wheel,{key:"ArrowRight"});
  expect(wheel).not.toBeInTheDocument();
  expect(screen.getAllByRole("button",{name:/Повернуть колесо сейфа/})).toHaveLength(2);
  fireEvent.click(screen.getByRole("button",{name:/Открыть все/}));
  expect(screen.queryByRole("button",{name:/Повернуть колесо сейфа/})).not.toBeInTheDocument();
  expect(screen.getByText("Общий выигрыш").parentElement).toHaveTextContent("13 000");
  expect(miniAppApi.vaultPurchase).toHaveBeenCalledTimes(1);
});
it("retries unknown purchase with original key and quantity",async()=>{
  vi.mocked(miniAppApi.vaultPurchase).mockRejectedValueOnce(new Error("timeout"));
  render(<VaultView initData="signed" balance={30000} onClose={vi.fn()} onSettled={vi.fn()} />);
  await act(async()=>{fireEvent.click(screen.getByRole("button",{name:/Купить билет/}));});
  const key=vi.mocked(miniAppApi.vaultPurchase).mock.calls[0][2];
  expect(screen.getByRole("button",{name:/3 билета.*Открыть вместе/})).toBeDisabled();
  await act(async()=>{fireEvent.click(screen.getByRole("button",{name:/Повторить запрос/}));});
  expect(miniAppApi.vaultPurchase).toHaveBeenLastCalledWith("signed",1,key);
});
it("requires full 15000 balance for three tickets",()=>{
  render(<VaultView initData="signed" balance={14999} onClose={vi.fn()} onSettled={vi.fn()} />);
  fireEvent.click(screen.getByRole("button",{name:/3 билета.*Открыть вместе/}));
  expect(screen.getByRole("button",{name:/Купить 3 билета/})).toBeDisabled();
});
