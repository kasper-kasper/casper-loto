import { describe, expect, test } from "vitest";
import { createKhanRandomTickets, khanSelectionPhase, toggleKhanNumber } from "./khan-state";

describe("6 из 36 client state",()=>{
  test("selects six unique in-range numbers and toggles them off",()=>{
    let selected:number[]=[];
    for(const value of [36,1,8,15,27,32])selected=toggleKhanNumber(selected,value);
    expect(selected).toEqual([1,8,15,27,32,36]);
    expect(toggleKhanNumber(selected,34)).toEqual(selected);
    expect(toggleKhanNumber(selected,15)).toEqual([1,8,27,32,36]);
    expect(toggleKhanNumber(selected,0)).toBe(selected);
  });

  test("derives the ticket phase without inventing sales state",()=>{
    expect(khanSelectionPhase([],true)).toBe("idle");
    expect(khanSelectionPhase([1,2],true)).toBe("selecting");
    expect(khanSelectionPhase([1,2,3,4,5,6],true)).toBe("ready");
    expect(khanSelectionPhase([1,2,3,4,5,6],false)).toBe("drawWaiting");
  });

  test("quick purchase creates the requested number of valid tickets",()=>{
    let value=0;
    const tickets=createKhanRandomTickets(25,36,6,()=>value++);
    expect(tickets).toHaveLength(25);
    for(const ticket of tickets){expect(ticket).toHaveLength(6);expect(new Set(ticket).size).toBe(6);expect(ticket).toEqual([...ticket].sort((a,b)=>a-b));expect(ticket[0]).toBeGreaterThanOrEqual(1);expect(ticket[5]).toBeLessThanOrEqual(36);}
  });
});

