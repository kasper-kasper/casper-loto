import { tr, getLocale } from "./i18n";
import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import { formatCompactAmount } from "./format";
import { splitGrandNumbers } from "./grand";
import { logoHorizontal, logoSymbol } from "./brand";
import { splitPulseNumbers } from "./fast";

export type IconName = "catalog" | "home" | "ticket" | "profile" | "cart" | "live" | "fast" | "replay" | "arrow" | "spark" | "repeat" | "close";

export function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    catalog: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
    home: <><path d="M4 11.5 12 4l8 7.5v8H4Z" /><path d="M8 15h8M12 11v8" /><path d="M4 11.5h16" /></>,
    ticket: <><path d="m5 7 13-2 1 12-13 2Z" /><path d="M9 9.5 10 16M13 9l3-.5M13.5 12l3-.5M14 15l2.5-.5" /></>,
    profile: <><path d="M12 4 16 8l-4 4-4-4Z" /><path d="M5 20c.8-4.3 3.1-6.5 7-6.5s6.2 2.2 7 6.5" /><path d="M7.5 20h9" /></>,
    cart: <><path d="M5 8h14l-1.2 11H6.2Z" /><path d="M8 8c0-2.6 1.3-4 4-4s4 1.4 4 4" /><path d="M8 13h8M12 10v6" /></>,
    live: <><path d="M3.5 12h3l2-5 3.2 10 2.4-7 2.2 4H21" /><path d="M5 4h14M5 20h14" /><path d="M3 7v10M21 7v10" /></>,
    fast: <path d="m13.5 2-7 11h5L10.5 22l7-12h-5Z" />,
    replay: <><path d="M6.5 7.5A7 7 0 1 1 5 14" /><path d="M3.5 7.5h3.5V4M10 9l5 3-5 3Z" /></>,
    arrow: <><path d="m14.5 5-7 7 7 7" /></>,
    spark: <><path d="M12 2.5c.5 4.6 2.9 7 7.5 7.5-4.6.5-7 2.9-7.5 7.5-.5-4.6-2.9-7-7.5-7.5 4.6-.5 7-2.9 7.5-7.5Z" /><path d="M19 16.5c.2 1.8 1.2 2.8 3 3-1.8.2-2.8 1.2-3 3-.2-1.8-1.2-2.8-3-3 1.8-.2 2.8-1.2 3-3Z" /></>,
    repeat: <><path d="M18 7h-9a5 5 0 0 0-5 5v1" /><path d="m15 4 3 3-3 3M6 17h9a5 5 0 0 0 5-5v-1" /><path d="m9 20-3-3 3-3" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  };
  return <svg aria-hidden="true" className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{tr(paths[name])}</svg>;
}

