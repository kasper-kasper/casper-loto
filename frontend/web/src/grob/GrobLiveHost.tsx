import { useEffect, useMemo, useRef } from "react";
import type Phaser from "phaser";
import type { LiveDraw, Lottery } from "../types";
import { deriveGrobLiveView, grobLivePhase } from "./application/live-state";
import { GrobBridge } from "./bridge/GrobBridge";
import type { GrobSnapshot } from "./bridge/contracts";
import { createGrobGame } from "./phaser/createGrobGame";
import "./grob.css";

export default function GrobLiveHost({draw,lottery,balance,now}:{draw:LiveDraw;lottery:Lottery;balance:number;now:number}){
  const container=useRef<HTMLDivElement>(null);const game=useRef<Phaser.Game|null>(null);const bridge=useMemo(()=>new GrobBridge(),[]);
  const live=useMemo(()=>deriveGrobLiveView(draw,now),[draw,now]);
  const snapshot=useMemo<GrobSnapshot>(()=>({revision:now,phase:grobLivePhase(live),lottery,balance,selectedNumbers:[],salesOpen:false,serverNow:now,purchase:{mode:null,quantity:null,status:"idle",message:"",ticketIds:[]},live,reducedMotion:window.matchMedia?.("(prefers-reduced-motion: reduce)").matches??false,muted:true}),[balance,live,lottery,now]);
  useEffect(()=>{if(!container.current||game.current)return;const frame=window.requestAnimationFrame(()=>{if(container.current&&!game.current)game.current=createGrobGame(container.current,bridge,"live");});return()=>{window.cancelAnimationFrame(frame);game.current?.destroy(true);game.current=null;}},[bridge]);
  useEffect(()=>bridge.publish(snapshot),[bridge,snapshot]);
  return <section className="grob-live-embed" aria-label={`Эфир лотереи ГРОБ, тираж №${draw.draw_number}`}><div className="grob-canvas" ref={container}/><p className="grob-live-region" aria-live="polite">{live.resultKind==="live"?`Прямой эфир. Раскрыто ${live.revealCount} из 3: ${live.revealedNumbers.join(", ")}`:live.resultKind==="waiting"?"Эфир ГРОБ готовится":`Результат: ${live.revealedNumbers.join(", ")}`}</p></section>;
}
