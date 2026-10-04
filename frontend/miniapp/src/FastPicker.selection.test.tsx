import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { FastPicker } from "./FastView";
import type { Lottery } from "./types";

const pulse: Lottery = {
  code: "pulse", name: "PULSE", kind: "DAILY", numbers_to_pick: 5, max_number: 18,
  primary_numbers_to_pick: 2, primary_max_number: 12, secondary_numbers_to_pick: 2,
  secondary_max_number: 6, secondary_storage_offset: 12, ticket_price: 1234,
  jackpot: 1234567, draw_number: 1, scheduled_at: null, sales_close_at: null,
  sales_open: true, purchase_available: true, player_ticket_count: 0,
  sales_status: "OPEN", max_tickets_per_purchase: 100, max_tickets_per_user_per_draw: 500,
};

it("keeps Pulse fields independent including main positions 11 and 12", () => {
  const onBuy = vi.fn();
  render(<FastPicker lottery={pulse} purchasing={false} success={false} onClose={() => undefined} onBuy={onBuy} />);
  for (const name of ["Позиция 11", "Позиция 12", "Pulse-число 1", "Pulse-число 6"]) {
    fireEvent.click(screen.getByRole("button", { name }));
  }
  expect(screen.getByRole("button", { name: "Запустить пульс" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Позиция 1" }));
  expect(screen.getByRole("button", { name: "Позиция 1" })).toHaveAttribute("aria-pressed", "false");
  fireEvent.click(screen.getByRole("button", { name: "Pulse-число 1" }));
  expect(screen.getByRole("button", { name: "Запустить пульс" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Позиция 12" })).toHaveAttribute("aria-pressed", "true");
  expect(onBuy).not.toHaveBeenCalled();
});

it("shows errors and locks the current selection while a request is pending", () => {
  const onBuy = vi.fn();
  const props = { lottery: pulse, success: false, onClose: () => undefined, onBuy };
  const { rerender } = render(<FastPicker {...props} purchasing={false} />);
  fireEvent.click(screen.getByRole("button", { name: "Случайный выбор" }));
  rerender(<FastPicker {...props} purchasing error="Продажи закрыты. Обновите тираж." />);
  expect(screen.getByRole("alert")).toHaveTextContent("Продажи закрыты");
  expect(screen.getByRole("button", { name: "Случайный выбор" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Позиция 12" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Pulse-число 6" })).toBeDisabled();
  expect(onBuy).not.toHaveBeenCalled();
});

it("keeps CODE digits ordered, allows repeats, and removes the last digit without buying", () => {
  const onBuy = vi.fn();
  const { container } = render(<FastPicker lottery={{ ...pulse, code: "shadow", name: "CODE", ruleset_code: "code_5_digits", numbers_to_pick: 5, max_number: 9 }} purchasing={false} success={false} onClose={vi.fn()} onBuy={onBuy} />);
  for (const value of [0, 7, 0, 3, 8, 9]) fireEvent.click(screen.getByRole("button", { name: `Цифра ${value}` }));
  expect(Array.from(container.querySelectorAll(".fast-selection i"), node => node.textContent)).toEqual(["0", "7", "0", "3", "8"]);
  expect(screen.getByRole("button", { name: "Подтвердить код" })).toBeEnabled();
  expect(screen.getByRole("button", { name: "Цифра 0" })).not.toHaveAttribute("aria-pressed");
  fireEvent.click(screen.getByRole("button", { name: "Удалить последнюю цифру" }));
  expect(screen.getByRole("button", { name: "Подтвердить код" })).toBeDisabled();
  expect(Array.from(container.querySelectorAll(".fast-selection i"), node => node.textContent)).toEqual(["0", "7", "0", "3", "—"]);
  expect(onBuy).not.toHaveBeenCalled();
});

it("keeps FLASH selection limited and lets a lit key release its position", () => {
  const onBuy = vi.fn();
  render(<FastPicker lottery={{ ...pulse, code: "flash", name: "FLASH", numbers_to_pick: 5, max_number: 20 }} purchasing={false} success={false} onClose={vi.fn()} onBuy={onBuy} />);
  for (const value of [1, 5, 9, 14, 20, 3]) fireEvent.click(screen.getByRole("button", { name: `Позиция ${value}` }));
  expect(screen.getByRole("button", { name: "Позиция 3" })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByRole("button", { name: "Активировать" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Позиция 20" }));
  expect(screen.getByRole("button", { name: "Активировать" })).toBeDisabled();
  expect(onBuy).not.toHaveBeenCalled();
});
