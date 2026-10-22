import { getLanguage, tr } from "./i18n";

/** Translate known historical system copy for display; never rewrite saved history. */
export function notificationText(value: string): string {
  if (getLanguage() === "ru") return value;
  const win = /^Выигрыш ([\d\s\u00a0]+) CAS$/.exec(value);
  if (win) return `Winnings ${win[1]} CAS`;
  const result = /^(.+), тираж №(\d+)\. Выигрыш уже зачислен\.$/.exec(value);
  if (result) return `${tr(result[1])}, draw No. ${result[2]}. Winnings credited.`;
  const invite = /^(.+), тираж №(\d+)\. Можно выбрать числа заранее\.$/.exec(value);
  if (invite) return `${tr(invite[1])}, draw No. ${invite[2]}. You can pick your numbers in advance.`;
  const dual = /^Билет №(\d+)\. Оба раунда завершены; выигрыш зачислен\.$/.exec(value);
  if (dual) return `Ticket No. ${dual[1]}. Both rounds finished; winnings credited.`;
  const jackpot = /^В (.+), тираж №(\d+), разыграно ([\d\s\u00a0]+) CAS\. Джекпот восстановлен\.$/.exec(value);
  if (jackpot) return `${tr(jackpot[1])}, draw No. ${jackpot[2]}: ${jackpot[3]} CAS paid out. Jackpot restored.`;
  return tr(value);
}
