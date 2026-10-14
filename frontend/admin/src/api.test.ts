import { adminApi } from "./api";

afterEach(() => vi.unstubAllGlobals());

it("requests operational monitoring at the real admin endpoint with credentials", async () => {
  const snapshot = { metrics: {}, operations: { checked_at: "2026-10-14T12:00:00Z", warnings: [] } };
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(snapshot), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  expect(await adminApi.monitoring()).toEqual(snapshot);
  expect(fetchMock).toHaveBeenCalledOnce();
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/admin/monitoring", expect.objectContaining({ credentials: "include" }));
});

it("applies approved aliases inside Admin without importing another client", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify([{ code: "weekly", name: "Kasper Grand" }]), { status: 200 })));
  expect(await adminApi.lotteries()).toEqual([{ code: "weekly", name: "Casper Grand" }]);
});
