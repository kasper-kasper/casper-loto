import { tr, getLocale } from "./i18n";
export function formatCas(value: number): string {
  return `${formatCompactAmount(value)} CAS`;
}

export function formatCompactAmount(value: number): string {
  const absolute = Math.abs(value);
  const format = (scaled: number, suffix: string) => `${new Intl.NumberFormat(getLocale(), { maximumFractionDigits: 1 }).format(scaled)} ${suffix}`;
  if (absolute >= 1_000_000_000) return format(value / 1_000_000_000, tr("млрд"));
  if (absolute >= 1_000_000) return format(value / 1_000_000, tr("млн"));
  return new Intl.NumberFormat(getLocale()).format(value);
}

export function formatDraw(value: number): string {
  return String(value).padStart(4, "0");
}

export function formatDrawLabel(lotteryCode: string, value: number): string {
  return lotteryCode === "dual" ? tr("Раунд #{0}", formatDraw(value)) : tr("Тираж #{0}", formatDraw(value));
}

export function formatTicketLabel(_lotteryCode: string, value: number): string {
  return tr("Билет #{0}", formatDraw(value));
}

export function formatMoscow(value: string): string {
  return new Intl.DateTimeFormat(getLocale(), {
    timeZone: "Europe/Moscow",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatMoscowTime(value: string): string {
  return new Intl.DateTimeFormat(getLocale(), {
    timeZone: "Europe/Moscow",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function countdown(value: string | null, now: number): string {
  if (!value) return tr("Расписание готовится");
  const seconds = Math.max(0, Math.floor((new Date(value).getTime() - now) / 1000));
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  if (days > 0) return tr("{0} д {1} ч", days, hours);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}
