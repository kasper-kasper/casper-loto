import { tr } from "./i18n";
import { achievementAppearance } from "./achievementAppearance";
import { AchievementIcon } from "./AchievementIcon";
import { LegendaryBadge } from "./LegendaryBadge";
import type { Achievement } from "./achievementTypes";

type BadgeItem = Pick<Achievement, "code" | "rarity" | "status" | "secret" | "icon">;

export function AchievementBadge({ item }: { item: BadgeItem }) {
  const hidden = item.secret && item.status !== "earned";
  if (!hidden && item.rarity === "legendary" && (item.icon?.startsWith("lottery:") || item.code === "legendary_casper_move_over")) return <LegendaryBadge game={item.code === "legendary_casper_move_over" ? "casper-master" : item.icon!.slice(8)} locked={item.status !== "earned"} />;
  const appearance = hidden ? { icon: "lock" } : achievementAppearance[item.code] ?? { icon: item.icon ?? "trophy" };
  return <span aria-hidden="true" className={`achievement-icon achievement-badge rarity-${item.rarity}${appearance.distinct ? " badge-distinct" : ""}${item.status === "earned" ? " is-earned" : " is-locked"}`}>
    <AchievementIcon name={appearance.icon} />
    {appearance.mark && <span className={`achievement-badge-mark${appearance.mark.length > 4 && /^\d+$/.test(appearance.mark) ? " badge-mark-long" : ""}`}>{tr(/^\d+$/.test(appearance.mark) ? appearance.mark : <AchievementIcon name={appearance.mark} />)}</span>}
  </span>;
}
