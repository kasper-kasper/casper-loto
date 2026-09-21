import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { Login, FastExperience } from "./Experience";
import { Picker } from "./App";
import { webApi } from "./api";
import type { Lottery } from "./types";

vi.mock("./api", () => ({ ApiError: class extends Error {}, webApi: { telegram: vi.fn(), purchase: vi.fn() } }));
const lottery: Lottery = {
 code:"flash", name:"FLASH", ruleset_code:"fast_3_20", kind:"DAILY", numbers_to_pick:3,
 max_number:20,primary_numbers_to_pick:3,primary_max_number:20,secondary_numbers_to_pick:0,
 secondary_max_number:0,secondary_storage_offset:0,ticket_price:88,jackpot:10000,draw_number:42,
 scheduled_at:"2026-09-21T17:03:00Z",sales_close_at:"2026-09-21T17:02:52Z",
 purchase_available:true,player_ticket_count:2,sales_status:"OPEN",max_tickets_per_purchase:10,
};

test("Telegram login submits the one-time code and retains server identity", async () => {
 const result={user_id:"canonical-id",display_name:"Player",csrf_token:"csrf",expires_at:"later"};
 vi.mocked(webApi.telegram).mockResolvedValue(result);
 const done=vi.fn();render(<Login onDone={done}/>);
 fireEvent.change(screen.getByLabelText("Код из Telegram"),{target:{value:"A123456789ABCDEF"}});
 fireEvent.click(screen.getByRole("button",{name:"Войти в Casper →"}));
 await waitFor(()=>expect(done).toHaveBeenCalledWith(result));
 expect(webApi.telegram).toHaveBeenCalledWith("A123456789ABCDEF");
});

test("Fast uses server ticket price, selection format and cutoff",()=>{
 const open=vi.fn();render(<FastExperience lotteries={[lottery]} now={Date.parse("2026-09-21T17:02:00Z")} onOpen={open}/>);
 expect(screen.getByText("00:52")).toBeInTheDocument();
 expect(screen.getByText("3 из 20")).toBeInTheDocument();
 fireEvent.click(screen.getByRole("button",{name:/Играть · 88 CAS/}));
 expect(open).toHaveBeenCalledWith(lottery);
});

test("retry after an ambiguous purchase failure preserves idempotency key",async()=>{
 vi.mocked(webApi.purchase).mockRejectedValue(new Error("connection lost"));
 render(<Picker lottery={lottery} onClose={vi.fn()} onBought={vi.fn()}/>);
 for(const n of [1,2,3])fireEvent.click(screen.getByRole("button",{name:String(n)}));
 fireEvent.click(screen.getByRole("button",{name:/Купить ·/}));
 await screen.findByText("Покупка не выполнена.");
 fireEvent.click(screen.getByRole("button",{name:/Купить ·/}));
 await waitFor(()=>expect(webApi.purchase).toHaveBeenCalledTimes(2));
 const calls=vi.mocked(webApi.purchase).mock.calls;
 expect(calls[0][3]).toBe(calls[1][3]);
 expect(calls[0][1]).toEqual([[1,2,3]]);
});
