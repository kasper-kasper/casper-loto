import { expect, test } from "vitest";
import { clearPendingPurchase, loadPendingPurchase, savePendingPurchase, type PendingGrobPurchase } from "./pending-purchase";

test("pending purchase survives reload with an immutable key and payload",()=>{
  const attempt:PendingGrobPurchase={key:"same-key",userId:"u1",drawNumber:42,price:6666,mode:"quick",quantity:5,combinations:[[1,2,3]],createdAt:"2026-09-23T00:00:00Z"};
  savePendingPurchase(attempt);expect(loadPendingPurchase("u1")).toEqual(attempt);clearPendingPurchase("u1");expect(loadPendingPurchase("u1")).toBeNull();
});

