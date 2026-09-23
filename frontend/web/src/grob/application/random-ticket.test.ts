import { describe, expect, test } from "vitest";
import { createRandomTickets } from "./random-ticket";

describe("secure quick tickets",()=>{
  test.each([1,5,25] as const)("creates %i sorted 3/16 tickets",quantity=>{
    const tickets=createRandomTickets(quantity,16,3);
    expect(tickets).toHaveLength(quantity);
    for(const ticket of tickets){expect(ticket).toHaveLength(3);expect(new Set(ticket).size).toBe(3);expect(ticket).toEqual([...ticket].sort((a,b)=>a-b));expect(ticket.every(n=>n>=1&&n<=16)).toBe(true);}
  });
});

