import { tr } from "./i18n";
import { useEffect, useRef, useState } from "react";
import { miniAppApi } from "./api";
import { AchievementBadge } from "./AchievementBadge";
import type { AchievementNotice, AchievementTarget } from "./achievementTypes";
import { AchievementRewards } from "./AchievementRewards";
import { AchievementTitle } from "./AchievementTitle";
import "./achievements.css";

/** Fetch only on entry, return to foreground or a committed purchase. No polling. */
export function AchievementNotices({ initData, enabled = true, onOpen }: { initData: string; enabled?: boolean; onOpen?: (target: AchievementTarget) => void }) {
  const [queue, setQueue] = useState<AchievementNotice[]>([]);
  const shown = useRef(new Set<string>());
  const lastUpdate = useRef("");
  const pendingAck = useRef(new Set<string>());
  const [interacting, setInteracting] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    let active = true, inFlight = false;
    let timers: number[] = [];
    async function fetchNotices() {
      if (inFlight || document.visibilityState === "hidden") return;
      inFlight = true;
      try {
        if (pendingAck.current.size) {
          const ids = [...pendingAck.current].slice(0, 10);
          await miniAppApi.achievementSeen(initData, ids);
          if (active) ids.forEach(id => pendingAck.current.delete(id));
        }
        const data = await miniAppApi.achievementNotices(initData);
        const signature = JSON.stringify(data.map(item => [item.notification_id, item.reward_status]));
        if (active && data.length && signature !== lastUpdate.current) {
          lastUpdate.current = signature;
          window.dispatchEvent(new Event("achievements:updated"));
        }
        if (active) setQueue(current => {
          const known = new Set(current.map(item => item.notification_id));
          return [...current, ...data.filter(item => !known.has(item.notification_id) && !shown.current.has(item.notification_id))];
        });
      } catch { /* A missed toast never affects a persisted award. Retry on next entry/action. */ }
      finally { inFlight = false; }
    }
    function refresh() {
      timers.forEach(window.clearTimeout);
      // Give the bounded worker time to process the committed event.
      timers = [900, 3200, 7000].map(delay => window.setTimeout(() => { if (active) void fetchNotices(); }, delay));
    }
    function foreground() { if (document.visibilityState === "visible") refresh(); }
    refresh();
    window.addEventListener("achievements:refresh", refresh);
    document.addEventListener("visibilitychange", foreground);
    return () => { active = false; timers.forEach(window.clearTimeout); window.removeEventListener("achievements:refresh", refresh); document.removeEventListener("visibilitychange", foreground); };
  }, [initData, enabled]);
  const current = queue[0];
  useEffect(() => {
    if (!current || !enabled || interacting) return;
    const timer = window.setTimeout(() => {
      shown.current.add(current.notification_id);
      pendingAck.current.add(current.notification_id);
      void miniAppApi.achievementSeen(initData, [current.notification_id]).then(() => pendingAck.current.delete(current.notification_id)).catch(() => undefined);
      setQueue(value => value.filter(item => item.notification_id !== current.notification_id));
      window.dispatchEvent(new Event("achievements:refresh"));
    }, 6500);
    return () => window.clearTimeout(timer);
  }, [current, initData, enabled, interacting]);
  // Remounting after a preference change discards the old client queue.
  if (!current || !enabled) return null;

  function dismiss() {
    if (!current) return;
    shown.current.add(current.notification_id);
    pendingAck.current.add(current.notification_id);
    void miniAppApi.achievementSeen(initData, [current.notification_id]).then(() => pendingAck.current.delete(current.notification_id)).catch(() => undefined);
    setQueue(value => value.filter(item => item.notification_id !== current.notification_id));
    setInteracting(false);
  }

  return <aside className={`achievement-toast rarity-${current.rarity}`} role="status" aria-live="polite" key={current.notification_id} onMouseEnter={() => setInteracting(true)} onMouseLeave={() => setInteracting(false)} onFocusCapture={() => setInteracting(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setInteracting(false); }}><button className="achievement-toast-open" type="button" aria-label={tr("Открыть достижение «{0}»", tr(current.title))} onClick={() => { dismiss(); onOpen?.({ code: current.code, category: current.secret ? "secret" : current.rarity }); }}><AchievementBadge item={current} /><span><small>{tr("Достижение получено")}</small><strong><AchievementTitle item={current} /></strong><AchievementRewards item={current} compact /><span className="achievement-toast-hint">{tr("Посмотреть достижение")} →</span></span></button><button className="achievement-toast-dismiss" type="button" aria-label={tr("Скрыть уведомление о достижении")} onClick={dismiss}>×</button></aside>;
}
