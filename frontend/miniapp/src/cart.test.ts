import { CART_MAX_TICKETS, loadCart, markCartPurchased, saveCart } from "./cart";

beforeEach(() => { sessionStorage.clear(); localStorage.clear(); });

describe("cart persistence", () => {
  it("does not resurrect purchased positions when a stale cart is saved after its TTL", () => {
    const ticket = { id: "purchased-before-ttl", lotteryCode: "weekly", lotteryName: "Weekly", price: 100, numbers: [1, 2, 3, 4, 5], drawCount: 1 as const };
    saveCart([ticket], 300, 1_000);
    markCartPurchased([ticket.id]);
    saveCart([ticket], 300, 1_000_000);
    expect(loadCart(300, 1_000_001)).toEqual([]);
  });

  it("honors existing session purchase markers from the previous client", () => {
    const ticket = { id: "legacy-purchased", lotteryCode: "weekly", lotteryName: "Weekly", price: 100, numbers: [1, 2, 3, 4, 5], drawCount: 1 as const };
    sessionStorage.setItem("k-loto:cart:purchased:v1", JSON.stringify({ [ticket.id]: Number.MAX_SAFE_INTEGER }));
    saveCart([ticket], null, 1_000);
    expect(loadCart(null, 2_000)).toEqual([]);
  });
  it("displays a legacy brand label without changing saved ticket data", () => {
    const ticket = { id: "legacy", lotteryCode: "weekly", lotteryName: "Kasper Grand", price: 50_000, numbers: [1, 2, 3, 4, 5, 36, 37], drawCount: 5 as const };
    saveCart([ticket], null, 1_000);
    expect(loadCart(null, 2_000)).toEqual([{ ...ticket, lotteryName: "Casper Grand" }]);
    expect(sessionStorage.getItem("k-loto:cart:v2")).toContain("Kasper Grand");
  });

  it("restores tickets before the configured expiration", () => {
    const tickets = [{ id: "one", lotteryCode: "weekly", lotteryName: "ЛСД-лото", price: 100, numbers: [1, 2, 3, 4, 5], drawCount: 1 as const }];
    saveCart(tickets, 300, 1_000);

    expect(loadCart(300, 300_000)).toEqual(tickets);
  });

  it("removes an expired cart", () => {
    saveCart([{ id: "one", lotteryCode: "weekly", lotteryName: "ЛСД-лото", price: 100, numbers: [1, 2, 3, 4, 5], drawCount: 1 }], 300, 1_000);

    expect(loadCart(300, 301_001)).toEqual([]);
    expect(localStorage.length).toBe(0);
  });

  it("survives a safe reload in the current tab without a configured TTL", () => {
    saveCart([{ id: "one", lotteryCode: "weekly", lotteryName: "ЛСД-лото", price: 100, numbers: [1, 2, 3, 4, 5], drawCount: 1 }], null, 1_000);

    expect(loadCart(null, 2_000)).toHaveLength(1);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(1);
  });

  it("never restores more than the cart safety limit", () => {
    const tickets = Array.from({ length: CART_MAX_TICKETS + 5 }, (_, index) => ({ id: String(index), lotteryCode: "weekly", lotteryName: "ЛСД-лото", price: 100, numbers: [1, 2, 3, 4, 5], drawCount: 1 as const }));
    saveCart(tickets, 300, 1_000);

    expect(loadCart(300, 2_000)).toHaveLength(CART_MAX_TICKETS);
  });
});
