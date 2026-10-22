import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { FastBroadcast, FastExperience } from "./Fast";
import { displayedNumber, fastPresentation, randomFastTicket } from "./fast-model";
import { webApi } from "./api";
import type { Dashboard, LiveDraw, LiveFeed, Lottery } from "./types";

vi.mock("./api", () => ({ ApiError: class extends Error {}, webApi: { purchase: vi.fn(), dashboard: vi.fn(), live: vi.fn() } }));
const now = Date.parse("2026-09-21T17:02:00Z");
const lottery: Lottery = {
  code:"flash", name:"FLASH", ruleset_code:"fast_3_20", kind:"DAILY", numbers_to_pick:3,
  max_number:20,primary_numbers_to_pick:3,primary_max_number:20,secondary_numbers_to_pick:0,
  secondary_max_number:0,secondary_storage_offset:0,ticket_price:88,jackpot:10000,draw_number:42,
  scheduled_at:"2026-09-21T17:03:00Z",sales_close_at:"2026-09-21T17:02:52Z",
  purchase_available:true,player_ticket_count:2,sales_status:"OPEN",max_tickets_per_purchase:10,
};
const pulse: Lottery = {...lottery,code:"pulse",name:"PULSE",ruleset_code:"pulse_2_12_2_6",primary_numbers_to_pick:2,primary_max_number:12,secondary_numbers_to_pick:2,secondary_max_number:6,secondary_storage_offset:12};
const code: Lottery = {...lottery,code:"shadow",name:"CODE",ruleset_code:"code_4_digits",primary_numbers_to_pick:4,primary_max_number:10};
const feed: LiveFeed = {server_time:new Date(now).toISOString(),latest_completed:null,next_scheduled:null,recent_completed:[]};
const props = {lotteries:[lottery],now,balance:10000,userId:"player",onBought:vi.fn(),onTickets:vi.fn()};
beforeEach(() => {
  vi.clearAllMocks(); sessionStorage.clear();
  vi.mocked(webApi.dashboard).mockResolvedValue({lotteries:[lottery,pulse,code]} as Dashboard);
  vi.mocked(webApi.live).mockResolvedValue(feed);
  vi.mocked(webApi.purchase).mockResolvedValue({ticket_ids:["ticket"],total_cost:88,balance_after:9912});
});
afterEach(cleanup);

