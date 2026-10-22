import { StrictMode, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import type { Root } from "react-dom/client";
import type Phaser from "phaser";
import type { Lottery } from "../types";
import { toggleKhanNumber } from "./application/khan-state";
import { KhanBridge } from "./bridge/KhanBridge";
import type { KhanPurchaseView, KhanSnapshot } from "./bridge/contracts";
import { createKhanGame } from "./phaser/createKhanGame";
import "./khan.css";

const lottery:Lottery={code:"khan",name:"6 из 36",ruleset_code:"classic_6_36",kind:"DAILY",numbers_to_pick:6,max_number:36,primary_numbers_to_pick:6,primary_max_number:36,secondary_numbers_to_pick:0,secondary_max_number:0,secondary_storage_offset:0,ticket_price:48000,jackpot:30000000,draw_number:184,scheduled_at:new Date(Date.now()+3_600_000).toISOString(),sales_close_at:new Date(Date.now()+3_480_000).toISOString(),purchase_available:true,player_ticket_count:3,sales_status:"OPEN",max_tickets_per_purchase:25};
const idle:KhanPurchaseView={mode:null,quantity:null,status:"idle",message:"",ticketIds:[]};

export function KhanPreview(){
  const holder=useRef<HTMLDivElement>(null),game=useRef<Phaser.Game|null>(null),bridge=useMemo(()=>new KhanBridge(),[]),revision=useRef(0);
  const [selected,setSelected]=useState<number[]>([]),[purchase,setPurchase]=useState<KhanPurchaseView>(idle),[balance,setBalance]=useState(12_500_000);
  useEffect(()=>{if(!holder.current||game.current)return;game.current=createKhanGame(holder.current,bridge);return()=>{game.current?.destroy(true);game.current=null;};},[bridge]);
  useEffect(()=>bridge.subscribeIntent(intent=>{if(intent.type==="TOGGLE_NUMBER"&&purchase.status!=="pending")setSelected(current=>toggleKhanNumber(current,intent.value));else if(intent.type==="BUY_MANUAL"&&selected.length===6){setPurchase({mode:"manual",quantity:1,status:"pending",message:"Билет печатается…",ticketIds:[]});window.setTimeout(()=>{setBalance(current=>current-48000);setPurchase({mode:"manual",quantity:1,status:"success",message:"Готово · 1 билет",ticketIds:["preview"]});window.setTimeout(()=>{setSelected([]);setPurchase(idle);},1050);},650);}else if(intent.type==="BUY_QUICK"){setPurchase({mode:"quick",quantity:intent.quantity,status:"pending",message:`Готовим случайные билеты ×${intent.quantity}…`,ticketIds:[]});window.setTimeout(()=>{setBalance(current=>current-48000*intent.quantity);setPurchase({mode:"quick",quantity:intent.quantity,status:"success",message:`Готово · ${intent.quantity} билетов`,ticketIds:Array.from({length:intent.quantity},(_,i)=>String(i))});window.setTimeout(()=>setPurchase(idle),1050);},650);}}),[bridge,purchase.status,selected.length]);
  useEffect(()=>{const snapshot:KhanSnapshot={revision:++revision.current,lottery,balance,selectedNumbers:selected,salesOpen:true,serverNow:Date.now(),phase:purchase.status==="pending"?"purchasePending":purchase.status==="success"?"purchaseSuccess":selected.length===6?"ready":selected.length?"selecting":"idle",purchase,reducedMotion:matchMedia("(prefers-reduced-motion: reduce)").matches};bridge.publish(snapshot);},[balance,bridge,purchase,selected]);
  return <main className="khan-experience" aria-label="Локальный визуальный стенд 6 из 36"><div className="khan-canvas" ref={holder}/></main>;
}

const rootElement=document.getElementById("root")!;
const root=(import.meta.hot?.data.previewRoot as Root|undefined)??createRoot(rootElement);
if(import.meta.hot)import.meta.hot.data.previewRoot=root;
root.render(<StrictMode><KhanPreview/></StrictMode>);
