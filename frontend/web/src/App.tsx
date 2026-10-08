import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AddPassword, Brand, LotteryGallery, Login } from "./Experience";
import { FastExperience } from "./Fast";
import { ApiError, webApi } from "./api";
import type { Account, BingoInventory, Dashboard, LiveDraw, Lottery, Ticket, WebSession } from "./types";

type View="lotteries"|"fast"|"live"|"tickets"|"profile";
const GrobExperienceHost=lazy(()=>import("./halloween/HalloweenExperienceHost"));
const GrobLiveHost=lazy(()=>import("./halloween/HalloweenLiveHost"));
const KhanExperienceHost=lazy(()=>import("./khan/KhanExperienceHost"));
const fastCodes = new Set(["flash", "shadow", "pulse"]);
const cas=(value:number)=>`${value.toLocaleString("ru-RU")} CAS`;
const msk=(value:string|null)=>value?new Intl.DateTimeFormat("ru-RU",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Moscow"}).format(new Date(value)):"—";
const countdown=(value:string|null,now=Date.now())=>{if(!value)return"—";const seconds=Math.max(0,Math.floor((new Date(value).getTime()-now)/1000));const h=Math.floor(seconds/3600),m=Math.floor(seconds%3600/60),s=seconds%60;return h?`${h} ч ${String(m).padStart(2,"0")} мин`:`${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`};
const theme=(code:string)=>code==="flash"?"blue":code==="shadow"?"code":code==="pulse"?"red":code==="september"?"autumn":code==="weekly"?"gold":code==="khan"?"classic":code==="grob"?"gothic":code==="pll"?"violet":code==="pss"?"ball":"navy";
const ticketNumbers=(numbers:number[],code:string)=>code==="pss"&&numbers.length===6?[...numbers.slice(0,5),`CB ${numbers[5]-36}`]:numbers;
const isGrobLottery=(lottery:Pick<Lottery,"code"|"name">)=>lottery.code.toLowerCase()==="grob"||lottery.name.toLocaleLowerCase("ru-RU").includes("гроб");
const isKhanLottery=(lottery:Pick<Lottery,"code"|"ruleset_code">)=>lottery.code.toLowerCase()==="khan"||lottery.ruleset_code==="classic_6_36";
const liveDraw=(feed:{latest_completed:LiveDraw|null;next_scheduled:LiveDraw|null})=>feed.latest_completed&&Date.now()<=new Date(feed.latest_completed.live_ends_at).getTime()+30_000?feed.latest_completed:feed.next_scheduled??feed.latest_completed;




function NumberGrid({max,selected,onToggle,ordered=false}:{max:number;selected:number[];onToggle:(n:number)=>void;ordered?:boolean}){return <div className={`number-grid ${ordered?"digits":""}`}>{Array.from({length:max},(_,i)=>i+(ordered?0:1)).map(value=><button key={value} className={selected.includes(value)&&!ordered?"selected":""} onClick={()=>onToggle(value)}><span>{value}</span></button>)}</div>}

export function Picker(props:{lottery:Lottery;onClose:()=>void;onBought:(message:string)=>void}){return <GenericPicker {...props}/>}
function GenericPicker({lottery,onClose,onBought}:{lottery:Lottery;onClose:()=>void;onBought:(message:string)=>void}){const[main,setMain]=useState<number[]>([]);const[special,setSpecial]=useState<number[]>([]);const[quantity,setQuantity]=useState(1);const[drawCount,setDrawCount]=useState<1|5>(1);const[busy,setBusy]=useState(false);const[error,setError]=useState("");const pending=useRef<{fingerprint:string;key:string}|null>(null);const inFlight=useRef(false);const ordered=lottery.ruleset_code==="code_4_digits";const pick=(list:number[],value:number,limit:number,set:(v:number[])=>void)=>{if(ordered){if(list.length<limit)set([...list,value]);return}set(list.includes(value)?list.filter(n=>n!==value):list.length<limit?[...list,value].sort((a,b)=>a-b):list)};const valid=main.length===lottery.primary_numbers_to_pick&&special.length===lottery.secondary_numbers_to_pick;const random=()=>{if(ordered){const values=new Uint32Array(lottery.primary_numbers_to_pick);crypto.getRandomValues(values);setMain(Array.from(values,value=>value%10))}else{const sample=(max:number,count:number)=>{const values=Array.from({length:max},(_,i)=>i+1);crypto.getRandomValues(new Uint32Array(values.length)).forEach((r,i)=>{const j=r%values.length;[values[i],values[j]]=[values[j],values[i]]});return values.slice(0,count).sort((a,b)=>a-b)};setMain(sample(lottery.primary_max_number,lottery.primary_numbers_to_pick));setSpecial(sample(lottery.secondary_max_number,lottery.secondary_numbers_to_pick))}};const buy=async()=>{if(!valid||inFlight.current)return;inFlight.current=true;setBusy(true);setError("");const combination=[...main,...special.map(n=>n+lottery.secondary_storage_offset)];const fingerprint=JSON.stringify([lottery.code,combination,quantity,drawCount]);if(pending.current?.fingerprint!==fingerprint)pending.current={fingerprint,key:crypto.randomUUID()};try{const result=await webApi.purchase(lottery.code,Array.from({length:quantity},()=>combination),pending.current.key,drawCount);onBought(`Куплено билетов: ${result.ticket_ids.length}. Списано ${cas(result.total_cost)}.`)}catch(reason){setError(reason instanceof ApiError?reason.message:"Покупка не выполнена.")}finally{inFlight.current=false;setBusy(false)}};return <div className="modal-backdrop" onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}><section className={`picker-panel theme-${theme(lottery.code)}`}><button className="close" onClick={onClose}>×</button><p className="eyebrow">ТИРАЖ №{lottery.draw_number}</p><h2>{lottery.name}</h2><p className="muted">{ordered?"Введите четыре цифры. Порядок важен, повторы разрешены.":`Выберите ${lottery.primary_numbers_to_pick} из ${lottery.primary_max_number}${lottery.secondary_numbers_to_pick?" и специальное поле ниже":""}.`}</p>{ordered&&<div className="code-slots">{Array.from({length:lottery.primary_numbers_to_pick},(_,i)=><span key={i}>{main[i]??"—"}</span>)}<button onClick={()=>setMain(main.slice(0,-1))}>⌫</button></div>}<NumberGrid max={lottery.primary_max_number} selected={main} onToggle={n=>pick(main,n,lottery.primary_numbers_to_pick,setMain)} ordered={ordered}/>{lottery.secondary_numbers_to_pick>0&&<div className="special-field"><p>СПЕЦИАЛЬНЫЕ ЧИСЛА · {special.length}/{lottery.secondary_numbers_to_pick}</p><NumberGrid max={lottery.secondary_max_number} selected={special} onToggle={n=>pick(special,n,lottery.secondary_numbers_to_pick,setSpecial)}/></div>}<div className="selection"><span>Ваш билет</span><strong>{main.length?[...main,...special.map(n=>`+${n}`)].join(" · "):"Числа не выбраны"}</strong><button onClick={random}>Случайная комбинация</button></div><div className="buy-options"><label>Билетов<input type="number" min={1} max={lottery.max_tickets_per_purchase} value={quantity} onChange={e=>setQuantity(Math.max(1,Math.min(lottery.max_tickets_per_purchase,Number(e.target.value))))}/></label>{lottery.kind!=="WEEKLY"&&<label className="checkbox"><input type="checkbox" checked={drawCount===5} onChange={e=>setDrawCount(e.target.checked?5:1)}/> На 5 тиражей</label>}<button className="primary" disabled={!valid||busy} onClick={()=>void buy()}>{busy?"Покупаем…":`Купить · ${cas((lottery.ticket_price??0)*quantity*drawCount)}`}</button></div>{error&&<p className="error">{error}</p>}</section></div>}


