import { tr, getLocale } from "./i18n";
import { useEffect, useRef, useState } from "react";
import { miniAppApi } from "./api";
import { NewYearSymbols } from "./NewYear";
import { Money } from "./components";
import type { ArchiveDraw, ArchivePage } from "./types";
import "./draw-archive.css";

const archiveDate = () => new Intl.DateTimeFormat(getLocale(), { timeZone: "Europe/Moscow", day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

function DrawCard({ draw }: { draw: ArchiveDraw }) {
  const numbers = draw.winning_numbers ?? [];
  const split = draw.secondary_storage_offset > 0;
  const groups = split ? [numbers.slice(0, draw.primary_numbers_to_pick), numbers.slice(draw.primary_numbers_to_pick).map(n => n - draw.secondary_storage_offset)] : [numbers];
  return <article className={`archive-card${draw.jackpot_amount ? " archive-jackpot" : ""}`}>
    {draw.jackpot_amount != null && <div className="archive-jackpot-banner"><span aria-hidden="true">✦</span><div><strong>{tr("Джекпот сорван!")}</strong><span><Money value={draw.jackpot_amount} /></span></div></div>}
    <header><h2>{tr(draw.lottery_name)}</h2><span>№ {draw.draw_number}</span></header>
    <time dateTime={draw.scheduled_at}>{tr(archiveDate().format(new Date(draw.scheduled_at)))}  {tr("МСК")}</time>
    <div className="archive-payout"><span>{tr("Всего выплачено")}</span><strong><Money value={draw.total_payout} /></strong></div>
    {draw.lottery_code !== "bingo" && <details><summary>{tr("Результаты тиража")} <span aria-hidden="true">＋</span></summary><div className="archive-detail">
      <p>{tr("Билетов в тираже")} <strong>{tr(draw.ticket_count?.toLocaleString(getLocale()) ?? "—")}</strong></p>
      {draw.lottery_code === "newyear2027" && numbers.length ? <NewYearSymbols values={numbers} /> : numbers.length ? groups.map((group, index) => <div className="archive-combination" key={index}><small>{split ? tr("Поле {0}", index + 1) : tr("Выигрышная комбинация")}</small><ol aria-label={split ? tr("Поле {0}", index + 1) : tr("Выигрышная комбинация")}>{group.map((number, i) => <li key={i}>{number}</li>)}</ol></div>) : <p>{tr("Комбинация не сохранена для этого тиража.")}</p>}
    </div></details>}
  </article>;
}

export function DrawArchive({ initData, onBack }: { initData: string; onBack: () => void }) {
  const [lottery, setLottery] = useState("");
  const [jackpotsOnly, setJackpotsOnly] = useState(false);
  return <section className="draw-archive view-content">
    <button className="archive-back" type="button" onClick={onBack}>{tr("← На главную")}</button>
    <header className="archive-heading"><span>{tr("ИСТОРИЯ РОЗЫГРЫШЕЙ")}</span><h1>{tr("Архив тиражей")}</h1><p>{tr("Результаты, выплаты и большие победы")}</p></header>
    <ArchiveResults key={`${lottery}:${jackpotsOnly}:${initData}`} initData={initData} lottery={lottery} jackpotsOnly={jackpotsOnly} onLottery={setLottery} onJackpots={setJackpotsOnly} />
  </section>;
}

function ArchiveResults({ initData, lottery, jackpotsOnly, onLottery, onJackpots }: { initData: string; lottery: string; jackpotsOnly: boolean; onLottery: (value: string) => void; onJackpots: (value: boolean) => void }) {
  const [page, setPage] = useState<ArchivePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const busy = useRef(false);
  useEffect(() => {
    const abort = new AbortController();
    controller.current = abort;
    miniAppApi.drawArchive(initData, lottery, jackpotsOnly, null, abort.signal).then(setPage).catch(() => { if (!abort.signal.aborted) setError(tr("Не удалось загрузить архив. Попробуйте ещё раз.")); }).finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [initData, lottery, jackpotsOnly, retry]);
  async function loadMore() {
    if (!page?.next_cursor || busy.current) return;
    busy.current = true;
    setLoading(true); setError("");
    try {
      const next = await miniAppApi.drawArchive(initData, lottery, jackpotsOnly, page.next_cursor, controller.current?.signal);
      setPage({ ...next, items: [...page.items, ...next.items] });
    } catch { if (!controller.current?.signal.aborted) setError(tr("Не удалось загрузить следующие тиражи. Попробуйте ещё раз.")); }
    finally { busy.current = false; if (!controller.current?.signal.aborted) setLoading(false); }
  }
  return <>
    <div className="archive-filters"><label>{tr("Лотерея")}<select aria-label={tr("Лотерея в архиве")} value={lottery} onChange={e => onLottery(e.target.value)}><option value="">{tr("Все лотереи")}</option>{!page && lottery && <option value={lottery}>{tr("Выбранная лотерея")}</option>}{page?.lotteries.map(item => <option key={item.code} value={item.code}>{tr(item.name)}</option>)}</select></label><button type="button" aria-pressed={jackpotsOnly} onClick={() => onJackpots(!jackpotsOnly)}>{tr("✦ Только джекпоты")}</button></div>
    <p className="archive-caption">{tr("От новых к старым · время по Москве")}</p>
    <div className="archive-list" aria-busy={loading}>{page?.items.map(draw => <DrawCard key={draw.id} draw={draw} />)}</div>
    {loading && <p role="status" className="archive-message">{tr("Загружаем тиражи…")}</p>}
    {error && <p role="alert" className="archive-message">{tr(error)}</p>}
    {!loading && error && !page && <button className="archive-more" type="button" onClick={() => { setLoading(true); setError(""); setRetry(n => n + 1); }}>{tr("Повторить")}</button>}
    {!loading && page?.items.length === 0 && <p className="archive-message">{jackpotsOnly ? tr("Сорванных джекпотов пока нет.") : tr("Завершённых тиражей пока нет.")}</p>}
    {page?.next_cursor && <button className="archive-more" disabled={loading} type="button" onClick={() => void loadMore()}>{loading ? tr("Загрузка…") : tr("Показать более ранние")}</button>}
    {page && page.items.length > 0 && !page.next_cursor && <p className="archive-caption">{tr("Вы дошли до начала истории")}</p>}
  </>;
}
