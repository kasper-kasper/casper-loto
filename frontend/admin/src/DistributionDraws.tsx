import { useEffect, useRef, useState } from "react";
import { adminApi } from "./api";
import type { DistributionDraw } from "./api";
import type { Lottery } from "./types";
import "./distribution.css";

const dateMoscow = () => new Intl.DateTimeFormat("en-CA", {timeZone:"Europe/Moscow"}).format(new Date());
const stamp = (value:string) => new Intl.DateTimeFormat("ru-RU", {timeZone:"Europe/Moscow",dateStyle:"long",timeStyle:"short"}).format(new Date(value));
const stateName: Record<string,string> = {queued:"В очереди — отправим автоматически",sending:"Отправляется; повтор не требуется",sent:"Пост опубликован",uncertain:"Ответ Telegram не получен. Проверьте канал: повторная отправка отключена",failed:"Telegram отклонил отправку. Проверьте права бота в канале",expired:"Пост не отправлен до начала тиража"};
export function DistributionDraws(){
  const [lotteries,setLotteries]=useState<Lottery[]>([]),[lotteryId,setLotteryId]=useState(""),[day,setDay]=useState(dateMoscow),[rows,setRows]=useState<DistributionDraw[]>([]),[selected,setSelected]=useState(""),[confirming,setConfirming]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(""),[loaded,setLoaded]=useState(false);
  const generation=useRef(0),saving=useRef(false);
  const [now,setNow]=useState(Date.now);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[]);
  const clearSelection=()=>{setLoaded(false);setRows([]);setSelected("");setConfirming(false);setError("");};
  useEffect(()=>{let active=true;void adminApi.lotteries().then(data=>{if(active){const available=data.filter(l=>l.is_active && l.code!=="dual" && !["kasper-live","aurora","vault"].includes(l.code));setLotteries(available);setLotteryId(available[0]?.id??"");}}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
  useEffect(()=>{if(!lotteryId)return;let active=true;const version=++generation.current;void adminApi.distributionDraws(lotteryId,day).then(data=>{if(active&&version===generation.current){setRows(data);setSelected(data[0]?.id??"");setLoaded(true);}}).catch(e=>{if(active&&version===generation.current){setError(e.message);setLoaded(true);}});return()=>{active=false;};},[lotteryId,day]);
  const draw=rows.find(d=>d.id===selected);
  useEffect(()=>{if(!draw?.is_distribution||["sent","failed","uncertain","expired"].includes(draw.announcement_state??""))return;let active=true;const timer=setInterval(()=>{void adminApi.distributionDraws(lotteryId,day).then(data=>{if(active)setRows(data);}).catch(()=>undefined);},3000);return()=>{active=false;clearInterval(timer);};},[draw?.is_distribution,draw?.announcement_state,lotteryId,day]);
  const assign=async()=>{if(!draw||saving.current)return;saving.current=true;setBusy(true);setError("");try{const next=await adminApi.assignDistribution(draw);setRows(current=>current.map(d=>d.id===draw.id?next:d));setSelected(next.id);setConfirming(false);}catch(e){setError(e instanceof Error?e.message:"Не удалось подтвердить. Обновите статус перед повтором.");}finally{saving.current=false;setBusy(false);}};
  const closed=!!draw&&(draw.status!=="SCHEDULED"||Date.parse(draw.sales_close_at)<=now);
  return <section className="distribution-room"><header><small>ОСОБЫЙ ТИРАЖ</small><h2>Распределительные тиражи</h2><p>Весь джекпот получит ближайшая категория с победителями. Если все категории пустые — все купленные билеты. Обычные выигрыши сохраняются.</p></header>
    <div className="distribution-controls"><label>Лотерея<select aria-label="Лотерея распределительного тиража" disabled={busy} value={lotteryId} onChange={e=>{clearSelection();setLotteryId(e.target.value);}}>{lotteries.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label><label>Дата по Москве<input type="date" aria-label="Дата распределительного тиража" value={day} disabled={busy} onChange={e=>{clearSelection();setDay(e.target.value);}} /></label><label>Время и тираж<select aria-label="Время распределительного тиража" value={selected} disabled={busy||!rows.length} onChange={e=>{setSelected(e.target.value);setConfirming(false);}}>{rows.map(d=><option key={d.id} value={d.id}>{new Intl.DateTimeFormat("ru-RU",{timeZone:"Europe/Moscow",timeStyle:"short"}).format(new Date(d.scheduled_at))} · №{d.number}{d.is_distribution?" · Распределительный":""}</option>)}</select></label></div>
    {error&&<p role="alert">{error}</p>}{!loaded&&lotteryId&&<p>Загружаем тиражи…</p>}{loaded&&!rows.length&&<p>На эту дату запланированных тиражей нет. Выберите другую дату.</p>}
    {draw&&<article className="distribution-confirm"><h3>{draw.lottery_name} · тираж №{draw.number}</h3><p>{stamp(draw.scheduled_at)} МСК</p><dl><div><dt>Продажи закроются</dt><dd>{stamp(draw.sales_close_at)} МСК</dd></div><div><dt>Сейчас в джекпоте</dt><dd>{draw.jackpot.toLocaleString("ru-RU")} CAS</dd></div><div><dt>Уже куплено билетов</dt><dd>{draw.ticket_count}</dd></div></dl>
    <p>Все ранее купленные билеты участвуют. После распределения базовый джекпот восстановится. Назначение фиксируется без отмены.</p>
    <details open={confirming}><summary>Текст поста в Telegram</summary><p className="distribution-post">{draw.post}</p></details>
    {draw.is_distribution?<p role="status"><b>Распределительный тираж назначен.</b><br/>{stateName[draw.announcement_state??"queued"]}</p>:closed?<p>Продажи закрыты — назначить распределение уже нельзя.</p>:confirming?<div className="distribution-buttons"><button type="button" disabled={busy} onClick={()=>void assign()}>{busy?"Подтверждаем…":"Подтвердить и опубликовать пост"}</button><button type="button" disabled={busy} onClick={()=>setConfirming(false)}>Назад</button></div>:<button type="button" onClick={()=>setConfirming(true)}>Назначить распределительный тираж</button>}
    </article>}
  </section>;
}
