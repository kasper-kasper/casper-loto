import { expect, test, vi } from "vitest";
import type { Lottery } from "../../types";
import { KhanBridge } from "./KhanBridge";
import type { KhanSnapshot } from "./contracts";

const lottery={code:"khan",name:"6 из 36",ruleset_code:"classic_6_36",kind:"DAILY",numbers_to_pick:6,max_number:36,primary_numbers_to_pick:6,primary_max_number:36,secondary_numbers_to_pick:0,secondary_max_number:0,secondary_storage_offset:0,ticket_price:48000,jackpot:30000000,draw_number:1,scheduled_at:null,sales_close_at:null,purchase_available:true,player_ticket_count:0,sales_status:"OPEN",max_tickets_per_purchase:25} satisfies Lottery;
const snapshot=(revision:number):KhanSnapshot=>({revision,lottery,balance:100000,selectedNumbers:[],salesOpen:true,serverNow:0,phase:"idle",purchase:{mode:null,quantity:null,status:"idle",message:"",ticketIds:[]},reducedMotion:false});

test("KhanBridge replays only the latest monotonic snapshot",()=>{const bridge=new KhanBridge();bridge.publish(snapshot(2));bridge.publish(snapshot(1));const listener=vi.fn();const unsubscribe=bridge.subscribeSnapshot(listener);expect(listener).toHaveBeenCalledTimes(1);expect(listener).toHaveBeenLastCalledWith(expect.objectContaining({revision:2}));unsubscribe();bridge.publish(snapshot(3));expect(listener).toHaveBeenCalledTimes(1);});
