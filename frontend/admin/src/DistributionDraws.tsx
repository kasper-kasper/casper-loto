import { useEffect, useRef, useState } from "react";
import { adminApi } from "./api";
import type { DistributionDraw } from "./api";
import type { Draw, Lottery } from "./types";
import "./distribution.css";

const dateMoscow = () => new Intl.DateTimeFormat("en-CA", {timeZone:"Europe/Moscow"}).format(new Date());
const stamp = (value:string) => new Intl.DateTimeFormat("ru-RU", {timeZone:"Europe/Moscow",dateStyle:"long",timeStyle:"short"}).format(new Date(value));
const stateName: Record<string,string> = {queued:"В очереди — отправим автоматически",sending:"Отправляется; повтор не требуется",sent:"Пост опубликован",uncertain:"Ответ Telegram не получен. Проверьте канал: повторная отправка отключена",failed:"Telegram отклонил отправку. Проверьте права бота в канале",expired:"Пост не отправлен до начала тиража"};
export function DistributionDraws({ onOpen }: { onOpen?: (id: string) => void }){
  const [lotteries,setLotteries]=useState<Lottery[]>([]),[lotteryId,setLotteryId]=useState(""),[day,setDay]=useState(dateMoscow),[rows,setRows]=useState<DistributionDraw[]>([]),[selected,setSelected]=useState(""),[confirming,setConfirming]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(""),[loaded,setLoaded]=useState(false);
  const generation=useRef(0),saving=useRef(false);
  const [now,setNow]=useState(Date.now);
  useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[]);
  const clearSelection=()=>{setLoaded(false);setRows([]);setSelected("");setConfirming(false);setError("");};
  useEffect(()=>{let active=true;void adminApi.lotteries().then(data=>{if(active){const available=data.filter(l=>l.is_active && l.code!=="dual" && !["kasper-live","aurora","vault"].includes(l.code));setLotteries(available);setLotteryId(available[0]?.id??"");}}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[]);
  useEffect(()=>{if(!lotteryId)return;let active=true;const version=++generation.current;void adminApi.distributionDraws(lotteryId,day).then(data=>{if(active&&version===generation.current){setRows(data);setSelected(data[0]?.id??"");setLoaded(true);}}).catch(e=>{if(active&&version===generation.current){setError(e.message);setLoaded(true);}});return()=>{active=false;};},[lotteryId,day]);
  const draw=rows.find(d=>d.id===selected);
  const assign=async()=>{if(!draw||saving.current)return;saving.current=true;setBusy(true);setError("");try{const next=await adminApi.assignDistribution(draw);setRows(current=>current.map(d=>d.id===draw.id?next:d));setSelected(next.id);setConfirming(false);}catch(e){setError(e instanceof Error?e.message:"Не удалось подтвердить. Обновите статус перед повтором.");}finally{saving.current=false;setBusy(false);}};
  const closed=!!draw&&(draw.status!=="SCHEDULED"||Date.parse(draw.sales_close_at)<=now);
  return <section className="distribution-room"><header><small>ОСОБЫЙ ТИРАЖ</small><h2>Распределительные тиражи</h2><p>Весь джекпот получит ближайшая категория с победителями. Если все категории пустые — все купленные билеты. Обычные выигрыши сохраняются.</p></header>
    <div className="distribution-controls"><label>Лотерея<select aria-label="Лотерея распределительного тиража" disabled={busy} value={lotteryId} onChange={e=>{clearSelection();setLotteryId(e.target.value);}}>{lotteries.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label><label>Дата по Москве<input type="date" aria-label="Дата распределительного тиража" value={day} disabled={busy} onChange={e=>{clearSelection();setDay(e.target.value);}} /></label><label>Время и тираж<select aria-label="Время распределительного тиража" value={selected} disabled={busy||!rows.length} onChange={e=>{setSelected(e.target.value);setConfirming(false);}}>{rows.map(d=><option key={d.id} value={d.id}>{new Intl.DateTimeFormat("ru-RU",{timeZone:"Europe/Moscow",timeStyle:"short"}).format(new Date(d.scheduled_at))} · №{d.number}{d.is_distribution?" · Распределительный":""}</option>)}</select></label></div>
    {lotteryId && <DistributionHistory key={lotteryId} lotteryId={lotteryId} onOpen={onOpen} />}
    {error&&<p role="alert">{error}</p>}{!loaded&&lotteryId&&<p>Загружаем тиражи…</p>}{loaded&&!rows.length&&<p>На эту дату запланированных тиражей нет. Выберите другую дату.</p>}
    {draw&&<article className="distribution-confirm"><h3>{draw.lottery_name} · тираж №{draw.number}</h3><p>{stamp(draw.scheduled_at)} МСК</p><dl><div><dt>Продажи закроются</dt><dd>{stamp(draw.sales_close_at)} МСК</dd></div><div><dt>Сейчас в джекпоте</dt><dd>{draw.jackpot.toLocaleString("ru-RU")} CAS</dd></div><div><dt>Уже куплено билетов</dt><dd>{draw.ticket_count}</dd></div></dl>
    <p>Все ранее купленные билеты участвуют. После распределения базовый джекпот восстановится. Назначение фиксируется без отмены.</p>

    {draw.is_distribution?<p role="status"><b>Распределительный тираж назначен.</b><br/>{draw.announcement_state ? stateName[draw.announcement_state] : "Результат будет доступен в истории после завершения."}</p>:closed?<p>Продажи закрыты — назначить распределение уже нельзя.</p>:confirming?<div className="distribution-buttons"><button type="button" disabled={busy} onClick={()=>void assign()}>{busy?"Подтверждаем…":"Подтвердить назначение"}</button><button type="button" disabled={busy} onClick={()=>setConfirming(false)}>Назад</button></div>:<button type="button" onClick={()=>setConfirming(true)}>Назначить распределительный тираж</button>}
    </article>}
  </section>;
}

function DistributionHistory({ lotteryId, onOpen }: { lotteryId: string; onOpen?: (id: string) => void }) {
  const [rows, setRows] = useState<Draw[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    let active = true;
    const query = new URLSearchParams({ scope: "all", period: "distribution", lottery_id: lotteryId, limit: "50" });
    void adminApi.draws(query.toString()).then(data => { if (active) setRows(data); })
      .catch(() => { if (active) setError("Не удалось загрузить историю распределений."); })
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, [lotteryId]);
  return <section aria-label="История распределительных тиражей"><h3>Последние завершённые распределительные тиражи</h3>
    {error && <p role="alert">{error}</p>}{!loaded && <p>Загружаем историю…</p>}
    {loaded && !error && !rows.length && <p>Завершённых распределительных тиражей пока нет.</p>}
    {!!rows.length && <div className="table-wrap"><table><thead><tr><th>Тираж / дата МСК</th><th>Билетов</th><th>Распределено</th><th>Все выплаты</th></tr></thead><tbody>{rows.map(draw => <tr key={draw.id}><td><button className="text-action" onClick={() => onOpen?.(draw.id)}>№{draw.public_number} · {stamp(draw.scheduled_at)}</button></td><td>{draw.ticket_count}</td><td>{(draw.distributed_amount ?? 0).toLocaleString("ru-RU")} CAS</td><td>{draw.total_payout.toLocaleString("ru-RU")} CAS</td></tr>)}</tbody></table></div>}
    {rows.length === 50 && <p>Показаны последние 50. Полная история доступна в разделе «Тиражи» → «Распределительные».</p>}
  </section>;
}
