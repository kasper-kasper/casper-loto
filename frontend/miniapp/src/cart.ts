import { displayBrandName } from "../../shared/brandNames";
import type { CartTicket } from "./types";

const STORAGE_KEY = "k-loto:cart:v2";
export const CART_MAX_TICKETS = 1_000;

interface StoredCart {
  expiresAt: number;
  tickets: CartTicket[];
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
    return value.tickets.slice(0, CART_MAX_TICKETS).map((ticket) => ({
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
