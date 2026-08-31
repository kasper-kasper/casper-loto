import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import { formatCas } from "./format";

export type IconName = "home" | "ticket" | "cart" | "arrow" | "spark" | "close";

export function Icon({ name }: { name: IconName }) {
  const paths: Record<IconName, ReactNode> = {
    home: <><path d="M3.5 10.5 12 3l8.5 7.5" /><path d="M5.5 9.5v10h13v-10M9.5 19.5v-6h5v6" /></>,
    ticket: <><path d="M4 5.5h16v4a2.5 2.5 0 0 0 0 5v4H4v-4a2.5 2.5 0 0 0 0-5z" /><path d="M9 8.5v7M13 8.5h4M13 12h4M13 15.5h3" /></>,
    cart: <><path d="M3 4.5h2l2 10h10.5l2-7H6" /><path d="M9 19.5h.01M17 19.5h.01" /></>,
    arrow: <><path d="m14.5 5-7 7 7 7" /></>,
    spark: <><path d="M12 2.5c.5 4.6 2.9 7 7.5 7.5-4.6.5-7 2.9-7.5 7.5-.5-4.6-2.9-7-7.5-7.5 4.6-.5 7-2.9 7.5-7.5Z" /><path d="M19 16.5c.2 1.8 1.2 2.8 3 3-1.8.2-2.8 1.2-3 3-.2-1.8-1.2-2.8-3-3 1.8-.2 2.8-1.2 3-3Z" /></>,
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
