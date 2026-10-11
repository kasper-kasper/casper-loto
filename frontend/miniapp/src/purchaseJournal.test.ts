import { durablePurchase, readPurchase, setPurchaseOwner, completePurchase } from "./purchaseJournal";
import { loadCart, saveCart } from "./cart";
import type { PurchaseResult } from "./types";

const receipt: PurchaseResult = { operation_id: "op", draw_id: "draw", draw_ids: ["draw"], draw_count: 1, ticket_ids: ["ticket"], total_cost: 100, balance_after: 900, already_processed: true };
const path = "/api/v1/miniapp/lotteries/daily/purchases";
const body = JSON.stringify({ idempotency_key: "m1-request", combinations: [[1, 2, 3, 4]], expected_scheduled_at: "2026-10-11T12:00:00Z" });
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); setPurchaseOwner("owner"); });

it("stores a request before sending and keeps it after a lost response", async () => {
  const send = vi.fn(async () => { expect(readPurchase()?.body).toBe(body); throw new TypeError("offline"); });
  await expect(durablePurchase(path, body, send, () => false)).rejects.toThrow("offline");
  expect(readPurchase()).toMatchObject({ key: "m1-request", body, uncertain: true });
  setPurchaseOwner("owner");
  expect(readPurchase()?.key).toBe("m1-request");
});

it("blocks a new purchase until the old request is resolved", async () => {
  await durablePurchase(path, body, async () => { throw new Error("offline"); }, () => false).catch(() => undefined);
  const send = vi.fn();
  await expect(durablePurchase(path, body.replace("m1-request", "m1-new"), send, () => false)).rejects.toThrow("предыдущей");
  expect(send).not.toHaveBeenCalled();
});

it("retries exactly the saved request and clears it after a receipt", async () => {
  await durablePurchase(path, body, async () => { throw new Error("offline"); }, () => false).catch(() => undefined);
  expect(await durablePurchase(path, body, async () => receipt, () => false)).toEqual(receipt);
  expect(readPurchase()).toBeNull();
});

it("does not forget an ambiguous purchase after a later rate limit", async () => {
  await durablePurchase(path, body, async () => { throw new Error("offline"); }, () => false).catch(() => undefined);
  await durablePurchase(path, body, async () => { throw new Error("limited"); }, () => true).catch(() => undefined);
  expect(readPurchase()?.uncertain).toBe(true);
});

it("isolates journals by verified player identity", async () => {
  await durablePurchase(path, body, async () => { throw new Error("offline"); }, () => false).catch(() => undefined);
  setPurchaseOwner("other"); expect(readPurchase()).toBeNull();
  setPurchaseOwner("owner"); expect(readPurchase()?.key).toBe("m1-request");
});

it("does not send if durable storage is unavailable", async () => {
  const set = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("storage blocked"); });
  const send = vi.fn();
  await expect(durablePurchase(path, body, send, () => false)).rejects.toThrow("storage blocked");
  expect(send).not.toHaveBeenCalled(); set.mockRestore();
});

it("removes bought cart entries and prevents a stale tab from saving them again", async () => {
  const ticket = { id: "cart-one", lotteryCode: "daily", lotteryName: "Casper Daily", price: 100, numbers: [1, 2, 3, 4], drawCount: 1 as const };
  saveCart([ticket], null);
  await durablePurchase(path, body, async () => { throw new Error("offline"); }, () => false, [ticket.id]).catch(() => undefined);
  completePurchase(readPurchase()!, receipt, true);
  expect(loadCart(null)).toEqual([]);
  saveCart([ticket], null); expect(loadCart(null)).toEqual([]);
  const send = vi.fn();
  await expect(durablePurchase(path, body.replace("m1-request", "m1-new"), send, () => false, [ticket.id])).rejects.toThrow("уже куплена");
  expect(send).not.toHaveBeenCalled();
});
