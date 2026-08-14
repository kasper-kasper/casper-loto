import { loadCart, saveCart } from "./cart";

describe("cart persistence", () => {
  it("restores tickets before the configured expiration", () => {
    const tickets = [{ id: "one", numbers: [1, 2, 3, 4, 5] }];
    saveCart(tickets, 300, 1_000);

    expect(loadCart(300, 300_000)).toEqual(tickets);
  });

  it("removes an expired cart", () => {
    saveCart([{ id: "one", numbers: [1, 2, 3, 4, 5] }], 300, 1_000);

    expect(loadCart(300, 301_001)).toEqual([]);
    expect(localStorage.length).toBe(0);
  });

  it("does not persist without an owner-configured TTL", () => {
    saveCart([{ id: "one", numbers: [1, 2, 3, 4, 5] }], null, 1_000);

    expect(loadCart(null, 2_000)).toEqual([]);
    expect(localStorage.length).toBe(0);
  });
});
