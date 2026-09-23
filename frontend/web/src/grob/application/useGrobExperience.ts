import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, webApi } from "../../api";
import type { Dashboard, Lottery } from "../../types";
import type { GrobBridge } from "../bridge/GrobBridge";
import type { GrobIntent, GrobPhase, GrobPurchaseView, GrobSnapshot, QuickQuantity } from "../bridge/contracts";
import { clearPendingPurchase, loadPendingPurchase, savePendingPurchase, type PendingGrobPurchase } from "./pending-purchase";
import { createRandomTickets } from "./random-ticket";
import { selectionPhase, toggleSelection } from "./grob-reducer";

const emptyPurchase: GrobPurchaseView = { mode: null, quantity: null, status: "idle", message: "", ticketIds: [] };
const emptyLive = { draw: null, revealedNumbers: [], revealCount: 0, resultKind: "waiting" as const };

export function useGrobExperience({ bridge, initialLottery, initialBalance, userId, onExit, onBalance }:{bridge:GrobBridge;initialLottery:Lottery;initialBalance:number;userId:string;onExit:()=>void;onBalance:(balance:number)=>void}) {
  const recovered = useMemo(() => loadPendingPurchase(userId), [userId]);
  const [lottery, setLottery] = useState(initialLottery);
  const [balance, setBalance] = useState(initialBalance);
  const [selected, setSelected] = useState<number[]>([]);
  const [phase, setPhase] = useState<GrobPhase>(() => recovered ? "purchaseUncertain" : selectionPhase([], initialLottery.purchase_available));
  const [purchase, setPurchase] = useState<GrobPurchaseView>(() => recovered ? {mode:recovered.mode,quantity:recovered.quantity,status:"uncertain",message:"Есть незавершённая печать. Повторите запрос.",ticketIds:[]} : emptyPurchase);
  const [clockOffset, setClockOffset] = useState(0);
  const [serverNow, setServerNow] = useState(() => Date.now());
  const [muted, setMuted] = useState(true);
  const revision = useRef(0);
  const inFlight = useRef(false);
  const pending = useRef<PendingGrobPurchase | null>(recovered);
  const abort = useRef(new AbortController());
  const reducedMotion = useMemo(() => matchMedia("(prefers-reduced-motion: reduce)").matches, []);

  const syncDashboard = useCallback(async (): Promise<Dashboard> => {
    const dashboard = await webApi.dashboard(abort.current.signal);
    const latest = dashboard.lotteries.find(item => item.code === "grob");
    if (latest) { setLottery(latest); if (!latest.purchase_available) setPhase("drawWaiting"); else setPhase(current => current === "drawWaiting" || current === "reconnecting" ? "idle" : current); }
    setClockOffset(Date.parse(dashboard.server_time) - Date.now());
    setBalance(dashboard.balance);
    onBalance(dashboard.balance);
    return dashboard;
  }, [onBalance]);

  const runPurchase = useCallback(async (attempt: PendingGrobPurchase) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setPhase("purchasePending");
    setPurchase({ mode: attempt.mode, quantity: attempt.quantity, status: "pending", message: "Печать ставится", ticketIds: [] });
    try {
      const result = await webApi.purchase("grob", attempt.combinations, attempt.key, 1, abort.current.signal);
      clearPendingPurchase(userId); pending.current = null;
      setBalance(result.balance_after); onBalance(result.balance_after);
      setPurchase({ mode: attempt.mode, quantity: attempt.quantity, status: "success", message: `Билет${result.ticket_ids.length > 1 ? "ы" : ""} принят${result.ticket_ids.length > 1 ? "ы" : ""} · ${result.ticket_ids.length}`, ticketIds: result.ticket_ids });
      setPhase("purchaseSuccess");
      window.setTimeout(() => { setSelected([]); setPurchase(emptyPurchase); setPhase("idle"); }, 850);
      void syncDashboard().catch(() => undefined);
    } catch (reason) {
      const final = reason instanceof ApiError && [402, 409, 422].includes(reason.status);
      if (final) { clearPendingPurchase(userId); pending.current = null; }
      const message = reason instanceof ApiError ? reason.message : "Ответ не получен. Повторите ту же печать.";
      setPurchase({ mode: attempt.mode, quantity: attempt.quantity, status: final ? "error" : "uncertain", message, ticketIds: [] });
      setPhase(final ? "purchaseError" : "purchaseUncertain");
    } finally { inFlight.current = false; }
  }, [onBalance, syncDashboard, userId]);

  const beginPurchase = useCallback(async (mode: "manual" | "quick", quantity: QuickQuantity) => {
    if (inFlight.current) return;
    try {
      const fresh = await syncDashboard();
      const current = fresh.lotteries.find(item => item.code === "grob");
      if (!current || !current.purchase_available || current.draw_number !== lottery.draw_number) { setPhase("drawWaiting"); return; }
      if (current.primary_numbers_to_pick !== 3 || current.primary_max_number !== 16 || current.draw_number == null || current.ticket_price == null) {
        setPurchase({ mode, quantity, status: "error", message: "Игра обновилась. Покупка временно закрыта.", ticketIds: [] }); return;
      }
      const combinations = mode === "manual" ? [selected.slice().sort((a,b)=>a-b)] : createRandomTickets(quantity, current.primary_max_number, current.primary_numbers_to_pick);
      if (mode === "manual" && combinations[0].length !== 3) return;
      const attempt: PendingGrobPurchase = { key: crypto.randomUUID(), userId, drawNumber: current.draw_number, price: current.ticket_price, mode, combinations, quantity, createdAt: new Date().toISOString() };
      savePendingPurchase(attempt); pending.current = attempt; await runPurchase(attempt);
    } catch (reason) {
      setPurchase({ mode, quantity, status: "error", message: reason instanceof Error ? reason.message : "Сервер недоступен", ticketIds: [] });
      setPhase("purchaseError");
    }
  }, [lottery.draw_number, runPurchase, selected, syncDashboard, userId]);

  useEffect(() => {
    const unsubscribe = bridge.subscribeIntent((intent: GrobIntent) => {
      if (intent.type === "EXIT") onExit();
      else if (intent.type === "SET_MUTED") setMuted(intent.muted);
      else if (intent.type === "RETRY_PURCHASE" && pending.current) void runPurchase(pending.current);
      else if (intent.type === "TOGGLE_NUMBER" && !inFlight.current && lottery.purchase_available) setSelected(current => {const next=toggleSelection(current,intent.value,lottery.primary_max_number,lottery.primary_numbers_to_pick);setPhase(selectionPhase(next,lottery.purchase_available));return next;});
      else if (intent.type === "BUY_MANUAL" && selected.length === lottery.primary_numbers_to_pick) void beginPurchase("manual", 1);
      else if (intent.type === "BUY_QUICK") void beginPurchase("quick", intent.quantity);
    });
    return unsubscribe;
  }, [beginPurchase, bridge, lottery, onExit, runPurchase, selected.length]);

  useEffect(() => { const timer = window.setInterval(() => setServerNow(Date.now() + clockOffset), 500); return () => window.clearInterval(timer); }, [clockOffset]);
  useEffect(() => {
    void syncDashboard().catch(() => setPhase("reconnecting"));
    const timer = window.setInterval(() => void syncDashboard().catch(() => setPhase("reconnecting")), 30000);
    return () => window.clearInterval(timer);
  }, [syncDashboard]);
  useEffect(() => { if (abort.current.signal.aborted) abort.current = new AbortController(); return () => abort.current.abort(); }, []);

  const snapshot = useMemo<GrobSnapshot>(() => ({ revision: 0, phase, lottery, balance, selectedNumbers: selected, salesOpen: lottery.purchase_available, serverNow, purchase, live: emptyLive, reducedMotion, muted }), [balance,lottery,muted,phase,purchase,reducedMotion,selected,serverNow]);
  useEffect(() => { bridge.publish({...snapshot,revision:++revision.current}); }, [bridge, snapshot]);
  return snapshot;
}
