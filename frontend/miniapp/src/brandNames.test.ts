import { afterEach, expect, it, vi } from "vitest";
import { brandViewData, displayBrandName } from "../../shared/brandNames";
import { miniAppApi } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("uses the approved spelling while retaining individual lottery identities", () => {
  expect(["Kasper Grand", "Kasper Bingo", "Kasper Fast", "KASPER LIVE", "Caster Loto", "Casper Lotto", "K-Loto", "ПЛЛ-Лото", "Каспер Лото", "6 из 36", "ГРОБ", "Casper Ball", "CODE"].map(displayBrandName))
    .toEqual(["Casper Grand", "Casper Bingo", "Casper Fast", "CASPER LIVE", "Casper Loto", "Casper Loto", "Casper Loto", "2:22", "Каспер Лото", "6 из 36", "ГРОБ", "Casper Ball", "CODE"]);
});

it("changes labels without mutating records, identifiers, people or financial values", () => {
  const original = { lotteries: [{ code: "bingo", name: "Kasper Bingo", jackpot: 10_000 }], ticket: { id: "kasper-live", lottery_name: "Kasper Grand", numbers: [1, 2, 3], prize_amount: 48_000 }, favorite_lottery_name: "ПЛЛ-лото", user: { code: "user", name: "Kasper", display_name: "Kasper", username: "Kasper" }, csrf_token: "Kasper-secret", audit: { reason: "Kasper Grand", message: "Kasper" } };
  const result = brandViewData(original);
  expect(result.lotteries[0].name).toBe("Casper Bingo");
  expect(result.ticket).toEqual({ ...original.ticket, lottery_name: "Casper Grand" });
  expect(result.favorite_lottery_name).toBe("2:22");
  expect(result.user).toEqual(original.user);
  expect(result.csrf_token).toBe(original.csrf_token);
  expect(result.audit).toEqual(original.audit);
  expect(original.lotteries[0].name).toBe("Kasper Bingo");
  expect(brandViewData(null)).toBeNull();
});

it("formats notification display text but preserves the stored payload source", () => {
  const notification = { id: "notice", type: "JACKPOT_NEWS", title: "Kasper Grand", body: "Джекпот Kasper Bingo", payload: { lottery_name: "Kasper Bingo", operation_id: "kasper-live" } };
  expect(brandViewData(notification)).toEqual({ ...notification, title: "Casper Grand", body: "Джекпот Casper Bingo", payload: { lottery_name: "Casper Bingo", operation_id: "kasper-live" } });
  expect(notification.payload.lottery_name).toBe("Kasper Bingo");
});

it("applies approved aliases to Mini App responses", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ lotteries: [{ code: "weekly", name: "Kasper Grand" }], lottery_name: "Kasper Bingo", display_name: "Kasper" }), { status: 200 })));
  const results = [await miniAppApi.dashboard("signed")];
  for (const result of results) {
    expect(result).toEqual({ lotteries: [{ code: "weekly", name: "Casper Grand" }], lottery_name: "Casper Bingo", display_name: "Kasper" });
  }
});

it("normalizes streamed live names as well as ordinary HTTP responses", async () => {
  const body = new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode('data: {"latest_completed":{"lottery_name":"Kasper Grand"}}\n\n')); controller.close(); } });
  vi.stubGlobal("fetch", vi.fn(async () => new Response(body)));
  const snapshot = vi.fn();
  await miniAppApi.liveStream("signed", snapshot, new AbortController().signal);
  expect(snapshot).toHaveBeenCalledWith({ latest_completed: { lottery_name: "Casper Grand" } });
});