function BingoPicker({onClose,onBought}:{onClose:()=>void;onBought:(message:string)=>void}){const[busy,setBusy]=useState(false);const pending=useRef<{fingerprint:string;key:string}|null>(null);const inFlight=useRef(false);const[data,setData]=useState<BingoInventory|null>(null);const[selected,setSelected]=useState<string[]>([]);const[error,setError]=useState("");useEffect(()=>{webApi.bingoInventory().then(setData).catch(e=>setError(e instanceof Error?e.message:"Bingo недоступно"))},[]);const buy=async()=>{if(!data||!selected.length||inFlight.current)return;inFlight.current=true;setBusy(true);const fingerprint=JSON.stringify([data.draw_id,selected]);if(pending.current?.fingerprint!==fingerprint)pending.current={fingerprint,key:crypto.randomUUID()};try{const result=await webApi.bingoPurchase(data.draw_id,selected,pending.current.key);onBought(`Куплено Bingo-билетов: ${result.ticket_ids.length}.`)}catch(e){setError(e instanceof Error?e.message:"Покупка не выполнена")}finally{inFlight.current=false;setBusy(false)}};return <div className="modal-backdrop"><section className="picker-panel theme-gold"><button className="close" onClick={onClose}>×</button><p className="eyebrow">CASPER BINGO</p><h2>Выберите готовый билет</h2>{data&&<p className="muted">Тираж №{data.draw_number} · {msk(data.scheduled_at)} · {cas(data.price)}</p>}<div className="bingo-pool">{data?.tickets.slice(0,12).map(ticket=><button className={selected.includes(ticket.id)?"selected":""} key={ticket.id} onClick={()=>setSelected(selected.includes(ticket.id)?selected.filter(id=>id!==ticket.id):[...selected,ticket.id])}><strong>№{ticket.public_number}</strong>{[0,1,2].map(row=><span key={row}>{ticket.numbers.slice(row*4,row*4+4).join("  ")}</span>)}</button>)}</div><button className="primary" disabled={!selected.length||busy} onClick={()=>void buy()}>Купить выбранные · {selected.length}</button>{error&&<p className="error">{error}</p>}</section></div>}