function useAnimatedValue(value: number): number {
  const previous = useRef(value);
  const [displayed, setDisplayed] = useState(value);

  useEffect(() => {
    const from = previous.current;
    previous.current = value;
    if (from === value || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplayed(value);
      return;
    }
    const started = performance.now();
    const duration = 420;
    let frame = 0;
    const animate = (time: number) => {
      const progress = Math.min(1, (time - started) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayed(Math.round(from + (value - from) * eased));
      if (progress < 1) frame = window.requestAnimationFrame(animate);
    };
    frame = window.requestAnimationFrame(animate);
    return () => window.cancelAnimationFrame(frame);
  }, [value]);

  return displayed;
}

export function Balance({ value }: { value: number }) {
  const displayed = useAnimatedValue(value);
  return <div aria-label={tr("Баланс: {0} CAS", new Intl.NumberFormat(getLocale()).format(displayed))} className="balance"><strong><Money compact value={displayed} /></strong></div>;
}

export function Money({ value, compact = false, prefix = "" }: { value: number; compact?: boolean; prefix?: string }) {
  return <span className="money-value" aria-label={tr(`${prefix}${new Intl.NumberFormat(getLocale()).format(value)} CAS`)}><span>{tr(prefix)}{tr(compact ? formatCompactAmount(value) : new Intl.NumberFormat(getLocale()).format(value))}</span><i className="currency-mark" aria-hidden="true">C</i></span>;
}

export function PrimaryButton({
  children,
  disabled,
  loading = false,
  success = false,
  onClick,
  className = "",
}: {
  children: ReactNode;
  disabled?: boolean;
  loading?: boolean;
  success?: boolean;
  onClick?: () => void;
  className?: string;
}) {
  return <button className={`primary-button ${loading ? "loading" : ""} ${success ? "success" : ""} ${className}`} disabled={disabled || loading} onClick={onClick} type="button">
    {loading && <span className="button-spinner" />}
    {success && <span className="button-check">✓</span>}
    <span>{tr(children)}</span>
  </button>;
}

export function NumberSet({
  values,
  winning,
  animate = false,
}: {
  values: number[];
  winning?: number[] | null;
  animate?: boolean;
}) {
  return <div className="number-row" aria-label={tr("Числа: {0}", values.join(", "))}>
    {values.map((value, index) => {
      const won = winning?.includes(value) ?? false;
      return <span className={`number ${won ? "won" : ""} ${animate && won ? "animate-win" : ""}`} key={value} style={{ "--number-index": index } as CSSProperties}>{value}</span>;
    })}
  </div>;
}

export function GrandNumberSet({
  values,
  winning,
  animate = false,
  offset = 35,
  specialLabel = tr("Спецчисла"),
}: {
  values: number[];
  winning?: number[] | null;
  animate?: boolean;
  offset?: number;
  specialLabel?: string;
}) {
  const parts = splitGrandNumbers(values, offset);
  const winningParts = winning ? splitGrandNumbers(winning, offset) : null;
  return <div className="grand-number-set" aria-label={tr("Основные числа: {0}; специальные числа: {1}", parts.main.join(", "), parts.special.join(", "))}>
    <div><small>{tr("Основное поле")}</small><NumberSet animate={animate} values={parts.main} winning={winningParts?.main} /></div>
    <span aria-hidden="true">+</span>
    <div className="grand-special"><small>{tr(specialLabel)}</small><NumberSet animate={animate} values={parts.special} winning={winningParts?.special} /></div>
  </div>;
}

export function SignalSet({ values, code, winning }: { values: number[]; code: "flash" | "shadow" | "pulse"; winning?: number[] | null }) {
  if (code === "pulse") {
    const parts = splitPulseNumbers(values);
    const won = winning ? splitPulseNumbers(winning) : null;
    return <div className="signal-set signal-pulse" aria-label={tr("Основные числа: {0}; Pulse-число: {1}", parts.main.join(", "), parts.pulse.join(", "))}>
      {parts.main.map((value) => <span className={won?.main.includes(value) ? "won" : ""} key={value}><i /><small>{tr(String(value).padStart(2, "0"))}</small></span>)}
      <b aria-hidden="true">+</b>
      {parts.pulse.map((value) => <span className={`pulse-special ${won?.pulse.includes(value) ? "won" : ""}`} key={`pulse-${value}`}><i /><small>P{value}</small></span>)}
    </div>;
  }
  return <div className={`signal-set signal-${code}`} aria-label={tr("Позиции: {0}", values.join(", "))}>{values.map((value) => <span className={winning?.includes(value) ? "won" : ""} key={value}><i /><small>{tr(String(value).padStart(2, "0"))}</small></span>)}</div>;
}

export function StatusBadge({ active, label }: { active: boolean; label?: string }) {
  return <span className={`status ${active ? "active" : "complete"} ${label ? "custom" : ""}`}><i />{tr(label ?? (active ? tr("Активен") : tr("Завершён")))}</span>;
}

export function EmptyState({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: { label: string; onClick: () => void };
}) {
  return <div className="empty-state">
    <div className="empty-illustration" aria-hidden="true"><span /><span /><Icon name="ticket" /></div>
    <strong>{tr(title)}</strong>
    <p>{tr(text)}</p>
    {action && <button className="empty-action" onClick={action.onClick} type="button">{tr(action.label)}<span>→</span></button>}
  </div>;
}

export function Skeleton() {
  return <main className="app-shell skeleton-shell" aria-label={tr("Загружаем Casper Loto")}>
    <header className="app-header"><div aria-label="Casper Loto" className="brand-lockup"><picture><source media="(max-width: 520px)" srcSet={logoSymbol} /><img alt="" className="brand-logo-horizontal" width="138" height="46" fetchPriority="high" src={logoHorizontal} /></picture></div><div className="skeleton header-balance-skeleton" /></header>
    <div className="skeleton hero-skeleton" />
    <div className="skeleton draw-skeleton" />
    <div className="skeleton title-skeleton" />
    <div className="skeleton card-skeleton" />
    <div className="skeleton card-skeleton short" />
  </main>;
}
