import { useEffect, useMemo, useRef } from "react";
import type Phaser from "phaser";
import type { Lottery } from "../types";
import { useKhanExperience } from "./application/useKhanExperience";
import { KhanBridge } from "./bridge/KhanBridge";
import { createKhanGame } from "./phaser/createKhanGame";
import "./khan.css";

export default function KhanExperienceHost({lottery,balance,userId,onClose,onBalance}:{lottery:Lottery;balance:number;userId:string;onClose:()=>void;onBalance:(balance:number)=>void}){
  const container=useRef<HTMLDivElement>(null),game=useRef<Phaser.Game|null>(null),bridge=useMemo(()=>new KhanBridge(),[]);
  const snapshot=useKhanExperience({bridge,initialLottery:lottery,initialBalance:balance,userId,onExit:onClose,onBalance});
  useEffect(()=>{if(!container.current||game.current)return;const frame=requestAnimationFrame(()=>{if(container.current&&!game.current)game.current=createKhanGame(container.current,bridge);});return()=>{cancelAnimationFrame(frame);game.current?.destroy(true);game.current=null;};},[bridge]);
  const busy=snapshot.purchase.status==="pending";
  return <main className="khan-experience" aria-label="Интерактивная сцена лотереи 6 из 36">
    <div className="khan-canvas" ref={container}/>
    <div className="khan-sr-controls"><fieldset disabled={busy||!snapshot.salesOpen}><legend>Выберите шесть чисел из тридцати шести</legend>{Array.from({length:36},(_,index)=>index+1).map(value=><button key={value} aria-pressed={snapshot.selectedNumbers.includes(value)} onClick={()=>bridge.emitIntent({type:"TOGGLE_NUMBER",value})}>Число {value}</button>)}<button disabled={snapshot.selectedNumbers.length!==6} onClick={()=>bridge.emitIntent({type:"BUY_MANUAL"})}>Купить выбранный билет</button>{([1,5,25] as const).map(quantity=><button key={quantity} onClick={()=>bridge.emitIntent({type:"BUY_QUICK",quantity})}>Купить случайных билетов: {quantity}</button>)}</fieldset><button onClick={onClose}>Вернуться в каталог</button></div>
    <p className="khan-status-region" aria-live="polite">{snapshot.purchase.message||`Выбрано ${snapshot.selectedNumbers.length} из 6: ${snapshot.selectedNumbers.join(", ")||"нет"}`}</p>
  </main>;
}