function LiveStage({draw,now}:{draw:LiveDraw|null;now:number}){if(!draw)return <div className="empty-stage"><span>⌁</span><h3>Ближайший эфир готовится</h3></div>;const start=new Date(draw.live_starts_at).getTime(),end=new Date(draw.live_ends_at).getTime();const active=now>=start&&now<=end;const revealCount=draw.reveal_at.filter(value=>now>=new Date(value).getTime()).length;const numbers=draw.winning_numbers??[];return <div className={`live-stage theme-${theme(draw.lottery_code)} ${active?"on-air":""}`}><div className="live-head"><div><p className="eyebrow">{active?"● ПРЯМОЙ ЭФИР":"БЛИЖАЙШИЙ ТИРАЖ"}</p><h2>{draw.lottery_name}</h2>{draw.lottery_code==="pss"&&<small className="live-format">5 из 36 · Casper Ball 1 из 8</small>}</div><span>№{draw.draw_number}<small>{msk(draw.scheduled_at)}</small></span></div><div className="live-clock">{active?"Каспер выбирает числа прямо сейчас":`До начала ${countdown(draw.scheduled_at,now)}`}</div><div className="reveal-row">{Array.from({length:Math.max(numbers.length,draw.reveal_at.length)},(_,i)=><span className={i<revealCount?"revealed":""} key={i}>{i<revealCount?(draw.lottery_code==="pss"&&i===5?`CB ${numbers[i]-36}`:numbers[i]):"?"}</span>)}</div><div className="live-player"><span>Ваших билетов: <b>{draw.player_ticket_count}</b></span>{draw.player_total_prize>0&&<strong>Выигрыш {cas(draw.player_total_prize)}</strong>}</div></div>}

