import type { KhanPhase } from "../bridge/contracts";

export function toggleKhanNumber(selected:number[],value:number,max=36,limit=6){
  if(!Number.isInteger(value)||value<1||value>max)return selected;
  if(selected.includes(value))return selected.filter(item=>item!==value);
  if(selected.length>=limit)return selected;
  return [...selected,value].sort((a,b)=>a-b);
}

export function khanSelectionPhase(selected:number[],salesOpen:boolean):KhanPhase {
  if(!salesOpen)return "drawWaiting";
  if(selected.length===0)return "idle";
  return selected.length===6?"ready":"selecting";
}

export function createKhanRandomTickets(quantity:number,max=36,count=6,random:()=>number=()=>crypto.getRandomValues(new Uint32Array(1))[0]){
  return Array.from({length:quantity},()=>{
    const pool=Array.from({length:max},(_,index)=>index+1);
    for(let index=pool.length-1;index>0;index--){const swap=random()%(index+1);[pool[index],pool[swap]]=[pool[swap],pool[index]];}
    return pool.slice(0,count).sort((a,b)=>a-b);
  });
}
