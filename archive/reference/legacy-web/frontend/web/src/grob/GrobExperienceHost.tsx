import { useEffect, useMemo, useRef } from "react";
import type Phaser from "phaser";
import type { Lottery } from "../types";
import { useGrobExperience } from "./application/useGrobExperience";
import { GrobBridge } from "./bridge/GrobBridge";
import { createGrobGame } from "./phaser/createGrobGame";
import "./grob.css";

export default function GrobExperienceHost({lottery,balance,userId,onClose,onBalance}:{lottery:Lottery;balance:number;userId:string;onClose:()=>void;onBalance:(balance:number)=>void}){
  const container=useRef<HTMLDivElement>(null);const game=useRef<Phaser.Game|null>(null);const bridge=useMemo(()=>new GrobBridge(),[]);
  const snapshot=useGrobExperience({bridge,initialLottery:lottery,initialBalance:balance,userId,onExit:onClose,onBalance});
  useEffect(()=>{if(!container.current||game.current)return;const frame=window.requestAnimationFrame(()=>{if(container.current&&!game.current)game.current=createGrobGame(container.current,bridge);});return()=>{window.cancelAnimationFrame(frame);game.current?.destroy(true);game.current=null;}},[bridge]);
  const busy=snapshot.purchase.status==="pending";
  return <main className="grob-experience" aria-label="Интерактивная сцена лотереи ГРОБ">
    <div className="grob-canvas" ref={container}/>
    <div className="grob-sr-controls">
      <fieldset disabled={busy||!snapshot.salesOpen}><legend>Выберите три числа из шестнадцати</legend>{Array.from({length:16},(_,index)=>index+1).map(value=><button key={value} aria-pressed={snapshot.selectedNumbers.includes(value)} onClick={()=>bridge.emitIntent({type:"TOGGLE_NUMBER",value})}>Число {value}</button>)}<button disabled={snapshot.selectedNumbers.length!==3} onClick={()=>bridge.emitIntent({type:"BUY_MANUAL"})}>Купить выбранный билет</button><button onClick={()=>bridge.emitIntent({type:"BUY_QUICK",quantity:1})}>Купить один случайный билет</button><button onClick={()=>bridge.emitIntent({type:"BUY_QUICK",quantity:5})}>Купить пять случайных билетов</button><button onClick={()=>bridge.emitIntent({type:"BUY_QUICK",quantity:25})}>Купить двадцать пять случайных билетов</button></fieldset>
      <button onClick={onClose}>Вернуться в каталог</button>
    </div>
    <p className="grob-live-region" aria-live="polite">{snapshot.purchase.message||`Выбрано ${snapshot.selectedNumbers.length} из 3: ${snapshot.selectedNumbers.join(", ")||"нет"}`}</p>
  </main>;
}
