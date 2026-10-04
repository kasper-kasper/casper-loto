/** Presentation aliases from docs/brand.md. Never apply to IDs or user text. */
const lotteryCodes = new Set(["weekly", "daily", "pll", "pss", "khan", "september", "grob", "flash", "shadow", "pulse", "bingo", "dual", "kasper-live"]);

export function displayBrandName(value: string): string {
  return value
    .replace(/\b(?:Kasper|Caster|Casper)\s+Lotto\b/gi, "Casper Loto")
    .replace(/\bK-Loto\b/gi, "Casper Loto")
    .replace(/\b(?:Kasper|Caster)\b/gi, (name) => name === name.toUpperCase() ? "CASPER" : "Casper")
    .replace(/ПЛЛ-лото/gi, "2:22");
}

/** Clone response view data, changing only declared lottery labels/notifications. */
export function brandViewData<T>(value: T): T {
  if (Array.isArray(value)) return value.map(item => brandViewData(item)) as T;
  if (!value || typeof value !== "object") return value;
  const record = value as Record<string, unknown>;
  const notification = typeof record.id === "string" && typeof record.body === "string"
    && ["WIN", "DRAW_RESULT", "DRAW_INVITATION", "JACKPOT_NEWS"].includes(String(record.type));
  return Object.fromEntries(Object.entries(record).map(([key, item]) => {
    const label = key === "lottery_name" || key === "favorite_lottery_name" || key === "lotteryName"
      || (key === "name" && typeof record.code === "string" && lotteryCodes.has(record.code))
      || (notification && (key === "title" || key === "body"));
    return [key, label && typeof item === "string" ? displayBrandName(item) : brandViewData(item)];
  })) as T;
}
