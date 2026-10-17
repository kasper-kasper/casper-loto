import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { EconomyPanel } from "./EconomyPanel";
import { adminApi } from "./api";
import type { EconomyDay, EconomyReport } from "./types";

vi.mock("./api", () => ({ adminApi: { economy: vi.fn() } }));
const day: EconomyDay = { day: "2026-10-18", included: true, partial: false,
  credited: 7500, debited: 3600, player_net: 3900, prizes: 5000, refunds: 2000,
  admin_credit: 300, admin_debit: 100, other_credit: 200, other_debit: 500,
  purchases: 3000, issued: 500, burned: 1800, supply_net: -1300 };
const report: EconomyReport = { today: "2026-10-18", selected_day: "2026-10-18", timezone: "Europe/Moscow", epoch: 2, scope: "current", epoch_started_at: null,
  days: [{ ...day, day: "2026-10-17", credited: 7000 }, day] };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(adminApi.economy).mockResolvedValue(report); });

it("shows player flows, separate refunds and actual system issuance/burning", async () => {
  render(<EconomyPanel refreshedAt={1} />);
  const label = await screen.findByText("НАЧИСЛЕНО ИГРОКАМ");
  expect(within(label.closest("article")!).getByText(/7\s500 CAS/)).toBeInTheDocument();
  expect(screen.getByText(/\+500 CAS к предыдущему дню/)).toBeInTheDocument();
  expect(screen.getByText("Возвраты билетов").parentElement).toHaveTextContent(/2\s000 CAS/);
  expect(screen.getByText("СОЗДАНО CAS В СИСТЕМЕ").parentElement).toHaveTextContent("500 CAS");
  expect(screen.getByText("СОЖЖЕНО CAS В СИСТЕМЕ").parentElement).toHaveTextContent(/1\s800 CAS/);
});

it("loads a selected day and comparison window", async () => {
  render(<EconomyPanel refreshedAt={1} />);
  await screen.findByText("НАЧИСЛЕНО ИГРОКАМ");
  fireEvent.change(screen.getByLabelText("Период экономики CAS"), { target: { value: "30" } });
  await waitFor(() => expect(adminApi.economy).toHaveBeenLastCalledWith(30, ""));
  fireEvent.change(screen.getByLabelText("День отчёта CAS"), { target: { value: "2026-10-16" } });
  await waitFor(() => expect(adminApi.economy).toHaveBeenLastCalledWith(30, "2026-10-16"));
});

it("marks partial days and avoids comparing with an excluded old-stage day", async () => {
  vi.mocked(adminApi.economy).mockResolvedValue({ ...report, days: [{ ...day, day: "2026-10-17", included: false }, { ...day, partial: true }] });
  render(<EconomyPanel refreshedAt={1} />);
  expect(await screen.findByText(/Часть дня: граница этапа внутри суток/)).toBeInTheDocument();
  expect(screen.getAllByText("Предыдущий день вне выбранного этапа")).toHaveLength(2);
  expect(screen.queryByText(/к предыдущему дню/)).not.toBeInTheDocument();
});

it("reports a failed request without showing invented zero flows", async () => {
  vi.mocked(adminApi.economy).mockRejectedValue(new Error("offline"));
  render(<EconomyPanel refreshedAt={1} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Не удалось загрузить движение CAS");
  expect(screen.queryByText("НАЧИСЛЕНО ИГРОКАМ")).not.toBeInTheDocument();
});
