import { useRef, useState } from "react";
import cryptArtwork from "./assets/grob/crypt-environment.png";
import { ApiError, webApi } from "./api";
import type { Lottery } from "./types";

const cas=(value:number)=>`${value.toLocaleString("ru-RU")} CAS`;
const msk=(value:string)=>new Intl.DateTimeFormat("ru-RU",{day:"2-digit",month:"long",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Moscow"}).format(new Date(value));

export function GrobGame({lottery,balance,onClose,onBought}:{lottery:Lottery;balance:number;onClose:()=>void;onBought:(message:string)=>void}){
  const [main,setMain]=useState<number[]>([]);
  const [quantity,setQuantity]=useState(1);
  const [drawCount,setDrawCount]=useState<1|5>(1);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const pending=useRef<{fingerprint:string;key:string}|null>(null);
  const inFlight=useRef(false);
  const needed=lottery.primary_numbers_to_pick;
  const price=(lottery.ticket_price??0)*quantity*drawCount;
  const toggle=(value:number)=>setMain(current=>current.includes(value)?current.filter(item=>item!==value):current.length<needed?[...current,value].sort((a,b)=>a-b):current);
  const random=()=>{const randoms=new Uint32Array(lottery.primary_max_number);crypto.getRandomValues(randoms);setMain(Array.from({length:lottery.primary_max_number},(_,i)=>i+1).map((value,index)=>({value,rank:randoms[index]})).sort((a,b)=>a.rank-b.rank).slice(0,needed).map(item=>item.value).sort((a,b)=>a-b));};
  const buy=async()=>{if(main.length!==needed||inFlight.current)return;inFlight.current=true;setBusy(true);setError("");const fingerprint=JSON.stringify([lottery.code,main,quantity,drawCount]);if(pending.current?.fingerprint!==fingerprint)pending.current={fingerprint,key:crypto.randomUUID()};try{const result=await webApi.purchase(lottery.code,Array.from({length:quantity},()=>main),pending.current.key,drawCount);onBought(`Печать поставлена. Куплено билетов: ${result.ticket_ids.length}. Списано ${cas(result.total_cost)}.`);}catch(reason){setError(reason instanceof ApiError?reason.message:"Печать не легла. Попробуйте ещё раз.");}finally{inFlight.current=false;setBusy(false);}};
  return <main className="grob-game" style={{"--grob-scene":`url(${cryptArtwork})`} as React.CSSProperties}>
    <div className="grob-game-atmosphere" aria-hidden="true"><i/><i/><i/><i/><i/><i/><i/><i/></div>
    <header className="grob-game-topbar"><button className="grob-back" onClick={onClose}><span>←</span> КОЛЛЕКЦИЯ</button><div className="grob-game-brand"><span className="grob-brand-sigil">✣</span><b>CASPER <small>PRIVATE LOTTERY CLUB</small></b></div><div className="grob-top-balance"><small>ВАШ КОШЕЛЁК</small><strong>{cas(balance)}</strong></div></header>
    <div className="grob-game-layout">
      <section className="grob-world-side" aria-label="Атмосфера игры GROБ">
        <div className="grob-world-label"><i/> СЕКТОР {lottery.draw_number ?? "—"} <span>·</span> РИТУАЛ ОТКРЫТ</div>
        <div className="grob-world-title"><p>КАЖДЫЙ ТИРАЖ — ЕЩЁ ОДНА ИСТОРИЯ</p><h1>GRO<span>Б</span></h1><div className="grob-title-rule"><i/> ТРИ ЧИСЛА ИЗ ШЕСТНАДЦАТИ <i/></div></div>
        <div className="grob-relic-ticket"><div className="grob-ticket-edge"><span>ВАША ПЕЧАТЬ</span><b>{String(main.length).padStart(2,"0")} / {String(needed).padStart(2,"0")}</b></div><div className="grob-relic-numbers">{Array.from({length:needed},(_,index)=><span className={main[index]!==undefined?"filled":""} key={index}>{main[index]!==undefined?String(main[index]).padStart(2,"0"):"✣"}</span>)}</div><div className="grob-ticket-caption">{main.length===needed?"ПЕЧАТЬ ГОТОВА К ЗАПИСКЕ":"ВЫБЕРИТЕ КАМНИ СВОЕЙ СУДЬБЫ"}</div></div>
        <div className="grob-world-footer"><span>СЛЕДУЮЩЕЕ ВСКРЫТИЕ</span><strong>ТИРАЖ №{lottery.draw_number ?? "—"}</strong><small>{lottery.scheduled_at?msk(lottery.scheduled_at):"ВРЕМЯ НЕ ОПРЕДЕЛЕНО"} МСК</small></div>
      </section>
      <section className="grob-select-side" aria-label="Выбор чисел для билета GROБ">
        <div className="grob-select-heading"><div><span className="grob-overline">ВЫБОР УЧАСТИ</span><h2>Назови <em>числа.</em></h2><p>Коснись надгробия, чтобы внести число в печать.</p></div><div className="grob-count-seal"><b>{main.length}</b><i>/</i>{needed}<small>ВЫБРАНО</small></div></div>
        <div className="grob-tomb-grid" role="group" aria-label={`Выберите ${needed} числа из ${lottery.primary_max_number}`}>
          {Array.from({length:lottery.primary_max_number},(_,index)=>{const value=index+1;const chosen=main.includes(value);return <button key={value} aria-label={`Надгробие ${value}`} aria-pressed={chosen} className={`grob-tomb-choice ${chosen?"chosen":""}`} onClick={()=>toggle(value)}><span className="grob-tomb-crest">✣</span><strong>{String(value).padStart(2,"0")}</strong><i className="grob-tomb-crack"/><span className="grob-tomb-select-mark">{chosen?"ЗАПЕЧАТАНО":"КАСАНИЕ"}</span></button>})}
        </div>
        <div className="grob-controls"><button className="grob-shuffle" onClick={random}><span>⟳</span> СЛУЧАЙНЫЕ ЧИСЛА</button><label className="grob-ticket-qty">БИЛЕТОВ<input type="number" min={1} max={lottery.max_tickets_per_purchase} value={quantity} onChange={event=>setQuantity(Math.max(1,Math.min(lottery.max_tickets_per_purchase,Number(event.target.value))))}/></label>{lottery.kind!=="WEEKLY"&&<label className="grob-five-draws"><input type="checkbox" checked={drawCount===5} onChange={event=>setDrawCount(event.target.checked?5:1)}/><span>×5</span> ПЯТЬ ТИРАЖЕЙ</label>}<button className="grob-seal-action" disabled={main.length!==needed||busy} onClick={()=>void buy()}><span>{busy?"ЗАПЕЧАТЫВАЕМ…":"ПРИЛОЖИТЬ ПЕЧАТЬ"}</span><b>{cas(price)} <i>→</i></b></button></div>
        {error&&<p role="alert" className="grob-purchase-error">{error}</p>}
        <footer className="grob-select-footer"><span>ЧИСЛА ВЫБРАНЫ ВАМИ</span><i>◆</i><span>РЕЗУЛЬТАТ ВСКРЫТИЯ ОПРЕДЕЛЯЕТ СЕРВЕР</span></footer>
      </section>
    </div>
  </main>;
}
