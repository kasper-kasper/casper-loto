import { tr } from "./i18n";
import "./distribution.css";

export function DistributionBadge({ active }: { active?: boolean }) {
  return active ? <span className="distribution-badge">{tr("Распределительный")}</span> : null;
}
