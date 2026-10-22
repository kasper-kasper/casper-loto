import { tr } from "./i18n";
import { useCallback, useEffect, useState } from "react";
import { miniAppApi } from "./api";
import type { CollectionState } from "./collectionTypes";

export function useProfileCosmetics(initData: string) {
  const [data,setData]=useState<CollectionState|null>(null);
  const [error,setError]=useState("");
  const [retry,setRetry]=useState(0);
  useEffect(()=>{
    let live=true;
    async function load(){ try { const result=await miniAppApi.collection(initData); if(live){setData(result);setError("");} } catch { if(live)setError(tr("Не удалось загрузить коллекцию")); } }
    void load();
    return ()=>{live=false;};
  },[initData,retry]);
  const refresh=useCallback(()=>setRetry(v=>v+1),[]);
  return {data,setData,error,refresh};
}
