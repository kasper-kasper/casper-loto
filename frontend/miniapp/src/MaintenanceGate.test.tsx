import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MaintenanceGate } from "./MaintenanceGate";

afterEach(() => { vi.unstubAllGlobals(); });

it("uses the regular app skeleton without a maintenance screen while checking", async () => {
  let finish!: (value: unknown) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise(resolve => { finish = resolve; })));
  const { container } = render(<MaintenanceGate><p>Game content</p></MaintenanceGate>);
  expect(screen.getByRole("main", { name: "Загружаем Casper Loto" })).toHaveClass("skeleton-shell");
  expect(container.querySelector(".economy-maintenance")).toBeNull();
  expect(screen.queryByText(/техническ|обновляем экономику/i)).not.toBeInTheDocument();
  expect(screen.queryByText("Game content")).not.toBeInTheDocument();
  await waitFor(() => expect(finish).toBeDefined());
  finish({ ok: true, json: async () => ({ maintenance: false }) });
  await screen.findByText("Game content");
  expect(screen.queryByText("Техническая пауза")).not.toBeInTheDocument();
});

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