function Tickets({state}:{state:"active"|"history"}){const[data,setData]=useState<{tickets:Ticket[];total:number;has_more:boolean}>({tickets:[],total:0,has_more:false});const[offset,setOffset]=useState(0);useEffect(()=>{webApi.tickets(state).then(setData)},[state]);const more=async()=>{const next=offset+100;const page=await webApi.tickets(state,next);setOffset(next);setData(current=>({...page,tickets:[...current.tickets,...page.tickets]}))};return <section className="content"><div className="section-head"><div><p className="eyebrow">ВАША ИСТОРИЯ</p><h2>{state==="active"?"Активные билеты":"Завершённые билеты"}</h2></div><b>{data.total}</b></div><div className="ticket-list">{data.tickets.map(ticket=><article key={ticket.id} className={ticket.prize_amount>0?"winner":""}><div><span>{ticket.lottery_name}</span><strong>Билет №{ticket.public_number}</strong><small>Тираж №{ticket.draw_number} · {msk(ticket.scheduled_at)}</small></div><div className="ticket-numbers">{ticketNumbers(ticket.numbers,ticket.lottery_code).map((n,i)=><i className={ticket.winning_numbers?.includes(ticket.numbers[i])?"hit":""} key={`${n}-${i}`}>{n}</i>)}</div><div className="ticket-result">{ticket.status==="PURCHASED"?"Ожидает тираж":ticket.status==="REFUNDED"?"Возврат":ticket.prize_amount?`+ ${cas(ticket.prize_amount)}`:"Без выигрыша"}</div></article>)}</div>{!data.tickets.length&&<p className="empty">Здесь пока нет билетов.</p>}{data.has_more&&<button className="secondary" onClick={()=>void more()}>Показать ещё</button>}</section>}

function Profile({account}:{account:Account|null}){if(!account)return <section className="content"><p>Загрузка…</p></section>;const rate=account.ticket_count?account.winning_ticket_count/account.ticket_count*100:0;const net=account.total_won-account.total_spent;return <section className="content"><div className="profile-hero"><p className="eyebrow">ЛИЧНАЯ СТАТИСТИКА</p><h2>{account.display_name}</h2><strong>{cas(account.balance)}</strong></div><div className="stats-grid"><div><span>Всего билетов</span><b>{account.ticket_count.toLocaleString("ru-RU")}</b></div><div><span>Выигрышных</span><b>{account.winning_ticket_count.toLocaleString("ru-RU")}</b></div><div><span>Процент выигрышей</span><b>{rate.toFixed(1)}%</b></div><div><span>Потрачено</span><b>{cas(account.total_spent)}</b></div><div><span>Выиграно</span><b>{cas(account.total_won)}</b></div><div className={net>=0?"positive":"negative"}><span>Итог</span><b>{net>=0?"+":"−"} {cas(Math.abs(net))}</b></div><div><span>Крупнейший выигрыш</span><b>{cas(account.best_win)}</b></div><div><span>Любимая лотерея</span><b>{account.favorite_lottery_name??"—"}</b></div><div><span>Любимые числа</span><b>{account.favorite_numbers.join(" · ")||"—"}</b></div></div></section>}

