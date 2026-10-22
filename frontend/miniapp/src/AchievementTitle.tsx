import { tr } from "./i18n";
import type { Achievement } from "./achievementTypes";
import "./achievement-title.css";

export function AchievementTitle({ item }: { item: Pick<Achievement, "code" | "title" | "rarity" | "secret"> }) {
  const style = item.rarity !== "common" && item.title
    ? item.code === "legendary_casper_move_over" ? "title-master" : `title-${item.rarity}`
    : "";
  return <span className={`achievement-title ${style}`}>{tr(item.title ?? tr("Секретное достижение"))}</span>;
}
