import { tr } from "./i18n";
import { displayBrandName } from "../../shared/brandNames";
import type { CartTicket } from "./types";

const STORAGE_KEY = "k-loto:cart:v2";
const PURCHASED_KEY = "k-loto:cart:purchased:v1";
const PURCHASED_PREFIX = "k-loto:cart:purchased:v2:";
export const CART_MAX_TICKETS = 1_000;

interface StoredCart {
  expiresAt: number;
  tickets: CartTicket[];
}

function purchasedIds(ttlSeconds: number | null, now: number): Record<string, number> {
  const storage = ttlSeconds === null ? sessionStorage : localStorage;
  const entries = JSON.parse(storage.getItem(PURCHASED_KEY) ?? "{}") as Record<string, number>;
  return Object.fromEntries(Object.entries(entries).filter(([, expiry]) => Number.isFinite(expiry) && expiry > now));
}

export function markCartPurchased(ids: string[]): void {
  // Each position has its own shared marker, avoiding lost read/modify/write
  // updates across players and protecting duplicated session-only carts.
  // Display TTL cannot make a purchased ID reusable in a stale, still-open tab.
  for (const id of ids) localStorage.setItem(PURCHASED_PREFIX + id, "1");
}

export function containsPurchasedCartIds(ids: string[], ttlSeconds: number | null): boolean {
  return filterPurchasedCartTickets(ids.map(id => ({ id })), ttlSeconds).length !== ids.length;
}

export function filterPurchasedCartTickets<T extends { id: string }>(tickets: T[], ttlSeconds: number | null, now = Date.now()): T[] {
  const consumed = purchasedIds(ttlSeconds, now);
  return tickets.filter(ticket => {
    const key = PURCHASED_PREFIX + ticket.id;
    const raw = localStorage.getItem(key);
    if (raw === null) return !consumed[ticket.id];
    if (raw !== "1") throw new Error(tr("Не удалось проверить купленные позиции корзины."));
    return false;
  });
}

export function isCartPurchaseMarker(key: string | null): boolean {
  return key === null || key === PURCHASED_KEY || key.startsWith(PURCHASED_PREFIX);
}

export function configuredCartTtl(): number | null {
  const raw = import.meta.env.VITE_CART_TTL_SECONDS;
  if (!raw) return null;
  const value = Number(raw);
  return Number.isInteger(value) && value > 0 ? value : null;
}

export function loadCart(ttlSeconds: number | null, now = Date.now()): CartTicket[] {
  const storage = ttlSeconds === null ? sessionStorage : localStorage;
  try {
    const value = JSON.parse(storage.getItem(STORAGE_KEY) ?? "null") as StoredCart | null;
    if (!value || (ttlSeconds !== null && value.expiresAt <= now) || !Array.isArray(value.tickets)) {
      storage.removeItem(STORAGE_KEY);
      return [];
    }
    return filterPurchasedCartTickets(value.tickets, ttlSeconds, now).slice(0, CART_MAX_TICKETS).map((ticket) => ({
      ...ticket,
      lotteryName: typeof ticket.lotteryName === "string" ? displayBrandName(ticket.lotteryName) : ticket.lotteryName,
      drawCount: ticket.drawCount === 5 ? 5 : 1,
    }));
  } catch {
    storage.removeItem(STORAGE_KEY);
    return [];
  }
}

export function saveCart(
  tickets: CartTicket[],
  ttlSeconds: number | null,
  now = Date.now(),
): void {
  const storage = ttlSeconds === null ? sessionStorage : localStorage;
  tickets = filterPurchasedCartTickets(tickets, ttlSeconds, now);
  if (tickets.length === 0) {
    storage.removeItem(STORAGE_KEY);
    return;
  }
  const value: StoredCart = {
    expiresAt: ttlSeconds === null ? Number.MAX_SAFE_INTEGER : now + ttlSeconds * 1000,
    tickets,
  };
  storage.setItem(STORAGE_KEY, JSON.stringify(value));
}
