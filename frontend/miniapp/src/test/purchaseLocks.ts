import { vi } from "vitest";

export function mockPurchaseLocks(): void {
  const held = new Set<string>();
  Object.defineProperty(navigator, "locks", { configurable: true, value: {
    request: vi.fn(async (name: string, _options: LockOptions, callback: (lock: Lock | null) => unknown) => {
      if (held.has(name)) return callback(null);
      held.add(name);
      try { return await callback({ name, mode: "exclusive" } as Lock); }
      finally { held.delete(name); }
    }),
  } });
}