test("three games have stable columns, distinct artwork and separate live feeds",async()=>{
  render(<FastExperience {...props} lotteries={[pulse,lottery,code]}/>);
  expect(screen.getAllByRole("article").map(a=>a.id)).toEqual(["fast-flash","fast-shadow","fast-pulse"]);
  expect(new Set(Array.from(document.querySelectorAll(".station-scene img")).map(i=>i.getAttribute("src"))).size).toBe(3);
  await waitFor(()=>expect(webApi.live).toHaveBeenCalledTimes(3));
  for(const value of ["flash","shadow","pulse"]) expect(webApi.live).toHaveBeenCalledWith("fast",value);
  expect(screen.getAllByText("00:52")).toHaveLength(3);
});
test("single click purchases exactly one random ticket with displayed price",async()=>{
  render(<FastExperience {...props}/>);
  const button=screen.getByRole("button",{name:/Купить случайный билет.*88 CAS/});
  fireEvent.click(button); fireEvent.click(button);
  await waitFor(()=>expect(webApi.purchase).toHaveBeenCalledTimes(1));
  const [game,combinations,key,count]=vi.mocked(webApi.purchase).mock.calls[0];
  expect(game).toBe("flash"); expect(combinations).toHaveLength(1); expect(new Set(combinations[0]).size).toBe(3);
  expect(combinations[0].every(n=>n>=1&&n<=20)).toBe(true); expect(key).toBeTruthy(); expect(count).toBe(1);
  await screen.findByText(/Билет куплен · 88 CAS/);
});
test("manual Pulse selection uses separate fields and the server storage offset",async()=>{
  render(<FastExperience {...props} lotteries={[pulse]}/>);
  fireEvent.click(screen.getByRole("button",{name:/Выбрать числа самостоятельно/}));
  for(const n of [11,12])fireEvent.click(screen.getByRole("button",{name:`Число ${n}`}));
  for(const n of [1,6])fireEvent.click(screen.getByRole("button",{name:`Pulse-число ${n}`}));
  fireEvent.click(screen.getByRole("button",{name:/Купить выбранный билет/}));
  await waitFor(()=>expect(webApi.purchase).toHaveBeenCalledWith("pulse",[[11,12,13,18]],expect.any(String),1));
});
test("CODE allows leading zero and repeated digits in order",async()=>{
  render(<FastExperience {...props} lotteries={[code]}/>);
  fireEvent.click(screen.getByRole("button",{name:/Выбрать числа самостоятельно/}));
  for(const n of [0,9,0,9])fireEvent.click(screen.getByRole("button",{name:`Цифра ${n}`}));
  fireEvent.click(screen.getByRole("button",{name:/Купить выбранный билет/}));
  await waitFor(()=>expect(webApi.purchase).toHaveBeenCalledWith("shadow",[[0,9,0,9]],expect.any(String),1));
});
test("ambiguous retry survives remount and reuses both numbers and key",async()=>{
  vi.mocked(webApi.purchase).mockRejectedValue(new Error("offline"));
  const first=render(<FastExperience {...props}/>);
  fireEvent.click(screen.getByRole("button",{name:/Купить случайный билет/}));
  await screen.findByText(/Ответ не получен/); const attempt=vi.mocked(webApi.purchase).mock.calls[0];
  first.unmount(); render(<FastExperience {...props}/>);
  fireEvent.click(screen.getByRole("button",{name:/Повторить запрос/}));
  await waitFor(()=>expect(webApi.purchase).toHaveBeenCalledTimes(2));
  expect(vi.mocked(webApi.purchase).mock.calls[1]).toEqual(attempt);
});
test("pending old-draw purchase blocks a new random ticket until user reviews",()=>{
  sessionStorage.setItem("casper:fast-pending:player:flash",JSON.stringify({key:"old",draw:41,price:88,numbers:[1,2,3]}));
  render(<FastExperience {...props}/>);
  expect(screen.getByRole("button",{name:/Повторить запрос/})).toBeDisabled();
  expect(screen.getByRole("button",{name:/Проверить билеты/})).toBeEnabled();
});
test("insufficient balance and elapsed cutoff disable purchase",()=>{
  const {rerender}=render(<FastExperience {...props} balance={87}/>);
  expect(screen.getByRole("button",{name:/Купить случайный билет/})).toBeDisabled();
  rerender(<FastExperience {...props} now={Date.parse(lottery.sales_close_at!)}/>);
  expect(screen.getByRole("button",{name:/Купить случайный билет/})).toBeDisabled();
});
test("changed draw in preflight does not submit a purchase",async()=>{
  vi.mocked(webApi.dashboard).mockResolvedValue({lotteries:[{...lottery,draw_number:43}]} as Dashboard);
  render(<FastExperience {...props}/>); fireEvent.click(screen.getByRole("button",{name:/Купить случайный билет/}));
  await screen.findByText(/Тираж или цена обновились/); expect(webApi.purchase).not.toHaveBeenCalled();
});

