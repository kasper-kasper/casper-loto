export interface PendingGrobPurchase {
  key: string;
  userId: string;
  drawNumber: number;
  price: number;
  mode: "manual" | "quick";
  combinations: number[][];
  quantity: 1 | 5 | 25;
  createdAt: string;
}

const keyFor = (userId: string) => `casper:grob:pending:${userId}`;
export function loadPendingPurchase(userId: string): PendingGrobPurchase | null {
  try { const raw = sessionStorage.getItem(keyFor(userId)); return raw ? JSON.parse(raw) as PendingGrobPurchase : null; }
  catch { return null; }
}
export function savePendingPurchase(value: PendingGrobPurchase) { sessionStorage.setItem(keyFor(value.userId), JSON.stringify(value)); }
export function clearPendingPurchase(userId: string) { sessionStorage.removeItem(keyFor(userId)); }

