import { tr, getLocale } from "./i18n";
import { useCallback, useEffect, useRef, useState } from "react";
import { miniAppApi } from "./api";
import { AchievementIcon } from "./AchievementIcon";
import { AchievementBadge } from "./AchievementBadge";
import type { Achievement, AchievementCategory, AchievementPage } from "./achievementTypes";
import { AchievementRewards } from "./AchievementRewards";
import { AchievementTitle } from "./AchievementTitle";
import { lockInteractionViewport } from "./interactionLock";
import "./achievements.css";

const categories: [AchievementCategory, string][] = [["common", "Обычные"], ["uncommon", "Необычные"], ["rare", "Редкие"], ["epic", "Эпические"], ["legendary", "Легендарные"], ["secret", "Секретные"]];
const date = () => new Intl.DateTimeFormat(getLocale(), { timeZone: "Europe/Moscow", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });

function useAchievementUpdates() {
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const refresh = () => setRevision(value => value + 1);
    window.addEventListener("achievements:updated", refresh);
    return () => window.removeEventListener("achievements:updated", refresh);
  }, []);
  return revision;
}

function Progress({ item }: { item: Achievement }) {
  const values = item.progress ?? [];
  // A single action is an event, not an artificial 0/1 progress meter.
  if (values.length !== 1 || values[0].target <= 1 || values[0].operator !== "gte") return null;
  const { current, target } = values[0];
  return <div className="achievement-progress"><span>{tr(Math.min(target, current).toLocaleString(getLocale()))} / {tr(target.toLocaleString(getLocale()))}</span><progress aria-label={tr("Прогресс достижения")} max={target} value={Math.min(target, current)} /></div>;
}

function Detail({ item, onClose }: { item: Achievement; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const element = dialog.current;
    element?.showModal();
    const release = lockInteractionViewport();
    return () => { element?.close(); release(); previous?.focus(); };
  }, []);
  return <dialog ref={dialog} className={`achievement-dialog rarity-${item.rarity}`} aria-labelledby="achievement-detail-title" onCancel={onClose} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="achievement-detail"><button type="button" className="achievement-close" aria-label={tr("Закрыть подробности")} onClick={onClose}>×</button><AchievementBadge item={item} /><small>{tr(categories.find(([key]) => key === item.rarity)?.[1])}</small><h2 id="achievement-detail-title"><AchievementTitle item={item} /></h2>{item.flavor && <p className="achievement-flavor">{tr(item.flavor)}</p>}<p>{tr(item.description ?? tr("Условие откроется после получения."))}</p><Progress item={item} /><AchievementRewards item={item} />{item.earned_at && <p className="achievement-earned-date">{tr("Получено")} {tr(date().format(new Date(item.earned_at)))}  {tr("МСК")}</p>}{item.code === "first_achievement_reward" && item.status !== "earned" && <p className="achievement-footnote">{tr("Засчитывается после первого успешного начисления CAS за другое достижение.")}</p>}</div>
  </dialog>;
}

export function AchievementSummary({ initData, onOpen }: { initData: string; onOpen: () => void }) {
  const revision = useAchievementUpdates();
  const [page, setPage] = useState<AchievementPage | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void miniAppApi.achievements(initData, { summary: true }, controller.signal).then(setPage).catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [initData, revision]);
  return <button type="button" className="hub-achievements rarity-common" onClick={onOpen}>
    <span className="achievement-summary-heading"><span className="achievement-icon"><AchievementIcon /></span><strong>{tr("Достижения")}</strong><span aria-hidden="true">↗</span></span>
    {page?.enabled ? <><span className="achievement-summary-count"><strong>{page.earned}<small> / {page.total}</small></strong><span>{tr("открыто")}</span></span><progress aria-label={tr("Общий прогресс достижений")} max={page.total || 1} value={page.earned} />{page.items.length > 0 ? <span className="achievement-recent">{page.items.map(item => <span className={`rarity-${item.rarity}`} key={item.code}><AchievementBadge item={item} /><span className="achievement-recent-name"><AchievementTitle item={item} /></span></span>)}</span> : <span className="achievement-empty-copy">{tr("Ваши первые достижения ещё впереди.")}<br />{tr("Посмотрите, с чего начать.")}</span>}</> : <span className="achievement-empty-copy">{error ? tr("Не удалось загрузить прогресс") : page ? tr("Готовим достижения к запуску") : tr("Загружаем прогресс…")}</span>}
    <span className="achievement-summary-link">{tr("Все достижения")} <span aria-hidden="true">→</span></span>
  </button>;
}

