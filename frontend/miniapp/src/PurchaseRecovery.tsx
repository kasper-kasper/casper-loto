import { useEffect, useState } from "react";
import { rawRequest } from "./api";
import { cancelPurchase, completePurchase, durablePurchase, journalEvent, purchaseActive, readPurchase, receiptGame } from "./purchaseJournal";
import type { PendingPurchase, Receipt } from "./purchaseJournal";
import { formatCas } from "./format";

export function PurchaseRecovery({ initData }: { initData: string }) {
  const [pending, setPending] = useState<PendingPurchase | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<Receipt | null>(null);
  useEffect(() => {
    let running = false, disposed = false;
    const check = async () => {
      if (running || purchaseActive() || document.visibilityState === "hidden") return;
      running = true;
      try {
        const value = readPurchase();
        if (!disposed) setPending(value);
        if (!value) return;
        const response = value.receipt ? { receipt: value.receipt } : await rawRequest<{ receipt: Receipt | null }>(
          `/api/v1/miniapp/purchase-receipts/${encodeURIComponent(value.key)}?game=${receiptGame(value)}`, initData);
        if (disposed || purchaseActive() || readPurchase()?.key !== value.key) return;
        if (response.receipt) {
          await completePurchase(value, response.receipt, true);
          setResult(response.receipt); setPending(readPurchase()); setMessage(null);
        }
      } catch (reason) {
        if (!disposed) setMessage(reason instanceof Error ? reason.message : "Нет связи. Проверим покупку, когда интернет вернётся.");
      } finally { running = false; }
    };
    const changed = () => { void check(); };
    const timer = window.setInterval(changed, 5_000);
    window.addEventListener(journalEvent, changed);
    window.addEventListener("online", changed);
    window.addEventListener("storage", changed);
    document.addEventListener("visibilitychange", changed);
    changed();
    return () => {
      disposed = true; window.clearInterval(timer);
      window.removeEventListener(journalEvent, changed); window.removeEventListener("online", changed);
      window.removeEventListener("storage", changed); document.removeEventListener("visibilitychange", changed);
    };
  }, [initData]);
  const resolve = async (cancel: boolean) => {
    if (!pending || busy || purchaseActive()) return;
    setBusy(true); setMessage(null);
    try {
      let receipt: Receipt | null;
      if (cancel) {
        const response = await cancelPurchase(pending, () => rawRequest<{ cancelled: boolean; receipt: Receipt | null }>(
          `/api/v1/miniapp/purchase-receipts/${encodeURIComponent(pending.key)}/cancel?game=${receiptGame(pending)}`, initData, { method: "POST" }));
        receipt = response.receipt;
        if (!receipt && response.cancelled) {
          setPending(readPurchase()); setMessage("Неподтверждённая покупка отменена. Билеты из корзины можно купить заново.");
        }
      } else {
        receipt = await durablePurchase(pending.path, pending.body,
          () => rawRequest<Receipt>(pending.path, initData, { method: "POST", body: pending.body }), () => false, pending.cartIds, true);
      }
      if (receipt) {
        if (cancel) await completePurchase(pending, receipt, true);
        setResult(receipt); setPending(readPurchase());
      }
    } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Связь прервалась. Покупку пока не удалось проверить."); }
    finally { setBusy(false); }
  };
  if (!pending && !result && !message) return null;
  return <aside className="purchase-recovery" role="status" aria-live="polite">
    <strong>{result ? "Покупка найдена" : pending ? "Проверяем предыдущую покупку" : "Проверка покупки"}</strong>
    {pending && <p>Ответ потерялся, но билеты могли быть куплены. Повтор отправит тот же запрос без второй покупки. Отмена затрагивает только ещё не выполненный запрос.</p>}
    {result && <p>Билетов: {"tickets" in result ? result.tickets.length : result.ticket_ids.length} · стоимость {formatCas(result.total_cost)}.{"total_prize" in result && ` Выигрыш: ${formatCas(result.total_prize)}.`} Билеты доступны в разделе «Мои билеты».</p>}
    {message && <p>{message}</p>}
    {pending ? <div><button disabled={busy} onClick={() => void resolve(false)}>{busy ? "Проверяем…" : "Повторить этот запрос"}</button><button disabled={busy} onClick={() => void resolve(true)}>Отменить неподтверждённую покупку</button></div>
      : <button onClick={() => { setResult(null); setMessage(null); }}>Понятно</button>}
  </aside>;
}
