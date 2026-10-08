import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import type { Publication } from "../../shared/publications";
import { PublicationArtwork } from "./PublicationArtwork";
import { miniAppApi } from "./api";
import "./stories.css";
import { lockInteractionViewport } from "./interactionLock";

function storedSeen(): string[] { try { const value: unknown = JSON.parse(localStorage.getItem("casper-news-seen") ?? "[]");return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string").slice(-100) : []; } catch { return []; } }

export function Stories({ initData, onOpen }: { initData: string; onOpen: (code: string) => void }) {
  const [items, setItems] = useState<Publication[]>([]), [index, setIndex] = useState<number | null>(null), [error, setError] = useState(false), [more, setMore] = useState(false), [busy, setBusy] = useState(false);
  const [seen, setSeen] = useState<string[]>(storedSeen);
  const [progress, setProgress] = useState(0), [paused, setPaused] = useState(false), [holding, setHolding] = useState(false);
  const elapsed = useRef(0);
  const hidden = useRef(document.hidden);
  const dialog = useRef<HTMLDialogElement>(null), gesture = useRef<{ x: number; y: number; at: number } | null>(null), ignoreTap = useRef(false), controller = useRef<AbortController | null>(null);
  const load = useCallback(async (before?: string) => { controller.current?.abort();const abort = new AbortController();controller.current = abort;setBusy(true);try { const rows = await miniAppApi.publications(initData, before, abort.signal);if (abort.signal.aborted) return;const remembered = storedSeen();setItems(rows.slice(0, 10).sort((a, b) => Number(remembered.includes(a.id)) - Number(remembered.includes(b.id))));setMore(false);setError(false); } catch { if (!abort.signal.aborted) setError(true); } finally { if (!abort.signal.aborted) setBusy(false); } }, [initData]);
  useEffect(() => { const start = window.setTimeout(() => void load(), 0);return () => { window.clearTimeout(start);controller.current?.abort(); }; }, [load]);
  useEffect(() => { if (index !== null && !dialog.current?.open) dialog.current?.showModal(); }, [index]);
  const selected = index === null ? null : items[index];
  const close = useCallback(() => { dialog.current?.close();setIndex(null);setPaused(false);setHolding(false);setItems(current => [...current].sort((a, b) => Number(seen.includes(a.id)) - Number(seen.includes(b.id)))); }, [seen]);
  const open = useCallback((position: number) => { const id = items[position]?.id;if (!id) return;const next = [...seen.filter(item => item !== id), id].slice(-100);setSeen(next);try { localStorage.setItem("casper-news-seen", JSON.stringify(next)); } catch { /* Reading news remains available without storage. */ }elapsed.current = 0;setProgress(0);setIndex(position); }, [items, seen]);
  const step = useCallback((direction: number) => { if (index === null) return;if (index + direction >= items.length) close();else open(Math.max(0, index + direction)); }, [index, items.length, close, open]);
  function tap(direction: number) { if (ignoreTap.current) { ignoreTap.current = false;return; }step(direction); }
  useEffect(() => {
    if (index === null || paused || holding) return;
    hidden.current = document.hidden;
    let previous = performance.now();
    const visibility = () => { hidden.current = document.hidden; previous = performance.now(); };
    document.addEventListener("visibilitychange", visibility);
    const timer = window.setInterval(() => {
      const now = performance.now(), delta = now - previous;previous = now;
      if (document.hidden || hidden.current) return;
      elapsed.current += delta;setProgress(Math.min(1, elapsed.current / 7000));
      if (elapsed.current >= 7000) { window.clearInterval(timer);step(1); }
    }, 50);
    return () => { window.clearInterval(timer); document.removeEventListener("visibilitychange", visibility); };
  }, [index, paused, holding, step]);
  const viewerOpen = index !== null;
  useEffect(() => {
    if (!viewerOpen) return;
    return lockInteractionViewport();
  }, [viewerOpen]);
  if (!items.length && !error) return null;
  return <section className="home-stories" aria-label="Новости Casper"><header><h2>Новости Casper</h2><span>{items.length ? `${items.length} историй` : ""}</span></header>
    {error && <button type="button" className="stories-retry" disabled={busy} onClick={() => void load()}>Не удалось загрузить новости · повторить</button>}
    <div className="stories-strip">{items.map((item, position) => <button type="button" key={item.id} onClick={() => open(position)} className="story-cover" style={{ backgroundColor: item.content.template.base, borderColor: item.content.template.accent, opacity: seen.includes(item.id) ? .55 : 1 }}><img src={item.content.template.formats.story.background} alt="" width={1080} height={1920} loading="lazy" /><span className="story-cover-game" style={{ color: item.content.template.accent }}>{item.content.template.lotteryLabel}</span><strong>{item.content.fields.title}</strong><small>Читать ↗</small></button>)}{more && <button type="button" className="story-more" disabled={busy} onClick={() => void load(items.at(-1)?.id)}>{busy ? "Загружаем…" : "Ещё истории →"}</button>}</div>
    <dialog ref={dialog} className="story-dialog" style={{ "--story-telegram-top": window.Telegram?.WebApp?.isFullscreen ? "56px" : "0px" } as CSSProperties} aria-label={selected?.content.fields.title ?? "История"} onClose={() => { setIndex(null);setPaused(false);setHolding(false); }} onKeyDown={event => { if (event.code === "Space" && !(event.target as Element).closest("button")) { event.preventDefault();setPaused(value => !value); }if (event.key === "ArrowRight") { event.preventDefault();step(1); }if (event.key === "ArrowLeft") { event.preventDefault();step(-1); } }}>
      {selected && <><header className="story-dialog-header"><div className="story-progress" aria-label={`${index! + 1} из ${items.length}`}>
        {items.map((item, position) => <span key={item.id} aria-current={position === index ? "step" : undefined}><i style={{ transform: `scaleX(${position < index! ? 1 : position === index ? progress : 0})` }} /></span>)}
      </div><div className="story-dialog-controls"><span>{selected.content.template.lotteryLabel}<small>{index! + 1} / {items.length}</small></span><div className="story-player-actions"><button autoFocus type="button" aria-label="Закрыть историю" onClick={close}>×</button></div></div></header>
      <div className="story-stage" onPointerDown={event => { if (event.button !== 0 || gesture.current || (event.target as Element).closest(".publication-story-cta")) return;(event.target as Element).setPointerCapture?.(event.pointerId);setHolding(true);ignoreTap.current = false;gesture.current = { x: event.clientX, y: event.clientY, at: Date.now() }; }} onPointerUp={event => {
        setHolding(false);const start = gesture.current;gesture.current = null;if (!start) return;
        const dx = event.clientX - start.x, dy = event.clientY - start.y;
        ignoreTap.current = Date.now() - start.at > 300 || Math.abs(dx) > 20 || Math.abs(dy) > 20;
        if (dy > 70 && Math.abs(dy) > Math.abs(dx)) close();else if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) step(dx < 0 ? 1 : -1);
      }} onPointerCancel={() => { setHolding(false);gesture.current = null;ignoreTap.current = true; }} onLostPointerCapture={() => { setHolding(false);gesture.current = null; }}>
        <PublicationArtwork template={selected.content.template} fields={selected.content.fields} ctaLabel={selected.content.cta_label} onOpen={() => { close();onOpen(selected.lottery_code); }} />
        <button className="story-tap story-tap-previous" type="button" aria-label="Предыдущая история" onClick={() => tap(-1)} />
        <button className="story-tap story-tap-next" type="button" aria-label="Следующая история" onClick={() => tap(1)} />
      </div></>}

    </dialog>
  </section>;
}