const draw: LiveDraw={lottery_code:"pulse",lottery_name:"PULSE",draw_number:40,scheduled_at:new Date(now).toISOString(),status:"COMPLETED",winning_numbers:[11,12,13,18],jackpot:10000,player_ticket_count:1,player_total_prize:700,highlighted_tickets:[],live_starts_at:new Date(now+1000).toISOString(),reveal_at:[2000,4000,6000,8000].map(t=>new Date(now+t).toISOString()),live_ends_at:new Date(now+10000).toISOString(),primary_numbers_to_pick:2,secondary_storage_offset:12};
const liveFeed={...feed,latest_completed:draw,recent_completed:[draw]};
test("broadcast does not leak future numbers or prize before server reveal timestamps",()=>{
  const {rerender}=render(<FastBroadcast feed={liveFeed} lottery={pulse} now={now+1999}/>);
  expect(screen.queryByText("P6")).not.toBeInTheDocument(); expect(screen.queryByText(/700 CAS/)).not.toBeInTheDocument();
  rerender(<FastBroadcast feed={liveFeed} lottery={pulse} now={now+2000}/>);
  expect(within(screen.getByLabelText("Числа тиража")).getByText("11")).toBeInTheDocument();
  expect(within(screen.getByLabelText("Числа тиража")).queryByText("12")).not.toBeInTheDocument();
  rerender(<FastBroadcast feed={liveFeed} lottery={pulse} now={now+10000}/>);
  expect(screen.getByText("P6")).toBeInTheDocument(); expect(screen.getByText(/700 CAS/)).toBeInTheDocument();
});
test("six-second result hold and prelive match Mini App",()=>{
  expect(fastPresentation(liveFeed,now+15999).phase).toBe("result");
  expect(fastPresentation(liveFeed,now+16000).phase).toBe("idle");
  const next={...draw,winning_numbers:null};
  expect(fastPresentation({...feed,next_scheduled:next},now-8000).phase).toBe("prelive");
  expect(fastPresentation({...feed,next_scheduled:next},now-8001).phase).toBe("waiting");
});
test("Pulse distinguishes high primary numbers from secondary numbers and handles old formats",()=>{
  expect(displayedNumber(draw,12,1)).toBe("12"); expect(displayedNumber(draw,13,2)).toBe("P1");
  expect(displayedNumber({...draw,secondary_storage_offset:10},11,2)).toBe("P1");
});
test("stale feed freezes reveal and signals reconnection",()=>{
  render(<FastBroadcast feed={liveFeed} lottery={pulse} now={now+20000}/>);
  expect(screen.getByText("Синхронизируем эфир…")).toBeInTheDocument();
  expect(within(screen.getByLabelText("Числа тиража")).queryByText("P6")).not.toBeInTheDocument();
});
test("random Pulse uses the current 2/12 + 2/6 format",()=>{
  for(let i=0;i<30;i++) {
    const numbers=randomFastTicket(pulse); expect(numbers).toHaveLength(4);
    expect(new Set(numbers.slice(0,2)).size).toBe(2);expect(new Set(numbers.slice(2)).size).toBe(2);
    expect(numbers.slice(0,2).every(n=>n>=1&&n<=12)).toBe(true);
    expect(numbers.slice(2).every(n=>n>=13&&n<=18)).toBe(true);
  }
});

test("broadcast replaces the scene, never creates a panel after purchase controls",async()=>{
  vi.mocked(webApi.live).mockResolvedValue(liveFeed);
  const {container,rerender}=render(<FastExperience {...props} lotteries={[pulse]} now={now+4000}/>);
  await waitFor(()=>expect(container.querySelector(".is-broadcasting")).not.toBeNull());
  expect(container.querySelectorAll(".station-scene .fast-broadcast")).toHaveLength(1);
  expect(container.querySelector(".station-controls + .fast-broadcast")).toBeNull();
  const scene=container.querySelector(".station-scene");
  rerender(<FastExperience {...props} lotteries={[pulse]} now={now+10000}/>);
  expect(container.querySelector(".station-scene")).toBe(scene);
  expect(container.querySelector(".phase-result")).not.toBeNull();
  rerender(<FastExperience {...props} lotteries={[pulse]} now={now+20000}/>);
  expect(container.querySelector(".is-broadcasting")).toBeNull();
});

test("manual selection stays in the scene and survives a live interruption",async()=>{
  vi.mocked(webApi.live).mockResolvedValue(liveFeed);
  const {container,rerender}=render(<FastExperience {...props} lotteries={[pulse]} now={now-10000}/>);
  await waitFor(()=>expect(webApi.live).toHaveBeenCalledTimes(3));
  fireEvent.click(screen.getByRole("button",{name:/Выбрать числа самостоятельно/}));
  fireEvent.click(screen.getByRole("button",{name:"Число 12"}));
  expect(container.querySelector(".station-scene .fast-selector")).not.toBeNull();
  rerender(<FastExperience {...props} lotteries={[pulse]} now={now+4000}/>);
  await waitFor(()=>expect(container.querySelector(".is-broadcasting")).not.toBeNull());
  expect(container.querySelector(".fast-selector")).toHaveAttribute("hidden");
  rerender(<FastExperience {...props} lotteries={[pulse]} now={now+20000}/>);
  expect(screen.getByRole("button",{name:"Число 12"})).toHaveAttribute("aria-pressed","true");
});
