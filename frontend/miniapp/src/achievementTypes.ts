export type Rarity = "common" | "uncommon" | "rare" | "epic" | "legendary";
export type AchievementCategory = Rarity | "secret";
export interface Achievement {
  code: string;
  title?: string;
  description?: string;
  flavor?: string | null;
  rarity: Rarity;
  icon?: string;
  secret: boolean;
  status: "earned" | "locked";
  progress?: { metric: string; current: number; target: number; operator: string }[];
  progress_mode?: "all" | "any";
  rewards?: { type: string; amount?: number; lottery?: string; planned?: boolean; item?: string }[];
  reward_pending?: boolean;
  reward_status?: string | null;
  earned_at?: string | null;
}
export interface AchievementPage {
  catalog_revision?: number;
  updated_at?: string | null;
  enabled: boolean;
  total: number;
  earned: number;
  total_by_category?: Partial<Record<AchievementCategory, number>>;
  earned_by_category: Partial<Record<AchievementCategory, number>>;
  items: Achievement[];
  next_offset?: number | null;
  filtered_total?: number;
}
export interface AchievementNotice extends Achievement { notification_id: string }
