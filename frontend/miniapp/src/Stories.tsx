import { useCallback, useEffect, useRef, useState } from "react";
import type { Publication } from "../../shared/publications";
import { PublicationArtwork } from "./PublicationArtwork";
import { miniAppApi } from "./api";
import "./stories.css";

export function Stories({ initData, onOpen }: { initData: string; onOpen: (code: string) => void }) {
  const [items, setItems] = useState<Publication[]>([]), [index, setIndex] = useState<number | null>(null), [error, setError] = useState(false), [more, setMore] = useState(false), [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null), touchStart = useRef<number | null>(null), controller = useRef<AbortController | null>(null);
  const load = useCallback(async (before?: string) => { controller.current?.abort();const abort = new AbortController();controller.current = abort;setBusy(true);try { const rows = await miniAppApi.publications(initData, before, abort.signal);if (abort.signal.aborted) return;setItems(current => before ? [...current, ...rows.filter(row => !current.some(item => item.id === row.id))] : rows);setMore(rows.length === 30);setError(false); } catch { if (!abort.signal.aborted) setError(true); } finally { if (!abort.signal.aborted) setBusy(false); } }, [initData]);
  useEffect(() => { const start = window.setTimeout(() => void load(), 0);return () => { window.clearTimeout(start);controller.current?.abort(); }; }, [load]);
  useEffect(() => { if (index !== null && !dialog.current?.open) dialog.current?.showModal(); }, [index]);
  const selected = index === null ? null : items[index];
  function close() { dialog.current?.close();setIndex(null); }
  function step(direction: number) { setIndex(current => current === null ? null : Math.max(0, Math.min(items.length - 1, current + direction))); }
  if (!items.length && !error) return null;
  return <section className="home-stories" aria-label="Новости Casper"><header><h2>Новости Casper</h2><span>{items.length ? `${items.length} историй` : ""}</span></header>
    {error && <button type="button" className="stories-retry" disabled={busy} onClick={() => void load()}>Не удалось загрузить новости · повторить</button>}
    <div className="stories-strip">{items.map((item, position) => <button type="button" key={item.id} onClick={() => setIndex(position)} className="story-cover" style={{ backgroundColor: item.content.template.base, borderColor: item.content.template.accent }}><img src={item.content.template.formats.story.background} alt="" width={1080} height={1920} loading="lazy" /><span className="story-cover-game" style={{ color: item.content.template.accent }}>{item.content.template.lotteryLabel}</span><strong>{item.content.fields.title}</strong><small>Читать ↗</small></button>)}{more && <button type="button" className="story-more" disabled={busy} onClick={() => void load(items.at(-1)?.id)}>{busy ? "Загружаем…" : "Ещё истории →"}</button>}</div>
    <dialog ref={dialog} className="story-dialog" aria-label={selected?.content.fields.title ?? "История"} onClose={() => setIndex(null)} onKeyDown={event => { if (event.key === "ArrowRight") { event.preventDefault();step(1); }if (event.key === "ArrowLeft") { event.preventDefault();step(-1); } }}>
      {selected && <><div className="story-dialog-controls"><span>{index! + 1} / {items.length}</span><button autoFocus type="button" aria-label="Закрыть историю" onClick={close}>×</button></div><div onTouchStart={event => { touchStart.current = event.touches[0]?.clientX ?? null; }} onTouchEnd={event => { const start = touchStart.current, end = event.changedTouches[0]?.clientX;touchStart.current = null;if (start !== null && end !== undefined && Math.abs(end - start) > 60) step(end < start ? 1 : -1); }}><PublicationArtwork template={selected.content.template} fields={selected.content.fields} ctaLabel={selected.content.cta_label} onOpen={() => { close();onOpen(selected.lottery_code); }} /></div><nav className="story-dialog-navigation" aria-label="Листать истории"><button type="button" disabled={index === 0} onClick={() => step(-1)}>← Назад</button><button type="button" disabled={index === items.length - 1} onClick={() => step(1)}>Далее →</button></nav></>}
    </dialog>
  </section>;
}

