import "./distribution.css";

export function DistributionBadge({ active }: { active?: boolean }) {
  return active ? <span className="distribution-badge">Распределительный</span> : null;
}
