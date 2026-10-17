import { useEffect, useState } from "react";
import { adminApi } from "./api";
import type { EconomyReport } from "./types";
import "./economy-panel.css";

const cash = (value: number) => `${value.toLocaleString("ru-RU")} CAS`;
const signed = (value: number) => `${value > 0 ? "+" : ""}${cash(value)}`;

export function EconomyPanel({ refreshedAt }: { refreshedAt: number }) {
  const [days, setDays] = useState<7 | 30>(7);
  const [through, setThrough] = useState("");
  const [loaded, setLoaded] = useState<{ key: string; data: EconomyReport } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const key = `${days}:${through}:${refreshedAt}`;
  useEffect(() => {
    let active = true;
    void adminApi.economy(days, through).then(data => {
      if (active) setLoaded({ key, data });
    }).catch(() => { if (active) setFailure({ key, message: "Не удалось загрузить движение CAS. Обнови данные страницы." }); });
    return () => { active = false; };
  }, [days, through, key]);
  const report = loaded?.key === key ? loaded.data : null;
  const selected = report?.days.at(-1);
  const previous = report?.days.at(-2);
  const comparison = (value: number, prior: number | undefined) => previous?.included && prior !== undefined
    ? `${signed(value - prior)} к предыдущему дню` : "Предыдущий день вне выбранного этапа";
  return <section className="panel economy-panel" aria-label="Экономика CAS">
    <header><div><small>ВСЕ ИГРЫ И НАЧИСЛЕНИЯ · МОСКОВСКОЕ ВРЕМЯ</small><h2>Экономика CAS</h2>
      <p>Сколько начислено и списано у игроков, как меняется объём валюты во всей системе.</p></div>
      <div className="economy-controls"><label>День отчёта<input aria-label="День отчёта CAS" type="date" value={through || report?.selected_day || ""} max={report?.today} onChange={event => setThrough(event.target.value)} /></label>
        <label>История<select aria-label="Период экономики CAS" value={days} onChange={event => setDays(Number(event.target.value) as 7 | 30)}><option value={7}>7 дней</option><option value={30}>30 дней</option></select></label>
        <button type="button" onClick={() => setThrough("")}>Сегодня</button></div></header>
    {failure?.key === key && <p role="alert" className="error">{failure.message}</p>}
    {!report && failure?.key !== key && <p role="status">Загружаем движение CAS…</p>}
    {report && selected && <>
      <p className="economy-period">{report.selected_day === report.today ? "Сегодня" : report.selected_day} · {report.scope === "archive" ? "Архив старой экономики" : "Текущий этап экономики"}{selected.partial ? " · Часть дня: граница этапа внутри суток" : ""}</p>
      {!selected.included ? <p className="source-note">Этот день вне выбранного этапа экономики. Старые дни доступны в архиве.</p> : <>
        <div className="metric-grid economy-metrics">
          <article className="metric"><small>НАЧИСЛЕНО ИГРОКАМ</small><strong>{cash(selected.credited)}</strong><em>{comparison(selected.credited, previous?.credited)}</em></article>
          <article className="metric"><small>СПИСАНО У ИГРОКОВ</small><strong>{cash(selected.debited)}</strong><em>{comparison(selected.debited, previous?.debited)}</em></article>
          <article className="metric"><small>ИЗМЕНЕНИЕ БАЛАНСОВ ИГРОКОВ</small><strong className={selected.player_net >= 0 ? "positive" : "negative"}>{signed(selected.player_net)}</strong><em>начислено − списано</em></article>
        </div>
        <div className="economy-details"><dl><div><dt>Призы и джекпоты</dt><dd>{cash(selected.prizes)}</dd></div><div><dt>Возвраты билетов</dt><dd>{cash(selected.refunds)}</dd></div><div><dt>Начисления администратора</dt><dd>{cash(selected.admin_credit)}</dd></div><div><dt>Бонусы и прочие начисления</dt><dd>{cash(selected.other_credit)}</dd></div></dl>
          <dl><div><dt>Покупки билетов · все игры</dt><dd>{cash(selected.purchases)}</dd></div><div><dt>Списания администратора</dt><dd>{cash(selected.admin_debit)}</dd></div><div><dt>Прочие списания</dt><dd>{cash(selected.other_debit)}</dd></div></dl></div>
        <div className="economy-supply"><article><small>СОЗДАНО CAS В СИСТЕМЕ</small><strong>{cash(selected.issued)}</strong></article><article><small>СОЖЖЕНО CAS В СИСТЕМЕ</small><strong>{cash(selected.burned)}</strong></article><article><small>ЧИСТОЕ ИЗМЕНЕНИЕ ОБЪЁМА CAS</small><strong>{signed(selected.supply_net)}</strong></article></div>
      </>}
      <details><summary>Сравнение по дням · {days} дней</summary><div className="table-wrap"><table><thead><tr><th>День · МСК</th><th>Начислено игрокам</th><th>Списано у игроков</th><th>Итог балансов</th><th>Создано CAS</th><th>Сожжено CAS</th><th>Изменение объёма</th></tr></thead><tbody>{[...report.days].reverse().map(day => <tr key={day.day}><td>{day.day}{day.partial ? " · часть дня" : ""}{!day.included ? " · вне этапа" : ""}</td>{[day.credited, day.debited, day.player_net, day.issued, day.burned, day.supply_net].map((value, index) => <td key={index}>{day.included ? (index === 2 || index === 5 ? signed(value) : cash(value)) : "—"}</td>)}</tr>)}</tbody></table></div></details>
      <p className="source-note">Начисления включают выплаты, возвраты, бонусы и ручные корректировки. Объём CAS учитывает счета игроков, джекпоты, фонды и резервы. Внутренние переводы дают нулевое изменение объёма. Данные считаются по журналу операций; операция целиком относится к дню её начала.</p>
    </>}
  </section>;
}
