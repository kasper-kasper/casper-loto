import { tr } from "./i18n";
import { useEffect, useRef, useState } from "react";
import { miniAppApi } from "./api";
import { LegendaryBadge } from "./LegendaryBadge";
import { AchievementTitle } from "./AchievementTitle";
import { formatMoscow } from "./format";
import "./collection.css";
import { useProfileCosmetics } from "./useProfileCosmetics";
import type { CollectionItem } from "./collectionTypes";

function BadgePreview({item,onClose}:{item:CollectionItem;onClose:()=>void}){
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{const node=dialog.current;if(node&&!node.open)node.showModal();return()=>node?.close();},[]);
  return <dialog ref={dialog} className="achievement-dialog collection-badge-dialog" aria-label={tr("Предпросмотр: {0}", tr(item.title))} onCancel={event=>{event.preventDefault();onClose();}} onClick={event=>{if(event.target===event.currentTarget)onClose();}}><div className="achievement-detail"><button type="button" className="achievement-close" aria-label={tr("Закрыть предпросмотр значка")} onClick={onClose}>×</button><small>{tr("Предпросмотр значка")}</small><LegendaryBadge game={item.game}/><h2>{tr(item.game === "casper-master" ? <AchievementTitle item={{code:"legendary_casper_move_over", title:item.title, rarity:"legendary", secret:false}} /> : item.title)}</h2><p>{tr(item.description)}</p><p>{item.unlocked?tr("Значок открыт и доступен для выбора."):tr("Значок откроется после выполнения условия. Предпросмотр не выдаёт награду.")}</p></div></dialog>;
}

export function Collection({initData,onBack}:{initData:string;onBack:()=>void}){
  const {data,setData,error,refresh}=useProfileCosmetics(initData);
  const [tab,setTab]=useState<"badge"|"theme">("badge");
  const [busy,setBusy]=useState(false);
  const [saveError,setSaveError]=useState("");
  const [preview,setPreview]=useState<string|null>(null);
  const [badgePreview,setBadgePreview]=useState<CollectionItem|null>(null);
  const previewTheme=preview ?? data?.active_theme ?? "theme:standard";
  async function choose(badge:string|null,theme:string|null){
    if(busy||!data)return;
    setBusy(true);setSaveError("");
    try{ const selected=await miniAppApi.chooseCollection(initData,badge,theme); setData({...data,...selected});setPreview(null); }
    catch(reason){setSaveError(reason instanceof Error?reason.message:tr("Не удалось сохранить выбор"));}
    finally{setBusy(false);}
  }
  return <section className="collection-screen"><button type="button" className="achievement-back" onClick={onBack}>{tr("← В профиль")}</button><header><span>{tr("CASPER LOTO / ПРОФИЛЬ")}</span><h1>{tr("Коллекция")}</h1><p>{tr("Твои достижения. Твой стиль.")}</p></header>
    <div className={`collection-preview profile-theme-${previewTheme.split(":")[1]}`}><span className="collection-preview-label">{preview ? tr("Предпросмотр") : tr("Твоё оформление")}</span><div>{data?.active_badge && <LegendaryBadge game={data.active_badge.slice(6)} compact />}<strong>{tr("Твой профиль")}</strong></div><p>{previewTheme==="theme:beyond"?tr("За гранью"):previewTheme==="theme:gold"?tr("Золотая тема"):tr("Стандартная тема")}</p><small>{tr("Оформление видно только тебе")}</small></div>
    <nav className="collection-tabs" aria-label={tr("Раздел коллекции")}><button type="button" aria-pressed={tab==="badge"} onClick={()=>setTab("badge")}>{tr("Значки")}</button><button type="button" aria-pressed={tab==="theme"} onClick={()=>setTab("theme")}>{tr("Темы профиля")}</button></nav>
    {(error||saveError)&&<p role="alert">{tr(error||saveError)}{error&&<button type="button" onClick={refresh}>{tr("Повторить")}</button>}</p>}
    {!data&&!error&&<p role="status">{tr("Загружаем коллекцию…")}</p>}
    {data&&<><button type="button" className="collection-reset" disabled={busy} onClick={()=>void choose(tab==="badge"?null:data.active_badge,tab==="theme"?null:data.active_theme)}>{tab==="badge"?tr("Без значка"):tr("Стандартная тема")}{(tab==="badge"?!data.active_badge:!data.active_theme)&&tr(" · выбрано")}</button><div className="collection-grid">{data.items.filter(item=>item.kind===tab).map(item=>{
      const selected=item.code===(tab==="badge"?data.active_badge:data.active_theme);
      return <article className={`collection-item${item.unlocked?"":" collection-locked"}${selected?" collection-selected":""}`} key={item.code}>{item.kind==="badge"?<button type="button" className="collection-art-preview" aria-label={tr("Посмотреть значок: {0}", tr(item.title))} onClick={()=>setBadgePreview(item)}><LegendaryBadge game={item.game} locked={!item.unlocked}/></button>:<div aria-hidden="true" className={`collection-theme-swatch profile-theme-${item.code.split(":")[1]}`}><span>Casper</span><i/><i/></div>}<h2>{tr(item.game === "casper-master" ? <AchievementTitle item={{code:"legendary_casper_move_over", title:item.title, rarity:"legendary", secret:false}} /> : item.title)}</h2><p>{tr(item.description)}</p>{item.unlocked?<small>{tr("Открыто")} {tr(item.unlocked_at?formatMoscow(item.unlocked_at):"")}</small>:<small>{tr("Пока не открыто")}</small>}{item.kind==="theme"&&<button type="button" className="collection-look" onClick={()=>setPreview(item.code)}>{tr("Посмотреть оформление")}</button>}<button type="button" disabled={busy||!item.unlocked||selected} aria-label={tr(`${selected?tr("Выбрано"):tr("Выбрать")}: ${tr(item.title)}`)} onClick={()=>void choose(tab==="badge"?item.code:data.active_badge,tab==="theme"?item.code:data.active_theme)}>{selected?tr("Выбрано"):item.unlocked?tr("Выбрать"):tr("Заблокировано")}</button></article>;
    })}</div><p className="collection-note">{tr("Значок виден рядом с твоим именем. Темы меняют только твой профиль. Шансы и игровые выплаты остаются прежними.")}</p></>}{badgePreview&&<BadgePreview item={badgePreview} onClose={()=>setBadgePreview(null)}/>}
  </section>;
}
