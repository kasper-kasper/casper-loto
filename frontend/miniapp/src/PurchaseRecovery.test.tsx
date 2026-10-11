import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PurchaseRecovery } from "./PurchaseRecovery";
import { durablePurchase, readPurchase, setPurchaseOwner } from "./purchaseJournal";

const path = "/api/v1/miniapp/lotteries/daily/purchases";
const body = JSON.stringify({ idempotency_key: "m1-lost", combinations: [[1, 2, 3, 4]], expected_scheduled_at: "2026-10-11T12:00:00Z" });
const receipt = { operation_id: "op", draw_id: "draw", draw_ids: ["draw"], draw_count: 1, ticket_ids: ["one"], total_cost: 100, balance_after: 900, already_processed: true };
beforeEach(async () => {
  localStorage.clear(); sessionStorage.clear(); setPurchaseOwner("user");
  await durablePurchase(path, body, async () => { throw new Error("offline"); }, () => false).catch(() => undefined);
});
afterEach(() => vi.unstubAllGlobals());

it("recovers a committed purchase after reopening without making a new POST", async () => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ receipt }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<PurchaseRecovery initData="signed" />);
  expect(await screen.findByText("Покупка найдена")).toBeInTheDocument();
  expect(readPurchase()).toBeNull();
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(fetchMock.mock.calls[0][0]).toContain("/purchase-receipts/m1-lost?game=scheduled");
  expect(fetchMock.mock.calls[0][1].method).toBeUndefined();
});

it("cancels only through the server fence and keeps the journal until it succeeds", async () => {
  const fetchMock = vi.fn().mockImplementation(async (url: string) => new Response(JSON.stringify(url.includes("/cancel?") ? { cancelled: true, receipt: null } : { receipt: null }), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  render(<PurchaseRecovery initData="signed" />);
  fireEvent.click(await screen.findByRole("button", { name: "Отменить неподтверждённую покупку" }));
  await waitFor(() => expect(readPurchase()).toBeNull());
  expect(fetchMock.mock.calls.some(call => call[0].includes("/cancel?") && call[1].method === "POST")).toBe(true);
});
