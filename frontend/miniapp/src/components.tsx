import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import { formatCas } from "./format";

export type IconName = "home" | "ticket" | "profile" | "cart" | "live" | "replay" | "arrow" | "spark" | "repeat" | "close";

export function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    home: <><path d="M4 12 12 4l8 8-8 8Z" /><path d="M9 12h6M12 9v6" /></>,
    ticket: <><path d="m5 7 13-2 1 12-13 2Z" /><path d="M9 9.5 10 16M13 9l3-.5M13.5 12l3-.5M14 15l2.5-.5" /></>,
    profile: <><path d="M12 3.5a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z" /><path d="M4.5 20c.7-4 3.2-6 7.5-6s6.8 2 7.5 6" /><path d="M8 20h8" /></>,
    cart: <><path d="M5 8h14l-1 11H6Z" /><path d="M8 8c0-2.5 1.3-4 4-4s4 1.5 4 4M9 12h6" /></>,
    live: <><path d="M4 12h3l2-5 3 10 2-6 2 3h4" /><path d="M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z" /></>,
    replay: <><path d="M6.5 7.5A7 7 0 1 1 5 14" /><path d="M3.5 7.5h3.5V4M10 9l5 3-5 3Z" /></>,
    arrow: <><path d="m14.5 5-7 7 7 7" /></>,
    spark: <><path d="M12 2.5c.5 4.6 2.9 7 7.5 7.5-4.6.5-7 2.9-7.5 7.5-.5-4.6-2.9-7-7.5-7.5 4.6-.5 7-2.9 7.5-7.5Z" /><path d="M19 16.5c.2 1.8 1.2 2.8 3 3-1.8.2-2.8 1.2-3 3-.2-1.8-1.2-2.8-3-3 1.8-.2 2.8-1.2 3-3Z" /></>,
    repeat: <><path d="M18 7h-9a5 5 0 0 0-5 5v1" /><path d="m15 4 3 3-3 3M6 17h9a5 5 0 0 0 5-5v-1" /><path d="m9 20-3-3 3-3" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  };
  return <svg aria-hidden="true" className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
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
  return <div className="balance"><span>Баланс</span><strong>{formatCas(displayed)}</strong></div>;
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
    <span>{children}</span>
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
  return <div className="number-row" aria-label={`Числа: ${values.join(", ")}`}>
    {values.map((value, index) => {
      const won = winning?.includes(value) ?? false;
      return <span className={`number ${won ? "won" : ""} ${animate && won ? "animate-win" : ""}`} key={value} style={{ "--number-index": index } as CSSProperties}>{value}</span>;
    })}
  </div>;
}

export function StatusBadge({ active }: { active: boolean }) {
  return <span className={`status ${active ? "active" : "complete"}`}><i />{active ? "Активен" : "Завершён"}</span>;
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
    <strong>{title}</strong>
    <p>{text}</p>
    {action && <button className="empty-action" onClick={action.onClick} type="button">{action.label}<span>→</span></button>}
  </div>;
}

export function Skeleton() {
  return <main className="app-shell skeleton-shell" aria-label="Загружаем K-Loto">
    <div className="skeleton header-skeleton" />
    <div className="skeleton hero-skeleton" />
    <div className="skeleton draw-skeleton" />
    <div className="skeleton title-skeleton" />
    <div className="skeleton card-skeleton" />
    <div className="skeleton card-skeleton short" />
  </main>;
}
