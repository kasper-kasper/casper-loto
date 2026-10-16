import { act, render, screen } from "@testing-library/react";
import { adminApi } from "./api";
import { OperationalMonitor } from "./OperationalMonitor";

vi.mock("./api", () => ({ adminApi: { monitoring: vi.fn() } }));

it("shows operational warnings and real timing percentiles", async () => {
  vi.useFakeTimers();
  try {
  vi.mocked(adminApi.monitoring).mockResolvedValue({ metrics: { purchase_client: { count: 12, errors: 1, p50_ms: 120, p95_ms: 2200 } }, operations: { checked_at: "2026-10-11T12:00:00Z", warnings: ["slow_purchase_client"], disk_used_percent: 41, disk_free_bytes: 20 * 1024 ** 3, backup_count: 7, backup_age_seconds: 3600 } });
  await act(async () => { render(<OperationalMonitor />); });
  expect(screen.getByText(/Игроки долго ждут покупку/)).toBeInTheDocument();
  expect(screen.getByText("2200 мс")).toBeInTheDocument();
  expect(screen.getByText("7 из 7")).toBeInTheDocument();
  await act(async () => { await vi.advanceTimersByTimeAsync(300_000); });
  expect(adminApi.monitoring).toHaveBeenCalledOnce();
  } finally { vi.useRealTimers(); }
});