export default function App() {
  const [session,setSession]=useState<WebSession|null>(null);
  const [checking,setChecking]=useState(true);
  const [dashboard,setDashboard]=useState<Dashboard|null>(null);
  const [account,setAccount]=useState<Account|null>(null);
  const [view,setView]=useState<View>("lotteries");
  const [ticketState,setTicketState]=useState<"active"|"history">("active");
  const [picker,setPicker]=useState<Lottery|null>(null);
  const [bingo,setBingo]=useState(false);
  const [notice,setNotice]=useState("");
  const [error,setError]=useState("");
  const [live,setLive]=useState<{standard:LiveDraw|null;grob:LiveDraw|null}>({standard:null,grob:null});
  const [now,setNow]=useState(()=>Date.now());
  const clockOffset=useRef(0);
  const refresh=useCallback(async()=>{
    const [d,a]=await Promise.all([webApi.dashboard(),webApi.account()]);
    clockOffset.current=new Date(d.server_time).getTime()-Date.now();
    setDashboard(d);setAccount(a);
  },[]);
  useEffect(()=>{
    let active=true;
    webApi.session().then(value=>{if(active)setSession(value)})
      .catch(()=>{if(active)setSession(null)}).finally(()=>{if(active)setChecking(false)});
    return()=>{active=false};
  },[]);
  useEffect(()=>{
    if(!session)return;
    const update=()=>void refresh().catch(e=>setError(e instanceof Error?e.message:"Не удалось обновить данные"));
    update();
    const timer=window.setInterval(update,view==="fast"||view==="live"?5000:30000);
    const visible=()=>{if(!document.hidden)update()};
    document.addEventListener("visibilitychange",visible);
    return()=>{window.clearInterval(timer);document.removeEventListener("visibilitychange",visible)};
  },[session,refresh,view]);
  useEffect(()=>{
    if(!session)return;
    const timer=window.setInterval(()=>setNow(Date.now()+clockOffset.current),1000);
    return()=>window.clearInterval(timer);
  },[session]);
  useEffect(()=>{
    if(!session||view!=="live")return;
    let cancelled=false;
    const update=async()=>{try {
      const [standard,grob]=await Promise.all([webApi.live("standard"),webApi.live("standard","grob")]);
      if(!cancelled)setLive({standard:liveDraw(standard),grob:liveDraw(grob)});
    }catch(e){if(!cancelled)setError(e instanceof Error?e.message:"Эфир временно недоступен")}};
    void update();const timer=window.setInterval(()=>void update(),3000);
    return()=>{cancelled=true;window.clearInterval(timer)};
  },[session,view]);
  const ordered=useMemo(()=>[...(dashboard?.lotteries??[])].sort((a,b)=>
    new Date(a.scheduled_at??"9999").getTime()-new Date(b.scheduled_at??"9999").getTime()),[dashboard]);
  const grobLottery=ordered.find(item=>item.code==="grob");
  const showGrobLive=Boolean(live.grob&&(live.standard?.lottery_code==="grob"||(now>=Date.parse(live.grob.live_starts_at)&&now<=Date.parse(live.grob.live_ends_at)+30_000)));
  const openLottery=async(lottery:Lottery)=>{
    try {
      const d=await webApi.dashboard();setDashboard(d);
      const latest=d.lotteries.find(l=>l.code===lottery.code);
      if(!latest){setError("Игра временно недоступна.");return}
      if(!latest.purchase_available&&!isGrobLottery(latest)&&!isKhanLottery(latest)){setError("Продажи закрыты. Дождитесь следующего тиража.");return}
      if(latest.code==="bingo")setBingo(true);else setPicker(latest);
    }catch(e){setError(e instanceof Error?e.message:"Не удалось открыть игру")}
  };
  if(checking)return <main className="loading"><Brand/><span>Открываем Casper…</span></main>;
  if(!session)return <Login onDone={setSession}/>;
  const bought=(message:string)=>{
    setPicker(null);setBingo(false);setNotice(message);
    void refresh().catch(()=>setError("Покупка завершена. Обновление баланса задерживается."));
  };
  const names:Record<View,string>={lotteries:"Коллекция",fast:"Casper Fast",live:"Эфир",tickets:"Мои билеты",profile:"Профиль"};
  if(picker?.code.toLowerCase()==="grob")return <Suspense fallback={<main className="grob-loading-shell">Открываем Casper Halloween</main>}><GrobExperienceHost lottery={picker} balance={dashboard?.balance??0} userId={session.user_id} onClose={()=>setPicker(null)} onBalance={balance=>setDashboard(current=>current?{...current,balance}:current)}/></Suspense>;
  if(picker&&isKhanLottery(picker))return <Suspense fallback={<main className="khan-loading-shell">Готовим классический тираж</main>}><KhanExperienceHost lottery={picker} balance={dashboard?.balance??0} userId={session.user_id} onClose={()=>setPicker(null)} onBalance={balance=>setDashboard(current=>current?{...current,balance}:current)}/></Suspense>;
  return <div className={`app ${view==="fast"?"fast-mode":""}`}>
    <header className="site-header"><button className="brand-button" onClick={()=>setView("lotteries")} aria-label="Casper Loto — коллекция"><Brand/></button>
      <nav aria-label="Основная навигация">{(Object.keys(names) as View[]).map(item=><button key={item} aria-current={view===item?"page":undefined} className={`${view===item?"active":""} ${item==="fast"?"fast-nav":""}`} onClick={()=>{setView(item);setError("")}}>{names[item]}</button>)}</nav>
      <div className="header-live-status"><i /> <span>LIVE / СЕЙЧАС</span><b>Открыть эфир</b></div><button className="balance-button" onClick={()=>setView("profile")}><span>ВАШ БАЛАНС</span><strong>{cas(dashboard?.balance??0)}</strong></button>
    </header>
    <main className="main-stage">
      {notice&&<div role="status" className="toast">{notice}<button aria-label="Закрыть уведомление" onClick={()=>setNotice("")}>×</button></div>}
      {error&&<div role="alert" className="error global-error">{error}<button onClick={()=>{setError("");void refresh().catch(()=>setError("Сервер недоступен. Повторите позже."))}}>Обновить</button></div>}
      {view==="lotteries"&&<LotteryGallery lotteries={ordered.filter(l=>!fastCodes.has(l.code))} now={now} onOpen={l=>void openLottery(l)}/>}
      {view==="fast"&&<FastExperience lotteries={ordered.filter(l=>fastCodes.has(l.code))} now={now} balance={dashboard?.balance??0} userId={session.user_id} onBought={bought} onTickets={()=>setView("tickets")}/>}
      {view==="live"&&<><div className="page-heading"><span className="eyebrow">CASPER LIVE / СОБЫТИЯ</span><h1>В первом ряду.</h1></div>{showGrobLive&&live.grob&&grobLottery&&<section className="content live-grid grob-live-grid"><Suspense fallback={<div className="grob-live-loading">Готовим праздничный эфир</div>}><GrobLiveHost draw={live.grob} lottery={grobLottery} balance={dashboard?.balance??0} now={now}/></Suspense></section>}{(!showGrobLive||live.standard?.lottery_code!=="grob")&&<section className="content live-grid"><LiveStage draw={live.standard} now={now}/></section>}<FastExperience lotteries={ordered.filter(l=>fastCodes.has(l.code))} now={now} balance={dashboard?.balance??0} userId={session.user_id} onBought={bought} onTickets={()=>setView("tickets")}/></>}
      {view==="tickets"&&<><div className="page-heading"><span className="eyebrow">ВАША КОЛЛЕКЦИЯ МОМЕНТОВ</span><h1>Мои билеты.</h1></div><div className="tabs"><button aria-pressed={ticketState==="active"} className={ticketState==="active"?"active":""} onClick={()=>setTicketState("active")}>В игре</button><button aria-pressed={ticketState==="history"} className={ticketState==="history"?"active":""} onClick={()=>setTicketState("history")}>История</button></div><Tickets key={ticketState} state={ticketState}/></>}
      {view==="profile"&&<><Profile account={account}/><section className="profile-identity"><span className="eyebrow">ВАШ УНИКАЛЬНЫЙ CASPER ID</span><code>{session.user_id}</code><button className="text-button" onClick={()=>void webApi.logout().then(()=>{setSession(null);setDashboard(null);setAccount(null)}).catch(()=>setError("Не удалось выйти. Повторите попытку."))}>Выйти из аккаунта ↗</button></section><AddPassword/></>}
    </main>
    <footer className="site-footer"><Brand/><p>Игра ради момента.<br/>CAS — виртуальные игровые единицы. Не покупаются и не обмениваются на деньги.</p><span>CASPER LOTO<br/>PRIVATE ENTERTAINMENT</span></footer>
    {picker&&<Picker lottery={picker} onClose={()=>setPicker(null)} onBought={bought}/>}
    {bingo&&<BingoPicker onClose={()=>setBingo(false)} onBought={bought}/>}
  </div>;
}
