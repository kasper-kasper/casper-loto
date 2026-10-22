import { tr } from "./i18n";
import { useEffect, useState, type ReactNode } from "react";
import { Skeleton } from "./components";

export function MaintenanceGate({ children }: { children: ReactNode }) {
  const preview = import.meta.env.VITE_DESIGN_PREVIEW === "true";
  const [state, setState] = useState<"checking" | "paused" | "open" | "error">(preview ? "open" : "checking");
  const check = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? ""}/api/v1/miniapp/maintenance`, { cache: "no-store" });
      if (!response.ok) throw new Error("Status unavailable");
      const data = await response.json() as { maintenance: boolean };
      if (typeof data.maintenance !== "boolean") throw new Error("Invalid status");
      setState(data.maintenance ? "paused" : "open");
    } catch { setState("error"); }
  };
  useEffect(() => {
    const task = !preview ? window.setTimeout(() => void check(), 0) : null;
    const pause = () => setState("paused");
    window.addEventListener("economy-maintenance", pause);
    return () => { if (task !== null) window.clearTimeout(task); window.removeEventListener("economy-maintenance", pause); };
  }, [preview]);
  if (state === "checking") return <Skeleton />;
  if (state === "open") return children;
  return <main className="economy-maintenance" aria-live="polite">
    <div className="economy-maintenance__orb" aria-hidden="true">✦</div>
    <small>CASPER LOTO</small>
    <h1>{state === "error" ? tr("Не удалось подключиться") : tr("Техническая пауза")}</h1>
    <p>{state === "error" ? tr("Попробуй проверить подключение ещё раз.") : tr("Приложение на технической паузе. Сейчас готовим обновление.")}</p>
    {state === "paused" && <p>{tr("Покупки и розыгрыши приостановлены.")}</p>}
    <button type="button" onClick={() => { setState("checking"); void check(); }}>{tr("Проверить снова")}</button>
  </main>;
}
