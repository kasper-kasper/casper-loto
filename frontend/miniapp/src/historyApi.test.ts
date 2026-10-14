import { afterEach, expect, it, vi } from "vitest";

import { miniAppApi } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("encodes an opaque history cursor without sending a growing offset", async () => {
  const request = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>().mockResolvedValue(new Response(JSON.stringify({ tickets: [], total: 0, has_more: false }), { status: 200 }));
  vi.stubGlobal("fetch", request);
  await miniAppApi.tickets("signed", "history", "scope:standard", true, "boundary/+==");
  const query = new URL(String(request.mock.calls[0][0]), "https://test.local").searchParams;
  expect(query.get("cursor")).toBe("boundary/+==");
  expect(query.has("offset")).toBe(false);
  expect(query.get("wins_only")).toBe("true");
  expect(query.get("scope")).toBe("standard");
});
