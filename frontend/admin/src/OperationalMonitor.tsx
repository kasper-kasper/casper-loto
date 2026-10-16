import { useEffect, useState } from "react";
import { adminApi } from "./api";

export interface MonitoringSnapshot {
  metrics: Record<string, { count: number; errors: number; p50_ms: number | null; p95_ms: number | null }>;
  operations: {
    checked_at: string | null; warnings: string[]; disk_used_percent?: number;
    disk_free_bytes?: number; backup_count?: number; backup_age_seconds?: number | null;
    overdue_draws?: number; delayed_distribution_posts?: number; delayed_posts?: number;
  };
}
const names: Record<string, string> = { startup_client: "Открытие мини-аппа", purchase_client: "Покупка у игрока", purchase: "Покупка на сервере", dashboard: "Загрузка главной", account: "Статистика профиля" };
const warningNames: Record<string, string> = {
  host_monitor_stale: "Внешняя проверка сервера давно не обновлялась", host_monitor_warning: "Внешняя проверка обнаружила проблему сервиса",
  monitor_warming_up: "Ожидается первая проверка", monitor_stale: "Монитор давно не обновлялся", monitor_check_failed: "Не удалось проверить сервер",
  disk_low: "На диске мало места", backup_missing_or_stale: "Нет свежей резервной копии", backup_retention_exceeded: "Хранится больше семи копий",
  overdue_draws: "Тиражи обрабатываются с задержкой", delayed_publications: "Есть задержки или ошибки публикаций", scheduler_stale: "Планировщик давно не завершал проверку",
  slow_startup_client: "Медленно открывается мини-апп", slow_purchase_client: "Игроки долго ждут покупку", slow_purchase: "Сервер медленно проводит покупки",
  errors_miniapp: "Повышенная доля ошибок сервера", errors_purchase_client: "Игроки получают ошибки покупки или теряют связь",
};
export function OperationalMonitor() {
  const [data, setData] = useState<MonitoringSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    const refresh = () => {
      void adminApi.monitoring().then(value => { if (active) { setData(value); setError(null); } })
        .catch(() => { if (active) setError("Не удалось обновить мониторинг."); });
    };
    refresh();
    return () => { active = false; };
  }, []);
  const operations = data?.operations;
  return <section className="panel"><header><div><h2>Скорость мини-аппа и контроль сервера</h2><span>Состояние на момент загрузки · «Обновить данные» для новой сводки · скорость за последний час</span></div></header>
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p>Загружаем мониторинг…</p>}
    {operations && <><p>{operations.checked_at ? `Проверено: ${new Date(operations.checked_at).toLocaleString("ru-RU")}` : "Ожидается проверка"}. {operations.warnings.length ? operations.warnings.map(code => warningNames[code] ?? code).join(" · ") : "Проблем не обнаружено"}</p>
      <div className="control-status"><article><small>Диск</small><strong>{operations.disk_used_percent ?? "—"}% занято</strong><span>Свободно {operations.disk_free_bytes === undefined ? "—" : (operations.disk_free_bytes / 1024 ** 3).toFixed(1)} ГБ</span></article><article><small>Резервные копии</small><strong>{operations.backup_count ?? "—"} из 7</strong><span>Последняя {operations.backup_age_seconds == null ? "не найдена" : `${Math.floor(operations.backup_age_seconds / 3600)} ч. назад`}</span></article><article><small>Задержки</small><strong>Тиражи: {operations.overdue_draws ?? "—"} · посты: {(operations.delayed_posts ?? 0) + (operations.delayed_distribution_posts ?? 0)}</strong><span>Проверяются просроченные тиражи и доставка постов</span></article></div>
      <div className="table-wrap"><table><thead><tr><th>Показатель</th><th>Измерений</th><th>Обычно</th><th>95% запросов быстрее</th><th>Ошибок / обрывов</th></tr></thead><tbody>{Object.entries(names).map(([key, name]) => { const metric = data.metrics[key]; return <tr key={key}><td>{name}</td><td>{metric?.count ?? 0}</td><td>{metric?.p50_ms == null ? "—" : `${metric.p50_ms} мс`}</td><td>{metric?.p95_ms == null ? "—" : `${metric.p95_ms} мс`}</td><td>{metric?.errors ?? 0}</td></tr>; })}</tbody></table></div></>}
  </section>;
}
