import { tr } from "./i18n";
import type { Lottery } from "./types";
import { randomCombination } from "./random";

export const GRAND_LOTTERY_CODE = "weekly";
export const GRAND_STORAGE_OFFSET = 35;

export function isGrandLottery(lotteryOrCode: Lottery | string): boolean {
  return typeof lotteryOrCode === "string"
    ? lotteryOrCode === GRAND_LOTTERY_CODE || lotteryOrCode === "pss"
    : (lotteryOrCode.secondary_numbers_to_pick ?? 0) > 0;
}

export function splitGrandNumbers(values: number[], offset = GRAND_STORAGE_OFFSET): { main: number[]; special: number[] } {
  return {
    main: values.filter((value) => value <= offset),
    special: values.filter((value) => value > offset).map((value) => value - offset),
  };
}

export function lotteryCombination(lottery: Lottery): number[] {
  if (lottery.code === "dual") {
    return [...randomCombination(12, 2), ...randomCombination(12, 2).map((value) => value + 12)];
  }
  if (!isGrandLottery(lottery)) return randomCombination(lottery.max_number, lottery.numbers_to_pick);
  const offset = lottery.secondary_storage_offset ?? GRAND_STORAGE_OFFSET;
  const main = randomCombination(lottery.primary_max_number ?? 35, lottery.primary_numbers_to_pick ?? 5);
  const special = randomCombination(lottery.secondary_max_number ?? 5, lottery.secondary_numbers_to_pick ?? 2)
    .map((value) => value + offset);
  return [...main, ...special];
}

export function lotteryFormat(lottery: Lottery): string {
  if (isGrandLottery(lottery)) {
    const specialLabel = lottery.code === "pss" ? "CASPER BALL " : "";
    return tr("{0} ИЗ {1} + {2}{3} ИЗ {4}", lottery.primary_numbers_to_pick ?? 5, lottery.primary_max_number ?? 35, specialLabel, lottery.secondary_numbers_to_pick ?? 2, lottery.secondary_max_number ?? 5);
  }
  return tr("{0} ИЗ {1}", lottery.numbers_to_pick, lottery.max_number);
}

export function lotteryKindLabel(lottery: Lottery): string {
  return lottery.kind === "WEEKLY" ? tr("Еженедельная") : tr("Ежедневная");
}

export function matchLabel(code: string, matches: number, grandFormat = matches >= 10): string {
  if (code === "pulse" && matches >= 100) return tr("{0}+{1}, шифр {2}", Math.floor(matches / 100), Math.floor(matches / 10) % 10, matches % 10 ? tr("совпал") : tr("не совпал"));
  if (!isGrandLottery(code) || !grandFormat) return String(matches);
  return `${Math.floor(matches / 10)}+${matches % 10}`;
}
