import type { CartTicket } from "./types";

const STORAGE_KEY = "k-loto:weekly-cart:v1";

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
  if (ttlSeconds === null) return [];
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as StoredCart | null;
    if (!value || value.expiresAt <= now || !Array.isArray(value.tickets)) {
      localStorage.removeItem(STORAGE_KEY);
      return [];
    }
    return value.tickets;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return [];
  }
}

export function saveCart(
  tickets: CartTicket[],
  ttlSeconds: number | null,
  now = Date.now(),
): void {
  if (ttlSeconds === null || tickets.length === 0) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  const value: StoredCart = {
    expiresAt: now + ttlSeconds * 1000,
    tickets,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
}
