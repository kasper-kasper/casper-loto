import { DimensionalIcon } from "./DimensionalIcon";
import { selectionHaptic } from "./telegram";
import "./mobile-navigation.css";

type Destination = "home" | "catalog" | "fast" | "account";
const items = [
  { id: "home", label: "Сегодня", icon: "home" },
  { id: "catalog", label: "Лотереи", icon: "catalog" },
  { id: "fast", label: "Casper Fast", icon: "fast" },
  { id: "account", label: "Моё", icon: "profile" },
] as const;

export function MobileNavigation({ view, unreadNotifications, onChange }: { view: string; unreadNotifications: number; onChange: (view: Destination) => void }) {
  return <nav className="mobile-dock" aria-label="Основная навигация">{items.map(item => <button key={item.id} type="button" aria-current={view === item.id ? "page" : undefined} aria-label={item.id === "account" && unreadNotifications > 0 ? "Моё: есть непрочитанные уведомления" : item.label} onClick={() => { selectionHaptic(); onChange(item.id); }}>
    <span className="dock-icon"><DimensionalIcon name={item.icon} />{item.id === "account" && unreadNotifications > 0 && <i className="dock-notification" />}</span><span className="dock-label">{item.label}</span>
  </button>)}</nav>;
}
