import { tr } from "./i18n";
import { configuredCartTtl, containsPurchasedCartIds, loadCart, markCartPurchased, saveCart } from "./cart";
import { withPurchaseLock } from "./purchaseLock";
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
async function withActiveLock<T>(ownerId: string, run: () => Promise<T>): Promise<T> {
  if (active) throw new Error(tr("Покупка уже проверяется. Дождитесь результата."));
  active = true;
  try { return await withPurchaseLock(ownerId, run); }
  finally { active = false; window.dispatchEvent(new Event(journalEvent)); }
}
export function readPurchase(): PendingPurchase | null {
  return owner ? readForOwner(owner) : null;
}
function readForOwner(ownerId: string): PendingPurchase | null {
  const raw = localStorage.getItem(prefix + ownerId);
  if (!raw) return null;
  const value = JSON.parse(raw) as PendingPurchase;
  const body = JSON.parse(value.body) as { idempotency_key?: string };
  if (!/^\/api\/v1\/miniapp\/(?:lotteries\/[a-z0-9-]+|bingo|kasper-live|aurora|vault)\/purchases$/.test(value.path)
    || typeof value.key !== "string" || body.idempotency_key !== value.key
    || value.ownerId !== ownerId || !Array.isArray(value.cartIds)) throw new Error(tr("Не удалось прочитать незавершённую покупку. Обратитесь в поддержку."));
  return value;
}
function writePurchase(value: PendingPurchase): void {
  if (!owner) throw new Error(tr("Дождитесь загрузки аккаунта перед покупкой."));
  localStorage.setItem(prefix + value.ownerId, JSON.stringify(value));
  window.dispatchEvent(new Event(journalEvent));
}
export function receiptGame(value: PendingPurchase): string {
  return ["kasper-live", "aurora", "vault"].find(game => value.path.endsWith(`/${game}/purchases`)) ?? "scheduled";
}
export function completePurchase(value: PendingPurchase, receipt: Receipt, recovered = false): Promise<void> {
  return withActiveLock(value.ownerId, async () => finishPurchase(value, receipt, recovered));
}
function finishPurchase(value: PendingPurchase, receipt: Receipt, recovered = false): void {
  // A response from an older tab must never overwrite a newer request journal.
  if (readForOwner(value.ownerId)?.key !== value.key) return;
  // Keep the receipt until cart cleanup is durable; a reload can resume this step.
  writePurchase({ ...value, receipt });
  const ids = new Set(value.cartIds);
  const ttl = configuredCartTtl();
  if (ids.size) {
    markCartPurchased(value.cartIds);
    saveCart(loadCart(ttl).filter(ticket => !ids.has(ticket.id)), ttl);
  }
  localStorage.removeItem(prefix + value.ownerId);
  if (recovered && owner === value.ownerId) window.dispatchEvent(new CustomEvent<PurchaseResolution>(recoveredEvent, { detail: { path: value.path, receipt, cartIds: value.cartIds } }));
  window.dispatchEvent(new Event(journalEvent));
}

export async function cancelPurchase(
  value: PendingPurchase,
  send: () => Promise<{ cancelled: boolean; receipt: Receipt | null }>,
): Promise<{ cancelled: boolean; receipt: Receipt | null }> {
  return withActiveLock(value.ownerId, async () => {
    if (readForOwner(value.ownerId)?.key !== value.key) throw new Error(tr("Покупка уже проверена в другом окне. Обновите её состояние."));
    const response = await send();
    if (!response.receipt && response.cancelled && readForOwner(value.ownerId)?.key === value.key) {
      localStorage.removeItem(prefix + value.ownerId);
      window.dispatchEvent(new Event(journalEvent));
      if (owner === value.ownerId) window.dispatchEvent(new CustomEvent<PurchaseResolution>(recoveredEvent, { detail: { path: value.path, receipt: null, cartIds: [] } }));
    }
    return response;
  });
}

export async function durablePurchase<T extends Receipt>(
  path: string, body: string, send: () => Promise<T>, definitive: (reason: unknown) => boolean,
  cartIds: string[] = [], recovered = false,
): Promise<T> {
  if (!owner) throw new Error(tr("Дождитесь загрузки аккаунта перед покупкой."));
  const ownerId = owner;
  return withActiveLock(ownerId, async () => {
    if (owner !== ownerId) throw new Error(tr("Аккаунт изменился. Обновите страницу перед покупкой."));
    // Recheck shared state inside the cross-tab lock, immediately before sending.
    const previous = readForOwner(ownerId);
    if (!previous && cartIds.length && containsPurchasedCartIds(cartIds, configuredCartTtl())) {
      throw new Error(tr("Часть позиций уже куплена. Корзина обновлена — проверьте оставшиеся билеты."));
    }
    const key = (JSON.parse(body) as { idempotency_key: string }).idempotency_key;
    if (previous && (previous.key !== key || previous.path !== path || previous.body !== body)) {
      throw new Error(tr("Сначала проверьте результат предыдущей покупки — она могла уже пройти."));
    }
    const pending = previous ?? { ownerId, path, body, key, cartIds, uncertain: false };
    try {
      // No request is sent if durable storage is unavailable.
      writePurchase(pending);
      const result = await send();
      finishPurchase(pending, result, recovered);
      return result;
    } catch (reason) {
      const current = readForOwner(ownerId);
      if (current?.key === key) {
        if (!current.uncertain && !current.receipt && definitive(reason)) localStorage.removeItem(prefix + ownerId);
        else writePurchase({ ...current, uncertain: true });
      }
      throw reason;
    }
  });
}
