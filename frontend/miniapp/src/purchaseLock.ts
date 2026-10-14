const busyMessage = "Покупка уже проверяется в другом окне. Дождитесь результата.";
const databaseName = "k-loto:purchase-locks:v1";
const storeName = "leases";
// A closed tab cannot hold the fallback forever. The durable journal still
// fences a different request after expiry; same-key retries are server-idempotent.
const leaseMilliseconds = 60_000;

interface Lease { token: string; expiresAt: number }

function openLocks(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(databaseName, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(storeName);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error("Не удалось защитить покупку в браузере. Проверьте доступ к хранилищу."));
  });
}

async function withLease<T>(name: string, run: () => Promise<T>): Promise<T> {
  if (typeof indexedDB === "undefined") {
    throw new Error("Браузер не позволяет защитить покупку. Откройте Mini App заново в Telegram.");
  }
  const database = await openLocks();
  const token = crypto.randomUUID();
  try {
    await new Promise<void>((resolve, reject) => {
      const transaction = database.transaction(storeName, "readwrite");
      const store = transaction.objectStore(storeName);
      const request = store.get(name);
      let busy = false;
      request.onsuccess = () => {
        const lease = request.result as Lease | undefined;
        if (lease && lease.expiresAt > Date.now()) {
          busy = true;
          transaction.abort();
        } else store.put({ token, expiresAt: Date.now() + leaseMilliseconds }, name);
      };
      transaction.oncomplete = () => resolve();
      transaction.onabort = () => reject(new Error(busy ? busyMessage : "Не удалось сохранить защиту покупки."));
      transaction.onerror = () => reject(new Error("Не удалось сохранить защиту покупки."));
    });
    try {
      return await run();
    } finally {
      await new Promise<void>((resolve, reject) => {
        const transaction = database.transaction(storeName, "readwrite");
        const store = transaction.objectStore(storeName);
        const request = store.get(name);
        request.onsuccess = () => {
          if ((request.result as Lease | undefined)?.token === token) store.delete(name);
        };
        transaction.oncomplete = () => resolve();
        transaction.onabort = transaction.onerror = () => reject(new Error("Не удалось освободить защиту покупки."));
      }).catch(() => {
        // Expiry releases a failed cleanup; keep the confirmed receipt/result.
      });
    }
  } finally { database.close(); }
}

export async function withPurchaseLock<T>(ownerId: string, run: () => Promise<T>): Promise<T> {
  const name = `k-loto:purchase:${ownerId}`;
  if (navigator.locks?.request) {
    return await navigator.locks.request(name, { ifAvailable: true }, lock => {
      if (!lock) throw new Error(busyMessage);
      return run();
    });
  }
  return withLease(name, run);
}
