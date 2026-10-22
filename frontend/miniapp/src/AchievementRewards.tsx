import { tr, getLanguage } from "./i18n";
import type { Achievement } from "./achievementTypes";
import { AchievementIcon } from "./AchievementIcon";
import { Money } from "./components";
import { collectionGames } from "./collectionGames";

const games: Record<string, string> = {
  ...collectionGames,
  september: "3 сентября", grob: "Halloween", pll: "2:22", khan: "6 из 36", pss: "Casper Ball", weekly: "Casper Grand", bingo: "Casper Bingo",
};

export function AchievementRewards({ item, compact = false }: { item: Achievement; compact?: boolean }) {
  if (item.reward_pending) return <span className="achievement-reward pending">{tr("Награда будет объявлена")}</span>;
  const cash = item.rewards?.filter(r => r.type === "cas").reduce((sum, r) => sum + (r.amount ?? 0), 0) ?? 0;
  const tickets = new Map<string, number>();
  for (const reward of item.rewards ?? []) {
    if (["ticket", "ticket_pack"].includes(reward.type) && reward.lottery) tickets.set(reward.lottery, (tickets.get(reward.lottery) ?? 0) + (reward.amount ?? 1));
  }
  const cosmetics=(item.rewards??[]).filter(r=>r.type==="cosmetic");
  return <span className={`achievement-rewards ${compact ? "compact" : ""}`}>
    {cash > 0 && <span className="achievement-reward"><Money value={cash} /></span>}
    {[...tickets].map(([lottery, amount]) => <span className="achievement-extra-reward" key={lottery}><AchievementIcon name="ticket-check" />{amount} {tr(ticketWord(amount, lottery === "bingo"))} «{tr(games[lottery] ?? lottery)}»</span>)}
    {cosmetics.some(r=>r.item?.startsWith("badge:"))&&<span className="achievement-extra-reward">{tr("Уникальный значок")}</span>}
    {cosmetics.some(r=>r.item==="theme:gold")&&<span className="achievement-extra-reward">{tr("Золотая тема")}</span>}
    {cosmetics.some(r=>r.item==="theme:beyond")&&<span className="achievement-extra-reward">{tr("Тема «За гранью»")}</span>}
  </span>;
}

function ticketWord(amount: number, bingo: boolean) {
  return quantityWord(amount, bingo ? [tr("карточка"), tr("карточки"), tr("карточек")] : [tr("билет"), tr("билета"), tr("билетов")]);
}

function quantityWord(amount: number, words: string[]) {
  if (getLanguage() === "en") return words[amount === 1 ? 0 : 2];
  const last = amount % 10, teen = amount % 100 >= 11 && amount % 100 <= 14;
  const form = teen ? 2 : last === 1 ? 0 : last >= 2 && last <= 4 ? 1 : 2;
  return words[form];
}
