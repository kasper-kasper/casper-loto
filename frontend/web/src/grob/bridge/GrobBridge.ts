import type { GrobIntent, GrobSnapshot, Unsubscribe } from "./contracts";

export class GrobBridge {
  private snapshots = new Set<(value: GrobSnapshot) => void>();
  private intents = new Set<(value: GrobIntent) => void>();
  private last: GrobSnapshot | null = null;
  private disposed = false;

  publish(value: GrobSnapshot) {
    if (this.disposed || (this.last && value.revision <= this.last.revision)) return;
    this.last = value;
    this.snapshots.forEach(listener => listener(value));
  }
  subscribeSnapshot(listener: (value: GrobSnapshot) => void): Unsubscribe {
    if (this.disposed) return () => undefined;
    this.snapshots.add(listener);
    if (this.last) listener(this.last);
    return () => this.snapshots.delete(listener);
  }
  emitIntent(value: GrobIntent) { if (!this.disposed) this.intents.forEach(listener => listener(value)); }
  subscribeIntent(listener: (value: GrobIntent) => void): Unsubscribe {
    if (this.disposed) return () => undefined;
    this.intents.add(listener);
    return () => this.intents.delete(listener);
  }
  dispose() { this.disposed = true; this.last = null; this.snapshots.clear(); this.intents.clear(); }
}

