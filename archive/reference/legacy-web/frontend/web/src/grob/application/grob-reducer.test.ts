import { expect, test } from "vitest";
import { selectionPhase, toggleSelection } from "./grob-reducer";

test("selection fills three physical sockets and remains editable",()=>{
  let selected:number[]=[];for(const value of [4,11,16,7])selected=toggleSelection(selected,value);
  expect(selected).toEqual([4,11,16]);expect(selectionPhase(selected,true)).toBe("ready");
  selected=toggleSelection(selected,11);expect(selected).toEqual([4,16]);expect(selectionPhase(selected,true)).toBe("selecting");
});
test("cutoff wins over a ready draft",()=>expect(selectionPhase([1,2,3],false)).toBe("drawWaiting"));

