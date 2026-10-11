import { configuredCartTtl, containsPurchasedCartIds, loadCart, markCartPurchased, saveCart } from "./cart";
import type { InstantPurchaseResult, PurchaseResult } from "./types";

export type Receipt = PurchaseResult | InstantPurchaseResult;
export interface PurchaseResolution { path: string; receipt: Receipt | null; cartIds: string[] }
export interface PendingPurchase {
  ownerId: string;
  key: string;
  path: string;
  body: string;
  cartIds: string[];
  uncertain: boolean;
  receipt?: Receipt;
}
let owner: string | null = null;
let active = false;
const prefix = "k-loto:purchase:v1:";
export const journalEvent = "k-loto:purchase-changed";
export const recoveredEvent = "k-loto:purchase-recovered";

export function setPurchaseOwner(value: string): void {
  owner = value;
  window.dispatchEvent(new Event(journalEvent));
}
export function purchaseActive(): boolean { return active; }
export function readPurchase(): PendingPurchase | null {
  if (!owner) return null;
  const raw = localStorage.getItem(prefix + owner);
  if (!raw) return null;
  const value = JSON.parse(raw) as PendingPurchase;
  const body = JSON.parse(value.body) as { idempotency_key?: string };
  if (!/^\/api\/v1\/miniapp\/(?:lotteries\/[a-z0-9-]+|bingo|kasper-live|aurora|vault)\/purchases$/.test(value.path)
    || typeof value.key !== "string" || body.idempotency_key !== value.key
    || value.ownerId !== owner || !Array.isArray(value.cartIds)) throw new Error("Не удалось прочитать незавершённую покупку. Обратитесь в поддержку.");
  return value;
}
function writePurchase(value: PendingPurchase): void {
  if (!owner) throw new Error("Дождитесь загрузки аккаунта перед покупкой.");
  localStorage.setItem(prefix + value.ownerId, JSON.stringify(value));
  window.dispatchEvent(new Event(journalEvent));
}
export function receiptGame(value: PendingPurchase): string {
  return ["kasper-live", "aurora", "vault"].find(game => value.path.endsWith(`/${game}/purchases`)) ?? "scheduled";
}
export function completePurchase(value: PendingPurchase, receipt: Receipt, recovered = false): void {
  // Keep the receipt until cart cleanup is durable; a reload can resume this step.
  writePurchase({ ...value, receipt });
  const ids = new Set(value.cartIds);
  const ttl = configuredCartTtl();
  if (ids.size) {
    markCartPurchased(value.cartIds, ttl);
    saveCart(loadCart(ttl).filter(ticket => !ids.has(ticket.id)), ttl);
  }
  localStorage.removeItem(prefix + value.ownerId);
  if (recovered && owner === value.ownerId) window.dispatchEvent(new CustomEvent<PurchaseResolution>(recoveredEvent, { detail: { path: value.path, receipt, cartIds: value.cartIds } }));
  window.dispatchEvent(new Event(journalEvent));
}

export async function durablePurchase<T extends Receipt>(
  path: string, body: string, send: () => Promise<T>, definitive: (reason: unknown) => boolean,
  cartIds: string[] = [],
): Promise<T> {
  const previous = readPurchase();
  if (!previous && cartIds.length && containsPurchasedCartIds(cartIds, configuredCartTtl())) {
    throw new Error("Часть позиций уже куплена. Корзина обновлена — проверьте оставшиеся билеты.");
  }
  const key = (JSON.parse(body) as { idempotency_key: string }).idempotency_key;
  if (previous && (previous.key !== key || previous.path !== path || previous.body !== body)) {
    throw new Error("Сначала проверьте результат предыдущей покупки — она могла уже пройти.");
  }
  if (active) throw new Error("Покупка уже проверяется. Дождитесь результата.");
  if (!owner) throw new Error("Дождитесь загрузки аккаунта перед покупкой.");
  const pending = previous ?? { ownerId: owner, path, body, key, cartIds, uncertain: false };
  // No request is sent if storage is unavailable.
  active = true;
  try {
    writePurchase(pending);
    // Also arbitrate old clients without Web Locks: only the surviving journal may send.
    await new Promise(resolve => window.setTimeout(resolve, 40));
    if (readPurchase()?.key !== key) throw new Error("Покупка уже начата в другом окне.");
    const result = await send();
    completePurchase(pending, result);
    return result;
  } catch (reason) {
    if (readPurchase()?.key === key) {
      if (!pending.uncertain && definitive(reason)) {
        localStorage.removeItem(prefix + pending.ownerId);
      } else writePurchase({ ...pending, uncertain: true });
    }
    throw reason;
  } finally {
    active = false;
    window.dispatchEvent(new Event(journalEvent));
  }
}
