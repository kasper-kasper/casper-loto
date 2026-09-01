export function formatCas(value: number): string {
  return `${new Intl.NumberFormat("ru-RU").format(value)} CAS`;
}

export function formatDraw(value: number): string {
  return String(value).padStart(4, "0");
}

export function formatDrawLabel(lotteryCode: string, value: number): string {
  return lotteryCode === "grob" ? `RIP ${formatDraw(value)}` : `Тираж #${formatDraw(value)}`;
}

export function formatTicketLabel(lotteryCode: string, value: number): string {
  return lotteryCode === "grob" ? `Могила ${formatDraw(value)}` : `Билет #${formatDraw(value)}`;
}

export function formatMoscow(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: "Europe/Moscow",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatMoscowTime(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    timeZone: "Europe/Moscow",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function countdown(value: string | null, now: number): string {
  if (!value) return "Расписание готовится";
  const seconds = Math.max(0, Math.floor((new Date(value).getTime() - now) / 1000));
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  if (days > 0) return `${days} д ${hours} ч`;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}