function AchievementList({ initData, category, status, onPage }: { initData: string; category?: AchievementCategory; status: string; onPage: (page: AchievementPage) => void }) {
  const revision = useAchievementUpdates();
  const [page, setPage] = useState<AchievementPage | null>(null);
  const [items, setItems] = useState<Achievement[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<Achievement | null>(null);
  const [retry, setRetry] = useState(0);
  const busy = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    void miniAppApi.achievements(initData, { category, status }, controller.signal).then(data => { setPage(data); setItems(data.items); setError(""); onPage(data); }).catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : tr("Не удалось загрузить достижения")); });
    return () => controller.abort();
  }, [initData, category, status, onPage, retry, revision]);
  async function more() {
    if (busy.current || page?.next_offset == null) return;
    busy.current = true; setLoading(true);
    try {
      const data = await miniAppApi.achievements(initData, { category, status, offset: page.next_offset });
      if (data.updated_at !== page.updated_at || data.catalog_revision !== page.catalog_revision) {
        const fresh = await miniAppApi.achievements(initData, { category, status });
        setPage(fresh); setItems(fresh.items); onPage(fresh); setError("");
        return;
      }
      setPage(data); setItems(current => { const known = new Set(current.map(i => i.code)); return [...current, ...data.items.filter(i => !known.has(i.code))]; }); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : tr("Не удалось загрузить достижения")); }
    finally { busy.current = false; setLoading(false); }
  }
  return <>{error && <div className="achievement-empty" role="alert"><p>{tr(error)}</p><button type="button" onClick={() => setRetry(value => value + 1)}>{tr("Повторить")}</button></div>}{!page && !error && <p role="status">{tr("Загружаем достижения…")}</p>}{page && !page.enabled && <div className="achievement-empty"><AchievementIcon /><h2>{tr("Скоро начнём")}</h2><p>{tr("Достижения готовятся к запуску. Прогресс начнёт учитываться с момента запуска системы.")}</p></div>}{page?.enabled && !items.length && <div className="achievement-empty"><AchievementIcon /><p>{status === "earned" ? tr("Пока нет полученных достижений") : status === "locked" ? tr("Все достижения этой категории получены") : tr("Здесь пока нет достижений")}</p></div>}<div className="achievement-list">{items.map(item => <button type="button" className={`achievement-card rarity-${item.rarity} ${item.status}`} key={item.code} onClick={() => setDetail(item)}><AchievementBadge item={item} /><span className="achievement-card-copy"><strong><AchievementTitle item={item} /></strong><span>{tr(item.description ?? tr("Условие скрыто до получения"))}</span>{item.status === "earned" ? <span className="achievement-earned">{tr("Получено")} <span aria-hidden="true">✓</span></span> : <Progress item={item} />}<AchievementRewards item={item} /></span><span className="achievement-card-arrow" aria-hidden="true">›</span></button>)}</div>{page?.next_offset != null && <button type="button" disabled={loading} className="achievement-more" onClick={() => void more()}>{loading ? tr("Загружаем…") : tr("Показать ещё")}</button>}{detail && <Detail item={detail} onClose={() => setDetail(null)} />}</>;
}

export function Achievements({ initData, onBack }: { initData: string; onBack: () => void }) {
  const [category, setCategory] = useState<AchievementCategory>("common");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState<AchievementPage | null>(null);
  const acceptPage = useCallback((data: AchievementPage) => {
    setPage(data);
    if (data.enabled && data.total_by_category?.[category] === 0) {
      const first = categories.find(([key]) => (data.total_by_category?.[key] ?? 0) > 0);
      if (first) setCategory(first[0]);
    }
  }, [category]);
  return <div className="achievements-screen"><button type="button" className="achievement-back" onClick={onBack}>{tr("← В профиль")}</button><header><span>{tr("CASPER LOTO / ПРОФИЛЬ")}</span><h1>{tr("Мои достижения")}</h1>{page?.enabled && <><p><strong>{page.earned}</strong> / {page.total}  {tr("открыто")}</p><progress aria-label={tr("Общий прогресс")} max={page.total || 1} value={page.earned} /></>}</header>{page?.enabled && <><div className="achievement-categories" aria-label={tr("Редкость")}>{categories.filter(([key]) => (page.total_by_category?.[key] ?? 0) > 0).map(([key, title]) => <button type="button" className={`rarity-${key}`} key={key} aria-pressed={category === key} onClick={() => { setCategory(key); setStatus("all"); }}>{tr(title)}<small>{page.earned_by_category[key] ?? 0} / {page.total_by_category?.[key]}</small></button>)}</div><div className="achievement-filters" aria-label={tr("Статус достижения")}>{[["all", tr("Все")], ["earned", tr("Получены")], ["locked", tr("Не получены")]].map(([key, title]) => <button type="button" key={key} aria-pressed={status === key} onClick={() => setStatus(key)}>{tr(title)}</button>)}</div></>}<AchievementList key={`${category}:${status}`} initData={initData} category={category} status={status} onPage={acceptPage} /></div>;
}
