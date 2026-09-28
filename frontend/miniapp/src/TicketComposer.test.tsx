import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TicketComposer } from "./TicketComposer";
import type { Lottery } from "./types";

vi.mock("./telegram", () => ({ selectionHaptic: vi.fn() }));
const base: Lottery = { code: "khan", name: "6 из 36", kind: "DAILY", numbers_to_pick: 6, max_number: 36, ticket_price: 48000, jackpot: 33456000, draw_number: 1, scheduled_at: null, sales_close_at: null, sales_open: true, purchase_available: true, player_ticket_count: 0, sales_status: "OPEN", max_tickets_per_purchase: 100, max_tickets_per_user_per_draw: 100 };
function setup(lottery = base, purchasing = false) {
  const onBuy = vi.fn();
  const onBuyMany = vi.fn();
  render(<TicketComposer lottery={lottery} balance={10000000} now={0} purchasing={purchasing} favorites={[]} onBuy={onBuy} onBuyMany={onBuyMany} onSaveFavorite={vi.fn()} onDeleteFavorite={vi.fn()} />);
  return { onBuy, onBuyMany };
}

describe("ticket selection presentation", () => {
  it("limits a 6/36 selection, enables the direct action, and never adds a cart step", () => {
    const { onBuy, onBuyMany } = setup();
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeDisabled();
    for (const value of [1, 2, 3, 4, 5, 6, 7]) fireEvent.click(screen.getByRole("button", { name: String(value) }));
    expect(within(screen.getByLabelText("Числа")).getAllByRole("button", { pressed: true })).toHaveLength(6);
    expect(screen.getByRole("button", { name: "7" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "3" }));
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "В корзину" })).not.toBeInTheDocument();
    expect(onBuy).not.toHaveBeenCalled();
    expect(onBuyMany).not.toHaveBeenCalled();
  });

  it.each([
    ["weekly", 35, 5, 5, 2],
    ["pss", 36, 5, 8, 1],
  ])("keeps %s main and special selection limits independent", (code, max, mainCount, specialMax, specialCount) => {
    setup({ ...base, code, numbers_to_pick: mainCount + specialCount, max_number: max + specialMax, primary_max_number: max, primary_numbers_to_pick: mainCount, secondary_max_number: specialMax, secondary_numbers_to_pick: specialCount, secondary_storage_offset: max });
    const main = screen.getByLabelText("Основные числа");
    const special = screen.getByLabelText(code === "pss" ? "Casper Ball" : "Звёзды");
    for (let n = 1; n <= mainCount + 1; n++) fireEvent.click(within(main).getByRole("button", { name: String(n) }));
    for (let n = 1; n <= specialCount + 1; n++) fireEvent.click(within(special).getByRole("button", { name: String(n) }));
    expect(within(main).getAllByRole("button", { pressed: true })).toHaveLength(mainCount);
    expect(within(special).getAllByRole("button", { pressed: true })).toHaveLength(specialCount);
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeEnabled();
  });

  it("keeps Dual's two independent fields without repeat options", () => {
    setup({ ...base, code: "dual", numbers_to_pick: 4, max_number: 24 });
    for (const phase of ["NIGHT", "DAWN"]) {
      for (const value of [1, 2, 3]) fireEvent.click(screen.getByRole("button", { name: `${phase} ${value}` }));
      expect(screen.getByRole("button", { name: `${phase} 3` })).toHaveAttribute("aria-pressed", "false");
    }
    expect(screen.getByRole("button", { name: "Купить билет" })).toBeEnabled();
    expect(screen.queryByText("Повторы и избранное")).not.toBeInTheDocument();
  });

  it("locks selection and quick controls during an in-flight request", () => {
    setup(base, true);
    expect(screen.getByRole("button", { name: "1" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Случайные числа" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Купить 5 случайных билетов" })).toBeDisabled();
  });
});
