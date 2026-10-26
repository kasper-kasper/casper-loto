import { tr } from "./i18n";
import { useCallback, useEffect, useRef, useState } from "react";
import { miniAppApi } from "./api";
import { AchievementBadge } from "./AchievementBadge";
import type { AchievementNotice, AchievementTarget } from "./achievementTypes";
import { AchievementRewards } from "./AchievementRewards";
import { AchievementTitle } from "./AchievementTitle";
import "./achievements.css";

/** Fetch only on entry, return to foreground or a committed purchase. No polling. */
export function AchievementNotices({ initData, enabled = true, suppressed = false, onOpen }: { initData: string; enabled?: boolean; suppressed?: boolean; onOpen?: (target: AchievementTarget) => void }) {
  const [queue, setQueue] = useState<AchievementNotice[]>([]);
  const shown = useRef(new Set<string>());
  const lastUpdate = useRef("");
  const pendingAck = useRef(new Set<string>());
  const [interacting, setInteracting] = useState(false);
  const acknowledge = useCallback((ids: string[]) => {
    const unseen = [...new Set(ids)].filter(id => !shown.current.has(id));
    unseen.forEach(id => { shown.current.add(id); pendingAck.current.add(id); });
    for (let index = 0; index < unseen.length; index += 10) {
      const batch = unseen.slice(index, index + 10);
      void miniAppApi.achievementSeen(initData, batch).then(() => batch.forEach(id => pendingAck.current.delete(id))).catch(() => undefined);
    }
  }, [initData]);
  useEffect(() => {
    if (!enabled || !suppressed || !queue.length) return;
    let active = true;
    acknowledge(queue.map(item => item.notification_id));
    // Clear the old UI queue even if its acknowledgement needs a network retry.
    void Promise.resolve().then(() => { if (active) setQueue([]); });
    return () => { active = false; };
  }, [enabled, suppressed, queue, acknowledge]);
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
        if (active) {
          if (suppressed) acknowledge(data.map(item => item.notification_id));
          else setQueue(current => {
            const remaining = current.filter(item => !shown.current.has(item.notification_id));
            const known = new Set(remaining.map(item => item.notification_id));
            return [...remaining, ...data.filter(item => !known.has(item.notification_id) && !shown.current.has(item.notification_id))];
          });
        }
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
  }, [initData, enabled, suppressed, acknowledge]);
  const current = queue[0];
  useEffect(() => {
    if (!current || !enabled || suppressed || interacting) return;
    const timer = window.setTimeout(() => {
      acknowledge([current.notification_id]);
      setQueue(value => value.filter(item => item.notification_id !== current.notification_id));
      window.dispatchEvent(new Event("achievements:refresh"));
    }, 6500);
    return () => window.clearTimeout(timer);
  }, [current, enabled, suppressed, interacting, acknowledge]);
  // Remounting after a preference change discards the old client queue.
  if (!current || !enabled || suppressed) return null;

  function dismiss() {
    if (!current) return;
    acknowledge([current.notification_id]);
    setQueue(value => value.filter(item => item.notification_id !== current.notification_id));
    setInteracting(false);
  }

  return <aside className={`achievement-toast rarity-${current.rarity}`} role="status" aria-live="polite" key={current.notification_id} onMouseEnter={() => setInteracting(true)} onMouseLeave={() => setInteracting(false)} onFocusCapture={() => setInteracting(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setInteracting(false); }}><button className="achievement-toast-open" type="button" aria-label={tr("Открыть достижение «{0}»", tr(current.title))} onClick={() => { dismiss(); onOpen?.({ code: current.code, category: current.secret ? "secret" : current.rarity }); }}><AchievementBadge item={current} /><span><strong><AchievementTitle item={current} /></strong><AchievementRewards item={current} compact /></span></button><button className="achievement-toast-dismiss" type="button" aria-label={tr("Скрыть уведомление о достижении")} onClick={dismiss}>×</button></aside>;
}
