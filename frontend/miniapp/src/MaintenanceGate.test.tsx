import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MaintenanceGate } from "./MaintenanceGate";

afterEach(() => { vi.unstubAllGlobals(); });

it("keeps the game unmounted during a persistent pause", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ maintenance: true }) }));
  render(<MaintenanceGate><p>Game content</p></MaintenanceGate>);
  await screen.findByText("Покупки и розыгрыши приостановлены.");
  expect(screen.queryByText("Game content")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Проверить снова" }));
  await screen.findByText("Покупки и розыгрыши приостановлены.");
  expect(screen.queryByText("Game content")).not.toBeInTheDocument();
});

it("fails closed on network errors and closes an already open app on a pause response", async () => {
  const fetch = vi.fn().mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ ok: true, json: async () => ({ maintenance: false }) });
  vi.stubGlobal("fetch", fetch);
  render(<MaintenanceGate><p>Game content</p></MaintenanceGate>);
  await screen.findByText("Не удалось подключиться");
  expect(screen.queryByText("Game content")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Проверить снова" }));
  await screen.findByText("Game content");
  fireEvent(window, new Event("economy-maintenance"));
  await waitFor(() => expect(screen.queryByText("Game content")).not.toBeInTheDocument());
});
