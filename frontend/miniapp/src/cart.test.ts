import { CART_MAX_TICKETS, loadCart, saveCart } from "./cart";

describe("cart persistence", () => {
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
